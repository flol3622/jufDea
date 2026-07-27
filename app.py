from __future__ import annotations

import asyncio
import base64
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

IS_PYODIDE = sys.platform == "emscripten"

if IS_PYODIDE:
    import nicegui_pyodide  # noqa: F401  # install browser runtime shims

from nicegui import background_tasks, events, run, ui  # noqa: E402

from models import ImageCatalog, Person, validate_people  # noqa: E402
from pdf_utils import (  # noqa: E402
    DEFAULT_LAYOUT_PATH,
    PdfGenerator,
    load_layout,
    load_pdf_project,
    render_preview_png,
    save_layout,
)

BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "GUI" / "images" / "ontwerpen"
DOWNLOAD_NAME = "naamkaartjes.pdf"
APP_VERSION = "v2026"
LAYOUT_STORAGE_KEY = "jufdea-layout-v2026"
COLOR_SWATCHES = {
    "geel": "#F0C419",
    "oranje": "#F57C00",
    "blauw": "#1E88E5",
    "rood": "#E53935",
    "groen": "#43A047",
    "roze": "#EC5FA0",
}
FALLBACK_SWATCH = "#9E9E9E"


async def _io_bound(function: Any, *args: Any) -> Any:
    """Run blocking work off-thread where possible.

    Pyodide runs in a browser sandbox without the thread helper used by the
    server build, so it executes the same function in the local interpreter.
    """

    if IS_PYODIDE:
        return function(*args)
    return await run.io_bound(function, *args)


def _load_active_layout() -> dict[str, Any]:
    layout = load_layout()
    if not IS_PYODIDE:
        return layout

    from js import localStorage  # type: ignore[import-not-found]

    stored = localStorage.getItem(LAYOUT_STORAGE_KEY)
    if not stored:
        return layout
    try:
        value = json.loads(str(stored))
        from pdf_utils import validate_layout

        validate_layout(value)
    except (json.JSONDecodeError, ValueError):
        localStorage.removeItem(LAYOUT_STORAGE_KEY)
        return layout
    return value


def _save_active_layout(layout: dict[str, Any]) -> None:
    if not IS_PYODIDE:
        save_layout(layout, DEFAULT_LAYOUT_PATH)
        return

    from js import localStorage  # type: ignore[import-not-found]

    from pdf_utils import validate_layout

    validate_layout(layout)
    localStorage.setItem(
        LAYOUT_STORAGE_KEY,
        json.dumps(layout, ensure_ascii=False),
    )


