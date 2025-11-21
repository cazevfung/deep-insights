"""
PDF to Markdown converter utility.
Simplified version based on pdf-to-markdown script.
"""
import re
import logging
from pathlib import Path
from typing import List, Optional

# Suppress verbose DEBUG logging from PDF parsing libraries
_pdf_loggers = ['pdfminer', 'pdfminer.pdfparser', 'pdfminer.pdfdocument', 
                'pdfminer.pdfinterp', 'pdfminer.pdfpage', 'pdfminer.converter',
                'pdfminer.layout', 'pdfminer.psparser', 'pdfminer.cmapdb',
                'pdfminer.six', 'pypdf', 'PyPDF2', 'pdfplumber']

for logger_name in _pdf_loggers:
    pdf_logger = logging.getLogger(logger_name)
    pdf_logger.setLevel(logging.WARNING)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


class PDFToMarkdownConverter:
    """Convert PDF files to markdown format."""

    BULLET_POINTS = "•◦▪▫●○"

    def __init__(self, pdf_path: Path):
        """
        Initialize converter with PDF path.

        Args:
            pdf_path: Path to the PDF file
        """
        if fitz is None:
            raise ImportError("PyMuPDF (fitz) is required. Install with: pip install PyMuPDF")
        
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    def convert(self) -> str:
        """
        Convert PDF to markdown format.

        Returns:
            Markdown content as string
        """
        try:
            doc = fitz.open(self.pdf_path)
            markdown_content = ""
            tables = self._extract_tables() if pdfplumber else []
            table_index = 0

            for page_num, page in enumerate(doc):
                page_content = ""
                blocks = page.get_text("dict")["blocks"]
                page_height = page.rect.height
                links = self._extract_links(page)

                for block in blocks:
                    if block["type"] == 0:  # Text block
                        page_content += self._process_text_block(
                            block, page_height, links
                        )
                    elif block["type"] == 1:
                        # Skip image placeholders until we add real image support
                        continue

                # Insert tables at their approximate positions
                while (
                    table_index < len(tables)
                    and tables[table_index]["page"] == page_num
                ):
                    page_content += (
                        "\n\n"
                        + self._table_to_markdown(tables[table_index]["content"])
                        + "\n\n"
                    )
                    table_index += 1

                markdown_content += page_content + "\n\n---\n\n"

            doc.close()
            markdown_content = self._post_process_markdown(markdown_content)
            return markdown_content

        except Exception as e:
            raise RuntimeError(f"Error converting PDF to markdown: {e}") from e

    def _extract_tables(self) -> List[dict]:
        """Extract tables from PDF using pdfplumber."""
        tables = []
        if pdfplumber is None:
            return tables

        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_number, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    if len(page_tables) > 128:  # Skip pages with too many tables
                        continue
                    for table in page_tables:
                        tables.append({"page": page_number, "content": table})
        except Exception:
            # If table extraction fails, continue without tables
            pass
        return tables

    def _table_to_markdown(self, table) -> str:
        """Convert a table to markdown format."""
        if not table:
            return ""

        try:
            # Clean table data
            table = [
                ["" if cell is None else str(cell).strip() for cell in row]
                for row in table
            ]
            
            if not table or not table[0]:
                return ""

            # Calculate column widths
            num_cols = max(len(row) for row in table) if table else 0
            col_widths = [0] * num_cols
            
            for row in table:
                for j, cell in enumerate(row):
                    if j < num_cols:
                        col_widths[j] = max(col_widths[j], len(cell))

            markdown = ""
            for i, row in enumerate(table):
                # Pad row to match column count
                padded_row = row + [""] * (num_cols - len(row))
                formatted_row = [
                    cell.ljust(col_widths[j]) for j, cell in enumerate(padded_row)
                ]
                markdown += "| " + " | ".join(formatted_row) + " |\n"

                # Add separator after header row
                if i == 0:
                    markdown += (
                        "|" + "|".join(["-" * (width + 2) for width in col_widths]) + "|\n"
                    )

            return markdown
        except Exception:
            return ""

    def _extract_links(self, page) -> List[dict]:
        """Extract links from the given page."""
        links = []
        try:
            for link in page.get_links():
                if link["kind"] == 2:  # URI link
                    links.append({"rect": link["from"], "uri": link["uri"]})
        except Exception:
            pass
        return links

    def _process_text_block(self, block: dict, page_height: float, links: List[dict]) -> str:
        """Process a text block and convert it to markdown."""
        try:
            block_rect = block["bbox"]
            # Skip headers and footers
            if block_rect[1] < 50 or block_rect[3] > page_height - 50:
                return ""

            block_text = ""
            last_y1 = None
            last_font_size = None

            for line in block["lines"]:
                line_text = ""
                curr_font_size = [span["size"] for span in line["spans"]]

                for span in line["spans"]:
                    text = span["text"]
                    font_size = span["size"]
                    flags = span["flags"]
                    span_rect = span["bbox"]

                    # Check for horizontal line
                    if self._is_horizontal_line(text):
                        line_text += "\n---\n"
                        continue

                    text = self._clean_text(text)

                    if text.strip():
                        # Check for headers based on font size
                        header_level = self._get_header_level(font_size)
                        if header_level > 0:
                            text = f"\n{'#' * header_level} {text}\n\n"
                        else:
                            # Apply formatting
                            text = self._apply_formatting(text, flags)

                    # Check for links
                    for link in links:
                        try:
                            span_rect_fitz = fitz.Rect(span_rect)
                            link_rect_fitz = fitz.Rect(link["rect"])
                            if span_rect_fitz.intersects(link_rect_fitz):
                                text = f"[{text.strip()}]({link['uri']})"
                                break
                        except Exception:
                            # If rect conversion fails, skip link
                            pass

                    line_text += text

                # Add line break if needed
                if last_y1 is not None:
                    avg_last_font_size = (
                        sum(last_font_size) / len(last_font_size)
                        if last_font_size
                        else 0
                    )
                    avg_current_font_size = sum(curr_font_size) / len(curr_font_size)
                    font_size_changed = (
                        abs(avg_current_font_size - avg_last_font_size) > 1
                    )

                    if abs(line["bbox"][3] - last_y1) > 2 or font_size_changed:
                        block_text += "\n"

                block_text += self._clean_text(line_text) + " "
                last_font_size = curr_font_size
                last_y1 = line["bbox"][3]

            # Process markdown formatting for lists
            markdown_content = ""
            lines = block_text.split("\n")
            list_counter = 0

            for line in lines:
                clean_line = self._clean_text(line)

                if self._is_bullet_point(clean_line):
                    markdown_content += "\n" + self._convert_bullet_to_markdown(clean_line)
                    list_counter = 0
                elif self._is_numbered_list_item(clean_line):
                    list_counter += 1
                    markdown_content += (
                        "\n" + self._convert_numbered_list_to_markdown(clean_line, list_counter)
                    )
                else:
                    markdown_content += f"{clean_line}\n"
                    list_counter = 0

            return markdown_content + "\n"

        except Exception:
            return ""

    def _clean_text(self, text: str) -> str:
        """Clean the given text by removing extra spaces."""
        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    def _apply_formatting(self, text: str, flags: int) -> str:
        """Apply markdown formatting to the given text based on flags."""
        text = text.strip()
        if not text:
            return text

        is_bold = flags & 2**4
        is_italic = flags & 2**1
        is_monospace = flags & 2**3
        is_superscript = flags & 2**0
        is_subscript = flags & 2**5

        if is_monospace:
            text = f"`{text}`"
        elif is_superscript and not bool(re.search(r"\s+", text)):
            text = f"^{text}^"
        elif is_subscript and not bool(re.search(r"\s+", text)):
            text = f"~{text}~"

        if is_bold and is_italic:
            text = f"***{text}***"
        elif is_bold:
            text = f"**{text}**"
        elif is_italic:
            text = f"*{text}*"

        return f" {text} "

    def _is_bullet_point(self, text: str) -> bool:
        """Check if the given text is a bullet point."""
        return text.strip().startswith(tuple(self.BULLET_POINTS))

    def _convert_bullet_to_markdown(self, text: str) -> str:
        """Convert a bullet point to markdown format."""
        text = re.sub(r"^\s*", "", text)
        return re.sub(f"^[{re.escape(self.BULLET_POINTS)}]\s*", "- ", text)

    def _is_numbered_list_item(self, text: str) -> bool:
        """Check if the given text is a numbered list item."""
        return bool(re.match(r"^\d+\s{0,3}[.)]", text.strip()))

    def _convert_numbered_list_to_markdown(self, text: str, list_counter: int) -> str:
        """Convert a numbered list item to markdown format."""
        text = re.sub(r"^\s*", "", text)
        return re.sub(r"^\d+\s{0,3}[.)]", f"{list_counter}. ", text)

    def _is_horizontal_line(self, text: str) -> bool:
        """Check if the given text represents a horizontal line."""
        return bool(re.match(r"^[_-]+$", text.strip()))

    def _get_header_level(self, font_size: float) -> int:
        """Determine header level based on font size."""
        if font_size > 24:
            return 1
        elif font_size > 20:
            return 2
        elif font_size > 18:
            return 3
        elif font_size > 16:
            return 4
        elif font_size > 14:
            return 5
        elif font_size > 12:
            return 6
        else:
            return 0

    def _post_process_markdown(self, markdown_content: str) -> str:
        """Post-process the markdown content."""
        try:
            # Remove excessive blank lines while preserving single paragraph breaks
            lines = markdown_content.splitlines()
            cleaned_lines = []
            previous_blank = False
            for line in lines:
                stripped_line = line.rstrip()
                is_blank = stripped_line == ""
                if is_blank:
                    if previous_blank:
                        continue
                    cleaned_lines.append("")
                    previous_blank = True
                else:
                    cleaned_lines.append(stripped_line)
                    previous_blank = False
            markdown_content = "\n".join(cleaned_lines)
            # Remove page numbers (standalone numbers)
            markdown_content = re.sub(r"^(\d+)\s*$", "", markdown_content, flags=re.MULTILINE)
            # Remove multiple spaces
            markdown_content = re.sub(r" +", " ", markdown_content)
            # Remove duplicate horizontal lines
            markdown_content = re.sub(r"\s*(---\n)+", "\n\n---\n", markdown_content)
            # Remove headers in the middle of lines
            markdown_content = re.sub(
                r"^#{1,6}\s.*\n",
                lambda m: re.sub(r"#", "", m.group(0)) if m.group(0).count("#") > 1 else m.group(0),
                markdown_content,
                flags=re.MULTILINE,
            )
            return markdown_content.strip()
        except Exception:
            return markdown_content


def convert_pdf_to_markdown(pdf_path: Path) -> str:
    """
    Convenience function to convert PDF to markdown.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Markdown content as string
    """
    converter = PDFToMarkdownConverter(pdf_path)
    return converter.convert()

