# SPDX-FileCopyrightText: 2026 ANI
# SPDX-License-Identifier: Apache-2.0
"""Build the methods paper from Markdown and checked aggregate figure data."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
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

BASE = Path(__file__).resolve().parent
WIDTH = 468
INK = colors.HexColor('#172B32')
BLUE = '#245C83'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inline(value: str) -> str:
    value = value.replace('–', '-').replace('—', '-').replace('‑', '-')
    value = html.escape(value, quote=False)
    value = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                   lambda m: f'<a href="{html.escape(m[2], quote=True)}" color="{BLUE}">{m[1]}</a>', value)
    value = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', value)
    # Same embedded Unicode font keeps mathematical code spans readable.
    return re.sub(r'`([^`]+)`', r'<font color="#245C83">\1</font>', value)


def build(out: Path) -> dict:
    out = out.resolve()
    figures = out.with_name(out.stem + '-figures')
    receipt = out.with_suffix('.receipt.json')
    if out.exists() or figures.exists() or receipt.exists():
        raise ValueError('Use a new output path; existing papers and receipts are preserved')
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(BASE / 'figures/plot.py'), '--out', str(figures)], check=True)

    for name, weight, style in [('Paper', 'normal', 'normal'),
                                ('PaperBold', 'bold', 'normal'),
                                ('PaperItalic', 'normal', 'oblique'),
                                ('PaperBoldItalic', 'bold', 'oblique')]:
        font = font_manager.findfont(font_manager.FontProperties(
            family='DejaVu Sans', weight=weight, style=style))
        pdfmetrics.registerFont(TTFont(name, font))
    pdfmetrics.registerFontFamily('Paper', normal='Paper', bold='PaperBold',
                                 italic='PaperItalic', boldItalic='PaperBoldItalic')
    body = ParagraphStyle('body', fontName='Paper', fontSize=9.3, leading=13.6,
                          textColor=INK, spaceAfter=7, allowWidows=0, allowOrphans=0)
    title = ParagraphStyle('title', parent=body, fontName='PaperBold', fontSize=22,
                           leading=27, spaceAfter=17)
    section = ParagraphStyle('section', parent=body, fontName='PaperBold', fontSize=13,
                             leading=17, spaceBefore=15, spaceAfter=8, keepWithNext=True)
    sub = ParagraphStyle('sub', parent=section, fontSize=10.3, leading=14, spaceBefore=9)
    cell = ParagraphStyle('cell', parent=body, fontSize=8, leading=11, spaceAfter=0)
    caption = ParagraphStyle('caption', parent=body, fontSize=8.3, leading=11.6,
                             textColor=colors.HexColor('#4C6269'), spaceAfter=12)
    code = ParagraphStyle('code', parent=body, fontSize=8, leading=11,
                          backColor=colors.HexColor('#F0F4F6'), borderPadding=6)
    source = BASE / 'AniBench_task_reference.md'
    lines = source.read_text().splitlines()
    story = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith('# '):
            story.append(Paragraph(inline(line[2:]), title)); i += 1
        elif line.startswith('##'):
            if line.startswith(('## 1.', '## Appendix')):
                story.append(PageBreak())
            story.append(Paragraph(inline(line.lstrip('# ')), sub if line.startswith('###') else section)); i += 1
        elif line.startswith('```'):
            block = []; i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                block.append(lines[i]); i += 1
            story.append(XPreformatted(html.escape('\n'.join(block)), code)); i += 1
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                fields = [x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+', x) for x in fields):
                    rows.append([Paragraph(inline(x), cell) for x in fields])
                i += 1
            n = len(rows[0])
            widths = [140, 328] if n == 2 else [150, 95, 223] if n == 3 else [204, 88, 88, 88]
            if 'Named observable' in line:
                widths = [102, 254, 112]
            table = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EDF2F5')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 0), (-1, 0), .5, INK),
                ('LINEBELOW', (0, -1), (-1, -1), .5, INK),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            story.extend([table, Spacer(1, 10)])
        else:
            block = [line]; i += 1
            numbered = bool(re.match(r'\d+\. ', line))
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(('#', '|', '```')):
                if numbered or re.match(r'\d+\. ', lines[i]):
                    break
                block.append(lines[i].strip()); i += 1
            prose = ' '.join(block)
            match = re.search(r'\]\((?:[^)]+/)?(conditional_frontier|temporal_sampling|molecular_validation|native_mean_pilot)\.svg\)', prose)
            if prose.startswith('**Figure ') and match:
                image = Image(str(figures / (match[1] + '.png')))
                image.drawHeight *= WIDTH / image.drawWidth
                image.drawWidth = WIDTH
                story.append(KeepTogether([Spacer(1, 9), image, Spacer(1, 8), Paragraph(inline(prose), caption)]))
            else:
                story.append(Paragraph(inline(prose), body))

    def page(canvas, doc):
        canvas.saveState()
        canvas.setFont('Paper', 7.3)
        canvas.setFillColor(colors.HexColor('#4C6269'))
        canvas.drawString(72, 758, 'ANIBENCH  /  TASK REFERENCE')
        canvas.drawRightString(540, 758, 'Research protocol · September 2026')
        canvas.setStrokeColor(colors.HexColor('#D4DFE2'))
        canvas.line(72, 748, 540, 748)
        canvas.drawString(72, 32, 'github.com/anibiome/anibench-benchmark')
        canvas.drawRightString(540, 32, str(doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(str(out), pagesize=(612, 792), leftMargin=72, rightMargin=72,
                            topMargin=62, bottomMargin=56, invariant=1,
                            title=lines[0][2:], author='Bruno Balen; ANI Biome PBC')
    doc.build(story, onFirstPage=page, onLaterPages=page)
    result = {'schema': 'anibench.methods-paper-build.v1', 'source_sha256': digest(source),
              'builder_sha256': digest(Path(__file__)), 'pdf_sha256': digest(out),
              'figure_receipt_sha256': digest(figures / 'receipt.json'),
              'runtime': {p: version(p) for p in ['reportlab', 'matplotlib']},
              'python': sys.version.split()[0],
              'scope': 'Paper rendering and aggregate-figure replay, not participant-level fitting'}
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    print(json.dumps(build(parser.parse_args().out), indent=2))
