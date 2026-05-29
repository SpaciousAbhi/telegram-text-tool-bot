from app.catalog import STYLE_TOOLS, UTILITY_TOOLS, STYLE_CATEGORY, UTILITY_CATEGORY, TOOLS
from app.keyboards import (
    admin_keyboard,
    category_keyboard,
    main_menu_keyboard,
    result_keyboard,
    settings_keyboard,
    tool_prompt_keyboard,
)
from app.renderers import category_screen, main_caption, processing_screen, result_screen, tool_prompt
from app.text_style import bold_unicode


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


def test_feature_buttons_have_intentional_matching_emojis():
    for category, tools in [(STYLE_CATEGORY, STYLE_TOOLS), (UTILITY_CATEGORY, UTILITY_TOOLS)]:
        rows = category_keyboard(category).inline_keyboard[: len(tools)]
        for row, tool in zip(rows, tools, strict=True):
            assert row[0].text.startswith(tool.emoji)
            assert bold_unicode(tool.title) in row[0].text


def test_selected_tool_prompt_uses_focused_navigation():
    markup = tool_prompt_keyboard(STYLE_CATEGORY)
    callbacks = [button.callback_data for button in flatten_buttons(markup)]

    assert f"cat:{STYLE_CATEGORY}" in callbacks
    assert "menu:home" in callbacks
    assert "menu:tasks" in callbacks
    assert "menu:help" in callbacks
    assert not any((callback or "").startswith("tool:") for callback in callbacks)


def test_core_ui_messages_are_polished_and_copy_friendly():
    home = main_caption(user={"first_name": "<Abhi>", "last_name": "", "username": ""})
    category = category_screen(STYLE_CATEGORY)
    prompt = tool_prompt("stylish_text")
    processing = processing_screen("stylish_text")
    result = result_screen("stylish_text", "Your Text", "Style 1: Your Text")

    assert "🧰" in home
    assert "&lt;Abhi&gt;" in home
    assert bold_unicode("Start with one section below") in home
    assert "✨" in category
    assert bold_unicode("Available tools") in category
    assert bold_unicode("Current Category") in prompt
    assert bold_unicode("Selected Tool") in prompt
    assert bold_unicode("Send next") in prompt
    assert "⏳" in processing
    assert bold_unicode("Copy-Friendly Result") in result
    assert "<code>Style 1: Your Text</code>" in result


def test_saved_result_button_opens_tasks():
    markup = result_keyboard(TOOLS["stylish_text"], saved=True)
    callbacks = [button.callback_data for button in flatten_buttons(markup)]

    assert "menu:tasks" in callbacks
    assert "task:save_latest" not in callbacks


def test_admin_and_settings_buttons_have_valid_callback_lengths():
    for markup in [admin_keyboard(), settings_keyboard()]:
        for button in flatten_buttons(markup):
            if button.callback_data:
                assert len(button.callback_data.encode("utf-8")) <= 64
