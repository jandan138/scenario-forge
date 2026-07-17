"""Extract the Feishu wiki task-design doc into a self-contained HTML reference.

Re-run to refresh docs/reference/wetlab-task-design.html from the live source:

    python scripts/extract_wetlab_task_design_doc.py

Requires lark-cli with user auth (docs + sheets read scopes). The output HTML is
self-contained: embedded sheet data is rendered as a table and document images
are inlined as base64. Do not hand-edit the output; update via re-extraction.
"""

from __future__ import annotations

import base64
import csv
import html
import io
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

DOC_URL = "https://aicarrier.feishu.cn/wiki/GNGCwR2uAi9dK3k6FT0cX5krnab"
SHEET_TOKEN = "A6cPsrjWbhLS68tgNmzcqdf7nqd"
SHEET_ID = "J1nUiN"
SHEET_RANGE = "A1:J19"
OUT_PATH = Path("docs/reference/wetlab-task-design.html")

ENV = {
    **os.environ,
    "LARKSUITE_CLI_NO_UPDATE_NOTIFIER": "1",
    "LARKSUITE_CLI_NO_SKILLS_NOTIFIER": "1",
}


def run_cli(args: list[str]) -> dict:
    result = subprocess.run(
        ["lark-cli", *args, "--as", "user"],
        capture_output=True,
        text=True,
        env=ENV,
        check=True,
    )
    return json.loads(result.stdout)


def fetch_doc() -> tuple[str, int]:
    data = run_cli(["docs", "+fetch", "--doc", DOC_URL])["data"]["document"]
    return data["content"], data["revision_id"]


def fetch_sheet_rows() -> list[list[str]]:
    data = run_cli(
        [
            "sheets",
            "+csv-get",
            "--spreadsheet-token",
            SHEET_TOKEN,
            "--sheet-id",
            SHEET_ID,
            "--range",
            SHEET_RANGE,
        ]
    )["data"]
    rows = []
    for line in data["annotated_csv"].splitlines(keepends=True):
        pass
    reader = csv.reader(io.StringIO(data["annotated_csv"]))
    for raw in reader:
        if not raw:
            continue
        first = raw[0]
        if first.startswith("[row="):
            raw[0] = first.split("] ", 1)[1] if "] " in first else ""
        rows.append(raw)
    return rows


