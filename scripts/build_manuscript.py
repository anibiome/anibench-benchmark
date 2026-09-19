"""Reproduce AniBench's manuscript, synthetic figures and numerical audit.

Requires the paper extra. No participant data or network access is used. Figures
are derived from a declared Gaussian model and the canonical geometry evaluator.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import tempfile
from functools import partial
from importlib.metadata import version
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)

from anibench.collection_ingest import import_collection_tables
from anibench.collection_v1 import profile_collection
from anibench.explorer import build_explorer_demo

ROOT = Path(__file__).resolve().parents[1]
INK, BLUE, MUTED = "#172234", "#2259C9", "#536273"
WIDTH = 468


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def figures(folder: Path) -> dict:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.labelcolor": INK, "text.color": INK,
                         "svg.hashsalt": "anibench-paper-v1", "savefig.facecolor": "white"})
    n = np.arange(1, 17)
    curves = {"different_coordinates": n / 2,
              "independent_repeats": np.log2(1 + n) / 2,
              "copied_observation": np.full(n.shape, 0.5)}
    fig, ax = plt.subplots(figsize=(6.5, 3.4), layout="constrained")
    for key, label, color, style in [
        ("different_coordinates", "Different target coordinates", BLUE, "-"),
        ("independent_repeats", "Independent repeats of one coordinate", "#127B6C", "-"),
        ("copied_observation", "Copies of the same observation", "#6D7585", "--"),
    ]:
        ax.plot(n, curves[key], label=label, color=color, linestyle=style, linewidth=2)
    ax.set(xlabel="Recorded scalar observations", ylabel="Information about the target (bits)",
           xlim=(1, 16), ylim=(0, 8.4), xticks=[1, 4, 8, 12, 16])
    ax.grid(axis="y", alpha=0.16)
    ax.legend(frameon=False, loc="upper left", fontsize=8.4)
    for ext in ("png", "svg"):
        fig.savefig(folder / f"figure-1-information.{ext}", dpi=240, metadata={"Date": None} if ext == "svg" else {})
    plt.close(fig)
    demo = build_explorer_demo(ROOT)
    families = {f["family_id"]: f for f in demo["comparison"]["families"]}

    def metric(family: str, key: str) -> list[float]:
        rows = sorted(families[family]["protocol_vectors"], key=lambda r: r["protocol_id"])
        return [next(o["value"] for o in row["objectives"] if o["metric_id"] == key) for row in rows]

    values = {
        "intensive_rank": metric("intensive", "effective_rank"),
        "intensive_log10_contraction": metric("intensive", "maximum_joint_bundle_log10_contraction"),
        "extensive_log10_contraction": metric("extensive", "retained_log10_contraction"),
        "median_span": metric("longitudinal", "participant_weighted_median_span"),
    }
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 3.2), layout="constrained")
    for ax, key, title, label in [
        (axes[0], "intensive_log10_contraction", "A  Intensive capacity", "Joint-bundle log10 contraction"),
        (axes[1], "median_span", "B  Observed duration", "Median span (protocol time units)"),
    ]:
        bars = ax.bar(["Deeper\nobservations", "Longer\nfollow-up"], values[key], color=[BLUE, "#127B6C"], width=0.6)
        ax.set_title(title, loc="left", fontsize=10, pad=12)
        ax.set_ylabel(label, fontsize=9)
        ax.set_ylim(0, max(values[key]) * 1.27)
        ax.bar_label(bars, labels=[f"{v:.3f}" if v < 1 else f"{v:g}" for v in values[key]], padding=5, fontsize=9)
        ax.grid(axis="y", alpha=0.14)
        ax.set_axisbelow(True)
    for ext in ("png", "svg"):
        fig.savefig(folder / f"figure-2-capacity.{ext}", dpi=240, metadata={"Date": None} if ext == "svg" else {})
    plt.close(fig)
    mapping_path = ROOT / "examples/collection/table-map.json"
    manifest, _ = import_collection_tables(json.loads(mapping_path.read_text()), base=mapping_path.parent)
    profile = profile_collection(manifest)
    return {"schema_version": "anibench.paper-replay.v1", "illustrative_only": True,
            "gaussian_model": {"prior_covariance": "identity_16", "noise_variance": 1,
                               "observations": n.tolist(), "information_bits": {k: v.tolist() for k, v in curves.items()}},
            "geometry_values": values, "geometry_demo": demo, "collection_profile": profile}


EQUATION_SOURCE_SHA256 = ['05a794ce57af247fa3881e0771ff98cb90e8565dfd5902506a19869a1392c324', '93385d977ba98a66f58ef955ff7fc32e2c4ddb398fdf3a91eada275f000f0e24', 'de0b0c6abe38c1e9653d4567a59e2162b6b3dd662d74b352ac94c56d42b53b17', '08da69323bd0d9e721f361e44ec433269b9a52ff8e6eab581701969b17bd13ca', 'f5fed22d40a5f624fef9c7bdd9d9c8ab721dd1b8aa1e8bd91f6f82dd38ee9e07', '7fafa9cda27ea6765d3e05ef4380593c9e241ee707793a0716de719fdb65ab5e', 'ad709ce127c6dc1e99c33ab2da0c5f90babaf1837baa119bb83589c159c6b053']

EQUATIONS = [
    [r"dz_i(t)=f_\theta(z_i(t),u_i(t),c_i(t))\,dt+G_\theta(z_i(t),u_i(t),c_i(t))\,dW_i(t)",
     r"y_{ij}(t)=h_j(z_i(t),s_{ij},b_{ij})+\epsilon_{ij}(t)"],
    [r"N_m=|\{i\in R:\exists e,\ A(i,e,m)\ne\varnothing\}|",
     r"E_m=|\{(i,e):A(i,e,m)\ne\varnothing\}|,\qquad C_m=\sum_{i,e}|A(i,e,m)|"],
    [r"D_{im}=\left|\bigcup_e A(i,e,m)\right|"],
    [r"J_{mn}=|\{(i,e): A(i,e,m)\ne\varnothing\ \wedge\ A(i,e,n)\ne\varnothing\}|"],
    [r"F=A^T R^{-1} A,\qquad P_{\mathrm{post}}=(P_0^{-1}+F)^{-1}"],
    [r"\mathcal{I}(\theta;y)=\frac{1}{2}\log\frac{\det P_0}{\det P_{\mathrm{post}}}",
     r"=\frac{1}{2}\log\det(I+P_0^{1/2}FP_0^{1/2})=\frac{1}{2}\sum_k\log(1+\lambda_k)"],
    [r"r=\max_{c\ne0}\frac{c^T\Sigma_{\mathrm{trial}}c}{c^T\Sigma_{\mathrm{reference}}c}",
     r"=\lambda_{\max}(\Sigma_{\mathrm{reference}}^{-1/2}\Sigma_{\mathrm{trial}}\Sigma_{\mathrm{reference}}^{-1/2})"],
]


def equation(index: int, folder: Path) -> Image:
    lines = EQUATIONS[index]
    height = 0.30 * len(lines) + 0.16
    fig = plt.figure(figsize=(6.5, height))
    for i, line in enumerate(lines):
        fig.text(0.04, 1 - (i + 0.6) / len(lines), f"${line}$", fontsize=10.5, va="center")
    path = folder / f"equation-{index + 1}.png"
    fig.savefig(path, dpi=280, transparent=True)
    plt.close(fig)
    return Image(BytesIO(path.read_bytes()), width=WIDTH, height=height * 72)


def inline(text: str) -> str:
    text = text.replace("–", "-").replace("—", "-").replace("‑", "-")
    text = html.escape(text, quote=False)
    def link(match):
        label, url = match.groups()
        if not url.startswith("https://"):
            url = urljoin("https://github.com/anibiome/anibench-benchmark/blob/main/paper/", url)
        return f'<a href="{html.escape(url, quote=True)}" color="{BLUE}">{label}</a>'
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, text)
    text = re.sub(r"&lt;(https://[^ ]+?)&gt;", lambda m: f'<a href="{m[1]}" color="{BLUE}">{m[1]}</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Typeset only the manuscript's named mathematical symbols; leave commands
    # and identifiers intact by applying this before restoring code spans.
    spans = []
    def code(match):
        spans.append(match[1])
        return f"CODEPLACEHOLDER{len(spans) - 1}END"
    text = re.sub(r"`([^`]+)`", code, text)
    text = re.sub(r"\b([zyNEDCJPLUHbc])_([a-z0-9]{1,2})\b", r"\1<sub>\2</sub>", text)
    text = text.replace("lambda_k", "λ<sub>k</sub>").replace("theta", "θ").replace("epsilon", "ε")
    text = text.replace("mu_0", "μ<sub>0</sub>").replace("Personalized/sequential", "Personalized / sequential")
    text = text.replace("Phi", "Φ").replace("^T", "<super>T</super>").replace("^{-1}", "<super>-1</super>")
    text = text.replace("log10", "log<sub>10</sub>").replace("log2", "log<sub>2</sub>")
    for index, value in enumerate(spans):
        text = text.replace(f"CODEPLACEHOLDER{index}END", f'<font name="Mono" size="8.5">{value}</font>')
    return text


def styles():
    for name, family, weight, style in [
        ("Body", "DejaVu Serif", "normal", "normal"),
        ("BodyBold", "DejaVu Serif", "bold", "normal"),
        ("BodyItalic", "DejaVu Serif", "normal", "italic"),
        ("Sans", "DejaVu Sans", "normal", "normal"),
        ("SansBold", "DejaVu Sans", "bold", "normal"),
        ("Mono", "DejaVu Sans Mono", "normal", "normal"),
    ]:
        path = font_manager.findfont(font_manager.FontProperties(family=family, weight=weight, style=style))
        pdfmetrics.registerFont(TTFont(name, path))
    pdfmetrics.registerFontFamily("Body", normal="Body", bold="BodyBold", italic="BodyItalic", boldItalic="BodyBold")
    pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="SansBold", italic="Sans", boldItalic="SansBold")
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("PaperBody", fontName="Body", fontSize=10, leading=14.2,
                         textColor=colors.HexColor(INK), spaceAfter=7, allowWidows=0, allowOrphans=0))
    s.add(ParagraphStyle("PaperTitle", fontName="SansBold", fontSize=24, leading=29,
                         textColor=colors.HexColor(INK), spaceAfter=21))
    s.add(ParagraphStyle("Section", fontName="SansBold", fontSize=13, leading=17,
                         textColor=colors.HexColor(INK), spaceBefore=14, spaceAfter=8, keepWithNext=True))
    s.add(ParagraphStyle("Subsection", parent=s["Section"], fontSize=10.7, leading=15, spaceBefore=10))
    s.add(ParagraphStyle("Caption", fontName="Sans", fontSize=8.4, leading=11.6,
                         textColor=colors.HexColor(MUTED), spaceAfter=12))
    s.add(ParagraphStyle("Cell", fontName="Sans", fontSize=8.2, leading=11, textColor=colors.HexColor(INK)))
    s.add(ParagraphStyle("CodeBlock", fontName="Mono", fontSize=8, leading=11,
                         backColor=colors.HexColor("#F2F5F8"), borderPadding=10, spaceBefore=6, spaceAfter=12))
    s.add(ParagraphStyle("Reference", parent=s["PaperBody"], fontSize=8.5, leading=11.5, spaceAfter=4))
    return s


def _build(out: Path) -> dict:
    out = out.resolve()
    if out.exists():
        raise ValueError("Output PDF must be a new path; preserve previously reviewed versions")
    out.parent.mkdir(parents=True, exist_ok=True)
    assets = out.parent / (out.stem + "-assets")
    assets.mkdir(exist_ok=False)
    audit = figures(assets)
    source = ROOT / "paper/AniBench_open_benchmark.md"
    text = source.read_text()
    source_equations = re.findall(r"\\\[(.*?)\\\]", text, re.DOTALL)
    if [hashlib.sha256(b.encode()).hexdigest() for b in source_equations] != EQUATION_SOURCE_SHA256:
        raise ValueError("Equation source changed; review typesetting mappings before publication")
    for value in audit["geometry_values"]["intensive_log10_contraction"] + audit["geometry_values"]["extensive_log10_contraction"]:
        if f"{value:.6f}" not in text:
            raise ValueError("Manuscript numerical table differs from the evaluator; reconcile before publication")
    style = styles()
    story = []
    lines = text.splitlines()
    i, eq, refs = 0, 0, False
    captions = {
        1: "Figure 1. Equal observation counts need not carry equal information. All curves use the same 16-coordinate Gaussian target and prior. Independent repeats reduce noise about one direction; different coordinates resolve more directions; exact copies add nothing. These are model-derived quantities, not real-study estimates.",
        2: "Figure 2. Different synthetic designs lead on different native quantities. The deeper design provides greater per-event contraction; the longer design has greater temporal span. Separate axes retain their units. Values come directly from the canonical evaluator; the assumed model is illustrative.",
    }
    def add_figure(number):
        name = "figure-1-information.png" if number == 1 else "figure-2-capacity.png"
        h = 244.8 if number == 1 else 230.4
        story.append(KeepTogether([Spacer(1, 10), Image(BytesIO((assets / name).read_bytes()), WIDTH, h),
                                  Spacer(1, 8), Paragraph(captions[number], style["Caption"])]))

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), style["PaperTitle"]))
            i += 1
        elif line.startswith("**Bruno Balen"):
            story.append(Paragraph("Bruno Balen<br/>ANI Biome PBC<br/>" + html.escape(lines[i + 2].strip()), style["Caption"]))
            i += 3
        elif line.startswith("##"):
            if line.startswith("## 1."):
                story.append(PageBreak())
            if line.startswith("### 6.3"):
                add_figure(2)
            if line.startswith("### 4.2"):
                add_figure(1)
            if line == "## References":
                refs = True
            story.append(Paragraph(inline(line.lstrip("# ")), style["Subsection" if line.startswith("###") else "Section"]))
            i += 1
        elif line == r"\[":
            while i < len(lines) and lines[i].strip() != r"\]":
                i += 1
            story.extend([equation(eq, assets), Spacer(1, 5)])
            eq += 1
            i += 1
        elif line.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            story.append(XPreformatted(html.escape("\n".join(block)), style["CodeBlock"]))
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                fields = [s.strip() for s in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch("[: -]+", s) for s in fields):
                    rows.append([Paragraph(inline(v), style["Cell"]) for v in fields])
                i += 1
            widths = [95, 170, 203] if "Family" in line else ([268, 100, 100] if "Native quantity" in line else [198, 82, 188])
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign=TA_LEFT)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F8")),
                ("LINEABOVE", (0, 0), (-1, 0), 0.8, colors.HexColor(INK)),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor(MUTED)),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor(MUTED)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.append(KeepTogether([table, Spacer(1, 12)]))
        else:
            block = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "```", "\\[")):
                if re.match(r"\d+\. ", lines[i]):
                    break
                block.append(lines[i].strip())
                i += 1
            prose = " ".join(block)
            paragraph = Paragraph(inline(prose), style["Reference" if refs else "PaperBody"])
            # Keep introductory lines with the equation, table or code they introduce.
            if prose.endswith(":"):
                paragraph.keepWithNext = True
            story.append(paragraph)
    if eq != len(EQUATIONS):
        raise ValueError("Equation mapping must match the manuscript")

    def page(c, doc):
        c.saveState()
        c.setStrokeColor(colors.HexColor("#D5DDE8"))
        c.line(72, 748, 540, 748)
        c.setFont("Sans", 7.5)
        c.setFillColor(colors.HexColor(MUTED))
        c.drawString(72, 759, "ANIBENCH  /  BIOLOGICAL LEARNING CAPACITY")
        c.drawRightString(540, 759, "Research manuscript")
        c.drawString(72, 35, "github.com/anibiome/anibench-benchmark")
        c.drawRightString(540, 35, str(doc.page))
        c.restoreState()

    doc = SimpleDocTemplate(str(out), pagesize=(612, 792), leftMargin=72, rightMargin=72,
                            topMargin=62, bottomMargin=57, title=text.splitlines()[0][2:],
                            author="Bruno Balen; ANI Biome PBC", invariant=1)
    doc.build(story, onFirstPage=page, onLaterPages=page, canvasmaker=partial(canvas.Canvas, invariant=1))
    audit["source_sha256"] = sha(source)
    audit["builder_sha256"] = sha(Path(__file__))
    audit["pdf_sha256"] = sha(out)
    audit["dependencies"] = {p: version(p) for p in ["anibench", "numpy", "matplotlib", "reportlab", "jsonschema"]}
    audit["source_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    audit["working_tree_clean"] = not bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    audit["assets"] = {p.name: sha(p) for p in sorted(assets.iterdir())}
    (assets / "replay.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    return {"pdf": str(out), "pdf_sha256": audit["pdf_sha256"], "replay": str(assets / "replay.json")}


def build(out: Path) -> dict:
    """Build in private temporary staging and publish only complete artifacts."""
    out = out.resolve()
    final_assets = out.parent / (out.stem + "-assets")
    if out.exists() or final_assets.exists():
        raise ValueError("Output PDF and asset directory must be new paths")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".anibench-paper-", dir=out.parent) as temporary:
        staged = Path(temporary) / out.name
        result = _build(staged)
        staged.replace(out)
        (staged.parent / final_assets.name).replace(final_assets)
    return {**result, "pdf": str(out), "replay": str(final_assets / "replay.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    print(json.dumps(build(parser.parse_args().out), indent=2))
