from __future__ import annotations

import base64
import re
import unicodedata
from collections import OrderedDict

from app.catalog import TOOLS
from app.text_style import (
    aesthetic,
    bold_italic_unicode,
    bold_unicode,
    italic_unicode,
    monospace_unicode,
    small_caps,
    strikethrough,
    underline,
)


URL_RE = re.compile(r"https?://[^\s<>()]+|t\.me/[^\s<>()]+|www\.[^\s<>()]+", re.IGNORECASE)


def clean_text(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.replace("\r\n", "\n").split("\n")]
    compact: list[str] = []
    blank = False
    for line in lines:
        if not line:
            if not blank and compact:
                compact.append("")
            blank = True
            continue
        compact.append(line)
        blank = False
    return "\n".join(compact).strip()


def title_case(text: str) -> str:
    return " ".join(word[:1].upper() + word[1:].lower() if word else word for word in text.split(" "))


def sentence_case(text: str) -> str:
    lowered = text.strip().lower()
    if not lowered:
        return lowered
    return lowered[0].upper() + lowered[1:]


def alternating_case(text: str) -> str:
    out: list[str] = []
    upper = True
    for ch in text:
        if ch.isalpha():
            out.append(ch.upper() if upper else ch.lower())
            upper = not upper
        else:
            out.append(ch)
    return "".join(out)


def remove_duplicate_lines(text: str) -> str:
    seen: OrderedDict[str, str] = OrderedDict()
    for line in text.replace("\r\n", "\n").split("\n"):
        normalized = line.strip()
        if normalized and normalized.casefold() not in seen:
            seen[normalized.casefold()] = normalized
    return "\n".join(seen.values())


def remove_extra_spaces(text: str) -> str:
    return clean_text(text)


def remove_emoji(text: str) -> str:
    return "".join(
        ch
        for ch in text
        if not (
            unicodedata.category(ch) in {"So", "Sk"}
            and not ch.isalnum()
            and ch not in {"©", "®", "™"}
        )
    ).strip()


def extract_links(text: str) -> list[str]:
    links = [match.group(0).rstrip(".,;!?)") for match in URL_RE.finditer(text)]
    return list(OrderedDict((link, None) for link in links).keys())


def format_message(text: str) -> str:
    cleaned = clean_text(text)
    paragraphs = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
    if not paragraphs:
        return ""
    formatted: list[str] = []
    for idx, paragraph in enumerate(paragraphs, start=1):
        lines = [line.strip(" -•") for line in paragraph.splitlines() if line.strip()]
        if len(lines) > 1:
            formatted.append("\n".join(f"• {line}" for line in lines))
        elif idx == 1 and len(lines[0]) <= 80:
            formatted.append(bold_unicode(lines[0]))
        else:
            formatted.append(lines[0])
    return "\n\n".join(formatted)


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def encode_or_decode(text: str) -> str:
    value = text.strip()
    if value.lower().startswith("decrypt:"):
        payload = value.split(":", 1)[1].strip()
        try:
            padded = payload + "=" * (-len(payload) % 4)
            return base64.urlsafe_b64decode(padded.encode()).decode("utf-8")
        except Exception:
            return "Unable to decrypt this value. Send decrypt:<Base64 text> from this bot."
    encoded = base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")
    return f"Base64: {encoded}\n\nTo decrypt later, send:\ndecrypt:{encoded}"


def word_stats(text: str) -> str:
    words = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)
    chars = len(text)
    no_spaces = len(re.sub(r"\s+", "", text))
    lines = len(text.splitlines()) if text else 0
    reading_minutes = max(1, round(len(words) / 200))
    return (
        f"Words: {len(words)}\n"
        f"Characters: {chars}\n"
        f"Characters without spaces: {no_spaces}\n"
        f"Lines: {lines}\n"
        f"Estimated reading time: {reading_minutes} min"
    )


def character_stats(text: str) -> str:
    spaces = sum(1 for ch in text if ch.isspace())
    return (
        f"Characters: {len(text)}\n"
        f"Characters without spaces: {len(text) - spaces}\n"
        f"Spaces: {spaces}"
    )


