"""测试夹具：构造临时 vault。"""
import textwrap

import pytest


@pytest.fixture()
def vault(tmp_path, monkeypatch):
    """一个最小可索引的知识库：1 source + 1 concept + 1 archive + index/tags。"""
    monkeypatch.delenv("KB_ROOT", raising=False)
    monkeypatch.delenv("KB_DATA_DIR", raising=False)
    root = tmp_path / "vault"
    (root / "wiki" / "sources").mkdir(parents=True)
    (root / "wiki" / "concepts").mkdir(parents=True)
    (root / "notes").mkdir()
    (root / "libry.toml").write_text(
        'title = "测试库"\ncontent_dirs = ["notes"]\n', encoding="utf-8")
    (root / "index.md").write_text(textwrap.dedent("""\
        # 知识库索引

        ## 来源文档 (Sources)

        - [[Foo Article]] — 一篇讲 foo 的文章

        ## 概念 (Concepts)

        - [[Bar Concept]] — bar 是 foo 的对立面
        """), encoding="utf-8")
    (root / "tags.md").write_text(textwrap.dedent("""\
        ---
        tags: [知识库管理]
        ---

        # Tag 主表

        ## 标准 Tag 全表

        | Tag | 次数 | 说明 |
        |---|---|---|
        | 测试 | 0 | 测试用 |

        ## 分类说明

        ### 其它
        **测试**
        """), encoding="utf-8")
    (root / "wiki" / "sources" / "foo-article.md").write_text(textwrap.dedent("""\
        ---
        tags: [测试]
        sources: ["《Foo》 https://example.com/foo"]
        created: 2026-01-02
        updated: 2026-01-03
        ---

        # Foo Article

        讲 foo 的文章，提到 [[Bar Concept]]。

        > **摘要**：这是一段足够长的摘要文字，用来通过 substantive 检查的门槛要求。

        ## 附录：原文全文

        （略）
        """), encoding="utf-8")
    (root / "wiki" / "concepts" / "bar-concept.md").write_text(textwrap.dedent("""\
        ---
        tags: [测试]
        sources: [foo-article.md]
        created: 2026-01-02
        updated: 2026-01-02
        ---

        # Bar Concept

        bar 是 foo 的对立面，见 [[Foo Article]]。
        """), encoding="utf-8")
    (root / "notes" / "note-1.md").write_text(
        "# 一篇归档笔记\n\n**摘要**：归档目录里的成品文章，type=archive，摘要从正文首段回退提取。\n",
        encoding="utf-8")
    return root


@pytest.fixture()
def env_clean(monkeypatch):
    """清掉可能影响 config 解析的环境变量。"""
    monkeypatch.delenv("KB_ROOT", raising=False)
    monkeypatch.delenv("KB_DATA_DIR", raising=False)
