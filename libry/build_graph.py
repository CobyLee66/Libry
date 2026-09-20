#!/usr/bin/env python3
"""Libry 知识库关联图构建器（可选组件：仅需要在哪端算图就装在哪端）。

基于 fastembed 本地 embedding（BAAI/bge-small-zh-v1.5）+ 结构信号
（wikilink / tag / source）合成 0~1 相关性权重，输出 <data>/graph.json：

- related: 每文档 top-10 相关页面（score >= RELATED_MIN）
- edges:   全图边表（每节点 top-5 且 score >= EDGE_MIN，去重）

graph.json 不入 git：由 publish.sh 构建后经 SSH 直传对端，
对端只读，不需要本脚本的依赖（pip install libry[graph] 才有）。
embedding 向量按内容哈希缓存在 <data>/embeddings.json（不入库），增量重算。
打分阶段全部向量化：wikilink/tag/source 信号预计算为 n×n 矩阵。

用法：
    libry graph [--full] [--sample 20] [--root VAULT]
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import get_config
from .indexer import normalize_key

MODEL_NAME = "BAAI/bge-small-zh-v1.5"
EMB_TEXT_CHARS = 1500      # 每文档参与 embedding 的正文截断长度
W_EMB, W_LINK, W_TAG, W_SRC = 0.50, 0.30, 0.15, 0.05  # 打分权重
RELATED_TOP, RELATED_MIN = 10, 0.30   # 每文档相关页面：条数 / 最低分
EDGE_TOP, EDGE_MIN = 5, 0.40          # 全图边：每节点条数 / 最低分


def content_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def emb_text(doc: dict, content: str) -> str:
    parts = [doc["title"]]
    if doc.get("summary"):
        parts.append(doc["summary"])
    parts.append((content or "")[:EMB_TEXT_CHARS])
    return "\n".join(parts)


def load_embeddings(docs, contents, full: bool, emb_cache_path: Path):
    """按内容哈希增量计算/复用 embedding，返回 {file: np.ndarray}。"""
    import numpy as np

    cache = {}
    if not full and emb_cache_path.exists():
        try:
            cache = json.loads(emb_cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            cache = {}
    if cache.get("_model") != MODEL_NAME:
        cache = {}

    texts = {d["file"]: emb_text(d, contents.get(d["file"]) or d.get("content") or "")
             for d in docs}
    hashes = {f: content_hash(t) for f, t in texts.items()}
    todo = [f for f in texts
            if cache.get(f, {}).get("hash") != hashes[f]]

    vectors = {}
    for f, entry in cache.items():
        if f != "_model" and f in hashes and entry.get("hash") == hashes[f]:
            vectors[f] = np.array(entry["vector"], dtype=np.float32)

    if todo:
        from fastembed import TextEmbedding
        model = TextEmbedding(model_name=MODEL_NAME)
        print(f"embedding 计算: {len(todo)} 篇（缓存命中 {len(vectors)} 篇）…")
        for f, vec in zip(todo, model.embed([texts[f] for f in todo])):
            vectors[f] = np.array(vec, dtype=np.float32)
    else:
        print(f"embedding 全部命中缓存（{len(vectors)} 篇）")

    out = {"_model": MODEL_NAME}
    for f, vec in vectors.items():
        out[f] = {"hash": hashes[f], "vector": [round(float(x), 6) for x in vec]}
    emb_cache_path.write_text(json.dumps(out), encoding="utf-8")
    return vectors


def _jaccard_matrix(sets_list):
    """两两 Jaccard 相似度矩阵（one-hot 矩阵乘法，替代逐对集合运算）。"""
    import numpy as np

    n = len(sets_list)
    vocab = {}
    for s in sets_list:
        for t in s:
            if t not in vocab:
                vocab[t] = len(vocab)
    if not vocab:
        return np.zeros((n, n), dtype=np.float64)
    m = np.zeros((n, len(vocab)), dtype=np.float64)
    for i, s in enumerate(sets_list):
        for t in s:
            m[i, vocab[t]] = 1.0
    inter = m @ m.T
    sizes = np.array([len(s) for s in sets_list], dtype=np.float64)
    union = sizes[:, None] + sizes[None, :] - inter
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(union > 0, inter / union, 0.0)


def build_graph(docs, vectors):
    import numpy as np

    files = [d["file"] for d in docs]
    n = len(files)
    pos = {f: i for i, f in enumerate(files)}

    # wikilink 解析键 → file（标题与文件名双向注册，复用 indexer 的归一化）
    key2file = {}
    for d in docs:
        key2file.setdefault(normalize_key(d["title"]), d["file"])
        key2file.setdefault(normalize_key(Path(d["file"]).stem), d["file"])

    mat = np.stack([vectors[f] for f in files])  # float32，bge 输出已归一化
    sim = mat @ mat.T
    np.fill_diagonal(sim, 0.0)
    sim = sim.astype(np.float64)

    # 结构信号预计算（归一化只做一次，替代逐对正则 + 线性扫描）
    link = np.zeros((n, n), dtype=np.float64)
    for d in docs:
        i = pos[d["file"]]
        for w in d["wikilinks"]:
            j = pos.get(key2file.get(normalize_key(w)))
            if j is not None and j != i:
                link[i, j] = 1.0
    link = np.maximum(link, link.T)  # a→b 或 b→a 记为有边

    tag_jac = _jaccard_matrix([set(d["tags"]) for d in docs])
    src_jac = _jaccard_matrix([set(d.get("sources") or []) for d in docs])

    scores = (W_EMB * np.maximum(sim, 0.0) + W_LINK * link
              + W_TAG * tag_jac + W_SRC * src_jac)
    np.fill_diagonal(scores, 0.0)
    scores = np.round(scores, 4)

    related = {}
    for i, f in enumerate(files):
        order = np.argsort(-scores[i])[:RELATED_TOP]
        related[f] = [{"file": files[j], "score": float(scores[i, j])}
                      for j in order if scores[i, j] >= RELATED_MIN]

    edge_set = {}
    for i, f in enumerate(files):
        order = np.argsort(-scores[i])[:EDGE_TOP]
        for j in order:
            if scores[i, j] >= EDGE_MIN:
                key = tuple(sorted((f, files[j])))
                edge_set[key] = max(edge_set.get(key, 0.0), float(scores[i, j]))
    edges = [[a, b, round(w, 4)] for (a, b), w in
             sorted(edge_set.items(), key=lambda kv: -kv[1])]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL_NAME,
        "weights": {"emb": W_EMB, "link": W_LINK, "tag": W_TAG, "source": W_SRC},
        "doc_count": n,
        "related": related,
        "edges": edges,
    }


def print_stats(graph, docs, graph_path: Path):
    related = graph["related"]
    edges = graph["edges"]
    title = {d["file"]: d["title"] for d in docs}
    counts = [len(v) for v in related.values()]
    lonely = sum(1 for c in counts if c < 3)
    print(f"graph.json 已生成: {graph_path}")
    print(f"条目: {graph['doc_count']}  边: {len(edges)}  "
          f"平均相关页: {sum(counts) / max(len(counts), 1):.1f}  孤立(<3 邻居): {lonely}")
    return title


def print_samples(graph, title, k):
    print(f"\n高分样例 top {k}:")
    for a, b, w in graph["edges"][:k]:
        print(f"  {w:.2f}  {title.get(a, a)}  <->  {title.get(b, b)}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="libry graph")
    ap.add_argument("--full", action="store_true", help="忽略 embedding 缓存全量重算")
    ap.add_argument("--sample", type=int, default=10, help="打印高分关联样例数")
    ap.add_argument("--root", default=None, help="vault 根目录（默认 KB_ROOT/cwd）")
    args = ap.parse_args(argv)

    cfg = get_config(args.root)
    if not cfg.index_path.exists():
        print("index.json 不存在，先运行 libry index", file=sys.stderr)
        return 1
    index = json.loads(cfg.index_path.read_text(encoding="utf-8"))
    docs = index["docs"]

    contents = {}
    if cfg.content_path.exists():
        try:
            contents = json.loads(cfg.content_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            contents = {}
    if not contents:
        print("提示：content.json 缺失/为空，embedding 退化为标题+摘要", file=sys.stderr)

    try:
        vectors = load_embeddings(docs, contents, args.full,
                                  cfg.data_dir / "embeddings.json")
    except ImportError:
        print("关联图需要可选依赖：pip install 'libry[graph]'（fastembed + numpy）",
              file=sys.stderr)
        return 1
    graph = build_graph(docs, vectors)
    cfg.graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=1),
                              encoding="utf-8")

    title = print_stats(graph, docs, cfg.graph_path)
    print_samples(graph, title, args.sample)
    return 0


if __name__ == "__main__":
    sys.exit(main())
