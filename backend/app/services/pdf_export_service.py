"""
PDF export service for research reports.

Builds a branded report PDF that exactly matches the web app design:
- Inter font family (with CJK fallback)
- Tailwind color palette (#FEC74A golden yellow, #031C34 dark)
- Card-based layout matching Phase3StepCard component
- Complete data export including all Phase 3 sections
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
import re
from loguru import logger
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    ListFlowable,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# Lazy import to avoid slow startup when service is unused.
try:
    from research.session import ResearchSession
except Exception:  # pragma: no cover - defensive, FastAPI handles import errors
    ResearchSession = None  # type: ignore


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
LOGO_PATH = PROJECT_ROOT / "client" / "public" / "logo.png"
FONTS_DIR = Path(__file__).parent / "fonts" / "extras" / "ttf"


@dataclass
class KeyClaim:
    """A key claim with supporting evidence."""
    claim: str
    supporting_evidence: Optional[str]


@dataclass
class FiveWhyItem:
    """Five Whys analysis item."""
    level: int
    question: str
    answer: str


@dataclass
class AnalysisDetails:
    """Analysis section details."""
    five_whys: List[FiveWhyItem] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    uncertainties: List[str] = field(default_factory=list)


@dataclass
class StepContent:
    """Complete Phase 3 step content matching web structure."""
    summary: Optional[str]
    article: Optional[str]
    key_claims: List[KeyClaim]
    analysis: AnalysisDetails
    insights: Optional[str]


@dataclass
class StepCard:
    """Phase 3 step card for export."""
    index: int
    title: str
    confidence: Optional[float]
    timestamp: Optional[str]
    content: StepContent


@dataclass
class ReportPayload:
    """Normalized data used to render the PDF."""
    session_id: str
    batch_id: Optional[str]
    research_objective: str
    prepared_by: Optional[str]
    exported_at: datetime
    step_cards: List[StepCard]
    final_article_blocks: List["ArticleBlock"]


@dataclass
class ArticleBlock:
    """Represents a segment of the markdown article."""
    text: str
    style: str
    bullet: bool = False


class PdfExportError(Exception):
    """Base exception for PDF export failures."""


class SessionNotFoundError(PdfExportError):
    """Raised when the requested research session cannot be found."""


class PdfExportService:
    """Service responsible for composing the PDF matching web app design."""

    # Exact Tailwind theme colors from client/tailwind.config.js
    primary_500 = colors.HexColor("#FEC74A")      # primary yellow
    primary_600 = colors.HexColor("#D4A03D")      # darker yellow
    primary_200 = colors.HexColor("#FFF2CC")      # light yellow
    primary_100 = colors.HexColor("#FFF9E6")      # very light yellow
    
    neutral_black = colors.HexColor("#031C34")    # main text
    neutral_800 = colors.HexColor("#1E3A4D")      # secondary text
    neutral_700 = colors.HexColor("#365566")      # tertiary text
    neutral_600 = colors.HexColor("#4D6B7E")      # muted text
    neutral_500 = colors.HexColor("#5D87A1")      # light muted text
    neutral_400 = colors.HexColor("#9EB7C7")      # very light text
    neutral_300 = colors.HexColor("#DFE7EC")      # borders
    neutral_200 = colors.HexColor("#E7EDF1")      # light borders
    neutral_100 = colors.HexColor("#F0F3F6")      # subtle bg
    neutral_50 = colors.HexColor("#F8F7F9")       # lightest bg
    neutral_white = colors.HexColor("#FFFFFF")    # white
    
    # Accent colors
    yellow_100 = colors.HexColor("#FEF3C7")       # confidence badge bg
    yellow_800 = colors.HexColor("#92400E")       # confidence badge text
    yellow_50 = colors.HexColor("#FEFCE8")        # insights bg
    yellow_500 = colors.HexColor("#EAB308")       # insights border
    green_500 = colors.HexColor("#22C55E")        # high confidence
    red_500 = colors.HexColor("#EF4444")          # low confidence

    page_margins = (0.75 * inch, 0.75 * inch, 0.85 * inch, 0.75 * inch)

    def __init__(self) -> None:
        self._register_fonts()
        self.styles = self._build_styles()

    def _register_fonts(self) -> None:
        """Register Inter fonts for Latin with CJK fallback."""
        try:
            # Register Inter fonts
            inter_regular = FONTS_DIR / "Inter-Regular.ttf"
            inter_medium = FONTS_DIR / "Inter-Medium.ttf"
            inter_semibold = FONTS_DIR / "Inter-SemiBold.ttf"
            inter_bold = FONTS_DIR / "Inter-Bold.ttf"
            
            if inter_regular.exists():
                pdfmetrics.registerFont(TTFont("Inter", str(inter_regular)))
                logger.debug("Registered Inter-Regular font")
            if inter_medium.exists():
                pdfmetrics.registerFont(TTFont("Inter-Medium", str(inter_medium)))
                logger.debug("Registered Inter-Medium font")
            if inter_semibold.exists():
                pdfmetrics.registerFont(TTFont("Inter-SemiBold", str(inter_semibold)))
                logger.debug("Registered Inter-SemiBold font")
            if inter_bold.exists():
                pdfmetrics.registerFont(TTFont("Inter-Bold", str(inter_bold)))
                logger.debug("Registered Inter-Bold font")
                
            # Register CJK fallback
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            logger.debug("Registered STSong-Light for CJK support")
        except Exception as exc:
            logger.warning("Failed to register some fonts: %s", exc)
            # Fallback to CJK only
            try:
                pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
            except Exception:
                pass

    def _build_styles(self) -> StyleSheet1:
        """Create style sheet matching web app typography."""
        styles = getSampleStyleSheet()
        
        # Determine which font to use
        base_font = "Inter" if self._has_font("Inter") else "STSong-Light"
        medium_font = "Inter-Medium" if self._has_font("Inter-Medium") else base_font
        semibold_font = "Inter-SemiBold" if self._has_font("Inter-SemiBold") else base_font
        bold_font = "Inter-Bold" if self._has_font("Inter-Bold") else base_font

        # Page headings
        styles.add(
            ParagraphStyle(
                name="PageHeading",
                fontName=bold_font,
                fontSize=20,
                leading=26,
                spaceAfter=20,
                spaceBefore=12,
                textColor=self.neutral_black,
            )
        )

        # Section headings
        styles.add(
            ParagraphStyle(
                name="SectionHeading",
                fontName=semibold_font,
                fontSize=14,
                leading=18,
                spaceAfter=12,
                spaceBefore=16,
                textColor=self.neutral_800,
            )
        )

        # Subsection headings
        styles.add(
            ParagraphStyle(
                name="SubsectionHeading",
                fontName=medium_font,
                fontSize=12,
                leading=16,
                spaceAfter=8,
                spaceBefore=10,
                textColor=self.neutral_800,
            )
        )

        # Card title
        styles.add(
            ParagraphStyle(
                name="CardTitle",
                fontName=semibold_font,
                fontSize=16,
                leading=22,
                textColor=self.neutral_800,
                spaceAfter=6,
            )
        )

        # Card subtitle
        styles.add(
            ParagraphStyle(
                name="CardSubtitle",
                fontName=base_font,
                fontSize=11,
                leading=15,
                textColor=self.neutral_500,
                spaceAfter=8,
            )
        )

        # Label text
        styles.add(
            ParagraphStyle(
                name="Label",
                fontName=medium_font,
                fontSize=12,
                leading=16,
                textColor=self.neutral_800,
                spaceBefore=10,
                spaceAfter=6,
            )
        )

        # Body text
        styles.add(
            ParagraphStyle(
                name="Body",
                fontName=base_font,
                fontSize=11,
                leading=18,
                textColor=self.neutral_700,
            )
        )

        # Small body text
        styles.add(
            ParagraphStyle(
                name="BodySmall",
                fontName=base_font,
                fontSize=10,
                leading=16,
                textColor=self.neutral_600,
            )
        )

        # Caption
        styles.add(
            ParagraphStyle(
                name="Caption",
                fontName=base_font,
                fontSize=10,
                leading=14,
                textColor=self.neutral_500,
            )
        )

        # Badge text
        styles.add(
            ParagraphStyle(
                name="Badge",
                fontName=medium_font,
                fontSize=9,
                leading=12,
                textColor=self.yellow_800,
            )
        )

        return styles

    def _has_font(self, font_name: str) -> bool:
        """Check if a font is registered."""
        try:
            pdfmetrics.getFont(font_name)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build_pdf(self, payload: ReportPayload) -> bytes:
        """Render the PDF document."""
        buffer = BytesIO()

        doc = BaseDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=self.page_margins[0],
            rightMargin=self.page_margins[1],
            topMargin=self.page_margins[2],
            bottomMargin=self.page_margins[3],
        )

        frame = Frame(
            doc.leftMargin,
            doc.bottomMargin,
            doc.width,
            doc.height,
            id="normal-frame",
        )

        page_template = PageTemplate(
            id="phase-report",
            frames=[frame],
            onPage=lambda canvas, _: self._draw_header_footer(canvas, doc, payload),
        )
        doc.addPageTemplates([page_template])

        story: List = []
        story.extend(self._build_body(payload))

        doc.build(story)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    # Page chrome
    # ------------------------------------------------------------------
    def _draw_header_footer(self, canvas, doc, payload: ReportPayload) -> None:
        """Render brand header & footer matching web app style."""
        canvas.saveState()
        header_y = doc.pagesize[1] - doc.topMargin + 34

        # Top accent bar
        canvas.setStrokeColor(self.primary_200)
        canvas.setLineWidth(2)
        canvas.line(doc.leftMargin, header_y + 10, doc.leftMargin + doc.width, header_y + 10)

        # Title
        font_name = "Inter-Bold" if self._has_font("Inter-Bold") else "STSong-Light"
        canvas.setFont(font_name, 15)
        canvas.setFillColor(self.neutral_black)
        canvas.drawString(doc.leftMargin, header_y - 6, "Research Tool")

        # Logo
        if LOGO_PATH.exists():
            try:
                canvas.drawImage(
                    str(LOGO_PATH),
                    doc.pagesize[0] - doc.rightMargin - 34,
                    header_y - 18,
                    width=26,
                    height=26,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception as exc:
                logger.debug("Unable to draw logo: %s", exc)

        # Footer
        footer_y = doc.bottomMargin - 26
        font_name = "Inter" if self._has_font("Inter") else "STSong-Light"
        canvas.setFont(font_name, 8)
        canvas.setFillColor(self.neutral_500)
        meta_text = f"Session {payload.session_id}"
        if payload.batch_id:
            meta_text += f" • Batch {payload.batch_id}"
        meta_text += f" • Exported {payload.exported_at.strftime('%Y-%m-%d %H:%M')}"
        canvas.drawString(doc.leftMargin, footer_y, meta_text)

        canvas.drawRightString(
            doc.leftMargin + doc.width,
            footer_y,
            f"Page {canvas.getPageNumber()}",
        )
        
        canvas.setStrokeColor(self.neutral_300)
        canvas.setLineWidth(0.5)
        canvas.line(doc.leftMargin, footer_y + 14, doc.leftMargin + doc.width, footer_y + 14)
        
        canvas.restoreState()

    # ------------------------------------------------------------------
    # Body content
    # ------------------------------------------------------------------
    def _build_body(self, payload: ReportPayload) -> List:
        story: List = []

        story.append(Spacer(1, 28))

        # Research Objective
        story.append(Paragraph("Research Objective", self.styles["PageHeading"]))
        story.append(self._build_objective_card(payload))
        story.append(Spacer(1, 24))

        # Phase 3 Steps
        if payload.step_cards:
            story.append(Paragraph("Research Execution Summary", self.styles["PageHeading"]))
            story.append(Spacer(1, 4))
            for card in payload.step_cards:
                # Add all elements from the step card (allows page breaks)
                card_elements = self._build_complete_step_card(card)
                story.extend(card_elements)
                story.append(Spacer(1, 16))

        # Final article
        story.append(Spacer(1, 12))
        story.append(Paragraph("Final Report Article", self.styles["PageHeading"]))
        story.append(self._build_article_section(payload.final_article_blocks))

        return story

    def _build_objective_card(self, payload: ReportPayload) -> Table:
        """Build objective card."""
        rows = [
            [Paragraph(payload.research_objective or "暂无研究目标", self.styles["CardTitle"])]
        ]

        if payload.prepared_by:
            rows.append([Paragraph(payload.prepared_by, self.styles["Caption"])])

        table = Table(rows, colWidths=[None])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), self.neutral_white),
                    ("BOX", (0, 0), (-1, -1), 1, self.neutral_300),
                    ("ROUNDEDCORNERS", [8, 8, 8, 8]),
                    ("TOPPADDING", (0, 0), (-1, -1), 16),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
                    ("LEFTPADDING", (0, 0), (-1, -1), 16),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ]
            )
        )
        return table

    def _build_complete_step_card(self, card: StepCard) -> List:
        """Build complete step card with all content sections."""
        elements: List = []
        
        # Card header
        header_rows = []
        title_text = f'<b>Step {card.index}:</b> {card.title}'
        header_rows.append([Paragraph(title_text, self.styles["CardTitle"])])
        
        if card.timestamp:
            header_rows.append([Paragraph(card.timestamp, self.styles["CardSubtitle"])])
        
        if card.confidence is not None:
            confidence_pct = int(card.confidence * 100)
            badge_style = ParagraphStyle(
                'ConfidenceBadge',
                parent=self.styles["Badge"],
                backColor=self.yellow_100,
            )
            header_rows.append([Paragraph(f'<b>Confidence: {confidence_pct}%</b>', badge_style)])
        
        header_table = Table(header_rows, colWidths=[None])
        header_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), self.neutral_white),
                    ("BOX", (0, 0), (-1, -1), 1, self.neutral_200),
                    ("ROUNDEDCORNERS", [12, 12, 0, 0]),
                    ("TOPPADDING", (0, 0), (-1, -1), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                    ("LEFTPADDING", (0, 0), (-1, -1), 14),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ]
            )
        )
        elements.append(header_table)

        # Content sections (allow page breaks between them)
        content = card.content
        
        if content.summary:
            elements.append(self._build_content_section("📝 摘要", content.summary))
            elements.append(Spacer(1, 8))
        
        if content.key_claims:
            elements.extend(self._build_key_claims_section(content.key_claims))
            elements.append(Spacer(1, 8))
        
        if content.article:
            elements.append(self._build_content_section("📄 深度文章", content.article))
            elements.append(Spacer(1, 8))
        
        if content.analysis.five_whys or content.analysis.assumptions or content.analysis.uncertainties:
            elements.extend(self._build_analysis_section(content.analysis))
            elements.append(Spacer(1, 8))
        
        if content.insights:
            elements.append(self._build_insights_box(content.insights))
            elements.append(Spacer(1, 8))
        
        return elements

    def _get_confidence_color(self, confidence: float):
        """Get color based on confidence level."""
        if confidence >= 0.8:
            return self.green_500
        elif confidence >= 0.6:
            return self.yellow_500
        else:
            return self.red_500

    def _build_content_section(self, title: str, text: str) -> KeepTogether:
        """Build a simple content section."""
        elements = [
            Paragraph(f'<b>{title}</b>', self.styles["Label"]),
            Spacer(1, 2),
            Paragraph(self._format_inline(text), self.styles["Body"]),
        ]
        return KeepTogether(elements)

    def _build_key_claims_section(self, claims: List[KeyClaim]) -> List:
        """Build key claims section."""
        elements = [
            Paragraph('<b>🔑 主要观点</b>', self.styles["Label"]),
            Spacer(1, 4)
        ]
        
        for claim in claims:
            claim_paras = [
                Paragraph(f'• <b>{self._format_inline(claim.claim)}</b>', self.styles["Body"])
            ]
            if claim.supporting_evidence:
                claim_paras.append(
                    Paragraph(
                        f'  <i>证据支持：</i>{self._format_inline(claim.supporting_evidence)}',
                        self.styles["BodySmall"]
                    )
                )
                claim_paras.append(Spacer(1, 6))
            
            elements.extend(claim_paras)
        
        return elements

    def _build_analysis_section(self, analysis: AnalysisDetails) -> List:
        """Build analysis section with Five Whys, Assumptions, Uncertainties."""
        elements = [
            Paragraph('<b>🔍 Q&A</b>', self.styles["Label"]),
            Spacer(1, 6)
        ]
        
        # Five Whys
        if analysis.five_whys:
            elements.append(Paragraph('<b>Five Whys:</b>', self.styles["SubsectionHeading"]))
            for item in analysis.five_whys:
                elements.append(
                    Paragraph(
                        f'<b>Q:</b> {self._format_inline(item.question)}',
                        self.styles["BodySmall"]
                    )
                )
                elements.append(
                    Paragraph(
                        f'<b>A:</b> {self._format_inline(item.answer)}',
                        self.styles["BodySmall"]
                    )
                )
                elements.append(Spacer(1, 4))
        
        # Assumptions
        if analysis.assumptions:
            elements.append(Spacer(1, 4))
            elements.append(Paragraph('<b>本分析有何假设？</b>', self.styles["SubsectionHeading"]))
            elements.append(self._build_bullet_list(analysis.assumptions))
            elements.append(Spacer(1, 4))
        
        # Uncertainties
        if analysis.uncertainties:
            elements.append(Spacer(1, 4))
            elements.append(Paragraph('<b>有什么未能确定？</b>', self.styles["SubsectionHeading"]))
            elements.append(self._build_bullet_list(analysis.uncertainties))
        
        return elements

    def _build_insights_box(self, insights: str) -> KeepTogether:
        """Build highlighted insights box."""
        elements = [
            Paragraph('<b>💡 洞察</b>', self.styles["Label"]),
            Spacer(1, 4),
            Paragraph(self._format_inline(insights), self.styles["Body"])
        ]
        return KeepTogether(elements)

    def _build_bullet_list(self, items: Iterable[str]) -> ListFlowable:
        """Build bullet list."""
        bullet_paragraphs = [
            Paragraph(self._format_inline(text), self.styles["BodySmall"])
            for text in items
        ]
        return ListFlowable(
            bullet_paragraphs,
            bulletType="bullet",
            start=None,
            leftIndent=18,
            bulletOffsetY=-2,
        )

    def _build_article_section(self, blocks: List[ArticleBlock]) -> Table:
        """Build final article."""
        rows: List[List] = []
        for block in blocks:
            if block.bullet:
                rows.append([self._build_bullet_list([block.text])])
            else:
                style = self.styles.get(block.style, self.styles["Body"])
                rows.append([Paragraph(self._format_inline(block.text), style)])

        table = Table(rows, colWidths=[None])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), self.neutral_white),
                    ("BOX", (0, 0), (-1, -1), 1, self.neutral_300),
                    ("ROUNDEDCORNERS", [8, 8, 8, 8]),
                    ("TOPPADDING", (0, 0), (-1, -1), 18),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
                    ("LEFTPADDING", (0, 0), (-1, -1), 18),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 18),
                ]
            )
        )
        return table

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _format_inline(self, text: str) -> str:
        """Apply minimal markup conversions."""
        formatted = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        formatted = re.sub(r"__(.+?)__", r"<b>\1</b>", formatted)
        formatted = formatted.replace("`", "")
        formatted = formatted.replace("\n", "<br/>")
        return formatted


# ----------------------------------------------------------------------
# Data normalization helpers
# ----------------------------------------------------------------------
def _load_session(session_id: str):
    if ResearchSession is None:
        raise PdfExportError("ResearchSession module not available")

    try:
        return ResearchSession.load(session_id)
    except FileNotFoundError as exc:
        logger.warning("Session not found for PDF export: %s", session_id)
        raise SessionNotFoundError(f"Session {session_id} not found") from exc


def _extract_step_cards(session) -> List[StepCard]:
    """Extract complete step data matching web app structure."""
    steps = []
    research_plan = {step.get("step_id"): step for step in session.metadata.get("research_plan") or []}

    for idx, key in enumerate(sorted(session.scratchpad.keys()), start=1):
        entry = session.scratchpad[key]
        step_id = entry.get("step_id")
        plan_goal = research_plan.get(step_id, {}).get("goal")
        title = _truncate(plan_goal or f"Step {step_id}", 120)

        # Extract findings
        findings_root = entry.get("findings", {})
        findings = findings_root.get("findings") if isinstance(findings_root, dict) and "findings" in findings_root else findings_root
        
        # Extract points of interest
        poi = findings.get("points_of_interest", {}) if isinstance(findings, dict) else {}
        
        # Extract analysis details
        analysis_details = findings.get("analysis_details", {}) if isinstance(findings, dict) else {}
        
        # Build content
        content = StepContent(
            summary=findings.get("summary") if isinstance(findings, dict) else None,
            article=findings.get("article") if isinstance(findings, dict) else None,
            key_claims=_extract_key_claims(poi.get("key_claims", [])),
            analysis=AnalysisDetails(
                five_whys=_extract_five_whys(analysis_details.get("five_whys", [])),
                assumptions=analysis_details.get("assumptions", []) if isinstance(analysis_details, dict) else [],
                uncertainties=analysis_details.get("uncertainties", []) if isinstance(analysis_details, dict) else [],
            ),
            insights=entry.get("insights"),
        )

        step_card = StepCard(
            index=idx,
            title=title,
            confidence=entry.get("confidence"),
            timestamp=_format_timestamp(entry.get("timestamp")),
            content=content,
        )
        steps.append(step_card)

    return steps


def _extract_key_claims(claims_data: list) -> List[KeyClaim]:
    """Extract key claims from data."""
    result = []
    for claim in claims_data:
        if isinstance(claim, dict):
            result.append(KeyClaim(
                claim=str(claim.get("claim", "")),
                supporting_evidence=claim.get("supporting_evidence")
            ))
    return result


def _extract_five_whys(five_whys_data: list) -> List[FiveWhyItem]:
    """Extract Five Whys from data."""
    result = []
    for idx, item in enumerate(five_whys_data):
        if isinstance(item, dict):
            result.append(FiveWhyItem(
                level=item.get("level", idx + 1),
                question=str(item.get("question", "")),
                answer=str(item.get("answer", ""))
            ))
    return result


def _parse_article_blocks(markdown_text: str) -> List[ArticleBlock]:
    blocks: List[ArticleBlock] = []
    current_bullets: List[str] = []
    lines = markdown_text.splitlines()

    def flush_bullets() -> None:
        nonlocal current_bullets
        for item in current_bullets:
            blocks.append(ArticleBlock(text=item, style="Body", bullet=True))
        current_bullets = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_bullets()
            blocks.append(ArticleBlock(text="", style="Body"))
            continue

        if line.startswith("# "):
            flush_bullets()
            blocks.append(ArticleBlock(text=line[2:], style="PageHeading"))
            continue

        if line.startswith("## "):
            flush_bullets()
            blocks.append(ArticleBlock(text=line[3:], style="SectionHeading"))
            continue

        if line.startswith("- "):
            current_bullets.append(line[2:])
            continue

        flush_bullets()
        blocks.append(ArticleBlock(text=line, style="Body"))

    flush_bullets()
    return blocks


def _format_timestamp(timestamp: Optional[str]) -> Optional[str]:
    if not timestamp:
        return None
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("Updated %Y-%m-%d %H:%M")
    except ValueError:
        return timestamp


def _truncate(text: str, max_length: int) -> str:
    text = str(text).strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def build_report_payload(session_id: str) -> ReportPayload:
    """Collect session data and normalize for PDF rendering."""
    session = _load_session(session_id)

    metadata = session.metadata or {}
    batch_id = metadata.get("batch_id")
    objective = metadata.get("selected_goal") or metadata.get("user_topic") or "未提供研究目标"

    phase4 = (session.phase_artifacts or {}).get("phase4", {})
    phase4_data = phase4.get("data") or {}
    final_article = (
        phase4_data.get("report_content")
        or phase4_data.get("final_report")
        or metadata.get("final_report")
        or ""
    )

    if not final_article:
        logger.info("No final article found for session %s; generating placeholder", session_id)
        final_article = "最终报告内容尚未生成。"

    logger.debug("Building PDF payload for session %s", session_id)

    return ReportPayload(
        session_id=session_id,
        batch_id=batch_id,
        research_objective=objective,
        prepared_by=metadata.get("researcher_name") or None,
        exported_at=datetime.utcnow(),
        step_cards=_extract_step_cards(session),
        final_article_blocks=_parse_article_blocks(final_article),
    )


def generate_phase_report_pdf(session_id: str) -> bytes:
    """High-level utility to produce the PDF for a given session."""
    payload = build_report_payload(session_id)
    service = PdfExportService()
    return service.build_pdf(payload)


__all__ = [
    "generate_phase_report_pdf",
    "build_report_payload",
    "PdfExportError",
    "SessionNotFoundError",
]
