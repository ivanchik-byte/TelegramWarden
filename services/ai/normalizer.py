"""Text normalization, homoglyph cleaning, and anti-bypass sanitization."""

import re
import unicodedata
from typing import NamedTuple

# Extended homoglyph mappings (Cyrillic and Greek lookalikes to Latin standard)
HOMOGLYPH_MAP = {
    # Cyrillic lookalikes
    "а": "a", "А": "A",
    "в": "b", "В": "B",
    "е": "e", "Е": "E",
    "к": "k", "К": "K",
    "м": "m", "М": "M",
    "н": "h", "Н": "H",
    "о": "o", "О": "O",
    "р": "p", "Р": "P",
    "с": "c", "С": "C",
    "т": "t", "Т": "T",
    "у": "y", "У": "Y",
    "х": "x", "Х": "X",
    "і": "i", "І": "I",
    "ї": "i", "Ї": "I",
    "ѕ": "s", "Ѕ": "S",
    "ј": "j", "Ј": "J",
    # Greek lookalikes
    "α": "a", "Α": "A",
    "β": "b", "Β": "B",
    "ε": "e", "Ε": "E",
    "ι": "i", "Ι": "I",
    "κ": "k", "Κ": "K",
    "ο": "o", "Ο": "O",
    "ρ": "p", "Ρ": "P",
    "τ": "t", "Τ": "T",
    "υ": "u", "Υ": "Y",
    "χ": "x", "Χ": "X",
}

# Regex for Zero-Width and invisible characters
ZERO_WIDTH_PATTERN = re.compile(
    r"[\u200B-\u200D\uFEFF\u2060\u200E\u200F\u00AD\u202A-\u202E\u2066-\u2069]"
)

# Regex for Markdown and HTML hidden links
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^\)\s]+|t\.me/[^\)\s]+)\)")
HTML_LINK_PATTERN = re.compile(r'<a\s+(?:[^>]*?\s+)?href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', re.IGNORECASE)
BARE_URL_PATTERN = re.compile(r"(?:https?://|t\.me/|telegram\.me/|www\.)[a-zA-Z0-9\-._~:/?#\[\]@!$&'*+,;=%]+", re.IGNORECASE)
TELEGRAM_USERNAME_PATTERN = re.compile(r"@[a-zA-Z0-9_]{3,32}")


class SanitizedTextResult(NamedTuple):
    """Result container for sanitized text processing."""

    clean_text: str
    canonical_text: str
    extracted_urls: list[str]
    extracted_usernames: list[str]
    had_invisible_characters: bool


class TextSanitizer:
    """Sanitizes and normalizes incoming Telegram text against evasion techniques."""

    @classmethod
    def sanitize(cls, raw_text: str) -> SanitizedTextResult:
        """Strip invisible characters, normalize homoglyphs, and extract hidden links."""
        if not raw_text:
            return SanitizedTextResult(
                clean_text="",
                canonical_text="",
                extracted_urls=[],
                extracted_usernames=[],
                had_invisible_characters=False,
            )

        # 1. Detect and strip Zero-Width & RTL characters
        had_invisible = bool(ZERO_WIDTH_PATTERN.search(raw_text))
        clean_text = ZERO_WIDTH_PATTERN.sub("", raw_text)

        # 2. Unicode normalization (NFKC decomposes combined glyphs)
        normalized = unicodedata.normalize("NFKC", clean_text)

        # 3. Extract hidden URLs from Markdown and HTML formatting
        extracted_urls: list[str] = []

        # Extract markdown links and replace them with inner text for clean bare URL scanning
        def _extract_md(match: re.Match) -> str:
            url = match.group(2).rstrip(").,;\"'")
            if url not in extracted_urls:
                extracted_urls.append(url)
            return match.group(1)

        text_without_md = MARKDOWN_LINK_PATTERN.sub(_extract_md, normalized)

        # Extract HTML links and replace with inner text
        def _extract_html(match: re.Match) -> str:
            url = match.group(1).rstrip(").,;\"'")
            if url not in extracted_urls:
                extracted_urls.append(url)
            return match.group(2)

        text_without_html = HTML_LINK_PATTERN.sub(_extract_html, text_without_md)

        # Extract remaining bare URLs
        for match in BARE_URL_PATTERN.finditer(text_without_html):
            url = match.group(0).rstrip(").,;\"'>]")
            if url and url not in extracted_urls:
                extracted_urls.append(url)

        # 4. Extract @mentions
        extracted_usernames = list(dict.fromkeys(TELEGRAM_USERNAME_PATTERN.findall(normalized)))

        # 5. Build Canonical Text (mapping lookalikes to Latin for keyword checking)
        canonical_chars = [HOMOGLYPH_MAP.get(ch, ch) for ch in normalized]
        canonical_text = "".join(canonical_chars)

        return SanitizedTextResult(
            clean_text=normalized.strip(),
            canonical_text=canonical_text.strip(),
            extracted_urls=extracted_urls,
            extracted_usernames=extracted_usernames,
            had_invisible_characters=had_invisible,
        )
