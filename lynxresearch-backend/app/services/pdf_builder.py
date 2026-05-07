# app/services/pdf_builder.py

import re
import logging
import uuid
from pathlib import Path
from typing import Optional
from html import unescape as _html_unescape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
    KeepTogether,
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Brand Colors ──────────────────────────────────────────────
NAVY       = colors.HexColor("#0D1B4B")
BLUE       = colors.HexColor("#1565C0")
LIGHT_BLUE = colors.HexColor("#E8EEF7")
ACCENT     = colors.HexColor("#FF8F00")
DARK_GRAY  = colors.HexColor("#333333")
MID_GRAY   = colors.HexColor("#666666")
LIGHT_GRAY = colors.HexColor("#F5F7FA")
WHITE      = colors.white
BLACK      = colors.black

PAGE_W, PAGE_H = A4


# ── Page numbering canvas ─────────────────────────────────────
class NumberedCanvas(canvas.Canvas):
    """Adds page numbers and footer to every page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(self._pageNumber, total)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def _draw_footer(self, page_num: int, total: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(MID_GRAY)

        # Left footer
        self.drawString(
            2 * cm, 1.2 * cm,
            "LynxResearch — Autonomous Research Report"
        )
        # Right footer — page numbers
        self.drawRightString(
            PAGE_W - 2 * cm, 1.2 * cm,
            f"Page {page_num} of {total}"
        )
        # Footer line
        self.setStrokeColor(colors.HexColor("#CCCCCC"))
        self.setLineWidth(0.5)
        self.line(2 * cm, 1.6 * cm, PAGE_W - 2 * cm, 1.6 * cm)
        self.restoreState()


# ── Style sheet ───────────────────────────────────────────────
def _build_styles() -> dict:
    base = getSampleStyleSheet()

    styles = {
        # Report title on cover page
        "ReportTitle": ParagraphStyle(
            "ReportTitle",
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=12,
            leading=32,
        ),
        # Subtitle / meta on cover
        "Subtitle": ParagraphStyle(
            "Subtitle",
            fontName="Helvetica",
            fontSize=13,
            textColor=MID_GRAY,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        # Section headings  (## in markdown)
        "Heading1": ParagraphStyle(
            "Heading1",
            fontName="Helvetica-Bold",
            fontSize=16,
            textColor=NAVY,
            spaceBefore=20,
            spaceAfter=8,
            borderPad=4,
            leading=20,
        ),
        # Sub-section headings  (### in markdown)
        "Heading2": ParagraphStyle(
            "Heading2",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=BLUE,
            spaceBefore=14,
            spaceAfter=6,
            leading=16,
        ),
        # Normal body paragraph
        "Body": ParagraphStyle(
            "Body",
            fontName="Helvetica",
            fontSize=10.5,
            textColor=DARK_GRAY,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=16,
        ),
        # Bullet item
        "Bullet": ParagraphStyle(
            "Bullet",
            fontName="Helvetica",
            fontSize=10.5,
            textColor=DARK_GRAY,
            alignment=TA_LEFT,
            leftIndent=18,
            spaceAfter=4,
            leading=15,
            bulletIndent=6,
        ),
        # Figure caption
        "Caption": ParagraphStyle(
            "Caption",
            fontName="Helvetica-Oblique",
            fontSize=9,
            textColor=MID_GRAY,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        # Citation superscript text
        "Citation": ParagraphStyle(
            "Citation",
            fontName="Helvetica",
            fontSize=9,
            textColor=MID_GRAY,
            alignment=TA_LEFT,
            spaceAfter=4,
            leading=13,
        ),
        # Table header cell
        "TableHeader": ParagraphStyle(
            "TableHeader",
            fontName="Helvetica-Bold",
            fontSize=9.5,
            textColor=WHITE,
            alignment=TA_LEFT,
        ),
        # Table body cell
        "TableCell": ParagraphStyle(
            "TableCell",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK_GRAY,
            alignment=TA_LEFT,
            leading=12,
        ),
        # Executive summary box text
        "ExecSummary": ParagraphStyle(
            "ExecSummary",
            fontName="Helvetica",
            fontSize=10.5,
            textColor=DARK_GRAY,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
            leading=16,
            leftIndent=10,
            rightIndent=10,
        ),
    }
    return styles


# ── Markdown → ReportLab elements parser ─────────────────────
class MarkdownParser:
    """
    Parses the markdown content our agents produce into
    a flat list of ReportLab Flowable elements.

    Handles:
    - # / ## / ### headings
    - Paragraphs
    - **bold** and *italic* inline
    - - bullet lists
    - ![alt](path) images
    - Markdown tables (| col | col |)
    - <sup>[N]</sup> citation markers
    - --- horizontal rules
    - Page break hints (after cover/TOC)
    """

    def __init__(self, styles: dict, *, enable_links: bool = True):
        self.styles = styles
        self.elements: list = []
        self._figure_counter = 0
        self._in_table_block: list[str] = []
        self._in_exec_summary = False
        self._in_references = False
        self._reference_ids: set[str] = set()
        self._enable_links = enable_links

    # ── Public entry point ────────────────────────────────────
    def parse(self, markdown_text: str) -> list:
        self.elements = []
        self._reference_ids = self._extract_reference_ids(markdown_text)
        lines = markdown_text.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # ── Blank line ────────────────────────────────────
            if not line.strip():
                # Flush any pending table
                if self._in_table_block:
                    self._flush_table()
                i += 1
                continue

            # ── Horizontal rule ───────────────────────────────
            if re.match(r"^-{3,}$", line.strip()):
                if self._in_table_block:
                    self._flush_table()
                self.elements.append(
                    HRFlowable(
                        width="100%", thickness=0.5,
                        color=colors.HexColor("#CCCCCC"),
                        spaceAfter=8, spaceBefore=8,
                    )
                )
                i += 1
                continue

            # ── Headings ──────────────────────────────────────
            heading_match = re.match(r"^(#{1,3})\s+(.+)$", line)
            if heading_match:
                if self._in_table_block:
                    self._flush_table()
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                self._add_heading(text, level)
                i += 1
                continue

            # ── Image ─────────────────────────────────────────
            img_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", line.strip())
            if img_match:
                if self._in_table_block:
                    self._flush_table()
                alt_text = img_match.group(1)
                img_path = img_match.group(2)
                self._add_image(img_path, alt_text)
                i += 1
                continue

            # ── Markdown table row ────────────────────────────
            if line.strip().startswith("|"):
                self._in_table_block.append(line)
                i += 1
                continue
            else:
                if self._in_table_block:
                    self._flush_table()

            # ── Bullet point ──────────────────────────────────
            bullet_match = re.match(r"^[\-\*]\s+(.+)$", line.strip())
            if bullet_match:
                text = self._inline_format(bullet_match.group(1))
                self.elements.append(
                    self._safe_paragraph(f"• {text}", self.styles["Bullet"])
                )
                i += 1
                continue

            # ── Numbered list ─────────────────────────────────
            num_match = re.match(r"^(\d+)\.\s+(.+)$", line.strip())
            if num_match:
                num = num_match.group(1)
                if self._in_references:
                    text = num_match.group(2).strip()
                    self.elements.append(
                        self._safe_paragraph(self._format_reference_entry(num, text), self.styles["Bullet"])
                    )
                else:
                    text = self._inline_format(num_match.group(2))
                    self.elements.append(
                        self._safe_paragraph(f"{num}. {text}", self.styles["Bullet"])
                    )
                i += 1
                continue

            # ── Regular paragraph ─────────────────────────────
            text = line.strip()
            if text:
                formatted = self._inline_format(text)
                # Use exec summary style for that section
                style_key = (
                    "ExecSummary"
                    if self._in_exec_summary
                    else "Body"
                )
                self.elements.append(
                    self._safe_paragraph(formatted, self.styles[style_key])
                )

            i += 1

        # Flush any remaining table
        if self._in_table_block:
            self._flush_table()

        return self.elements

    def _safe_paragraph(self, text: str, style):
        """
        ReportLab's paraparser is strict. Never let a malformed inline tag
        crash the entire PDF build. Try to render; if it fails, strip tags and retry;
        if still too large/unparseable, chunk into multiple paragraphs.
        """
        try:
            return Paragraph(text, style)
        except Exception:
            plain = re.sub(r"<[^>]+>", "", text)
            plain = _html_unescape(plain)
            try:
                return Paragraph(plain, style)
            except Exception:
                chunks: list[str] = []
                s = plain
                max_len = 1400
                while len(s) > max_len:
                    cut = s.rfind(". ", 0, max_len)
                    if cut < 200:
                        cut = max_len
                    chunks.append(s[:cut].strip())
                    s = s[cut:].strip()
                if s:
                    chunks.append(s)
                flow = [Paragraph(c, style) for c in chunks if c]
                return KeepTogether(flow)

    def _extract_reference_ids(self, markdown_text: str) -> set[str]:
        refs: set[str] = set()
        in_references = False
        for line in markdown_text.splitlines():
            heading_match = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
            if heading_match:
                in_references = heading_match.group(2).strip().lower() == "references"
                continue
            if not in_references:
                continue
            ref_match = re.match(r"^(\d+)\.\s+", line.strip())
            if ref_match:
                refs.add(ref_match.group(1))
        return refs

    # ── Heading handler ───────────────────────────────────────
    def _add_heading(self, text: str, level: int):
        self._in_references = text.strip().lower() == "references"
        if "executive summary" in text.lower():
            self._in_exec_summary = True
        elif level <= 2:
            self._in_exec_summary = False

        if level == 1:
            # Top-level title → cover page style
            self.elements.append(Spacer(1, 0.3 * cm))
            self.elements.append(
                Paragraph(text, self.styles["ReportTitle"])
            )
            self.elements.append(Spacer(1, 0.2 * cm))
        elif level == 2:
            self.elements.append(Spacer(1, 0.2 * cm))
            # Decorative left-border effect via a 1-row table
            header_table = Table(
                [[Paragraph(text, self.styles["Heading1"])]],
                colWidths=[16.5 * cm],
            )
            header_table.setStyle(TableStyle([
                ("LEFTPADDING",  (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING",   (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
                ("LINEBEFORE",   (0, 0), (0, -1), 4, BLUE),
                ("BACKGROUND",   (0, 0), (-1, -1), LIGHT_BLUE),
                ("ROUNDEDCORNERS", [3]),
            ]))
            self.elements.append(header_table)
            self.elements.append(Spacer(1, 0.15 * cm))
        else:
            self.elements.append(
                Paragraph(text, self.styles["Heading2"])
            )

    # ── Image handler ─────────────────────────────────────────
    def _add_image(self, img_path: str, alt_text: str):
        # Strip file:// prefix if present
        clean_path = img_path.replace("file://", "").strip()
        p = Path(clean_path)

        if not p.exists():
            logger.warning(f"[PDFBuilder] Image not found, skipping: {clean_path}")
            self.elements.append(
                Paragraph(
                    f"[Figure not available: {alt_text}]",
                    self.styles["Caption"],
                )
            )
            return

        self._figure_counter += 1
        try:
            # Max width = full text area, maintain aspect ratio
            max_width  = 15 * cm
            max_height = 10 * cm

            img_reader = ImageReader(str(p))
            iw, ih = img_reader.getSize()
            aspect = ih / iw

            width  = min(max_width, iw)
            height = width * aspect
            if height > max_height:
                height = max_height
                width  = height / aspect

            img_flowable = Image(str(p), width=width, height=height)
            img_flowable.hAlign = "CENTER"

            caption_text = (
                alt_text
                if alt_text
                else f"Figure {self._figure_counter}"
            )
            caption = Paragraph(
                f"<i>Figure {self._figure_counter}: {caption_text}</i>",
                self.styles["Caption"],
            )

            self.elements.append(Spacer(1, 0.3 * cm))
            self.elements.append(
                KeepTogether([img_flowable, caption])
            )
            self.elements.append(Spacer(1, 0.3 * cm))

        except Exception as e:
            logger.error(f"[PDFBuilder] Failed to embed image {p}: {e}")
            self.elements.append(
                Paragraph(
                    f"[Figure {self._figure_counter}: {alt_text}]",
                    self.styles["Caption"],
                )
            )

    # ── Table handler ─────────────────────────────────────────
    def _flush_table(self):
        lines = self._in_table_block
        self._in_table_block = []

        rows = []
        for line in lines:
            # Skip separator rows like |---|---|
            if re.match(r"^\|[-:\s|]+\|$", line.strip()):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if cells:
                rows.append(cells)

        if len(rows) < 2:
            return

        # Normalize column count
        max_cols = max(len(r) for r in rows)
        for r in rows:
            while len(r) < max_cols:
                r.append("")

        # Build ReportLab table data with styled paragraphs
        header_row = [
            Paragraph(self._inline_format(cell), self.styles["TableHeader"])
            for cell in rows[0]
        ]
        body_rows = [
            [
                Paragraph(self._inline_format(cell), self.styles["TableCell"])
                for cell in row
            ]
            for row in rows[1:]
        ]
        table_data = [header_row] + body_rows

        col_width = 16.5 * cm / max_cols
        tbl = Table(table_data, colWidths=[col_width] * max_cols, repeatRows=1)

        tbl.setStyle(TableStyle([
            # Header row
            ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
            ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
            ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0),  9.5),
            ("TOPPADDING",    (0, 0), (-1, 0),  7),
            ("BOTTOMPADDING", (0, 0), (-1, 0),  7),
            # Body rows
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 9),
            ("TOPPADDING",    (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            # Alternating row colors
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            # Grid
            ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
            ("LINEBELOW",     (0, 0), (-1, 0),  1.5, NAVY),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))

        self.elements.append(Spacer(1, 0.3 * cm))
        self.elements.append(tbl)
        self.elements.append(Spacer(1, 0.3 * cm))

    # ── Inline markdown formatter ─────────────────────────────
    def _inline_format(self, text: str) -> str:
        """
        Convert inline markdown to ReportLab XML tags.
        **bold** → <b>bold</b>
        *italic* → <i>italic</i>
        <sup>[N]</sup> → <super><font size=7 color=#1565C0>[N]</font></super>
        [ref:KEY] → (stripped, already resolved by validator)
        """
        text = _sanitize_pdf_inline(text)

        # Normalize citation anchors to plain [N] before rebuilding PDF-safe links.
        text = re.sub(r'<a\s+href="#ref-(\d+)">\[?(\d+)\]?</a>', r"[\1]", text, flags=re.IGNORECASE)
        text = re.sub(r"\[(\d+)\]\(#ref-\d+\)", r"[\1]", text)
        # Convert markdown links before escaping.
        if self._enable_links:
            text = re.sub(
                r"\[([^\]]+)\]\((https?://[^)]+)\)",
                r'<a href="\2">\1</a>',
                text,
            )
        # Strip html anchors used by web report for in-page jumps.
        text = re.sub(r"<a id=\"[^\"]+\"></a>", "", text)

        # Escape any stray XML characters first
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;").replace(">", "&gt;")

        # Restore our own intentional tags
        text = text.replace("&lt;sup&gt;", "<super>")
        text = text.replace("&lt;/sup&gt;", "</super>")
        text = text.replace("&lt;b&gt;", "<b>")
        text = text.replace("&lt;/b&gt;", "</b>")
        text = text.replace("&lt;i&gt;", "<i>")
        text = text.replace("&lt;/i&gt;", "</i>")
        text = re.sub(
            r'&lt;a href="([^"]+)"&gt;([^<]*)&lt;/a&gt;',
            r'<a href="\1">\2</a>',
            text,
        )
        # Drop explicit anchor name tags in body text.
        text = re.sub(r"<a\s+name=\"[^\"]+\"/?>", "", text, flags=re.IGNORECASE)

        # **bold**
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        # *italic*
        text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)

        # Citation markers: render clean [N] as clickable internal links.
        text = re.sub(
            r"&lt;super&gt;\[(\d+)\]&lt;/super&gt;",
            r"[\1]",
            text,
        )
        text = re.sub(
            r"<super>\[(\d+)\]</super>",
            r"[\1]",
            text,
        )
        def _citation_link(match: re.Match[str]) -> str:
            ref_num = match.group(1)
            if self._enable_links and ref_num in self._reference_ids:
                return f'<font color="#1565C0"><a href="#ref-{ref_num}">[{ref_num}]</a></font>'
            return f"[{ref_num}]"

        text = re.sub(r"\[(\d+)\]", _citation_link, text)

        # Strip leftover [ref:KEY] that validator missed
        text = re.sub(r"\[ref:[^\]]+\]", "", text)

        return text

    def _format_reference_entry(self, num: str, text: str) -> str:
        """
        Render references as:
        [N] Title of article
        with title clickable when a source URL is available.
        """
        # Strip pre-rendered anchor/link tags so we can rebuild a clean single-link reference line.
        plain = re.sub(r"</?a[^>]*>", "", text, flags=re.IGNORECASE)
        plain = re.sub(r"</?font[^>]*>", "", plain, flags=re.IGNORECASE)
        plain = _html_unescape(plain)

        url_match = re.search(r"(https?://[^\s)]+)", plain)
        url = url_match.group(1).rstrip(").,;") if url_match else ""
        cleaned = re.sub(r"\s*\[Link\]\(https?://[^)]+\)\s*", "", plain, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s*Link\s*[—:-]\s*https?://\S+\s*", " ", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"\s*Retrieved from\s+https?://\S+\s*$", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"(https?://\S+)", "", cleaned).strip(" .;,-")
        anchor = f'<a name="ref-{num}"/>'
        if url:
            title = cleaned or re.sub(r"(https?://\S+)", "", plain).strip(" .;,-")
            if self._enable_links:
                return f'{anchor}[{num}] {title}. Retrieved from <font color="#1565C0"><a href="{url}">{url}</a></font>'
            return f"{anchor}[{num}] {title}. Retrieved from {url}"
        return f"{anchor}[{num}] {cleaned or plain}"


def _sanitize_pdf_inline(text: str) -> str:
    """
    Remove/neutralize malformed HTML that can crash ReportLab paraparser.
    - No nested anchors
    - No internal anchors produced by LLM (we control refs/citations ourselves)
    - Drop unknown tags; keep content
    """
    if not text:
        return text

    # Remove any explicit <a ...>...</a> internal links (LLMs sometimes emit broken ones).
    text = re.sub(r'<a\s+[^>]*href\s*=\s*"#?ref-\d+"[^>]*>.*?</a>', r"", text, flags=re.IGNORECASE | re.DOTALL)

    # Remove any <a ...> that contains another <a ...> (nested anchors).
    text = re.sub(r"<a\b[^>]*>[^<]*<a\b[^>]*>.*?</a>.*?</a>", r"", text, flags=re.IGNORECASE | re.DOTALL)

    # Remove orphan <a ...> start tags or end tags.
    text = re.sub(r"<\s*/\s*a\s*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*a\b[^>]*>", "", text, flags=re.IGNORECASE)

    # Strip other potentially problematic tags but keep their inner content.
    text = re.sub(r"</?(div|span|section|article|header|footer|nav|main|aside|figure|figcaption)\b[^>]*>", "", text, flags=re.IGNORECASE)

    return text


# ── Cover page builder ────────────────────────────────────────
def _build_cover_page(topic: str, styles: dict, report_style: Optional[str] = None) -> list:
    """Returns flowables for a professional cover page."""
    elements = []
    elements.append(Spacer(1, 3 * cm))

    # Logo-like top bar
    bar = Table(
        [[""]],
        colWidths=[16.5 * cm],
        rowHeights=[0.8 * cm],
    )
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY)]))
    elements.append(bar)
    elements.append(Spacer(1, 1.5 * cm))

    # Title
    elements.append(Paragraph(topic, styles["ReportTitle"]))
    elements.append(Spacer(1, 0.5 * cm))

    # Subtitle
    elements.append(
        Paragraph("A Comprehensive Research Report", styles["Subtitle"])
    )
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(
        Paragraph(
            "Generated by <b>LynxResearch</b> — Autonomous Multi-Agent Research System",
            styles["Subtitle"],
        )
    )

    elements.append(Spacer(1, 2 * cm))

    # Info box
    from datetime import datetime
    from zoneinfo import ZoneInfo
    date_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%B %d, %Y")
    info_data = [
        ["Report Date", date_str],
        ["Classification", "Research Report"],
        ["Report Style/Category", (report_style or "general").replace("_", " ").title()],
        ["Generated By", "LynxResearch AI System"],
    ]
    info_table = Table(info_data, colWidths=[5 * cm, 11 * cm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), LIGHT_BLUE),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",     (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR",     (1, 0), (1, -1), DARK_GRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
    ]))
    elements.append(info_table)

    elements.append(Spacer(1, 2 * cm))

    # Bottom bar
    elements.append(bar)
    elements.append(PageBreak())
    return elements


# ── Main public function ──────────────────────────────────────
async def build_pdf(run_id: str, markdown_content: str, report_style: Optional[str] = None) -> Optional[str]:
    """
    Main entry point called from runs.py background task.
    Converts the full markdown report → professional PDF using ReportLab.
    Returns absolute path to saved PDF or None on failure.
    """
    try:
        reports_dir = Path(settings.REPORTS_DIR)
        reports_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = reports_dir / f"report_{run_id}.pdf"

        styles = _build_styles()

        # Extract topic from the first # heading in markdown
        topic_match = re.search(r"^#\s+(.+)$", markdown_content, re.MULTILINE)
        topic = topic_match.group(1).strip() if topic_match else "Research Report"

        # Remove the first # heading — we'll render it on the cover page instead
        content_without_title = re.sub(
            r"^#\s+.+\n", "", markdown_content, count=1
        ).strip()
        content_without_title = _truncate_after_references(content_without_title)

        # ── Build document ────────────────────────────────────
        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=2.5 * cm,
            rightMargin=2.5 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm,
            title=topic,
            author="LynxResearch",
            subject="Research Report",
        )

        # ── Assemble all flowables ────────────────────────────
        all_elements = []

        # 1. Cover page
        all_elements.extend(_build_cover_page(topic, styles, report_style=report_style))

        def _build_attempt(enable_links: bool) -> None:
            all_elements_local = []
            all_elements_local.extend(_build_cover_page(topic, styles, report_style=report_style))
            parser = MarkdownParser(styles, enable_links=enable_links)
            body_elements = parser.parse(content_without_title)
            all_elements_local.extend(body_elements)
            doc.build(all_elements_local, canvasmaker=NumberedCanvas)

        # 2/3. Build PDF (retry once with links disabled)
        try:
            _build_attempt(enable_links=True)
        except Exception as e:
            logger.error(f"[PDFBuilder] First build attempt failed: {e}", exc_info=True)
            logger.warning("[PDFBuilder] Retrying PDF build with links disabled (safe mode)")
            _build_attempt(enable_links=False)

        file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ PDF built: {pdf_path} ({file_size_mb:.2f} MB)")
        return str(pdf_path)

    except Exception as e:
        logger.error(f"[PDFBuilder] Failed: {e}", exc_info=True)
        return None


def estimate_page_count(markdown_content: str) -> int:
    """Rough estimate: ~500 words per A4 page."""
    word_count = len(markdown_content.split())
    return max(1, round(word_count / 500))


def _truncate_after_references(content: str) -> str:
    lines = content.splitlines()
    ref_idx = -1
    for i, line in enumerate(lines):
        if re.match(r"^\s*#{1,3}\s*References\s*$", line, flags=re.IGNORECASE):
            ref_idx = i
            break
    if ref_idx == -1:
        return content
    end_idx = len(lines)
    for i in range(ref_idx + 1, len(lines)):
        if re.match(r"^\s*#{1,3}\s+", lines[i]):
            end_idx = i
            break
    return "\n".join(lines[:end_idx]).strip()