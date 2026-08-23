"""Build docs/memoria.md into a paginated academic PDF.

No dependency this repo doesn't already have access to: `npx marked`
(CommonMark + GFM tables, already resolvable locally -- verified against
this machine's npm cache) converts the Markdown body to HTML, and the
system's installed Chrome (`--headless --print-to-pdf`) renders that HTML
to PDF. Neither pandoc nor a Python markdown/PDF library is required or
installed, and none is added to pyproject.toml for a one-off build step.

Usage:
    uv run python scripts/build_memoria_pdf.py
    # -> reports/memoria.html (inspectable) and reports/memoria.pdf
"""

from __future__ import annotations

import re
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMORIA = ROOT / "docs" / "memoria.md"
OUT_DIR = ROOT / "reports"
HTML_OUT = OUT_DIR / "memoria.html"
PDF_OUT = OUT_DIR / "memoria.pdf"

_CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

_TITLE_FIELDS = ("Autor", "Programa", "Modalidad", "Tutor/a", "Curso académico")

_PRINT_CSS = """
@page {
  size: A4;
  margin: 2.4cm 2.2cm 2.6cm 2.2cm;
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  font-family: "Iowan Old Style", "Palatino Linotype", Georgia,
    "Times New Roman", serif;
  color: #1a1f29;
  font-size: 10.6pt;
  line-height: 1.5;
}
.cover {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  page-break-after: always;
}
.cover .kicker {
  font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 10pt;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #4a5568;
  margin-bottom: 18px;
}
.cover h1 {
  font-size: 22pt;
  line-height: 1.28;
  margin: 0 0 34px;
  max-width: 92%;
  text-wrap: balance;
}
.cover dl {
  font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 11pt;
  display: grid;
  grid-template-columns: auto 1fr;
  column-gap: 14px;
  row-gap: 6px;
}
.cover dt { color: #4a5568; font-weight: 600; }
.cover dd { margin: 0; }

.toc {
  page-break-after: always;
}
.toc h2 {
  font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 10pt;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #4a5568;
  border-bottom: 1px solid #d8dee8;
  padding-bottom: 8px;
  margin-bottom: 18px;
}
.toc ol { list-style: none; padding: 0; margin: 0; counter-reset: item; }
.toc li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 0;
  border-bottom: 1px dotted #d8dee8;
  font-size: 10.5pt;
}
.toc a { color: inherit; text-decoration: none; }

.body-content { }
.body-content h1 {
  font-size: 15pt;
  border-bottom: 2px solid #1a1f29;
  padding-bottom: 6px;
  margin: 0 0 16px;
}
.body-content h2 {
  font-size: 13pt;
  margin: 30px 0 12px;
  padding-top: 6px;
  border-top: 1px solid #d8dee8;
  page-break-before: auto;
}
.body-content h3 { font-size: 11.3pt; margin: 20px 0 8px; }
.body-content h4 { font-size: 10.6pt; margin: 16px 0 6px; font-style: italic; }
.body-content p, .body-content li { orphans: 3; widows: 3; }
.body-content blockquote {
  margin: 12px 0;
  padding: 8px 14px;
  border-left: 3px solid #94a3b8;
  background: #f4f6f9;
  font-size: 9.8pt;
  color: #334155;
}
.body-content code {
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 9pt;
  background: #eef1f6;
  padding: 1px 4px;
  border-radius: 3px;
}
.body-content pre {
  background: #1a1f29;
  color: #e2e8f0;
  padding: 10px 12px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 8.4pt;
  line-height: 1.45;
  page-break-inside: avoid;
}
.body-content pre code { background: none; padding: 0; color: inherit; }
.body-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0;
  font-size: 9.2pt;
  page-break-inside: avoid;
}
.body-content th, .body-content td {
  border: 1px solid #cbd5e1;
  padding: 5px 8px;
  text-align: left;
  vertical-align: top;
}
.body-content th { background: #eef1f6; font-weight: 700; }
.body-content hr { border: none; border-top: 1px solid #d8dee8; margin: 26px 0; }
.body-content a { color: #1f6f6b; word-break: break-word; }
.body-content strong { font-weight: 700; }
.body-content ul, .body-content ol { padding-left: 22px; }
.body-content li { margin: 3px 0; }
"""


