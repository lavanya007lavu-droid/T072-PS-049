
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import mm
from xml.sax.saxutils import escape

source = Path("docs/DESIGN_SUMMARY.md")
output = Path("docs/DESIGN_SUMMARY.pdf")

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name="ProjectTitle",
    parent=styles["Title"],
    alignment=TA_CENTER,
    textColor=colors.HexColor("#17365D"),
    fontSize=18,
    spaceAfter=18
))

styles.add(ParagraphStyle(
    name="SectionHeading",
    parent=styles["Heading2"],
    textColor=colors.HexColor("#1F4E79"),
    spaceBefore=12,
    spaceAfter=6
))

story = []

for line in source.read_text(encoding="utf-8").splitlines():
    line = line.strip()

    if not line:
        story.append(Spacer(1, 3 * mm))

    elif line.startswith("# "):
        story.append(Paragraph(
            escape(line[2:]), styles["ProjectTitle"]
        ))

    elif line.startswith("## "):
        story.append(Paragraph(
            escape(line[3:]), styles["SectionHeading"]
        ))

    elif line.startswith("- "):
        story.append(Paragraph(
            "&#8226; " + escape(line[2:]),
            styles["BodyText"]
        ))

    else:
        line = line.replace("`", "")
        story.append(Paragraph(
            escape(line), styles["BodyText"]
        ))

doc = SimpleDocTemplate(
    str(output),
    pagesize=A4,
    rightMargin=20 * mm,
    leftMargin=20 * mm,
    topMargin=18 * mm,
    bottomMargin=18 * mm
)

doc.build(story)

print(f"PDF created successfully: {output}")
