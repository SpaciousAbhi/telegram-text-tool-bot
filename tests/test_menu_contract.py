from app.catalog import STYLE_TOOLS, UTILITY_TOOLS, STYLE_CATEGORY, UTILITY_CATEGORY
from app.keyboards import admin_keyboard, category_keyboard, main_menu_keyboard, settings_keyboard


def flatten_buttons(markup):
    return [button for row in markup.inline_keyboard for button in row]


def test_start_menu_has_no_admin_panel_button_or_callback():
    buttons = flatten_buttons(main_menu_keyboard())
    text = " ".join(button.text for button in buttons)
    callbacks = " ".join(button.callback_data or "" for button in buttons)

    assert "Admin" not in text
    assert "ADMIN" not in text
    assert "admin:" not in callbacks


def test_start_menu_keeps_categories_before_tools():
    buttons = flatten_buttons(main_menu_keyboard())
    callbacks = [button.callback_data for button in buttons]

    assert "cat:style" in callbacks
    assert "cat:utility" in callbacks
    assert not any((callback or "").startswith("tool:") for callback in callbacks)


def test_feature_buttons_do_not_include_bot_word():
    titles = [tool.title for tool in [*STYLE_TOOLS, *UTILITY_TOOLS]]

    assert all("Bot" not in title for title in titles)
    assert "Stylish Text Generator" in titles
    assert "Text Cleaner" in titles


def test_category_keyboards_show_every_listed_tool_once():
    style_callbacks = [button.callback_data for button in flatten_buttons(category_keyboard(STYLE_CATEGORY))]
    utility_callbacks = [button.callback_data for button in flatten_buttons(category_keyboard(UTILITY_CATEGORY))]

    assert [f"tool:{tool.key}" for tool in STYLE_TOOLS] == [callback for callback in style_callbacks if callback and callback.startswith("tool:")]
    assert [f"tool:{tool.key}" for tool in UTILITY_TOOLS] == [callback for callback in utility_callbacks if callback and callback.startswith("tool:")]


def test_admin_and_settings_buttons_have_valid_callback_lengths():
    for markup in [admin_keyboard(), settings_keyboard()]:
        for button in flatten_buttons(markup):
            if button.callback_data:
                assert len(button.callback_data.encode("utf-8")) <= 64
