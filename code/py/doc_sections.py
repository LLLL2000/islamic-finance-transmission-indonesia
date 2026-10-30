"""Convert the paper's Markdown sections into Docs-ready Markdown, one file per doc section.

Run from the project root:  python -I code/py/doc_sections.py <out_dir> [<blob_map.json>]
- display math ($$ ... $$) becomes a ```latex block; inline math becomes plain Unicode text;
- hard-wrapped paragraphs and list items are unwrapped;
- figure links become blob/<id> references when a blob map {"fig1a_islamic_share.png": "blob/..."} is given.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import assemble_paper as ap  # noqa: E402

INLINE = {
    r"$2.80 \times \text{s.e.}$": "2.80 × s.e.", "$X$": "X", "$[t-1, t+h]$": "[t−1, t+h]",
    r"$\alpha_{s,b}$": "α_{s,b}", r"$\alpha_{s,t}$": "α_{s,t}", r"$\beta$": "β", r"$\beta_h$": "β_h",
    r"$\beta_{12} = -0.34$": "β₁₂ = −0.34", r"$\beta_{12} = -1.0$": "β₁₂ = −1.0", r"$\beta_{12} = -1.6$": "β₁₂ = −1.6",
    r"$\beta_{12}$": "β₁₂", r"$\theta$": "θ", r"$\theta_h$": "θ_h", r"$\theta_{12}$": "θ₁₂",
    r"$\varepsilon_t$": "ε_t", r"$b \in \{\text{ISL}, \text{CONV}\}$": "b ∈ {ISL, CONV}",
    r"$h = 0, \dots, 24$": "h = 0, …, 24", "$h$": "h", "$h+2$": "h+2", "$h=0$": "h = 0", "$h=12$": "h = 12",
    "$h=24$": "h = 24", "$s$": "s", "$t$": "t", "$y_{s,b,t}$": "y_{s,b,t}", r"$|\beta_{12}| \le 4.3$": "|β₁₂| ≤ 4.3",
    "$|t| = 3.3$": "|t| = 3.3", "$|t| > 1.3$": "|t| > 1.3",
}
NEWBLOCK = re.compile(r"^(\s*([-*+]|\d+\.)\s|\||#|!\[|```|>|\*Figure|\$\$)")


def convert(md, blobs):
    md = re.sub(r"\$\$\n(.*?)\n\$\$", lambda m: "```latex\n" + m.group(1).strip() + "\n```", md, flags=re.S)
    for k, v in INLINE.items():
        md = md.replace(k, v)
    left = re.findall(r"\$[^$\n]+\$", md)
    if left:
        raise SystemExit(f"unconverted inline math: {left}")
    for fn, bid in blobs.items():
        md = md.replace(f"({ap.FIGDIR}/{fn})", f"({bid})")
    out, fence = [], False
    for line in md.split("\n"):
        if line.startswith("```"):
            fence = not fence
            out.append(line)
            continue
        if fence or not out or not line.strip() or not out[-1].strip() or NEWBLOCK.match(line) \
                or out[-1].startswith(("|", "#", "```", "![")) or out[-1].rstrip().endswith("```"):
            out.append(line)
        else:
            out[-1] = out[-1].rstrip() + " " + line.strip()
    return "\n".join(out)


def main():
    outdir = pathlib.Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    blobs = json.loads(pathlib.Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else {}
    sec = {}
    t = (ap.SEC / "00_title_abstract.md").read_text(encoding="utf-8")
    t = t[t.index("**Abstract.**"):].replace("**Abstract.** ", "", 1)
    sec["s0"] = "## Abstract\n\n" + t.strip()
    for i, name in enumerate(ap.ORDER[1:], start=1):
        sec[f"s{i}"] = ap.insert_figs(name, (ap.SEC / f"{name}.md").read_text(encoding="utf-8").strip())
    tabs = (ap.ROOT / "output" / "tables" / "paper_tables.md").read_text(encoding="utf-8")
    sec["s11"] = "## Tables\n\n" + re.sub(r"^## Table", "### Table", tabs, flags=re.M).strip()
    sec["s12"] = (ap.SEC / "90_appendix.md").read_text(encoding="utf-8").strip()
    for k, v in sec.items():
        (outdir / f"{k}.md").write_text(convert(v, blobs) + "\n", encoding="utf-8")
    print("wrote", len(sec), "sections to", outdir)


if __name__ == "__main__":
    main()
