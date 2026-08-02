from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
from fpdf import FPDF

from models import ImageCatalog, Person, validate_people

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_LAYOUT_PATH = BASE_DIR / "layout.json"
DEFAULT_FONT_PATH = BASE_DIR / "GUI" / "assets" / "SchoolKX_new_SemiBold.ttf"
FONT_NAME = "SchoolKX"
PROJECT_ATTACHMENT = "jufdea-project.json"
PROJECT_VERSION = 1


@dataclass(slots=True)
class PdfProject:
    people: list[Person]
    layout: dict[str, Any]


def load_layout(path: Path = DEFAULT_LAYOUT_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        layout = json.load(file)
    validate_layout(layout)
    return layout


def save_layout(layout: dict[str, Any], path: Path = DEFAULT_LAYOUT_PATH) -> None:
    validate_layout(layout)
    path.write_text(
        json.dumps(layout, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def validate_layout(layout: Any) -> None:
    """Validate the small part of the layout schema required by the renderer."""

    if not isinstance(layout, dict) or not isinstance(layout.get("Types"), dict):
        raise ValueError("Layout must contain a 'Types' object.")
    if not layout["Types"]:
        raise ValueError("Layout must define at least one type.")

    required_sections = {"Size & positions", "Background", "Text"}
    for name, details in layout["Types"].items():
        if not isinstance(details, dict) or not required_sections <= details.keys():
            raise ValueError(
                f"Layout type '{name}' must contain Size & positions, "
                "Background, and Text."
            )
        positions = details["Size & positions"]
        tops = positions.get("top (mm)", [])
        lefts = positions.get("left (mm)", [])
        if not isinstance(tops, list) or not isinstance(lefts, list):
            raise ValueError(f"Layout type '{name}' positions must be lists.")
        if len(tops) != len(lefts):
            raise ValueError(
                f"Layout type '{name}' must have the same number of "
                "top and left positions."
            )


class PdfGenerator:
    """Generate previews and complete PDF documents from plain Python models."""

    def __init__(
        self,
        layout_path: Path = DEFAULT_LAYOUT_PATH,
        font_path: Path = DEFAULT_FONT_PATH,
    ) -> None:
        self.layout_path = layout_path
        self.font_path = font_path

    def preview(
        self,
        person: Person,
        catalog: ImageCatalog,
        layout: dict[str, Any] | None = None,
    ) -> bytes:
        layout = layout or load_layout(self.layout_path)
        validate_layout(layout)
        pdf = self._new_pdf()
        pdf.add_page(orientation="L")
        self._draw_person_page(pdf, person, catalog, layout)
        return bytes(pdf.output())

    def document(
        self,
        people: Sequence[Person],
        catalog: ImageCatalog,
        layout: dict[str, Any] | None = None,
    ) -> bytes:
        layout = layout or load_layout(self.layout_path)
        validate_layout(layout)
        pdf = self._new_pdf()
        self._draw_group_pages(pdf, people, catalog, title="hulpjeslijst")
        self._draw_group_pages(pdf, people, catalog, title="namenlijst")
        for person in people:
            pdf.add_page(orientation="L")
            self._draw_person_page(pdf, person, catalog, layout)
        pdf.embed_file(
            bytes=encode_project(people, layout),
            basename=PROJECT_ATTACHMENT,
            mime_type="application/json",
            desc="Editable JufDea project data",
            compress=True,
            checksum=True,
        )
        return bytes(pdf.output())

    def _new_pdf(self) -> FPDF:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=False)
        pdf.add_font(FONT_NAME, fname=str(self.font_path))
        pdf.set_font(FONT_NAME, size=14)
        return pdf

    @staticmethod
    def _draw_person_page(
        pdf: FPDF,
        person: Person,
        catalog: ImageCatalog,
        layout: dict[str, Any],
    ) -> None:
        image_path = catalog.image_for(person)

        for layout_type, details in layout["Types"].items():
            positions = details["Size & positions"]
            background = details["Background"]
            text = details["Text"]

            width = float(positions["width (mm)"])
            height = float(positions["height (mm)"])
            portrait = bool(positions.get("portrait", False))
            margin = float(background["margin (mm)"])
            top_offset = float(background.get("top offset (mm)", 0))
            base_font_size = int(text["font-size"])
            text_margin = float(text["margin (mm)"])
            bottom_offset = float(text.get("margin-bottom (mm)", 0))

            for top, left in zip(
                positions["top (mm)"],
                positions["left (mm)"],
                strict=True,
            ):
                PdfGenerator._draw_card(
                    pdf=pdf,
                    layout_type=layout_type,
                    name=person.name.strip(),
                    birth_date=person.birth_date.strip(),
                    image_path=image_path,
                    x=float(left),
                    y=float(top),
                    width=width,
                    height=height,
                    portrait=portrait,
                    margin=margin,
                    top_offset=top_offset,
                    base_font_size=base_font_size,
                    text_margin=text_margin,
                    bottom_offset=bottom_offset,
                )

    @staticmethod
    def _draw_card(
        *,
        pdf: FPDF,
        layout_type: str,
        name: str,
        birth_date: str,
        image_path: Path,
        x: float,
        y: float,
        width: float,
        height: float,
        portrait: bool,
        margin: float,
        top_offset: float,
        base_font_size: int,
        text_margin: float,
        bottom_offset: float,
    ) -> None:
        pdf.rect(x, y, width, height)
        image_size = width - 2 * margin if portrait else height - 2 * margin
        font_box = base_font_size * 0.352778 * 1.3

        if layout_type == "Fest":
            text_x = x + text_margin
            text_y = y + text_margin
            text_width = width - 2 * text_margin
            image_x = x + margin
            image_y = y + font_box + 2 * text_margin + top_offset - bottom_offset
            bottom_text_y = image_y + image_size + text_margin
        elif portrait:
            text_x = x + text_margin
            text_y = y + height - font_box - text_margin - bottom_offset
            text_width = width - 2 * text_margin
            image_x = x + margin
            image_y = y + margin + top_offset
        else:
            text_x = x + image_size + margin + text_margin
            text_y = y + (height - font_box) / 2
            text_width = width - image_size - margin - 2 * text_margin
            image_x = x + margin
            image_y = y + margin + top_offset

        display_name = name
        font_size = PdfGenerator._fit_font(
            pdf,
            display_name,
            text_width,
            base_font_size,
        )
        PdfGenerator._draw_colored_name(
            pdf,
            display_name,
            text_x,
            text_y,
            text_width,
            font_box,
        )
        pdf.image(str(image_path), x=image_x, y=image_y, h=image_size)

        if layout_type == "Fest":
            pdf.set_font(FONT_NAME, size=font_size)
            pdf.set_text_color(0, 0, 0)
            date_width = pdf.get_string_width(birth_date)
            pdf.set_xy(text_x + (text_width - date_width) / 2, bottom_text_y)
            pdf.cell(date_width, font_box, birth_date)

    @staticmethod
    def _fit_font(pdf: FPDF, text: str, width: float, size: int) -> int:
        while size > 1:
            pdf.set_font(FONT_NAME, size=size)
            if pdf.get_string_width(text) <= width:
                return size
            size -= 1
        pdf.set_font(FONT_NAME, size=1)
        return 1

    @staticmethod
    def _draw_colored_name(
        pdf: FPDF,
        text: str,
        x: float,
        y: float,
        width: float,
        height: float,
    ) -> None:
        first_letter, remaining = text[:1], text[1:]
        text_width = pdf.get_string_width(text)
        pdf.set_xy(x + (width - text_width) / 2, y)
        pdf.set_text_color(0, 128, 0)
        pdf.cell(pdf.get_string_width(first_letter), height, first_letter)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(pdf.get_string_width(remaining), height, remaining)

    @staticmethod
    def _draw_group_pages(
        pdf: FPDF,
        people: Sequence[Person],
        catalog: ImageCatalog,
        title: str,
    ) -> None:
        groups = {
            group: sorted(
                (person for person in people if person.group == group),
                key=lambda person: person.birth_date_value,
            )
            for group in (1, 2)
        }
        rows_per_page = 22
        title_height = 12.0
        page_count = max(
            1,
            math.ceil(max(len(groups[1]), len(groups[2])) / rows_per_page),
        )

        for page_index in range(page_count):
            pdf.add_page(orientation="P")
            pdf.set_font(FONT_NAME, size=18)
            pdf.set_text_color(0, 0, 0)
            pdf.set_xy(10, 8)
            pdf.cell(190, title_height - 4, title, align="C")
            start = page_index * rows_per_page
            stop = start + rows_per_page
            PdfGenerator._draw_group_column(
                pdf,
                x=10,
                y=10 + title_height,
                people=groups[1][start:stop],
                catalog=catalog,
            )
            PdfGenerator._draw_group_column(
                pdf,
                x=100,
                y=10 + title_height,
                people=groups[2][start:stop],
                catalog=catalog,
            )

    @staticmethod
    def _draw_group_column(
        pdf: FPDF,
        *,
        x: float,
        y: float,
        people: Sequence[Person],
        catalog: ImageCatalog,
    ) -> None:
        cell_width = 90.0
        cell_height = 12.0
        margin = 0.5

        for person in people:
            pdf.rect(x, y, cell_width, cell_height)
            image_size = cell_height - 2 * margin
            image_x = x + margin
            image_y = y + margin
            pdf.image(
                str(catalog.image_for(person)),
                x=image_x,
                y=image_y,
                w=image_size,
                h=image_size,
            )
            pdf.line(
                image_x + image_size,
                y + margin,
                image_x + image_size,
                y + cell_height - margin,
            )
            text_x = image_x + image_size + margin
            text_width = cell_width - image_size - 2 * margin
            PdfGenerator._fit_font(pdf, person.full_name, text_width, 14)
            pdf.set_xy(text_x, y + margin)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(text_width, cell_height - 2 * margin, person.full_name)
            y += cell_height


def encode_project(
    people: Sequence[Person],
    layout: dict[str, Any],
) -> bytes:
    """Serialize the editable source data embedded in generated PDFs."""

    validate_layout(layout)
    payload = {
        "application": "JufDea",
        "version": PROJECT_VERSION,
        "people": [person.to_dict() for person in people],
        "layout": layout,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()


def load_pdf_project(pdf_bytes: bytes, catalog: ImageCatalog) -> PdfProject:
    """Restore editable data from current or legacy generated PDFs."""

    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
            attachments = set(document.embfile_names())
            if PROJECT_ATTACHMENT in attachments:
                payload = json.loads(document.embfile_get(PROJECT_ATTACHMENT))
                project = _decode_current_project(payload)
            elif "table.json" in attachments:
                table = json.loads(document.embfile_get("table.json"))
                layout = (
                    json.loads(document.embfile_get("layout.json"))
                    if "layout.json" in attachments
                    else load_layout()
                )
                project = PdfProject(_decode_legacy_people(table), layout)
            else:
                project = _reconstruct_legacy_project(document, catalog)
    except (fitz.FileDataError, json.JSONDecodeError) as error:
        raise ValueError("Het gekozen bestand is geen geldige JufDea-PDF.") from error

    validate_layout(project.layout)
    errors = validate_people(project.people, catalog)
    if errors:
        raise ValueError(f"De opgeslagen gegevens zijn ongeldig: {errors[0]}")
    return project


def render_preview_png(pdf_bytes: bytes, zoom: float = 1.5) -> bytes:
    """Render the first PDF page to a stable browser image."""

    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        if document.page_count == 0:
            raise ValueError("De PDF bevat geen pagina's.")
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return pixmap.tobytes("png")


def _decode_current_project(payload: Any) -> PdfProject:
    if not isinstance(payload, dict):
        raise ValueError("De ingesloten projectgegevens hebben een ongeldig formaat.")
    if payload.get("version") != PROJECT_VERSION:
        raise ValueError(
            f"Projectversie {payload.get('version')} wordt niet ondersteund."
        )
    people_data = payload.get("people")
    if not isinstance(people_data, list) or not all(
        isinstance(row, dict) for row in people_data
    ):
        raise ValueError("De ingesloten leerlingenlijst is ongeldig.")
    return PdfProject(
        people=[Person.from_dict(row) for row in people_data],
        layout=payload.get("layout"),
    )


def _decode_legacy_people(table: Any) -> list[Person]:
    if isinstance(table, list):
        rows = table
    elif isinstance(table, dict) and isinstance(table.get("data"), list):
        rows = table["data"]
    elif isinstance(table, dict) and all(
        isinstance(column, dict) for column in table.values()
    ):
        indexes = sorted({index for column in table.values() for index in column})
        rows = [
            {name: values.get(index) for name, values in table.items()}
            for index in indexes
        ]
    else:
        raise ValueError("De oudere leerlingenlijst heeft een ongeldig formaat.")

    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("De oudere leerlingenlijst bevat ongeldige rijen.")
    return [Person.from_dict(row) for row in rows]


def _reconstruct_legacy_project(
    document: fitz.Document,
    catalog: ImageCatalog,
) -> PdfProject:
    """Recover rows from old generated PDFs that predate embedded project data."""

    person_pages = [page for page in document if page.rect.width > page.rect.height]
    group_pages = [page for page in document if page.rect.width <= page.rect.height]
    if not person_pages or not group_pages:
        raise ValueError("Deze PDF bevat geen herkenbare JufDea-projectgegevens.")

    people: list[Person] = []
    date_pattern = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")
    for page in person_pages:
        lines = [line.strip() for line in page.get_text().splitlines() if line.strip()]
        birth_date = next(
            (match.group() for line in lines if (match := date_pattern.search(line))),
            "",
        )
        names = [
            line
            for line in lines
            if not date_pattern.fullmatch(line) and not line.endswith("fest")
        ]
        images = page.get_images(full=True)
        if not names or not birth_date or not images:
            raise ValueError("Deze PDF bevat geen herkenbare JufDea-projectgegevens.")

        image = document.extract_image(images[0][0])["image"]
        scene, color = catalog.selection_for_image(image)
        people.append(
            Person(
                name=names[0],
                birth_date=birth_date,
                scene=scene,
                color=color,
            )
        )

    group_rows: list[tuple[str, int]] = []
    for page in group_pages:
        midpoint = page.rect.width / 2
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"]).strip()
                if text:
                    group = 1 if line["bbox"][0] < midpoint else 2
                    group_rows.append((text, group))

    unused_rows = list(group_rows)
    for person in people:
        match_index = next(
            (
                index
                for index, (full_name, _) in enumerate(unused_rows)
                if full_name == person.name or full_name.startswith(f"{person.name} ")
            ),
            None,
        )
        if match_index is None:
            continue
        full_name, person.group = unused_rows.pop(match_index)
        person.family_name = full_name.removeprefix(person.name).strip()

    return PdfProject(people, load_layout())
