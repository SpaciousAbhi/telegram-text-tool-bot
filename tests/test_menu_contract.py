from datetime import UTC, datetime

from bson import ObjectId

from app.catalog import STYLE_TOOLS, UTILITY_TOOLS, STYLE_CATEGORY, UTILITY_CATEGORY, TOOLS
from app.keyboards import (
    admin_back_keyboard,
    admin_ban_keyboard,
    admin_bot_settings_keyboard,
    admin_broadcast_keyboard,
    admin_force_keyboard,
    admin_keyboard,
    admin_premium_keyboard,
    admin_referral_keyboard,
    category_keyboard,
    confirm_keyboard,
    force_gate_keyboard,
    help_keyboard,
    language_keyboard,
    main_menu_keyboard,
    output_style_keyboard,
    premium_keyboard,
    profile_keyboard,
    referral_keyboard,
    result_keyboard,
    settings_keyboard,
    status_keyboard,
    support_keyboard,
    task_detail_keyboard,
    tasks_keyboard,
    terms_keyboard,
    tool_prompt_keyboard,
)
from app.renderers import (
    admin_bot_settings_screen,
    admin_broadcast_screen,
    admin_force_screen,
    admin_home_screen,
    admin_referral_screen,
    admin_stats_screen,
    category_screen,
    choose_tool_first_screen,
    empty_input_screen,
    force_subscription_screen,
    help_screen,
    logs_screen,
    main_caption,
    premium_screen,
    private_result_screen,
    processing_error_screen,
    processing_screen,
    profile_screen,
    referral_leaderboard_screen,
    referral_screen,
    result_screen,
    settings_screen,
    support_screen,
    system_status_screen,
    task_detail_screen,
    tasks_screen,
    terms_screen,
    too_long_screen,
    tool_cancelled_screen,
    tool_prompt,
    unauthorized_screen,
)
from app.text_style import bold_unicode


def flatten_buttons(markup):
    return [button for row in markup.inline_keyboard for button in row]


def callbacks(markup):
    return [button.callback_data for button in flatten_buttons(markup) if button.callback_data]


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
    assert callbacks.index("menu:tasks") < callbacks.index("menu:status")
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
    assert "tool:cancel" in callbacks
    assert "menu:help" not in callbacks
    assert [callback for callback in callbacks if (callback or "").startswith("tool:")] == ["tool:cancel"]


def test_core_ui_messages_are_polished_and_copy_friendly():
    home = main_caption(user={"first_name": "<Abhi>", "last_name": "", "username": ""})
    category = category_screen(STYLE_CATEGORY)
    prompt = tool_prompt("stylish_text")
    processing = processing_screen("stylish_text")
    result = result_screen("stylish_text", "Your Text", "Style 1: Your Text")

    assert "🧰" in home
    assert "&lt;Abhi&gt;" in home
    assert bold_unicode("Start Here") in home
    assert "✨" in category
    assert bold_unicode("Available tools") in category
    assert bold_unicode("Category") in prompt
    assert bold_unicode("Status") in prompt
    assert bold_unicode("Send") in prompt
    assert "cancel this tool" in prompt
    assert "⏳" in processing
    assert bold_unicode("Saved") in result
    assert bold_unicode("Copy-Friendly Result") in result
    assert "<code>Style 1: Your Text</code>" in result


def test_encrypt_prompt_escapes_html_like_example_text():
    prompt = tool_prompt("text_encrypt_decrypt")

    assert "decrypt:&lt;value&gt;" in prompt
    assert "decrypt:<value>" not in prompt


def test_custom_start_caption_stays_photo_caption_safe():
    caption = main_caption("<&>" * 5000, user={"first_name": "User"})

    assert len(caption) <= 1024
    assert "&lt;" in caption


def test_html_heavy_results_stay_message_safe():
    for output_style in ["Clean", "Compact", "Detailed"]:
        result = result_screen("text_cleaner", "input", "<&>" * 5000, output_style=output_style)

        assert len(result) <= 4096
        assert "&lt;" in result


def test_saved_result_button_opens_tasks():
    markup = result_keyboard(TOOLS["stylish_text"], saved=True)
    callbacks = [button.callback_data for button in flatten_buttons(markup)]

    assert "menu:tasks" in callbacks
    assert "task:save_latest" not in callbacks


def test_privacy_mode_result_removes_unavailable_save_action():
    result = private_result_screen("text_cleaner", "  hello  ", "hello")
    markup = result_keyboard(TOOLS["text_cleaner"], can_save=False)

    assert "Privacy Mode is on" in result
    assert "task:save_latest" not in callbacks(markup)
    assert "menu:tasks" not in callbacks(markup)


def test_output_style_setting_changes_result_presentation():
    clean = result_screen("text_cleaner", "hello", "hello", output_style="Clean")
    compact = result_screen("text_cleaner", "hello", "hello", output_style="Compact")
    detailed = result_screen("text_cleaner", "hello", "hello", output_style="Detailed")

    assert bold_unicode("Input") in clean
    assert bold_unicode("Input") not in compact
    assert bold_unicode("Category") in detailed
    assert len(compact) < len(clean) < len(detailed)