class AppPage:
    """One independent editor session in the browser."""

    def __init__(self) -> None:
        self.catalog = ImageCatalog(IMAGE_DIR)
        self.generator = PdfGenerator()
        self.layout = _load_active_layout()
        self.people = [self.catalog.new_person()]
        self.selected_person = self.people[0]
        self.preview_task: asyncio.Task[Any] | None = None
        self.preview_buttons: dict[int, Any] = {}
        self.row_elements: dict[int, Any] = {}
        self.rows: ui.column
        self.preview: ui.image
        self.preview_error: ui.label
        self.preview_caption: ui.label
        self.preview_spinner: ui.spinner
        self.count_label: ui.label
        self._build()

    def _build(self) -> None:
        ui.colors(primary="#356859", secondary="#FD5523", accent="#F4B942")
        ui.add_css(
            """
            body {
                background:
                    radial-gradient(1100px 500px at 15% -10%,
                        rgba(53, 104, 89, 0.10), transparent 60%),
                    radial-gradient(900px 420px at 95% 0%,
                        rgba(244, 185, 66, 0.12), transparent 55%),
                    #f6f4ee;
                color: #24332f;
            }
            .app-header {
                background: linear-gradient(105deg, #2c584c 0%, #356859 55%,
                    #47806f 100%) !important;
                box-shadow: 0 2px 12px rgba(36, 51, 47, 0.25);
            }
            .app-card {
                border-radius: 18px !important;
                border: 1px solid rgba(36, 51, 47, 0.08);
                box-shadow: 0 8px 24px rgba(36, 51, 47, 0.07) !important;
                background: rgba(255, 255, 255, 0.92);
                backdrop-filter: blur(4px);
            }
            .editor-card { min-width: 680px; }
            .preview-card {
                min-width: 440px;
                position: sticky;
                top: 88px;
            }
            .preview-frame {
                border: 1px solid rgba(36, 51, 47, 0.10);
                background: repeating-conic-gradient(#fafafa 0% 25%, #ffffff 0% 50%)
                    50% / 22px 22px;
            }
            .person-row {
                border: 1px solid #dde2dd;
                border-radius: 14px;
                transition: border-color 0.15s ease, background-color 0.15s ease,
                    box-shadow 0.15s ease, transform 0.15s ease;
            }
            .person-row:hover {
                box-shadow: 0 4px 14px rgba(36, 51, 47, 0.12);
                transform: translateY(-1px);
                border-color: #b9c6bf;
            }
            .person-row.active {
                border-color: #FD5523;
                background: linear-gradient(180deg, #fff8f0, #fff3e4);
                box-shadow: 0 4px 16px rgba(253, 85, 35, 0.14);
            }
            .section-title { letter-spacing: -0.01em; }
            .color-dot {
                width: 14px;
                height: 14px;
                border-radius: 9999px;
                border: 1px solid rgba(0, 0, 0, 0.25);
                display: inline-block;
            }
            @media (max-width: 900px) {
                .editor-card, .preview-card { min-width: 100%; }
                .preview-card { position: static; }
            }
            """
        )

        with ui.header().classes("app-header items-center px-6 py-3 gap-3"):
            ui.icon("school", size="28px")
            ui.label("Naamkaartjes").classes(
                "text-xl font-semibold tracking-tight"
            )
            ui.badge(APP_VERSION).props("color=secondary").classes("rounded-full")
            ui.space()
            ui.button(
                "PDF openen",
                icon="folder_open",
                on_click=self._open_pdf_dialog,
            ).props("flat no-caps rounded color=white")
            ui.button("Instellingen", icon="tune", on_click=self._open_settings).props(
                "flat no-caps rounded color=white"
            )

        with ui.row().classes("w-full items-start gap-5 p-5 flex-wrap"):
            with ui.card().classes("app-card editor-card flex-1 p-5"):
                with ui.row().classes("w-full items-center"):
                    with ui.column().classes("gap-0"):
                        with ui.row().classes("items-baseline gap-2"):
                            ui.label("Leerlingen").classes(
                                "section-title text-xl font-semibold"
                            )
                            self.count_label = ui.label("").classes(
                                "text-sm text-grey-6"
                            )
                        ui.label(
                            "Vul de gegevens in en selecteer een rij voor de preview."
                        ).classes("text-sm text-grey-7")
                    ui.space()
                    ui.button(
                        "Rij toevoegen", icon="add", on_click=self._add_person
                    ).props("unelevated no-caps rounded")

                self.rows = ui.column().classes("w-full gap-3 mt-3")

                with ui.row().classes("w-full justify-end mt-2"):
                    ui.button(
                        "PDF downloaden",
                        icon="download",
                        on_click=self._download_pdf,
                    ).props("unelevated no-caps rounded color=secondary size=md")

            with ui.card().classes("app-card preview-card flex-1 p-5"):
                with ui.row().classes("w-full items-center gap-2"):
                    ui.label("Preview").classes("section-title text-xl font-semibold")
                    self.preview_spinner = ui.spinner(size="20px").props(
                        "color=secondary"
                    )
                    self.preview_spinner.set_visibility(False)
                self.preview_caption = ui.label("").classes("text-sm text-grey-7")
                self.preview_error = ui.label("").classes("text-negative text-sm mt-2")
                self.preview_error.set_visibility(False)
                self.preview = (
                    ui.image("")
                    .classes("preview-frame w-full mt-2 rounded-xl")
                    .props("no-spinner no-transition fit=contain")
                )

        self._render_rows()
        self._update_preview_now()

    def _render_rows(self) -> None:
        self.rows.clear()
        self.preview_buttons.clear()
        self.row_elements.clear()
        with self.rows:
            for index, person in enumerate(self.people):
                row = ui.row().classes(
                    "person-row no-wrap w-full items-center gap-3 p-3 bg-white"
                )
                self.row_elements[id(person)] = row
                with row:
                    with ui.column().classes("items-center gap-0 shrink-0"):
                        preview_button = (
                            ui.button(
                                "Toon",
                                icon="visibility",
                                on_click=lambda person=person: self._select_person(
                                    person
                                ),
                            )
                            .props("dense no-caps")
                            .mark(f"preview-{index}")
                            .tooltip("Toon deze rij in de preview")
                        )
                        ui.label(f"Rij {index + 1}").classes("text-xs text-grey-6")
                    self.preview_buttons[id(person)] = preview_button
                    with ui.row().classes("grow items-center gap-2"):
                        name_input = (
                            ui.input(
                                "Voornaam",
                                value=person.name,
                                on_change=lambda event, person=person: self._set_value(
                                    person, "name", event.value
                                ),
                            )
                            .props("dense outlined debounce=350")
                            .classes("grow")
                            .style("min-width: 130px")
                            .mark(f"name-{index}")
                        )
                        family_input = (
                            ui.input(
                                "Familienaam",
                                value=person.family_name,
                                on_change=lambda event, person=person: self._set_value(
                                    person, "family_name", event.value
                                ),
                            )
                            .props("dense outlined debounce=350")
                            .classes("grow")
                            .style("min-width: 130px")
                        )
                        color_select = (
                            ui.select(
                                self.catalog.colors,
                                label="Kleur",
                                value=person.color,
                            )
                            .props("dense outlined")
                            .classes("w-32")
                        )
                        with color_select.add_slot("prepend"):
                            color_dot = ui.element("span").classes("color-dot")
                        color_dot.style(
                            f"background: "
                            f"{COLOR_SWATCHES.get(person.color, FALLBACK_SWATCH)}"
                        )
                        color_select.on_value_change(
                            lambda event,
                            person=person,
                            color_dot=color_dot: self._set_color(
                                person,
                                color_dot,
                                event.value,
                            )
                        )
                        scene_select = (
                            ui.select(
                                self.catalog.scenes,
                                label="Afbeelding",
                                value=person.scene,
                                on_change=lambda event, person=person: self._set_value(
                                    person, "scene", event.value
                                ),
                            )
                            .props("dense outlined")
                            .classes("w-32")
                        )
                        birth_input = (
                            ui.input("Geboortedatum", value=person.birth_date)
                            .props('dense outlined debounce=350 mask="##-##-####"')
                            .classes("w-36")
                            .mark(f"birth-date-{index}")
                        )
                        with birth_input:
                            with ui.menu().props("no-parent-event") as calendar_menu:
                                birth_picker = (
                                    ui.date(
                                        value=self._valid_birth_date(person.birth_date),
                                        mask="DD-MM-YYYY",
                                    )
                                    .props("first-day-of-week=1")
                                    .mark(f"birth-date-picker-{index}")
                                )
                            with birth_input.add_slot("append"):
                                (
                                    ui.icon("calendar_month")
                                    .classes("cursor-pointer")
                                    .on("click", calendar_menu.open)
                                    .tooltip("Kies een datum")
                                )
                        birth_input.on_value_change(
                            lambda event,
                            person=person,
                            birth_picker=birth_picker: self._type_birth_date(
                                person,
                                birth_picker,
                                event.value,
                            )
                        )
                        birth_picker.on_value_change(
                            lambda event,
                            person=person,
                            birth_input=birth_input,
                            calendar_menu=calendar_menu: self._pick_birth_date(
                                person,
                                birth_input,
                                calendar_menu,
                                event.value,
                            )
                        )
                        group_select = (
                            ui.select(
                                [1, 2],
                                label="Groep",
                                value=person.group,
                                on_change=lambda event, person=person: self._set_value(
                                    person, "group", int(event.value)
                                ),
                            )
                            .props("dense outlined")
                            .classes("w-24")
                        )
                    ui.button(
                        icon="delete_outline",
                        on_click=lambda person=person: self._remove_person(person),
                    ).props("flat round color=negative").classes("shrink-0").tooltip(
                        "Verwijder rij"
                    )
                    for control in (
                        name_input,
                        family_input,
                        color_select,
                        scene_select,
                        birth_input,
                        group_select,
                    ):
                        control.on(
                            "focus",
                            lambda person=person: self._select_person(person),
                        )
        self._update_count_label()
        self._sync_preview_selection()

    def _update_count_label(self) -> None:
        total = len(self.people)
        group_1 = sum(1 for person in self.people if person.group == 1)
        group_2 = total - group_1
        noun = "leerling" if total == 1 else "leerlingen"
        self.count_label.set_text(
            f"{total} {noun} · groep 1: {group_1} · groep 2: {group_2}"
        )

    def _set_color(self, person: Person, color_dot: Any, value: str) -> None:
        color_dot.style(f"background: {COLOR_SWATCHES.get(value, FALLBACK_SWATCH)}")
        self._set_value(person, "color", value)

    def _set_value(self, person: Person, field: str, value: Any) -> None:
        setattr(person, field, value)
        self._set_selected_person(person)
        self._schedule_preview()

    @staticmethod
    def _valid_birth_date(value: str) -> str | None:
        try:
            day, month, year = map(int, value.strip().split("-"))
            date(year, month, day)
        except (AttributeError, TypeError, ValueError):
            return None
        return value

    def _type_birth_date(
        self,
        person: Person,
        birth_picker: Any,
        value: str | None,
    ) -> None:
        birth_date = value or ""
        self._set_value(person, "birth_date", birth_date)
        if self._valid_birth_date(birth_date):
            birth_picker.set_value(birth_date)

    def _pick_birth_date(
        self,
        person: Person,
        birth_input: Any,
        calendar_menu: Any,
        value: str | None,
    ) -> None:
        if not value:
            return
        birth_input.set_value(value)
        calendar_menu.close()

    def _select_person(self, person: Person) -> None:
        if person is self.selected_person:
            return
        self._set_selected_person(person)
        self._schedule_preview(delay=0)

    def _set_selected_person(self, person: Person) -> None:
        self.selected_person = person
        self._sync_preview_selection()

    def _sync_preview_selection(self) -> None:
        selected = self.selected_person
        selected_index = next(
            (index for index, person in enumerate(self.people) if person is selected),
            None,
        )
        if selected_index is not None:
            full_name = " ".join(
                part.strip()
                for part in (selected.name, selected.family_name)
                if part and part.strip()
            )
            caption = f"Rij {selected_index + 1}"
            if full_name:
                caption += f": {full_name}"
            self.preview_caption.set_text(caption)
        for person in self.people:
            selected = person is self.selected_person
            button = self.preview_buttons.get(id(person))
            row = self.row_elements.get(id(person))
            if button:
                button.props(
                    (
                        "unelevated color=secondary icon=visibility"
                        if selected
                        else "outline color=primary icon=radio_button_unchecked"
                    ),
                    remove="flat outline unelevated color icon",
                )
            if row:
                row.classes(
                    add="active" if selected else "bg-white",
                    remove="bg-white" if selected else "active",
                )

    def _add_person(self) -> None:
        person = self.catalog.new_person()
        self.people.append(person)
        self.selected_person = person
        self._render_rows()
        self._schedule_preview(delay=0)

    def _remove_person(self, person: Person) -> None:
        if len(self.people) == 1:
            ui.notify("Er moet minstens één rij blijven staan.", type="warning")
            return
        index = next(
            i for i, candidate in enumerate(self.people) if candidate is person
        )
        del self.people[index]
        if self.selected_person is person:
            self.selected_person = self.people[min(index, len(self.people) - 1)]
        self._render_rows()
        self._schedule_preview(delay=0)

    def _preview_source(self) -> str:
        pdf = self.generator.preview(
            self.selected_person,
            self.catalog,
            self.layout,
        )
        png = render_preview_png(pdf)
        encoded = base64.b64encode(png).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _update_preview_now(self) -> None:
        try:
            self.preview.set_source(self._preview_source())
        except Exception as error:
            self.preview_error.set_text(f"Preview kon niet worden gemaakt: {error}")
            self.preview_error.set_visibility(True)
            return
        self.preview_error.set_visibility(False)

    def _schedule_preview(self, *, delay: float = 0.35) -> None:
        if self.preview_task and not self.preview_task.done():
            self.preview_task.cancel()
        self.preview_spinner.set_visibility(True)
        self.preview_task = background_tasks.create(
            self._update_preview_after(delay),
            name="update PDF preview",
        )

    async def _update_preview_after(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            source = await _io_bound(self._preview_source)
        except asyncio.CancelledError:
            return
        except Exception as error:
            self.preview_error.set_text(f"Preview kon niet worden gemaakt: {error}")
            self.preview_error.set_visibility(True)
            self.preview_spinner.set_visibility(False)
            return
        self.preview.set_source(source)
        self.preview_error.set_visibility(False)
        self.preview_spinner.set_visibility(False)

    def _download_pdf(self) -> None:
        errors = validate_people(self.people, self.catalog)
        if errors:
            ui.notify(errors[0], type="negative", multi_line=True)
            return

        try:
            pdf = self.generator.document(self.people, self.catalog, self.layout)
        except Exception as error:
            ui.notify(f"PDF kon niet worden gemaakt: {error}", type="negative")
            return

        ui.download.content(pdf, DOWNLOAD_NAME, "application/pdf")
        ui.notify("PDF is klaar.", type="positive")

    def _open_pdf_dialog(self) -> None:
        dialog = ui.dialog()

        async def open_pdf(event: events.UploadEventArguments) -> None:
            try:
                data = await event.file.read()
                project = await _io_bound(load_pdf_project, data, self.catalog)
            except Exception as error:
                ui.notify(f"PDF kon niet worden geopend: {error}", type="negative")
                return

            self.people = project.people
            self.layout = project.layout
            self.selected_person = self.people[0]
            self._render_rows()
            self._schedule_preview(delay=0)
            dialog.close()
            ui.notify(
                f"{event.file.name} geopend ({len(self.people)} rijen).",
                type="positive",
            )

        with dialog, ui.card().classes("app-card w-[560px] max-w-[95vw] p-5"):
            ui.label("Bestaande PDF openen").classes("text-xl font-semibold")
            ui.label(
                "Kies een PDF die eerder met JufDea inclusief projectgegevens "
                "is opgeslagen."
            ).classes("text-sm text-grey-7")
            ui.upload(
                label="PDF kiezen",
                auto_upload=True,
                max_file_size=25_000_000,
                on_upload=open_pdf,
                on_rejected=lambda: ui.notify(
                    "Kies een PDF van maximaal 25 MB.",
                    type="negative",
                ),
            ).props("accept=.pdf").classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Sluiten", on_click=dialog.close).props("flat")
        dialog.open()

    def _open_settings(self) -> None:
        dialog = ui.dialog()
        with dialog, ui.card().classes("app-card w-[800px] max-w-[95vw]"):
            ui.label("Layout-instellingen").classes("text-xl font-semibold")
            ui.label(
                "Pas de JSON-layout aan. De preview wordt na opslaan vernieuwd."
            ).classes("text-sm text-grey-7")
            editor = (
                ui.textarea(value=json.dumps(self.layout, indent=4, ensure_ascii=False))
                .props("outlined rows=24")
                .classes("w-full font-mono")
            )

            def save(_: events.ClickEventArguments) -> None:
                try:
                    value = json.loads(editor.value)
                    _save_active_layout(value)
                except (json.JSONDecodeError, ValueError) as error:
                    ui.notify(f"Ongeldige layout: {error}", type="negative")
                    return
                self.layout = value
                dialog.close()
                self._schedule_preview(delay=0)
                ui.notify("Instellingen opgeslagen.", type="positive")

            with ui.row().classes("w-full justify-end"):
                ui.button("Annuleren", on_click=dialog.close).props("flat")
                ui.button("Opslaan", icon="save", on_click=save)
        dialog.open()


if IS_PYODIDE:
    from nicegui import Client
    from nicegui_pyodide import page

    with Client(page("/")) as client:
        AppPage()
else:

    @ui.page("/")
    def index() -> None:
        AppPage()

    def main() -> None:
        ui.run(title=f"Naamkaartjes {APP_VERSION}", favicon="🎓")

    if __name__ in {"__main__", "__mp_main__"}:
        main()
