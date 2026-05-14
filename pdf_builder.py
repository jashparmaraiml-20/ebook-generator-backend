# -*- coding: utf-8 -*-
"""
pdf_builder.py — Stage 4: Professional eBook PDF Assembler

Converts markdown content + images into a polished, professional-quality PDF
with proper typography, spacing, cover page, TOC, and chapter layouts.
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch, cm, mm
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, NextPageTemplate,
    Paragraph, Spacer, Image, PageBreak, KeepTogether,
    Table, TableStyle, HRFlowable, Flowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Rect, Line
from PIL import Image as PILImage
from colorama import Fore, Style as CStyle

# ═══════════════════════════════════════════════════════════════
# FONT REGISTRATION (Google Fonts if available, else Helvetica)
# ═══════════════════════════════════════════════════════════════

FONT_DIR = Path(__file__).parent / "fonts"
BODY_FONT = "Helvetica"
BOLD_FONT = "Helvetica-Bold"
ITALIC_FONT = "Helvetica-Oblique"
HEADING_FONT = "Helvetica-Bold"

# Try to register better fonts
try:
    if FONT_DIR.exists():
        for name, file in [
            ("CustomBody", "Inter-Regular.ttf"),
            ("CustomBold", "Inter-Bold.ttf"),
            ("CustomItalic", "Inter-Italic.ttf"),
        ]:
            fp = FONT_DIR / file
            if fp.exists():
                pdfmetrics.registerFont(TTFont(name, str(fp)))
        BODY_FONT = "CustomBody"
        BOLD_FONT = "CustomBold"
        ITALIC_FONT = "CustomItalic"
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════
# THEME
# ═══════════════════════════════════════════════════════════════

T = {
    "primary":    "#1565C0",
    "primary_lt": "#E3F2FD",
    "accent":     "#0D47A1",
    "text":       "#212121",
    "muted":      "#757575",
    "light":      "#9E9E9E",
    "border":     "#E0E0E0",
    "bg_tip":     "#E8F5E9",
    "bg_warn":    "#FFF3E0",
    "bg_quote":   "#F5F5F5",
    "white":      "#FFFFFF",
}

PAGE_W, PAGE_H = A4
MARGIN_L = 1.1 * inch
MARGIN_R = 0.9 * inch
MARGIN_T = 0.85 * inch
MARGIN_B = 0.85 * inch
CONTENT_W = PAGE_W - MARGIN_L - MARGIN_R

# ═══════════════════════════════════════════════════════════════
# CUSTOM FLOWABLES
# ═══════════════════════════════════════════════════════════════

class ColorBar(Flowable):
    """A colored rectangle bar used as a decorative element."""
    def __init__(self, width, height, color):
        super().__init__()
        self.width = width
        self.height = height
        self.color = HexColor(color)

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)


class QuoteBlock(Flowable):
    """A styled blockquote with left border and background."""
    def __init__(self, text, width, bg_color="#F5F5F5", border_color="#1565C0"):
        super().__init__()
        self.text = text
        self.block_width = width
        self.bg = HexColor(bg_color)
        self.border = HexColor(border_color)
        self._para = Paragraph(text, ParagraphStyle(
            name="QInner", fontSize=10.5, leading=16,
            fontName=ITALIC_FONT, textColor=HexColor(T["text"]),
            leftIndent=14, rightIndent=8,
        ))
        self._para.wrapOn(None, width - 22, 9999)
        self.height = self._para.height + 16

    def wrap(self, aW, aH):
        return self.block_width, self.height

    def draw(self):
        self.canv.setFillColor(self.bg)
        self.canv.roundRect(0, 0, self.block_width, self.height, 4, fill=1, stroke=0)
        self.canv.setFillColor(self.border)
        self.canv.rect(0, 0, 4, self.height, fill=1, stroke=0)
        self._para.drawOn(self.canv, 4, 8)


# ═══════════════════════════════════════════════════════════════
# STYLES
# ═══════════════════════════════════════════════════════════════

def _styles():
    s = getSampleStyleSheet()
    def add(name, **kw):
        if name in s:
            for k, v in kw.items():
                setattr(s[name], k, v)
        else:
            s.add(ParagraphStyle(name=name, **kw))

    # Cover
    add("CoverTitle", fontSize=36, leading=44, alignment=TA_CENTER,
        textColor=HexColor(T["white"]), fontName=HEADING_FONT, spaceAfter=12)
    add("CoverSub", fontSize=15, leading=22, alignment=TA_CENTER,
        textColor=HexColor("#B3E5FC"), fontName=BODY_FONT, spaceAfter=30)
    add("CoverMeta", fontSize=10, leading=15, alignment=TA_CENTER,
        textColor=HexColor("#B3E5FC"), fontName=BODY_FONT)

    # TOC
    add("TOCTitle", fontSize=26, leading=34, alignment=TA_LEFT,
        textColor=HexColor(T["primary"]), fontName=HEADING_FONT,
        spaceBefore=10, spaceAfter=20)
    add("TOCEntry", fontSize=12, leading=24, alignment=TA_LEFT,
        textColor=HexColor(T["text"]), fontName=BODY_FONT,
        leftIndent=10, spaceAfter=2)
    add("TOCNum", fontSize=12, leading=24, alignment=TA_LEFT,
        textColor=HexColor(T["primary"]), fontName=BOLD_FONT,
        spaceAfter=2)

    # Chapter
    add("ChLabel", fontSize=11, leading=14, alignment=TA_LEFT,
        textColor=HexColor(T["primary"]), fontName=BOLD_FONT,
        spaceBefore=0, spaceAfter=6, tracking=2)
    add("ChTitle", fontSize=26, leading=32, alignment=TA_LEFT,
        textColor=HexColor(T["accent"]), fontName=HEADING_FONT,
        spaceBefore=0, spaceAfter=6)

    # Section headings
    add("H2", fontSize=17, leading=24, alignment=TA_LEFT,
        textColor=HexColor(T["primary"]), fontName=HEADING_FONT,
        spaceBefore=18, spaceAfter=8)
    add("H3", fontSize=14, leading=20, alignment=TA_LEFT,
        textColor=HexColor(T["accent"]), fontName=BOLD_FONT,
        spaceBefore=14, spaceAfter=6)
    add("H4", fontSize=12, leading=17, alignment=TA_LEFT,
        textColor=HexColor(T["text"]), fontName=BOLD_FONT,
        spaceBefore=10, spaceAfter=4)

    # Body
    add("Body", fontSize=11, leading=18, alignment=TA_JUSTIFY,
        textColor=HexColor(T["text"]), fontName=BODY_FONT,
        spaceAfter=8, firstLineIndent=0)
    add("BodyIndent", fontSize=11, leading=18, alignment=TA_JUSTIFY,
        textColor=HexColor(T["text"]), fontName=BODY_FONT,
        spaceAfter=8, leftIndent=18)

    # Lists
    add("Bullet", fontSize=11, leading=18, alignment=TA_LEFT,
        textColor=HexColor(T["text"]), fontName=BODY_FONT,
        leftIndent=22, bulletIndent=8, spaceAfter=3)
    add("NumItem", fontSize=11, leading=18, alignment=TA_LEFT,
        textColor=HexColor(T["text"]), fontName=BODY_FONT,
        leftIndent=22, bulletIndent=8, spaceAfter=3)

    # Special
    add("Tip", fontSize=10.5, leading=16, alignment=TA_LEFT,
        textColor=HexColor("#2E7D32"), fontName=ITALIC_FONT,
        leftIndent=12, spaceAfter=8)
    add("Warning", fontSize=10.5, leading=16, alignment=TA_LEFT,
        textColor=HexColor("#E65100"), fontName=ITALIC_FONT,
        leftIndent=12, spaceAfter=8)
    add("KeyTakeaway", fontSize=11, leading=17, alignment=TA_LEFT,
        textColor=HexColor(T["accent"]), fontName=BOLD_FONT,
        spaceBefore=6, spaceAfter=10)

    # Footer
    add("Footer", fontSize=8, leading=11, alignment=TA_CENTER,
        textColor=HexColor(T["light"]), fontName=BODY_FONT)

    return s


# ═══════════════════════════════════════════════════════════════
# PAGE DRAWING CALLBACKS
# ═══════════════════════════════════════════════════════════════

_book_title = ""

def _draw_cover(canvas, doc):
    """Draw the full-bleed cover page background."""
    canvas.saveState()
    # Gradient-like solid background
    canvas.setFillColor(HexColor(T["primary"]))
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # Decorative lighter bar at top
    canvas.setFillColor(HexColor(T["accent"]))
    canvas.rect(0, PAGE_H - 80, PAGE_W, 80, fill=1, stroke=0)
    # Bottom bar
    canvas.setFillColor(HexColor("#0A3A7A"))
    canvas.rect(0, 0, PAGE_W, 50, fill=1, stroke=0)
    canvas.restoreState()

def _draw_content(canvas, doc):
    """Draw header/footer on content pages."""
    canvas.saveState()
    pg = doc.page
    # Footer line + page number
    canvas.setStrokeColor(HexColor(T["border"]))
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN_L, MARGIN_B - 10, PAGE_W - MARGIN_R, MARGIN_B - 10)
    canvas.setFont(BODY_FONT, 8)
    canvas.setFillColor(HexColor(T["light"]))
    canvas.drawCentredString(PAGE_W / 2, MARGIN_B - 24, str(pg))
    # Header: book title (from page 3+)
    if pg > 2 and _book_title:
        canvas.setFont(BODY_FONT, 7.5)
        canvas.setFillColor(HexColor(T["muted"]))
        canvas.drawString(MARGIN_L, PAGE_H - MARGIN_T + 14, _book_title[:70])
        canvas.setStrokeColor(HexColor(T["border"]))
        canvas.line(MARGIN_L, PAGE_H - MARGIN_T + 8, PAGE_W - MARGIN_R, PAGE_H - MARGIN_T + 8)
    canvas.restoreState()


# ═══════════════════════════════════════════════════════════════
# MARKDOWN PARSER
# ═══════════════════════════════════════════════════════════════

def _esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _inline(text):
    """Convert inline markdown (bold, italic) to ReportLab XML."""
    text = _esc(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
    return text


def _is_implicit_heading(line, prev_blank, next_line):
    """
    Detect lines that ChatGPT writes as section headings but WITHOUT
    markdown ## markers. These are short, title-like lines that appear
    after a blank line and before content.

    Patterns detected:
      - "The Dream That Everyone Is Chasing"
      - "Step 1: Choose Your First Product"
      - "What This Book Will Help You Do"
      - "1. Product" (numbered section header)
      - "Example:" standalone
    """
    s = line.strip()
    if not s or not prev_blank:
        return False, None

    # Skip lines that are clearly NOT headings
    if s.startswith(("- ", "* ", "• ", "> ", '"', "'", "(")):
        return False, None
    # Skip emoji lines
    if any(s.startswith(e) for e in ["💡", "📊", "✔", "❌", "⚠"]):
        return False, None
    # Skip very long lines (headings are short)
    if len(s) > 90:
        return False, None
    # Skip lines ending with common sentence endings that suggest body text
    if s.endswith((",", ".", "!", ";")) and not s.endswith(("...", "etc.")):
        # Exception: lines like "Step 1: Do Something." can still be headings
        if not re.match(r'^(Step|Phase|Stage|Part|Tip|Rule|Lesson|Mistake|Fix|Strategy)\s+\d', s, re.I):
            return False, None

    # --- Positive patterns ---

    # "Chapter N: ..." — skip, already handled externally
    if re.match(r'^Chapter\s+\d', s, re.I):
        return False, None

    # "Step N: ...", "Phase N: ...", "Pillar N: ...", etc.
    if re.match(r'^(Step|Phase|Stage|Part|Tip|Rule|Pillar|Lesson|Mistake|Fix|Strategy|Method)\s+\d', s, re.I):
        return True, "H3"

    # "N. Title" — numbered section heading (e.g. "1. Product", "2. Marketing")
    # Only if short and followed by content, not a list item with long text
    if re.match(r'^\d+\.\s+[A-Z]', s) and len(s) < 60:
        next_s = next_line.strip() if next_line else ""
        # If next line is blank or starts a new paragraph, it's a heading
        if not next_s or (next_s and not next_s.startswith(("- ", "* ", "•"))):
            return True, "H3"

    # "What/Why/How/When/Where ..." question-style headings
    if re.match(r'^(What|Why|How|When|Where|Who|Which|Can|Do|Does|Is|Are|Should|Will|Would)\s', s) and len(s) < 70:
        if "?" in s or (next_line and not next_line.strip()):
            return True, "H3"

    # "The ... (Title Case)" — common ChatGPT heading pattern
    # Title case heuristic: most words start with uppercase
    words = s.replace(":", "").replace("?", "").replace("(", "").replace(")", "").split()
    if len(words) >= 2 and len(words) <= 12:
        skip_words = {"a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
                      "for", "of", "with", "is", "it", "by", "not", "you", "your",
                      "vs", "vs.", "from", "into", "this", "that"}
        upper_count = sum(1 for w in words if w[0].isupper() or w.lower() in skip_words)
        ratio = upper_count / len(words)
        if ratio >= 0.7 and len(s) < 70:
            return True, "H3"

    # Single-word or two-word labels like "Example:", "Summary:", "Key Terms:"
    if s.endswith(":") and len(words) <= 4:
        return True, "H4"

    return False, None


def _md_to_flowables(md_text, styles):
    """Parse markdown into ReportLab flowables with proper formatting."""
    items = []
    lines = md_text.split("\n")
    n = len(lines)
    prev_was_blank = True  # start of content counts as after blank

    for i in range(n):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            items.append(Spacer(1, 4))
            prev_was_blank = True
            continue

        next_line = lines[i + 1] if i + 1 < n else ""

        # Skip top-level title / subtitle (already on cover)
        if stripped.startswith("# ") and not stripped.startswith("## "):
            prev_was_blank = False
            continue

        # Skip "Chapter N:" lines (handled by chapter builder)
        if re.match(r'^Chapter\s+\d', stripped, re.I):
            prev_was_blank = False
            continue

        # ── Explicit markdown headings ──
        if stripped.startswith("#### "):
            items.append(Spacer(1, 6))
            items.append(Paragraph(_inline(stripped[5:].strip(" #")), styles["H4"]))
            prev_was_blank = False
            continue
        if stripped.startswith("### "):
            items.append(Spacer(1, 8))
            items.append(Paragraph(_inline(stripped[4:].strip(" #")), styles["H3"]))
            prev_was_blank = False
            continue
        if stripped.startswith("## "):
            items.append(Spacer(1, 10))
            items.append(Paragraph(_inline(stripped[3:].strip(" #")), styles["H2"]))
            prev_was_blank = False
            continue

        # ── Horizontal rule ──
        if stripped in ("---", "***", "___"):
            items.append(Spacer(1, 6))
            items.append(HRFlowable(width="70%", thickness=0.5,
                color=HexColor(T["border"]), spaceAfter=6, spaceBefore=2))
            prev_was_blank = False
            continue

        # ── Bullet lists ──
        if stripped.startswith(("- ", "* ", "• ")):
            text = _inline(stripped[2:])
            items.append(Paragraph(f"<bullet>&bull;</bullet> {text}", styles["Bullet"]))
            prev_was_blank = False
            continue

        # ── Numbered lists ──
        if re.match(r'^\d+[\.\)]\s', stripped):
            m = re.match(r'^(\d+)[\.\)]\s*(.*)', stripped)
            num, text = m.group(1), _inline(m.group(2))
            # Check if this is a numbered HEADING (short, followed by content)
            is_heading, _ = _is_implicit_heading(stripped, prev_was_blank, next_line)
            if is_heading:
                items.append(Spacer(1, 8))
                items.append(Paragraph(f"<b>{num}. {text}</b>", styles["H3"]))
            else:
                items.append(Paragraph(f"<b>{num}.</b>  {text}", styles["NumItem"]))
            prev_was_blank = False
            continue

        # ── Emoji callouts (tips, warnings) ──
        if any(stripped.startswith(e) for e in ["💡", "📊", "✔", "❌"]):
            items.append(QuoteBlock(_inline(stripped), CONTENT_W,
                bg_color=T["bg_tip"], border_color="#4CAF50"))
            items.append(Spacer(1, 6))
            prev_was_blank = False
            continue
        if any(stripped.startswith(e) for e in ["⚠", "⚠️"]):
            items.append(QuoteBlock(_inline(stripped), CONTENT_W,
                bg_color=T["bg_warn"], border_color="#FF9800"))
            items.append(Spacer(1, 6))
            prev_was_blank = False
            continue

        # ── Key Takeaways header ──
        if "key takeaway" in stripped.lower():
            items.append(Spacer(1, 10))
            items.append(ColorBar(CONTENT_W, 2, T["primary"]))
            items.append(Spacer(1, 6))
            items.append(Paragraph(_inline(stripped), styles["KeyTakeaway"]))
            prev_was_blank = False
            continue

        # ── Blockquotes ──
        if stripped.startswith("> "):
            text = _inline(stripped[2:])
            items.append(QuoteBlock(text, CONTENT_W))
            items.append(Spacer(1, 4))
            prev_was_blank = False
            continue

        # ── Implicit heading detection (ChatGPT plain-text headings) ──
        is_heading, level = _is_implicit_heading(stripped, prev_was_blank, next_line)
        if is_heading and level:
            items.append(Spacer(1, 8 if level == "H3" else 6))
            items.append(Paragraph(_inline(stripped), styles[level]))
            prev_was_blank = False
            continue

        # ── Regular paragraph ──
        items.append(Paragraph(_inline(stripped), styles["Body"]))

    return items


# ═══════════════════════════════════════════════════════════════
# IMAGE HELPER
# ═══════════════════════════════════════════════════════════════

def _fit_image(path, max_w=None, max_h=None):
    if not path or not Path(path).exists():
        return None
    if max_w is None: max_w = CONTENT_W
    if max_h is None: max_h = 3.5 * inch
    try:
        pil = PILImage.open(path)
        w, h = pil.size
        r = min(max_w / w, max_h / h)
        return Image(path, width=w * r, height=h * r, hAlign="CENTER")
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# MAIN BUILD
# ═══════════════════════════════════════════════════════════════

def build_pdf(content_result, images_result, output_dir, brief):
    global _book_title
    _book_title = brief["title"]

    print(f"\n{'='*60}")
    print(f"  {Fore.CYAN}[STAGE 4] Professional PDF Builder{CStyle.RESET_ALL}")
    print(f"{'='*60}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[^\w\s-]', '', brief["title"]).strip().replace(" ", "_")[:50]
    pdf_path = output_dir / f"{safe}.pdf"

    styles = _styles()
    story = []

    # ── COVER PAGE ────────────────────────────────────────────
    print(f"  {Fore.YELLOW}[PDF] Building cover page...{CStyle.RESET_ALL}")
    story.append(NextPageTemplate("cover"))
    story.append(Spacer(1, 1.8 * inch))

    # Cover image (centered, smaller)
    cover_img = images_result.get("cover_image")
    if cover_img:
        img = _fit_image(cover_img, max_w=3.2*inch, max_h=3.2*inch)
        if img:
            story.append(img)
            story.append(Spacer(1, 0.4 * inch))

    story.append(Paragraph(_esc(brief["title"]), styles["CoverTitle"]))
    story.append(Paragraph(_esc(brief["subtitle"]), styles["CoverSub"]))
    story.append(Spacer(1, 0.6 * inch))
    meta = f'{brief["category"]}  |  {brief["audience"].title()} Level  |  {datetime.now().strftime("%B %Y")}'
    story.append(Paragraph(_esc(meta), styles["CoverMeta"]))

    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    # ── TABLE OF CONTENTS ─────────────────────────────────────
    print(f"  {Fore.YELLOW}[PDF] Building table of contents...{CStyle.RESET_ALL}")
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Table of Contents", styles["TOCTitle"]))
    story.append(ColorBar(60, 3, T["primary"]))
    story.append(Spacer(1, 16))

    for ch in content_result["chapters"]:
        num = f'<font color="{T["primary"]}"><b>{ch["number"]:02d}</b></font>'
        toc_line = f'{num}  &mdash;  {_esc(ch["title"])}'
        story.append(Paragraph(toc_line, styles["TOCEntry"]))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # ── CHAPTERS ──────────────────────────────────────────────
    for ch in content_result["chapters"]:
        cn = ch["number"]
        ct = ch["title"]
        print(f"  {Fore.YELLOW}[PDF] Chapter {cn}: {ct}{CStyle.RESET_ALL}")

        # Chapter opening
        story.append(Spacer(1, 0.6 * inch))
        story.append(Paragraph(f"CHAPTER {cn}", styles["ChLabel"]))
        story.append(Paragraph(_esc(ct), styles["ChTitle"]))
        story.append(ColorBar(80, 3, T["primary"]))
        story.append(Spacer(1, 12))

        # Chapter image
        ch_imgs = images_result.get("chapter_images", {})
        ch_img = ch_imgs.get(cn) or ch_imgs.get(str(cn))
        if ch_img:
            img = _fit_image(ch_img, max_w=CONTENT_W * 0.85, max_h=2.8*inch)
            if img:
                story.append(img)
                story.append(Spacer(1, 12))

        # Chapter content
        flowables = _md_to_flowables(ch["content"], styles)
        story.extend(flowables)

        story.append(PageBreak())

    # ── END PAGE ──────────────────────────────────────────────
    story.append(Spacer(1, 2.5 * inch))
    story.append(Paragraph("Thank You for Reading", styles["ChTitle"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        f'This eBook was generated on {datetime.now().strftime("%B %d, %Y")}.',
        styles["Body"]
    ))

    # ── BUILD ─────────────────────────────────────────────────
    print(f"  {Fore.CYAN}[PDF] Rendering...{CStyle.RESET_ALL}")

    # Create page templates
    cover_frame = Frame(0.5*inch, 0.5*inch, PAGE_W - inch, PAGE_H - inch,
                        id="cover")
    content_frame = Frame(MARGIN_L, MARGIN_B, CONTENT_W, PAGE_H - MARGIN_T - MARGIN_B,
                          id="content")

    doc = BaseDocTemplate(
        str(pdf_path), pagesize=A4,
        title=brief["title"], author="eBook Generator",
        subject=brief["category"],
    )
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[cover_frame], onPage=_draw_cover),
        PageTemplate(id="content", frames=[content_frame], onPage=_draw_content),
    ])

    doc.build(story)

    sz = pdf_path.stat().st_size / (1024 * 1024)
    print(f"\n  {Fore.GREEN}[OK] PDF: {pdf_path}{CStyle.RESET_ALL}")
    print(f"  {Fore.GREEN}     Size: {sz:.1f} MB | Chapters: {len(content_result['chapters'])}{CStyle.RESET_ALL}")
    return pdf_path


if __name__ == "__main__":
    mock_content = {
        "chapters": [
            {"number": 1, "title": "Introduction",
             "content": "## Welcome\n\nThis is a test.\n\n- Point one\n- Point two\n\n### Key Takeaways\n\n- Great stuff\n- More stuff",
             "word_count": 20},
        ],
        "total_words": 20,
    }
    mock_images = {"cover_image": None, "chapter_images": {}}
    mock_brief = {"title": "Test eBook", "subtitle": "Test Sub", "category": "Test", "audience": "beginner"}
    build_pdf(mock_content, mock_images, Path("output/test_pdf"), mock_brief)
