"""Build offline HTML entrypoints and browser metadata from catalog.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "assets" / "templates"


def main():
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    ids = [item["id"] for item in catalog["templates"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate template IDs")
    (ROOT / "shared").mkdir(exist_ok=True)
    (ROOT / "shared" / "catalog-data.js").write_text(
        "window.ADMIN_TEMPLATES = " + json.dumps(catalog, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )
    for item in catalog["templates"]:
        folder = ROOT / item["id"]
        folder.mkdir(exist_ok=True)
        html = f'''<!doctype html>
<html lang="zh-CN" data-template="{item['id']}" data-mode="{item['mode']}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{item['name']} · 后台风格模板</title>
<link rel="stylesheet" href="../shared/base.css">
<script src="../shared/catalog-data.js" defer></script><script src="../shared/dashboard.js" defer></script></head>
<body><div id="app"></div><noscript>请启用 JavaScript 查看交互组件。</noscript></body></html>
'''
        (folder / "index.html").write_text(html, encoding="utf-8")
    print(f"Built {len(ids)} offline template entrypoints")


if __name__ == "__main__":
    main()
