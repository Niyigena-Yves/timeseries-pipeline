"""Render REPORT.md as a PDF using ReportLab."""

import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "REPORT.md"
OUTPUT = ROOT / "REPORT.pdf"


def inline_markup(text):
    escaped = escape(text)
    escaped = re.sub(r"`([^`]+)`", r'<font name="Courier">\1</font>', escaped)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)


def render():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#17324D"), spaceAfter=12))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=colors.HexColor("#176B67"), spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    story = []
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                row = [value.strip() for value in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[:\- ]+", value or " ") for value in row):
                    rows.append([Paragraph(inline_markup(value), styles["Small"]) for value in row])
                index += 1
            table = Table(rows, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C6CC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EEF4F3")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.extend([Spacer(1, 4), table, Spacer(1, 8)])
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline_markup(line[2:]), styles["ReportTitle"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline_markup(line[3:]), styles["Section"]))
        elif line.startswith("- "):
            story.append(Paragraph("&bull; " + inline_markup(line[2:]), styles["BodyText"]))
        else:
            story.append(Paragraph(inline_markup(line), styles["BodyText"]))
            story.append(Spacer(1, 5))
        index += 1

    document = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=19 * mm, leftMargin=19 * mm,
        topMargin=17 * mm, bottomMargin=17 * mm, title="African Crises Time-Series Project Report",
    )
    document.build(story)
    print("Wrote", OUTPUT)


if __name__ == "__main__":
    render()