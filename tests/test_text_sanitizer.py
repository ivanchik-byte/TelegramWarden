"""Unit tests for TextSanitizer normalization and evasion defense."""

from services.ai.normalizer import TextSanitizer


def test_zero_width_and_invisible_character_removal():
    """Verify that zero-width and invisible bypass characters are stripped."""
    # Text with zero-width space \u200b and byte order mark \ufeff
    evasion_text = "к\u200bр\u200cи\u200dп\ufeffт\u2060а"
    result = TextSanitizer.sanitize(evasion_text)

    assert result.clean_text == "крипта"
    assert result.had_invisible_characters is True


def test_markdown_and_html_link_extraction():
    """Verify that hidden URLs in Markdown and HTML formatting are extracted."""
    formatted_text = "Заходи на [наш канал](https://t.me/scam_channel) или на <a href=\"https://phishing-site.xyz\">сайт</a>"
    result = TextSanitizer.sanitize(formatted_text)

    assert len(result.extracted_urls) == 2
    assert "https://t.me/scam_channel" in result.extracted_urls
    assert "https://phishing-site.xyz" in result.extracted_urls


def test_telegram_username_extraction():
    """Verify that @usernames and contacts are extracted."""
    text = "Пишите в личку @crypto_manager_top или @support_bot"
    result = TextSanitizer.sanitize(text)

    assert len(result.extracted_usernames) == 2
    assert "@crypto_manager_top" in result.extracted_usernames
    assert "@support_bot" in result.extracted_usernames


def test_homoglyph_canonicalization():
    """Verify that Cyrillic lookalikes are mapped to canonical Latin characters."""
    # Mixed string containing Cyrillic 'es' / 'a' and Latin characters
    mixed_text = "сaѕh"

    result = TextSanitizer.sanitize(mixed_text)

    # In canonical text, Cyrillic lookalikes should be normalized
    assert result.canonical_text.isascii()


def test_hidden_text_link_entities_are_extracted():
    """Telegram text_link entities hide URLs behind innocent display text."""
    from types import SimpleNamespace
    from bot.utils.text_moderation import extract_entity_urls

    message = SimpleNamespace(
        text="просто привет",
        caption=None,
        entities=[
            SimpleNamespace(type="text_link", offset=0, length=7, url="https://spam.example/ton"),
            SimpleNamespace(type="bold", offset=8, length=5, url=None),
        ],
        caption_entities=[],
    )
    urls = extract_entity_urls(message)
    assert "https://spam.example/ton" in urls
