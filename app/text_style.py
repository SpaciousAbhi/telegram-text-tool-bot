from __future__ import annotations

import html
import re
import unicodedata


BOLD_UPPER = 0x1D400
BOLD_LOWER = 0x1D41A
BOLD_DIGIT = 0x1D7CE
ITALIC_UPPER = 0x1D434
ITALIC_LOWER = 0x1D44E
BOLD_ITALIC_UPPER = 0x1D468
BOLD_ITALIC_LOWER = 0x1D482
MONO_UPPER = 0x1D670
MONO_LOWER = 0x1D68A
MONO_DIGIT = 0x1D7F6


SMALL_CAPS = {
    "a": "ᴀ",
    "b": "ʙ",
    "c": "ᴄ",
    "d": "ᴅ",
    "e": "ᴇ",
    "f": "ꜰ",
    "g": "ɢ",
    "h": "ʜ",
    "i": "ɪ",
    "j": "ᴊ",
    "k": "ᴋ",
    "l": "ʟ",
    "m": "ᴍ",
    "n": "ɴ",
    "o": "ᴏ",
    "p": "ᴘ",
    "q": "ǫ",
    "r": "ʀ",
    "s": "ꜱ",
    "t": "ᴛ",
    "u": "ᴜ",
    "v": "ᴠ",
    "w": "ᴡ",
    "x": "x",
    "y": "ʏ",
    "z": "ᴢ",
}


def escape_html(value: object) -> str:
    return html.escape(str(value), quote=False)


def _math_alpha(text: str, upper_start: int, lower_start: int, digit_start: int | None = None) -> str:
    out: list[str] = []
    for ch in text:
        if "A" <= ch <= "Z":
            out.append(chr(upper_start + ord(ch) - ord("A")))
        elif "a" <= ch <= "z":
            out.append(chr(lower_start + ord(ch) - ord("a")))
        elif digit_start is not None and "0" <= ch <= "9":
            out.append(chr(digit_start + ord(ch) - ord("0")))
        else:
            out.append(ch)
    return "".join(out)


def bold_unicode(text: str) -> str:
    return _math_alpha(text, BOLD_UPPER, BOLD_LOWER, BOLD_DIGIT)


def italic_unicode(text: str) -> str:
    out: list[str] = []
    for ch in text:
        if "A" <= ch <= "Z":
            out.append(chr(ITALIC_UPPER + ord(ch) - ord("A")))
        elif "a" <= ch <= "z":
            idx = ord(ch) - ord("a")
            if ch == "h":
                out.append("ℎ")
            elif ch > "h":
                out.append(chr(ITALIC_LOWER + idx + 1))
            else:
                out.append(chr(ITALIC_LOWER + idx))
        else:
            out.append(ch)
    return "".join(out)


def bold_italic_unicode(text: str) -> str:
    return _math_alpha(text, BOLD_ITALIC_UPPER, BOLD_ITALIC_LOWER)


def monospace_unicode(text: str) -> str:
    return _math_alpha(text, MONO_UPPER, MONO_LOWER, MONO_DIGIT)


def small_caps(text: str) -> str:
    return "".join(SMALL_CAPS.get(ch.lower(), ch) if ch.isalpha() else ch for ch in text)


def underline(text: str) -> str:
    return "".join(f"{ch}\u0332" if ch.strip() else ch for ch in text)


def strikethrough(text: str) -> str:
    return "".join(f"{ch}\u0336" if ch.strip() else ch for ch in text)


def aesthetic(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    return " ".join(cleaned)


def normalize_plain(text: str) -> str:
    return unicodedata.normalize("NFKC", text)