def _slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug or "section"


def _extract_title_page(markdown: str) -> tuple[str, dict[str, str]]:
    title_match = re.search(r"^# (.+)$", markdown, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "ERP Agent OS"
    fields: dict[str, str] = {}
    for field in _TITLE_FIELDS:
        pattern = rf"^\*\*{re.escape(field)}:\*\*\s*(.+)$"
        match = re.search(pattern, markdown, re.MULTILINE)
        if match:
            fields[field] = match.group(1).strip()
    return title, fields


def _markdown_to_html(markdown: str) -> str:
    result = subprocess.run(
        ["npx", "--yes", "marked", "--gfm"],
        input=markdown,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT,
        check=False,
        shell=True,  # npx.cmd on Windows requires the shell to resolve
    )
    if result.returncode != 0:
        raise RuntimeError(f"npx marked failed: {result.stderr}")
    return result.stdout


_HEADING_RE = re.compile(r"<h([1-3])>(.*?)</h\1>", re.DOTALL)


def _inject_heading_ids_and_build_toc(
    html: str,
) -> tuple[str, list[tuple[int, str, str]]]:
    toc: list[tuple[int, str, str]] = []
    seen_slugs: dict[str, int] = {}

    def _replace(match: re.Match[str]) -> str:
        level = int(match.group(1))
        text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        slug = _slugify(text)
        count = seen_slugs.get(slug, 0)
        seen_slugs[slug] = count + 1
        if count:
            slug = f"{slug}-{count}"
        if level == 2:
            toc.append((level, text, slug))
        return f'<h{level} id="{slug}">{match.group(2)}</h{level}>'

    return _HEADING_RE.sub(_replace, html), toc


def _find_chrome() -> str:
    for candidate in _CHROME_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    raise RuntimeError(
        "No Chrome/Edge executable found at any known path. "
        "Install Chrome or edit _CHROME_CANDIDATES in this script."
    )


def build() -> None:
    markdown = MEMORIA.read_text(encoding="utf-8")
    title, fields = _extract_title_page(markdown)

    # The H1 and title-page fields are rendered on the cover, not repeated
    # inside the flowing body, so the body starts at "## Resumen".
    body_markdown = markdown[markdown.index("## Resumen") :]
    body_html_raw = _markdown_to_html(body_markdown)
    body_html, toc = _inject_heading_ids_and_build_toc(body_html_raw)

    toc_items = "\n".join(
        f'<li><a href="#{slug}">{text}</a></li>' for _, text, slug in toc
    )
    cover_fields = "\n".join(
        f"<dt>{field}</dt><dd>{value}</dd>" for field, value in fields.items()
    )

    html_doc = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<style>{_PRINT_CSS}</style>
</head>
<body>
<section class="cover">
  <div class="kicker">Trabajo Fin de Máster</div>
  <h1>{title}</h1>
  <dl>{cover_fields}</dl>
</section>
<section class="toc">
  <h2>Índice</h2>
  <ol>{toc_items}</ol>
</section>
<section class="body-content">
{body_html}
</section>
</body>
</html>
"""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    HTML_OUT.write_text(html_doc, encoding="utf-8")
    print(f"HTML written: {HTML_OUT} ({len(html_doc)} bytes, {len(toc)} TOC entries)")

    chrome = _find_chrome()
    html_uri = HTML_OUT.resolve().as_uri()
    result = subprocess.run(
        [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={PDF_OUT.resolve()}",
            html_uri,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not PDF_OUT.exists():
        raise RuntimeError(
            f"Chrome print-to-pdf failed (code {result.returncode}): "
            f"{result.stderr[-2000:]}"
        )
    size_kb = PDF_OUT.stat().st_size / 1024
    print(f"PDF written: {PDF_OUT} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    build()
