from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

DESIGN_COLORS = ("geel", "oranje", "blauw", "rood", "groen", "roze")


@dataclass(slots=True)
class Person:
    """Data entered for one child's PDF page."""

    name: str = "Naam"
    family_name: str = "Familienaam"
    color: str = ""
    scene: str = ""
    birth_date: str = "01-01-2000"
    group: int = 1

    @property
    def full_name(self) -> str:
        return f"{self.name.strip()} {self.family_name.strip()}".strip()

    @property
    def birth_date_value(self) -> date:
        day, month, year = map(int, self.birth_date.strip().split("-"))
        return date(year, month, day)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Person:
        """Load current or legacy row data without retaining filesystem paths."""

        scene = str(data.get("scene", ""))
        color = str(data.get("color", ""))
        if (not scene or not color) and data.get("image_path"):
            image_name = Path(str(data["image_path"])).stem
            if "-" in image_name:
                scene, color = image_name.split("-", maxsplit=1)

        return cls(
            name=str(data.get("name", "")),
            family_name=str(data.get("family_name", "")),
            color=color,
            scene=scene,
            birth_date=str(data.get("birth_date", "")),
            group=int(data.get("group", 1)),
        )


class ImageCatalog:
    """Discover card designs and resolve their theme/color selections.

    The artwork is numbered in groups of six. Within every group, the variants
    use the same color order defined by ``DESIGN_COLORS``.
    """

    def __init__(self, image_dir: Path) -> None:
        self.image_dir = image_dir
        self._images: dict[tuple[str, str], Path] = {}
        for path in sorted(image_dir.glob("*.jpg")):
            if "-" not in path.stem:
                continue
            scene, variant = path.stem.rsplit("-", maxsplit=1)
            try:
                variant_number = int(variant)
            except ValueError:
                color = variant
            else:
                color = DESIGN_COLORS[(variant_number - 1) % len(DESIGN_COLORS)]
            selection = (scene, color)
            if selection in self._images:
                raise ValueError(
                    f"Duplicate design for scene '{scene}' and color '{color}'"
                )
            self._images[selection] = path

        if not self._images:
            raise FileNotFoundError(f"No card designs found in {image_dir}")

        self.scenes = sorted({scene for scene, _ in self._images})
        available_colors = {color for _, color in self._images}
        self.colors = [
            color for color in DESIGN_COLORS if color in available_colors
        ] + sorted(available_colors - set(DESIGN_COLORS))
        self._image_hashes = {
            sha256(path.read_bytes()).digest(): selection
            for selection, path in self._images.items()
        }

    def image_for(self, person: Person) -> Path:
        try:
            return self._images[(person.scene, person.color)]
        except KeyError as error:
            raise ValueError(
                f"No image exists for scene '{person.scene}' and color '{person.color}'"
            ) from error

    def new_person(self) -> Person:
        scene, color = next(iter(self._images))
        return Person(scene=scene, color=color)

    def selection_for_image(self, image: bytes) -> tuple[str, str]:
        """Identify a catalog image extracted from a generated PDF."""

        try:
            return self._image_hashes[sha256(image).digest()]
        except KeyError as error:
            raise ValueError("De PDF bevat een onbekende kaartafbeelding.") from error


def validate_people(people: list[Person], catalog: ImageCatalog) -> list[str]:
    """Return user-facing validation errors for the current rows."""

    errors: list[str] = []
    if not people:
        return ["Add at least one person."]

    for row_number, person in enumerate(people, start=1):
        prefix = f"Row {row_number}"
        if not person.name.strip():
            errors.append(f"{prefix}: name is required.")
        try:
            _ = person.birth_date_value
        except ValueError:
            errors.append(f"{prefix}: birth date must use dd-mm-yyyy.")
        if person.group not in (1, 2):
            errors.append(f"{prefix}: group must be 1 or 2.")
        try:
            catalog.image_for(person)
        except ValueError as error:
            errors.append(f"{prefix}: {error}.")

    return errors