def line_stats(text: str) -> str:
    lines = text.splitlines()
    non_empty = [line for line in lines if line.strip()]
    return f"Lines: {len(lines)}\nNon-empty lines: {len(non_empty)}\nEmpty lines: {len(lines) - len(non_empty)}"


def stylish_variants(text: str) -> str:
    variants = [
        ("Style 1", bold_unicode(text)),
        ("Style 2", italic_unicode(text)),
        ("Style 3", monospace_unicode(text)),
        ("Style 4", bold_italic_unicode(text)),
        ("Style 5", small_caps(text)),
        ("Style 6", aesthetic(text)),
        ("Style 7", underline(text)),
        ("Style 8", strikethrough(text)),
    ]
    return "\n".join(f"{label}: {value}" for label, value in variants)


def fancy_fonts(text: str) -> str:
    return "\n".join(
        [
            f"Bold: {bold_unicode(text)}",
            f"Italic: {italic_unicode(text)}",
            f"Bold Italic: {bold_italic_unicode(text)}",
            f"Monospace: {monospace_unicode(text)}",
            f"Small Caps: {small_caps(text)}",
            f"Underline: {underline(text)}",
        ]
    )


def emoji_text(text: str) -> str:
    cleaned = clean_text(text)
    if "\n" in cleaned:
        return "\n".join(f"✨ {line} ✨" if line.strip() else "" for line in cleaned.splitlines())
    return f"✨ {cleaned} ✨\n💫 {bold_unicode(cleaned)} 💫\n🌟 {aesthetic(cleaned)} 🌟"


def stylish_name(text: str) -> str:
    value = clean_text(text).replace("\n", " ")
    return "\n".join(
        [
            f"1. {bold_unicode(value)}",
            f"2. {small_caps(value)}",
            f"3. 『{value}』",
            f"4. 么 {value} 么",
            f"5. ✦ {aesthetic(value)} ✦",
            f"6. {strikethrough(value)}",
        ]
    )


def case_conversions(text: str) -> str:
    return "\n".join(
        [
            f"UPPERCASE: {text.upper()}",
            f"lowercase: {text.lower()}",
            f"Title Case: {title_case(text)}",
            f"Sentence case: {sentence_case(text)}",
            f"Alternating Case: {alternating_case(text)}",
            f"Capitalized Words: {' '.join(word.capitalize() for word in text.split())}",
        ]
    )


def process_tool(tool_key: str, text: str) -> str:
    if tool_key not in TOOLS:
        raise KeyError(f"Unknown tool: {tool_key}")
    processors = {
        "stylish_text": stylish_variants,
        "fancy_fonts": fancy_fonts,
        "bold_text": bold_unicode,
        "italic_text": italic_unicode,
        "underline_text": underline,
        "strikethrough_text": strikethrough,
        "monospace_text": monospace_unicode,
        "small_caps_text": small_caps,
        "aesthetic_text": aesthetic,
        "emoji_text": emoji_text,
        "fonts_preview": stylish_variants,
        "stylish_name": stylish_name,
        "message_formatter": format_message,
        "text_cleaner": clean_text,
        "case_converter": case_conversions,
        "word_counter": word_stats,
        "character_counter": character_stats,
        "line_counter": line_stats,
        "duplicate_line_remover": remove_duplicate_lines,
        "extra_space_remover": remove_extra_spaces,
        "emoji_remover": remove_emoji,
        "link_extractor": lambda value: _format_links(extract_links(value)),
        "text_formatter": format_message,
        "slug_generator": slugify,
        "text_encrypt_decrypt": encode_or_decode,
    }
    return processors[tool_key](text).strip()


def _format_links(links: list[str]) -> str:
    if not links:
        return "Found Links: 0"
    lines = [f"Found Links: {len(links)}", ""]
    lines.extend(f"{idx}. {link}" for idx, link in enumerate(links, start=1))
    return "\n".join(lines)
