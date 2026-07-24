from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from typing import Any

from nicegui import background_tasks, events, run, ui

from models import ImageCatalog, Person, validate_people
from pdf_utils import (
    DEFAULT_LAYOUT_PATH,
    PdfGenerator,
    load_layout,
    load_pdf_project,
    render_preview_png,
    save_layout,
)

BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "GUI" / "images" / "potloden"
DOWNLOAD_NAME = "naamkaartjes.pdf"


class AppPage:
    """One independent editor session in the browser."""

    def __init__(self) -> None:
        self.catalog = ImageCatalog(IMAGE_DIR)
        self.generator = PdfGenerator()
        self.layout = load_layout()
        self.people = [self.catalog.new_person()]
        self.selected_person = self.people[0]
        self.preview_task: asyncio.Task[Any] | None = None
        self.preview_buttons: dict[int, Any] = {}
        self.row_elements: dict[int, Any] = {}
        self.rows: ui.column
        self.preview: ui.image
        self.preview_error: ui.label
        self._build()

    def _build(self) -> None:
        ui.colors(primary="#356859", secondary="#FD5523", accent="#F4B942")
        ui.add_css(
            """
            body { background: #f5f4ef; color: #24332f; }
            .editor-card { min-width: 680px; }
            .preview-card { min-width: 440px; }
            .person-row { border: 1px solid #d8ddd8; border-radius: 12px; }
            .person-row.active {
                border-color: #FD5523;
                background: #fff7ed;
            }
            @media (max-width: 900px) {
                .editor-card, .preview-card { min-width: 100%; }
            }
            """
        )

        with ui.header().classes("items-center px-6 py-3"):
            ui.icon("school", size="28px")
            ui.label("Naamkaartjes").classes("text-xl font-semibold")
            ui.space()
            ui.button(
                "PDF openen",
                icon="folder_open",
                on_click=self._open_pdf_dialog,
            ).props("flat no-caps color=white")
            ui.button("Instellingen", icon="tune", on_click=self._open_settings).props(
                "flat no-caps color=white"
            )

        with ui.row().classes("w-full items-start gap-5 p-5 flex-wrap"):
            with ui.card().classes("editor-card flex-1 p-5 shadow-sm"):
                with ui.row().classes("w-full items-center"):
                    with ui.column().classes("gap-0"):
                        ui.label("Leerlingen").classes("text-xl font-semibold")
                        ui.label(
                            "Vul de gegevens in en selecteer een rij voor de preview."
                        ).classes("text-sm text-grey-7")
                    ui.space()
                    ui.button("Rij toevoegen", icon="add", on_click=self._add_person)

                self.rows = ui.column().classes("w-full gap-3 mt-3")

                with ui.row().classes("w-full justify-end mt-2"):
                    ui.button(
                        "PDF downloaden",
                        icon="download",
                        on_click=self._download_pdf,
                    ).props("unelevated")

            with ui.card().classes("preview-card flex-1 p-5 shadow-sm"):
                ui.label("Preview").classes("text-xl font-semibold")
                self.preview_error = ui.label("").classes("text-negative text-sm mt-2")
                self.preview_error.set_visibility(False)
                self.preview = (
                    ui.image("")
                    .classes("w-full mt-2 rounded-lg bg-white shadow-inner")
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
                    "person-row w-full items-center gap-2 p-3 bg-white"
                )
                self.row_elements[id(person)] = row
                with row:
                    preview_button = (
                        ui.button(
                            "Toon",
                            icon="visibility",
                            on_click=lambda person=person: self._select_person(person),
                        )
                        .props("dense no-caps")
                        .mark(f"preview-{index}")
                        .tooltip("Toon deze rij in de preview")
                    )
                    self.preview_buttons[id(person)] = preview_button
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
                    )
                    color_select = (
                        ui.select(
                            self.catalog.colors,
                            label="Kleur",
                            value=person.color,
                            on_change=lambda event, person=person: self._set_value(
                                person, "color", event.value
                            ),
                        )
                        .props("dense outlined")
                        .classes("w-28")
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
                        ui.input(
                            "Geboortedatum",
                            value=person.birth_date,
                            on_change=lambda event, person=person: self._set_value(
                                person, "birth_date", event.value
                            ),
                        )
                        .props('dense outlined debounce=350 mask="##-##-####"')
                        .classes("w-36")
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
                    ).props("flat round color=negative").tooltip("Verwijder rij")
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
                ui.label(f"Rij {index + 1}").classes("hidden")
        self._sync_preview_selection()

    def _set_value(self, person: Person, field: str, value: Any) -> None:
        setattr(person, field, value)
        self._set_selected_person(person)
        self._schedule_preview()

    def _select_person(self, person: Person) -> None:
        if person is self.selected_person:
            return
        self._set_selected_person(person)
        self._schedule_preview(delay=0)

    def _set_selected_person(self, person: Person) -> None:
        self.selected_person = person
        self._sync_preview_selection()

    def _sync_preview_selection(self) -> None:
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
        index = self.people.index(person)
        self.people.remove(person)
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
        self.preview_task = background_tasks.create(
            self._update_preview_after(delay),
            name="update PDF preview",
        )

    async def _update_preview_after(self, delay: float) -> None:
        try:
            await asyncio.sleep(delay)
            source = await run.io_bound(self._preview_source)
        except asyncio.CancelledError:
            return
        except Exception as error:
            self.preview_error.set_text(f"Preview kon niet worden gemaakt: {error}")
            self.preview_error.set_visibility(True)
            return
        self.preview.set_source(source)
        self.preview_error.set_visibility(False)

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
                project = await run.io_bound(load_pdf_project, data, self.catalog)
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

        with dialog, ui.card().classes("w-[560px] max-w-[95vw] p-5"):
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
        with dialog, ui.card().classes("w-[800px] max-w-[95vw]"):
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
                    save_layout(value, DEFAULT_LAYOUT_PATH)
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


@ui.page("/")
def index() -> None:
    AppPage()


def main() -> None:
    ui.run(title="Naamkaartjes", favicon="🎓")


if __name__ in {"__main__", "__mp_main__"}:
    main()