def download_media(token: str, tmpdir: Path) -> str:
    # lark-cli only accepts cwd-relative --output paths.
    rel = tmpdir.relative_to(Path.cwd())
    run_cli(["docs", "+media-download", "--token", token, "--output", f"{rel}/m"])
    for entry in sorted(tmpdir.glob("m*")):
        mime = "image/jpeg" if entry.suffix in {".jpg", ".jpeg"} else "image/png"
        encoded = base64.b64encode(entry.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    raise RuntimeError(f"media download produced no file for token {token}")


def sheet_table_html(rows: list[list[str]]) -> str:
    parts = ['<table class="sheet"><thead><tr>']
    for cell in rows[0]:
        parts.append(f"<th>{html.escape(cell)}</th>")
    parts.append("</tr></thead><tbody>")
    for row in rows[1:]:
        parts.append("<tr>")
        for cell in row:
            parts.append(f"<td>{html.escape(cell)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


def node_html(node: ET.Element, ctx: dict) -> str:
    tag = node.tag
    inner = "".join(
        html.escape(node.text or "")
        + "".join(node_html(child, ctx) + html.escape(child.tail or "") for child in node)
    )
    if tag == "title":
        return f"<h1 class=\"doc-title\">{inner}</h1>"
    if tag in {"h1", "h2", "h3"}:
        return f"<{tag}>{inner}</{tag}>"
    if tag == "p":
        return f"<p>{inner}</p>" if inner.strip() else ""
    if tag in {"ul", "ol"}:
        return f"<{tag}>{inner}</{tag}>"
    if tag == "li":
        return f"<li>{inner}</li>"
    if tag == "b":
        return f"<strong>{inner}</strong>"
    if tag == "del":
        return f"<del>{inner}</del>"
    if tag == "table":
        return f"<table>{inner}</table>"
    if tag == "thead":
        return f"<thead>{inner}</thead>"
    if tag == "tbody":
        return f"<tbody>{inner}</tbody>"
    if tag == "tr":
        return f"<tr>{inner}</tr>"
    if tag in {"td", "th"}:
        return f"<{tag}>{inner}</{tag}>"
    if tag == "colgroup":
        return ""
    if tag == "img":
        token = node.attrib.get("src") or node.attrib.get("token", "")
        name = node.attrib.get("name", "document image")
        src = ctx["media"].get(token)
        if src is None:
            return f"<p class=\"missing\">[image not downloaded: {html.escape(name)}]</p>"
        return (
            f'<figure><img src="{src}" alt="{html.escape(name)}"/>'
            f"<figcaption>{html.escape(name)}</figcaption></figure>"
        )
    if tag == "sheet":
        return ctx["sheet_html"]
    if tag == "cite":
        doc_id = node.attrib.get("doc-id", "")
        title = node.attrib.get("title", doc_id)
        return (
            f'<p class="cite">Referenced document: '
            f'<a href="https://aicarrier.feishu.cn/docx/{doc_id}">{html.escape(title)}</a>'
            f" (Feishu login required)</p>"
        )
    return inner


CSS = """
body { font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
       max-width: 1080px; margin: 2rem auto; padding: 0 1.5rem; color: #1f2329; line-height: 1.65; }
.doc-title { border-bottom: 2px solid #3370ff; padding-bottom: .4rem; }
.provenance { background: #f5f6f7; border: 1px solid #dee0e3; border-radius: 8px;
              padding: .8rem 1rem; font-size: .9rem; color: #646a73; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .88rem; }
th, td { border: 1px solid #dee0e3; padding: 6px 10px; vertical-align: top; text-align: left; }
thead th { background: #3370ff; color: #fff; }
table.sheet td { white-space: pre-wrap; }
tbody tr:nth-child(even) { background: #f8f9fa; }
del { color: #bbb; }
figure { margin: 1.2rem 0; text-align: center; }
figure img { max-width: 100%; border: 1px solid #dee0e3; border-radius: 6px; }
figcaption { font-size: .8rem; color: #8f959e; margin-top: .3rem; }
.cite { background: #eef3ff; border-left: 3px solid #3370ff; padding: .5rem .8rem; }
"""


def main() -> None:
    content, revision = fetch_doc()
    sheet_rows = fetch_sheet_rows()

    tmpdir = Path.cwd() / ".extract_media_tmp"
    shutil.rmtree(tmpdir, ignore_errors=True)
    tmpdir.mkdir()
    try:
        media = {}
        root = ET.fromstring(f"<root>{content}</root>")
        for img in root.iter("img"):
            token = img.attrib.get("src") or img.attrib.get("token", "")
            if token and token not in media:
                media[token] = download_media(token, tmpdir)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    ctx = {"media": media, "sheet_html": sheet_table_html(sheet_rows)}
    body = "".join(node_html(child, ctx) for child in root)

    provenance = (
        f'<div class="provenance">Source: <a href="{DOC_URL}">{DOC_URL}</a><br/>'
        f"Extracted {date.today().isoformat()} by "
        f"<code>scripts/extract_wetlab_task_design_doc.py</code>; "
        f"Feishu doc revision {revision}. "
        f"External requirements reference — do not edit; refresh by re-running the script.</div>"
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\"/>\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        f"<title>湿实验具身操作评测任务设计</title>\n<style>{CSS}</style>\n</head>\n"
        f"<body>\n{provenance}\n{body}\n</body>\n</html>\n",
        encoding="utf-8",
    )
    size_kb = OUT_PATH.stat().st_size // 1024
    print(f"wrote {OUT_PATH} ({size_kb} KiB, doc revision {revision})")


if __name__ == "__main__":
    main()
