from __future__ import annotations

from dataclasses import dataclass

from app.text_style import bold_unicode


STYLE_CATEGORY = "style"
UTILITY_CATEGORY = "utility"


@dataclass(frozen=True)
class ToolDefinition:
    key: str
    title: str
    category: str
    instruction: str
    result_hint: str

    @property
    def display_title(self) -> str:
        return bold_unicode(self.title)


STYLE_TOOLS = [
    ToolDefinition("stylish_text", "Stylish Text Generator", STYLE_CATEGORY, "Send the text you want to convert into stylish formats.", "multiple stylish Unicode versions"),
    ToolDefinition("fancy_fonts", "Fancy Fonts Generator", STYLE_CATEGORY, "Send the text you want to convert into fancy fonts.", "multiple fancy font versions"),
    ToolDefinition("bold_text", "Bold Text Generator", STYLE_CATEGORY, "Send the text you want to convert into bold Unicode text.", "bold Unicode text"),
    ToolDefinition("italic_text", "Italic Text Generator", STYLE_CATEGORY, "Send the text you want to convert into italic Unicode text.", "italic Unicode text"),
    ToolDefinition("underline_text", "Underline Text Generator", STYLE_CATEGORY, "Send the text you want to underline.", "underlined text"),
    ToolDefinition("strikethrough_text", "Strikethrough Text Generator", STYLE_CATEGORY, "Send the text you want to strike through.", "strikethrough text"),
    ToolDefinition("monospace_text", "Monospace Text Generator", STYLE_CATEGORY, "Send the text you want to convert into monospace Unicode text.", "monospace Unicode text"),
    ToolDefinition("small_caps_text", "Small Caps Text Generator", STYLE_CATEGORY, "Send the text you want to convert into small caps.", "small caps text"),
    ToolDefinition("aesthetic_text", "Aesthetic Text Generator", STYLE_CATEGORY, "Send the text you want to make aesthetic and spaced.", "aesthetic spaced text"),
    ToolDefinition("emoji_text", "Emoji Text Generator", STYLE_CATEGORY, "Send the text you want decorated with clean emoji styling.", "emoji-decorated text"),
    ToolDefinition("fonts_preview", "Fonts Preview", STYLE_CATEGORY, "Send text to preview it in multiple font styles at once.", "font comparison preview"),
    ToolDefinition("stylish_name", "Stylish Name Generator", STYLE_CATEGORY, "Send a name, username, nickname, gaming name, or channel name.", "stylish name ideas"),
    ToolDefinition("message_formatter", "Message Formatter", STYLE_CATEGORY, "Send the message you want cleaned into a Telegram-ready format.", "formatted Telegram message"),
]


UTILITY_TOOLS = [
    ToolDefinition("text_cleaner", "Text Cleaner", UTILITY_CATEGORY, "Send the text you want to clean.", "cleaned text"),
    ToolDefinition("case_converter", "Case Converter", UTILITY_CATEGORY, "Send text to convert it into common case formats.", "case conversion list"),
    ToolDefinition("word_counter", "Word Counter", UTILITY_CATEGORY, "Send text to count words and reading time.", "word statistics"),
    ToolDefinition("character_counter", "Character Counter", UTILITY_CATEGORY, "Send text to count characters, spaces, and characters without spaces.", "character statistics"),
    ToolDefinition("line_counter", "Line Counter", UTILITY_CATEGORY, "Send text to count lines.", "line statistics"),
    ToolDefinition("duplicate_line_remover", "Duplicate Line Remover", UTILITY_CATEGORY, "Send text or a list with repeated lines.", "deduplicated text"),
    ToolDefinition("extra_space_remover", "Extra Space Remover", UTILITY_CATEGORY, "Send text with extra spaces or blank lines.", "space-cleaned text"),
    ToolDefinition("emoji_remover", "Emoji Remover", UTILITY_CATEGORY, "Send text that contains emojis you want removed.", "text without emojis"),
    ToolDefinition("link_extractor", "Link Extractor", UTILITY_CATEGORY, "Send text that contains links.", "clean link list"),
    ToolDefinition("text_formatter", "Text Formatter", UTILITY_CATEGORY, "Send messy text that needs better spacing and structure.", "formatted readable text"),
    ToolDefinition("slug_generator", "Slug Generator", UTILITY_CATEGORY, "Send a title or phrase to convert into a URL-friendly slug.", "URL-friendly slug"),
    ToolDefinition("text_encrypt_decrypt", "Text Encrypt/Decrypt", UTILITY_CATEGORY, "Send text to encode, or send decrypt:<value> to decode a previous Base64 result.", "encoded or decoded text"),
]


TOOLS = {tool.key: tool for tool in [*STYLE_TOOLS, *UTILITY_TOOLS]}
CATEGORY_TOOLS = {
    STYLE_CATEGORY: STYLE_TOOLS,
    UTILITY_CATEGORY: UTILITY_TOOLS,
}


def category_title(category: str) -> str:
    if category == STYLE_CATEGORY:
        return bold_unicode("TEXT STYLE & FONTS")
    if category == UTILITY_CATEGORY:
        return bold_unicode("TEXT CLEANING & UTILITY")
    return bold_unicode("TEXT TOOLS")


def category_description(category: str) -> str:
    if category == STYLE_CATEGORY:
        return (
            "This section is for stylish, fancy, bold, italic, aesthetic, emoji-based, "
            "and Telegram-ready captions, bios, usernames, posts, and messages."
        )
    return "This section is for cleaning, formatting, counting, extracting, removing, converting, and processing text quickly."