def test_referral_keyboard_has_real_share_action_and_refresh():
    markup = referral_keyboard("https://t.me/TextToolBot?start=ref_123")
    buttons = flatten_buttons(markup)

    assert buttons[0].url.startswith("https://t.me/share/url?")
    assert "ref_123" in buttons[0].url
    assert "referral:refresh" in callbacks(markup)
    assert "menu:home" in callbacks(markup)


def test_force_gate_has_one_clear_verification_action():
    markup = force_gate_keyboard([{"target": "@updates", "label": "Updates"}])

    assert callbacks(markup) == ["fs:check"]
    assert any(button.url == "https://t.me/updates" for button in flatten_buttons(markup))


def test_premium_keyboard_lists_explicit_stars_plans():
    markup = premium_keyboard()
    buttons = flatten_buttons(markup)

    assert callbacks(markup) == ["premium:buy:30", "premium:buy:90", "premium:buy:365", "menu:home"]
    assert all(bold_unicode("Stars") in button.text for button in buttons[:3])


def test_every_keyboard_family_is_mobile_safe_and_telegram_safe():
    task_id = str(ObjectId())
    channel = {"_id": ObjectId(), "target": "@updates", "label": "Updates", "enabled": True}
    task = {"_id": ObjectId(task_id), "tool_title": "Text Cleaner"}
    markups = [
        main_menu_keyboard(),
        category_keyboard(STYLE_CATEGORY),
        category_keyboard(UTILITY_CATEGORY),
        tool_prompt_keyboard(STYLE_CATEGORY),
        result_keyboard(TOOLS["text_cleaner"]),
        result_keyboard(TOOLS["text_cleaner"], saved=True),
        result_keyboard(TOOLS["text_cleaner"], can_save=False),
        profile_keyboard(),
        premium_keyboard(),
        referral_keyboard("https://t.me/TextToolBot?start=ref_123"),
        settings_keyboard(),
        language_keyboard(),
        output_style_keyboard(),
        tasks_keyboard([]),
        tasks_keyboard([task]),
        task_detail_keyboard(task_id),
        confirm_keyboard("settings:clear_data"),
        support_keyboard("support", "updates"),
        force_gate_keyboard([channel]),
        help_keyboard(),
        status_keyboard(),
        terms_keyboard(),
        admin_keyboard(),
        admin_back_keyboard(),
        admin_broadcast_keyboard(),
        admin_referral_keyboard(True),
        admin_premium_keyboard(),
        admin_force_keyboard([channel]),
        admin_ban_keyboard(),
        admin_bot_settings_keyboard(),
    ]
    for markup in markups:
        assert markup.inline_keyboard
        assert all(1 <= len(row) <= 2 for row in markup.inline_keyboard)
        for button in flatten_buttons(markup):
            assert button.callback_data or button.url
            if button.callback_data:
                assert len(button.callback_data.encode("utf-8")) <= 64


def test_all_major_screens_fit_telegram_message_limits():
    now = datetime.now(UTC)
    user = {
        "user_id": 123,
        "first_name": "User",
        "last_name": "",
        "username": "user",
        "joined_at": now,
        "settings": {},
    }
    task = {
        "_id": ObjectId(),
        "tool_key": "text_cleaner",
        "tool_title": "Text Cleaner",
        "status": "Completed",
        "original": " messy text ",
        "result": "messy text",
        "created_at": now,
    }
    counts = {"users": 3, "tasks": 2, "premium": 1, "banned": 0, "force_channels": 1}
    config = {"referral_rewards_enabled": True, "referral_required_joins": 3, "referral_reward_days": 7}
    screens = [
        main_caption(user=user),
        category_screen(STYLE_CATEGORY),
        category_screen(UTILITY_CATEGORY),
        choose_tool_first_screen(),
        empty_input_screen(),
        too_long_screen(3000),
        processing_error_screen(),
        tool_cancelled_screen(),
        profile_screen(user, 1, 50, 500),
        premium_screen(user, 500),
        referral_screen(user, "TextToolBot", True, 3, 7),
        settings_screen(user),
        help_screen(),
        terms_screen(),
        support_screen("support", "updates"),
        system_status_screen(counts, "2h 10m", False, 2),
        tasks_screen([]),
        tasks_screen([task]),
        task_detail_screen(task),
        force_subscription_screen([{"target": "@updates", "label": "Updates"}]),
        unauthorized_screen(),
        admin_home_screen(counts, False),
        admin_stats_screen(counts),
        admin_broadcast_screen(),
        admin_force_screen([{"target": "@updates", "label": "Updates", "enabled": True}]),
        admin_referral_screen(config),
        referral_leaderboard_screen([user | {"valid_referrals": 2}]),
        admin_bot_settings_screen({}),
        logs_screen([]),
    ]
    for tool_key in TOOLS:
        screens.extend(
            [
                tool_prompt(tool_key),
                processing_screen(tool_key),
                result_screen(tool_key, "sample text", "sample result"),
                private_result_screen(tool_key, "sample text", "sample result"),
            ]
        )
    assert len(main_caption(user=user)) <= 1024
    assert all(len(screen) <= 4096 for screen in screens)


def test_admin_and_settings_buttons_have_valid_callback_lengths():
    for markup in [admin_keyboard(), settings_keyboard()]:
        for button in flatten_buttons(markup):
            if button.callback_data:
                assert len(button.callback_data.encode("utf-8")) <= 64
