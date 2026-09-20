"""前端 i18n 字典一致性检查。

约束（约定即测试）：
- 每个 locale 文件以 window.LibryLocales["<code>"] = {...} 注册，对象字面量必须是严格 JSON；
- 所有 locale 的 key 路径集合与 en 完全一致（防漏译，也约束复数对象各语言结构相同）；
- 模板/JS 中静态引用的 t('key') 必须存在于字典（抓漏键/拼写错误）；
- index.html 必须加载 i18n/ 下全部字典文件（新语言文件漏挂 <script> 会静默失效）。
"""
import json
import re
from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent.parent / "libry" / "static"
ASSIGN_RE = re.compile(r'window\.LibryLocales\["([^"]+)"\]\s*=\s*')
USED_KEY_RE = re.compile(r"\bt\('([^']+)'")


def load_locales() -> dict:
    locales = {}
    for f in sorted((STATIC_DIR / "i18n").glob("*.js")):
        if f.name == "core.js":
            continue
        text = f.read_text(encoding="utf-8")
        m = ASSIGN_RE.search(text)
        assert m, f'{f.name} 须以 window.LibryLocales["<code>"] = {{...}} 形式注册'
        locales[m.group(1)] = json.loads(text[m.end():].rstrip().rstrip(";"))
    return locales


def flatten(d: dict, prefix: str = "") -> dict:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def test_locales_exist():
    locales = load_locales()
    assert "zh-CN" in locales
    assert "en" in locales


def test_locale_key_parity():
    flat = {code: flatten(d) for code, d in load_locales().items()}
    base = set(flat["en"])
    for code, keys in flat.items():
        assert set(keys) == base, (
            f"{code} 与 en 的 key 不一致：缺失 {sorted(base - set(keys))}，"
            f"多出 {sorted(set(keys) - base)}")


def test_locale_values_nonempty():
    for code, d in load_locales().items():
        for k, v in flatten(d).items():
            assert isinstance(v, str) and v.strip(), f"{code} 的 {k} 不是非空字符串"


def test_meta_name_present():
    for code, d in load_locales().items():
        assert d.get("_meta", {}).get("name"), f"{code} 缺少 _meta.name（语言切换器显示名）"


def test_used_keys_exist():
    en = load_locales()["en"]
    flat_en = flatten(en)
    used = set()
    for name in ("index.html", "app.js"):
        used.update(USED_KEY_RE.findall((STATIC_DIR / name).read_text(encoding="utf-8")))
    assert used, "未提取到任何 t('key') 引用（正则或文件结构变化？）"
    missing = []
    for k in sorted(used):
        if k.endswith("."):
            # 动态拼接前缀（t('type.' + value)）：前缀必须是字典命名空间
            ns = k[:-1]
            assert isinstance(en.get(ns), dict), f"动态 key 前缀 {ns!r} 不是字典命名空间"
            continue
        if k not in flat_en:
            missing.append(k)
    assert not missing, f"模板/JS 引用了字典中不存在的 key：{missing}"


def test_locale_files_loaded_in_html():
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    for f in (STATIC_DIR / "i18n").glob("*.js"):
        assert f'src="/i18n/{f.name}"' in html, f"index.html 未加载 {f.name}"
