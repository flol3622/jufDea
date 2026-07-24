from nicegui.testing import User

import app  # noqa: F401  # register the NiceGUI page


async def test_preview_button_follows_active_row(user: User) -> None:
    await user.open("/")

    await user.should_see("v2026")
    await user.should_see("PDF openen")
    open_button = next(iter(user.find("PDF openen").elements))
    assert open_button.props["color"] == "white"
    first_button = next(iter(user.find(marker="preview-0").elements))
    assert first_button.props["color"] == "secondary"
    assert first_button.props["icon"] == "visibility"
    assert "outline" not in first_button.props

    user.find("Rij toevoegen").click()
    first_button = next(iter(user.find(marker="preview-0").elements))
    second_button = next(iter(user.find(marker="preview-1").elements))
    assert first_button.props["color"] == "primary"
    assert first_button.props["icon"] == "radio_button_unchecked"
    assert second_button.props["color"] == "secondary"
    assert second_button.props["icon"] == "visibility"

    user.find(marker="name-0").trigger("focus")
    assert first_button.props["color"] == "secondary"
    assert first_button.props["icon"] == "visibility"
    assert second_button.props["color"] == "primary"


async def test_birth_date_has_optional_calendar(user: User) -> None:
    await user.open("/")

    birth_input = next(iter(user.find(marker="birth-date-0").elements))
    birth_picker = next(iter(user.find(marker="birth-date-picker-0").elements))

    assert birth_input.value == "01-01-2000"
    assert birth_picker.value == "01-01-2000"
    assert birth_picker.props["mask"] == "DD-MM-YYYY"

    user.find(marker="birth-date-picker-0").trigger(
        "update:modelValue",
        "14-02-2014",
    )
    assert birth_input.value == "14-02-2014"

    user.find(marker="birth-date-0").clear().type("31-12-2012")
    assert birth_picker.value == "31-12-2012"
