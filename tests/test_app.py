from nicegui.testing import User

import app  # noqa: F401  # register the NiceGUI page


async def test_preview_button_follows_active_row(user: User) -> None:
    await user.open("/")

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
