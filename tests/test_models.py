from pathlib import Path

from models import ImageCatalog, Person, validate_people

IMAGE_DIR = Path(__file__).parents[1] / "GUI" / "images" / "potloden"


def test_catalog_discovers_assets() -> None:
    catalog = ImageCatalog(IMAGE_DIR)

    assert "blij" in catalog.scenes
    assert "blauw" in catalog.colors
    assert catalog.image_for(Person(scene="blij", color="blauw")).is_file()


def test_validate_people_reports_invalid_rows() -> None:
    catalog = ImageCatalog(IMAGE_DIR)
    person = catalog.new_person()
    person.name = ""
    person.birth_date = "not-a-date"

    errors = validate_people([person], catalog)

    assert errors == [
        "Row 1: name is required.",
        "Row 1: birth date must use dd-mm-yyyy.",
    ]


def test_person_full_name_is_trimmed() -> None:
    assert Person(name="  Ada ", family_name=" Lovelace  ").full_name == "Ada Lovelace"


def test_person_loads_scene_and_color_from_legacy_image_path() -> None:
    person = Person.from_dict(
        {
            "name": "Ada",
            "image_path": "/old/location/blij-blauw.jpg",
            "birth_date": "01-01-2000",
        }
    )

    assert person.scene == "blij"
    assert person.color == "blauw"


def test_catalog_identifies_extracted_image_bytes() -> None:
    catalog = ImageCatalog(IMAGE_DIR)
    image = (IMAGE_DIR / "bril-groen.jpg").read_bytes()

    assert catalog.selection_for_image(image) == ("bril", "groen")
