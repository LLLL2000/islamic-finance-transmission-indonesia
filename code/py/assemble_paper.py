"""Assemble paper/working_paper.md from paper/sections/*.md, output/tables/paper_tables.md and the figures.

Run from the project root:  python -I code/py/assemble_paper.py
Figures are inserted after the anchor paragraph listed in FIGS; tables go in a 'Tables' section after the
references, and the appendix comes last.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
SEC = ROOT / "paper" / "sections"
FIGDIR = "../output/figures"

ORDER = ["00_title_abstract", "01_intro", "02_background", "03_data", "04_design", "05_results_credit",
         "06_robustness", "07_mechanisms", "08_sovereign", "09_discussion_conclusion", "99_references"]

# (section file, text that ends the anchor block, figure label, file, caption)
FIGS = [
    ("02_background", "- In manufacturing and mining, they supply about 3 percent.", "Figure 1A", "fig1a_islamic_share.png",
     "Islamic share of commercial-bank credit, 2009-2025 (H9 panel, all sectors)."),
    ("02_background", "- In manufacturing and mining, they supply about 3 percent.", "Figure 1B", "fig1b_sector_shares.png",
     "Islamic share of commercial-bank credit by sector, June 2025 (H15 panel)."),
    ("07_mechanisms", "as Section 5.1 found for market rates.", "Figure 7", "fig7_deposit_passthrough.png",
     "Deposit pricing: BI policy rate, conventional 1-month deposit rate, Islamic 1-month deposit return and their spread."),
    ("07_mechanisms", "and -0.68 (0.35) on 40 months.",
     "Figure 8", "fig8_spread_samples.png", "The 12-month deposit spread across sample variants, per standard deviation of three US shocks."),
    ("08_sovereign", "keeps building to -0.37 pp (s.e. 0.14).",
     "Figure 9", "fig9_sovereign.png", "Non-resident holdings of SUN and SBSN after a US pure monetary policy surprise (daily local projections)."),
]


def insert_figs(name, text):
    # figures sharing an anchor are inserted together, in the order listed
    blocks = {}
    for sec, anchor, label, fn, cap in FIGS:
        if sec == name:
            blocks.setdefault(anchor, []).append(f"![{label}]({FIGDIR}/{fn})\n\n*{label}. {cap}*")
    for anchor, figs in blocks.items():
        # find the end of the block (paragraph or list) that contains the anchor
        i = text.find(anchor)
        if i < 0:
            raise SystemExit(f"anchor not found in {name}: {anchor[:50]!r}")
        j = text.find("\n\n", i + len(anchor))
        j = len(text) if j < 0 else j
        text = text[:j] + "\n\n" + "\n\n".join(figs) + text[j:]
    return text


def main():
    parts = []
    for name in ORDER:
        t = (SEC / f"{name}.md").read_text(encoding="utf-8").strip()
        parts.append(insert_figs(name, t))
    tabs = (ROOT / "output" / "tables" / "paper_tables.md").read_text(encoding="utf-8")
    tabs = re.sub(r"^## Table", "### Table", tabs, flags=re.M).strip()
    parts.append("## Tables\n\n" + tabs)
    parts.append((SEC / "90_appendix.md").read_text(encoding="utf-8").strip())
    out = "\n\n".join(parts) + "\n"
    (ROOT / "paper" / "working_paper.md").write_text(out, encoding="utf-8")
    print("wrote paper/working_paper.md:", len(out.splitlines()), "lines")


if __name__ == "__main__":
    main()
