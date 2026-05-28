import pytest

from app.catalog import TOOLS
from app.text_tools import extract_links, process_tool


def test_stylish_text_returns_multiple_copyable_styles():
    result = process_tool("stylish_text", "Your Text")

    assert "Style 1:" in result
    assert "𝐘𝐨𝐮𝐫" in result
    assert "𝚈𝚘𝚞𝚛" in result


def test_utility_counters_are_labeled():
    result = process_tool("word_counter", "one two\nthree")

    assert "Words: 3" in result
    assert "Characters:" in result
    assert "Estimated reading time:" in result


def test_link_extractor_deduplicates_links():
    links = extract_links("Visit https://example.com and https://example.com. Also t.me/example")

    assert links == ["https://example.com", "t.me/example"]


def test_duplicate_line_remover_keeps_first_unique_lines():
    result = process_tool("duplicate_line_remover", "Alpha\nBeta\nalpha\n\nBeta\nGamma")

    assert result == "Alpha\nBeta\nGamma"


def test_encrypt_decrypt_round_trip():
    encrypted = process_tool("text_encrypt_decrypt", "secret text")
    payload = encrypted.split("decrypt:", 1)[1]

    assert process_tool("text_encrypt_decrypt", f"decrypt:{payload}") == "secret text"


@pytest.mark.parametrize("tool_key", sorted(TOOLS))
def test_every_listed_tool_returns_a_real_result(tool_key):
    sample = "My New Post Title\nhttps://example.com\nMy New Post Title ✨"
    result = process_tool(tool_key, sample)

    assert result.strip()
    assert "Traceback" not in result
    assert "None" not in result


def test_cleaning_utilities_deliver_expected_outputs():
    assert process_tool("slug_generator", "My New Post Title") == "my-new-post-title"
    assert "Characters without spaces:" in process_tool("character_counter", "ab cd")
    assert "Non-empty lines: 2" in process_tool("line_counter", "a\n\nb")
    assert "✨" not in process_tool("emoji_remover", "Hello ✨")
    assert "UPPERCASE: HELLO WORLD" in process_tool("case_converter", "hello world")
