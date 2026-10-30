"""Render paper/working_paper.md to paper/working_paper.pdf.

Run from the project root:  python -I code/py/build_pdf.py
No LaTeX or pandoc is needed: the Markdown is turned into an HTML page (marked.js for Markdown, KaTeX for
the maths, both from cdnjs), which headless Microsoft Edge prints to PDF. Maths is lifted out before the
Markdown pass so that underscores and backslashes reach KaTeX intact.
"""
import html
import json
import pathlib
import re
import subprocess
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper"
EDGE = r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"

CSS = """
@page { size: A4; margin: 22mm 20mm 22mm 20mm; }
body { font-family: 'Source Serif 4', Georgia, 'Times New Roman', serif; font-size: 10.5pt; line-height: 1.45;
       color: #111; max-width: 170mm; margin: 0 auto; }
h1 { font-size: 17pt; line-height: 1.25; margin: 0 0 6pt; }
h2 { font-size: 13pt; margin: 18pt 0 6pt; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 12pt 0 4pt; page-break-after: avoid; }
p { margin: 0 0 7pt; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 7pt 0; padding-left: 18pt; }
li { margin-bottom: 2pt; }
img { display: block; max-width: 100%; margin: 8pt auto 2pt; page-break-inside: avoid; }
p.cap { font-size: 9pt; font-style: italic; color: #333; text-align: left; }
table { border-collapse: collapse; width: 100%; font-size: 7.4pt; line-height: 1.25; margin: 4pt 0 10pt;
        page-break-inside: auto; }
th, td { border-bottom: 0.4pt solid #bbb; padding: 2pt 3pt; text-align: left; vertical-align: top; }
th { border-bottom: 0.8pt solid #333; font-weight: 600; }
tr { page-break-inside: avoid; }
code { font-size: 9pt; }
.katex-display { margin: 8pt 0; overflow: visible; }
.byline { color: #444; margin-bottom: 12pt; }
"""

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css">
<style>{css}</style></head>
<body><div id="out"></div>
<script id="md" type="text/plain">{md}</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js"></script>
<script>
const MATH = {math};
const src = document.getElementById('md').textContent;
let h = marked.parse(src);
h = h.replace(/MATHTOKEN(\\d+)X/g, (m, i) => {{
  const e = MATH[+i];
  try {{ return katex.renderToString(e.tex, {{displayMode: e.display, throwOnError: false}}); }}
  catch (err) {{ return e.tex; }}
}});
document.getElementById('out').innerHTML = h;
document.title = "done";
</script></body></html>"""


def main():
    md = (PAPER / "working_paper.md").read_text(encoding="utf-8")
    math = []

    def keep(tex, display):
        math.append({"tex": tex.strip(), "display": display})
        return f"MATHTOKEN{len(math) - 1}X"

    md = re.sub(r"\$\$(.+?)\$\$", lambda m: "\n\n" + keep(m.group(1), True) + "\n\n", md, flags=re.S)
    md = re.sub(r"\$([^$\n]+?)\$", lambda m: keep(m.group(1), False), md)
    md = re.sub(r"^\*(Figure [0-9A-B]+\..*)\*$", lambda m: f'<p class="cap">{html.escape(m.group(1))}</p>', md, flags=re.M)
    title = md.splitlines()[0].lstrip("# ").strip()
    page = TEMPLATE.format(title=html.escape(title), css=CSS, md=md.replace("</script", "<\\/script"),
                           math=json.dumps(math))
    out_html = PAPER / "working_paper_print.html"
    out_html.write_text(page, encoding="utf-8")
    out_pdf = PAPER / "working_paper.pdf"
    out_pdf.unlink(missing_ok=True)   # Edge does not reliably overwrite an existing file
    profile = tempfile.mkdtemp(prefix="edge_pdf_")   # own profile, so a running Edge does not swallow the job
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={profile}",
                    "--virtual-time-budget=30000", "--run-all-compositor-stages-before-draw",
                    f"--print-to-pdf={out_pdf}", out_html.as_uri()], check=True, timeout=180)
    for _ in range(240):   # the Edge launcher can return before the renderer has written the file
        if out_pdf.exists() and out_pdf.stat().st_size > 0:
            time.sleep(2)
            break
        time.sleep(0.5)
    print("wrote", out_pdf, out_pdf.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
