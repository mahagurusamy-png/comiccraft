from datetime import datetime
from pathlib import Path
import re
import unicodedata

from fpdf import FPDF
from PIL import Image

from app.config import BASE_DIR
from app.schemas import Panel


EXPORT_DIR = (
    BASE_DIR
    / "static"
    / "exports"
)

EXPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# A4 page width = 210 mm
# Left/right margin = 15 mm
CONTENT_WIDTH = 180


def _clean_text(value: str) -> str:
    """
    Make AI-generated text safer for PDF rendering.
    """

    if not value:
        return ""

    # Normalize unicode
    value = unicodedata.normalize(
        "NFKC",
        str(value),
    )

    # Replace common special characters
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2026": "...",
        "\u00a0": " ",
        "\u2022": "-",
        "\u200b": "",
        "\ufeff": "",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    # Remove unsupported control characters
    value = "".join(
        char
        for char in value
        if char == "\n"
        or char == "\t"
        or ord(char) >= 32
    )

    # Normalize whitespace
    value = re.sub(
        r"[ \t]+",
        " ",
        value,
    )

    # Prevent extremely long unbreakable words
    def break_long_word(match):
        word = match.group(0)

        if len(word) <= 35:
            return word

        chunks = [
            word[i:i + 35]
            for i in range(0, len(word), 35)
        ]

        return " ".join(chunks)

    value = re.sub(
        r"\S{36,}",
        break_long_word,
        value,
    )

    return value.strip()


def _write_text(
    pdf: FPDF,
    text: str,
    size: int = 11,
    style: str = "",
    line_height: float = 7,
):
    """
    Safely write text into the PDF.
    """

    text = _clean_text(text)

    if not text:
        return

    pdf.set_font(
        "Helvetica",
        style,
        size,
    )

    # Always reset X position to left margin.
    pdf.set_x(pdf.l_margin)

    pdf.multi_cell(
        w=CONTENT_WIDTH,
        h=line_height,
        text=text,
    )

    # Reset cursor again for next block.
    pdf.set_x(pdf.l_margin)


def _fit_image(
    pdf: FPDF,
    path: str,
    x: float,
    y: float,
    max_w: float,
    max_h: float,
):
    """
    Fit image inside given PDF dimensions.
    """

    with Image.open(path) as image:
        width, height = image.size

    if width <= 0 or height <= 0:
        return

    ratio = min(
        max_w / width,
        max_h / height,
    )

    final_width = width * ratio
    final_height = height * ratio

    pdf.image(
        path,
        x=x,
        y=y,
        w=final_width,
        h=final_height,
    )


def save_pdf(
    title: str,
    panels: list[Panel],
) -> Path:
    """
    Generate multi-page A4 comic PDF.
    """

    pdf = FPDF(
        orientation="P",
        unit="mm",
        format="A4",
    )

    pdf.set_margins(
        left=15,
        top=15,
        right=15,
    )

    pdf.set_auto_page_break(
        auto=True,
        margin=15,
    )

    for panel in panels:

        pdf.add_page()

        # =====================================
        # PANEL TITLE
        # =====================================

        panel_title = (
            f"Panel {panel.panel_number}: "
            f"{panel.title}"
        )

        _write_text(
            pdf,
            panel_title,
            size=18,
            style="B",
            line_height=9,
        )

        # =====================================
        # IMAGE
        # =====================================

        if panel.image_path:

            image_path = (
                BASE_DIR
                / panel.image_path.lstrip("/")
            )

            if image_path.exists():

                # Keep image below title
                image_y = pdf.get_y() + 5

                _fit_image(
                    pdf,
                    str(image_path),
                    15,
                    image_y,
                    180,
                    110,
                )

                # Move cursor below image
                pdf.set_y(
                    image_y + 115
                )

        # =====================================
        # SCENE DESCRIPTION
        # =====================================

        _write_text(
            pdf,
            panel.scene_description,
            size=11,
            style="I",
            line_height=7,
        )

        pdf.ln(2)

        # =====================================
        # CAPTION
        # =====================================

        _write_text(
            pdf,
            "Caption",
            size=11,
            style="B",
            line_height=7,
        )

        _write_text(
            pdf,
            panel.caption,
            size=11,
            style="",
            line_height=7,
        )

        pdf.ln(2)

        # =====================================
        # NARRATION
        # =====================================

        _write_text(
            pdf,
            "Narration",
            size=11,
            style="B",
            line_height=7,
        )

        _write_text(
            pdf,
            panel.narration,
            size=11,
            style="",
            line_height=7,
        )

        # =====================================
        # DIALOGUE
        # =====================================

        if panel.dialogue:

            pdf.ln(2)

            _write_text(
                pdf,
                "Dialogue",
                size=11,
                style="B",
                line_height=7,
            )

            _write_text(
                pdf,
                panel.dialogue,
                size=11,
                style="",
                line_height=7,
            )

    # =====================================
    # SAVE PDF
    # =====================================

    filename = (
        "comiccraft_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    path = EXPORT_DIR / filename

    pdf.output(str(path))

    return path