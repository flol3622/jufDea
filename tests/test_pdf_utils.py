import json
from pathlib import Path

import fitz
import pytest
from fpdf import FPDF

from models import ImageCatalog
from pdf_utils import (
    PdfGenerator,
    load_layout,
    load_pdf_project,
    render_preview_png,
    validate_layout,
)

ROOT = Path(__file__).parents[1]
CATALOG = ImageCatalog(ROOT / "GUI" / "images" / "potloden")


def test_layout_is_valid() -> None:
    validate_layout(load_layout(ROOT / "layout.json"))


def test_preview_creates_pdf() -> None:
    pdf = PdfGenerator().preview(CATALOG.new_person(), CATALOG)

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1_000
    assert render_preview_png(pdf).startswith(b"\x89PNG")


def test_document_creates_person_and_group_pages() -> None:
    people = [CATALOG.new_person(), CATALOG.new_person()]
    people[0].name = "Ada"
    people[1].group = 2
    pdf = PdfGenerator().document(people, CATALOG)

    assert pdf.startswith(b"%PDF")
    assert pdf.count(b"/Type /Page") >= 3

    restored = load_pdf_project(pdf, CATALOG)
    assert [person.name for person in restored.people] == ["Ada", "Naam"]
    assert restored.people[1].group == 2
    assert restored.layout == load_layout()


def test_legacy_pdf_attachments_can_be_opened() -> None:
    person = CATALOG.new_person()
    table = {key: {"0": value} for key, value in person.to_dict().items()}
    pdf = FPDF()
    pdf.add_page()
    pdf.embed_file(
        bytes=json.dumps(table).encode(),
        basename="table.json",
        mime_type="application/json",
    )
    pdf.embed_file(
        bytes=json.dumps(load_layout()).encode(),
        basename="layout.json",
        mime_type="application/json",
    )

    restored = load_pdf_project(bytes(pdf.output()), CATALOG)

    assert restored.people == [person]


def test_pdf_without_project_data_is_rejected() -> None:
    pdf = FPDF()
    pdf.add_page()

    with pytest.raises(ValueError, match="geen herkenbare JufDea-projectgegevens"):
        load_pdf_project(bytes(pdf.output()), CATALOG)


def test_attachment_free_generated_pdf_is_reconstructed() -> None:
    people = [CATALOG.new_person(), CATALOG.new_person()]
    people[0].name = "Ada"
    people[0].family_name = "Lovelace"
    people[0].birth_date = "10-12-2014"
    people[1].name = "Grace"
    people[1].family_name = "Hopper"
    people[1].birth_date = "09-12-2013"
    people[1].scene = "bril"
    people[1].color = "groen"
    people[1].group = 2
    pdf = PdfGenerator().document(people, CATALOG)
    with fitz.open(stream=pdf, filetype="pdf") as document:
        document.embfile_del("jufdea-project.json")
        old_pdf = document.tobytes()

    restored = load_pdf_project(old_pdf, CATALOG)

    assert restored.people == people
