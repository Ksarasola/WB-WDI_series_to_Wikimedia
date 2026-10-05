"""Convert a JSON or XML file into a simple, single-column CSV: one row per line of
the beautified (pretty-printed) source content.

This replaces the earlier field-by-field flattening approach (metadata_ETL_specifications)
for the WDI dataset-wide metadata files, which proved too complex given how much the
JSON/XML shape varies across different WB endpoints (plain objects, arrays of {id,value},
deeply nested SDMX structures, etc.) - each requiring its own conversion rules and
repeatedly surfacing new edge cases. Beautifying and splitting into lines needs no
per-source-shape logic at all: every file, regardless of its structure, is handled by
the same two functions.

Trade-off: this is not queryable field-by-field the way the earlier approach was -
it's a readable, line-searchable rendering of the original file, not a structured table.

Wikimedia Commons .tab import constraints handled here:
- Leading whitespace: Commons' .tab renderer strips/collapses a leading run of literal
  spaces, which destroys the pretty-printed indentation. Each leading space character is
  therefore substituted with '_' (e.g. two levels of 2-space indent -> "____") so the
  indentation survives rendering and stays visually obvious as indentation rather than
  content.
- 400-char string limit: Commons .tab rejects any single string value longer than
  MAX_LINE_LEN characters. Lines longer than that are split into consecutive chunks;
  every chunk after the first is prefixed with CONTINUATION_PREFIX ('+') so a human or a
  future parser can tell it is a continuation of the previous row rather than a new,
  independent line of the source file. Chunk boundaries are computed against the length
  the chunk will actually have once csv.writer serializes it - not its raw Python string
  length - since csv.QUOTE_ALL wraps every field in quotechar (2 extra characters) and
  doubles every internal '"' regardless of content, and JSON/XML text is almost always
  full of '"' characters. Budgeting on raw length alone was letting rows through that
  were >400 chars once actually written to the file.
- No trailing whitespace in a cell (same MediaWiki page): a wrap boundary that would
  leave a chunk ending in a space instead carries that space over into the next chunk.
  A trailing space at the very end of the whole line, with no next chunk to move it
  into, is simply dropped.
- No literal tabs/newlines in a cell (per https://www.mediawiki.org/wiki/Help:Tabular_data):
  json.dumps already escapes embedded tabs/newlines *inside JSON string values* as the
  two-character sequences '\\t'/'\\n', so those never reach us as raw control characters.
  XML text nodes carry no such guarantee - minidom.toprettyxml passes an embedded literal
  tab or newline straight through. CRLF line endings in the source file are a second,
  unrelated source of stray literal '\r' characters once we split on '\n'. Both are
  normalized/escaped per line before the row is written: CRLF/CR is normalized to '\n'
  (so it becomes an ordinary extra row, not a stray control character), and any literal
  tab, or other ASCII control character that survives within a line, is rendered as its
  visible backslash-escape (matching the style JSON already uses for its own values) so
  the information is preserved, human-readable, and never a raw control byte.
"""

import csv
import json
import re
import xml.dom.minidom
from pathlib import Path

import requests

MAX_LINE_LEN = 400
CONTINUATION_PREFIX = "+"

# Default license and Commons category applied to every .tab file this
# project produces (dataset-level metadata, per-indicator metadata, and
# indicator data). Kept as single named constants here - rather than
# repeated string literals in wb_api_raw_export_lib.py - so every .tab
# file stays consistent, and there's exactly one place to update if either
# value ever needs to change.
LICENSE_ID = "CC-BY-4.0"
COMMONS_CATEGORY = "World Development Indicators"

def translate_to_basque(text: str) -> str:
    """
    Translate an English string to Basque (eu) automatically, using the
    MyMemory Translation API (https://mymemory.translated.net/) - a free
    service that needs no API key/signup, so the script keeps working
    out of the box.

    Best-effort: on any problem (no internet, API error, empty input...)
    the original English text is returned unchanged rather than crashing
    the whole pipeline. Since this is a free automatic translation, it's
    still worth a human glance before the page is saved on Commons -
    but the field is no longer left blank/as a manual placeholder.
    """
    text = (text or "").strip()
    if not text:
        return text

    # The keyless/free MyMemory tier rejects requests over 500 characters,
    # so long text (e.g. a full World Bank sourceNote) is split into
    # sentence-sized chunks, each translated separately, then rejoined.
    MAX_CHARS = 480
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > MAX_CHARS and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)

    translated_chunks = []
    for chunk in chunks:
        try:
            resp = requests.get(
                "https://api.mymemory.translated.net/get",
                params={"q": chunk, "langpair": "en|eu"},
                timeout=15,
            )
            resp.raise_for_status()
            payload = resp.json()
            translated = payload.get("responseData", {}).get("translatedText")
            status = payload.get("responseStatus")
            if not translated or status not in (200, "200"):
                print(f"  [WARN] Basque translation returned no result for a chunk (status={status}); keeping English text for it.")
                translated_chunks.append(chunk)
            else:
                translated_chunks.append(translated)
        except (requests.RequestException, ValueError) as exc:
            print(f"  [WARN] Basque translation request failed for a chunk ({exc}); keeping English text for it.")
            translated_chunks.append(chunk)

    return " ".join(translated_chunks)


# Visible escapes for control characters MediaWiki tabular data disallows (or that are
# simply unsafe/invisible in a rendered cell). Tab and newline are named explicitly by
# MediaWiki's rule; any other ASCII control character is escaped generically so nothing
# is silently dropped.
_CONTROL_CHAR_ESCAPES = {"\t": "\\t", "\n": "\\n"}


def _escape_control_chars(line: str) -> str:
    """Replace literal control characters in a single line with visible escapes.

    Named escapes (tab, newline) use the same two-character style JSON itself already
    uses for string values ('\\t', '\\n'). Any other stray ASCII control character
    (ord < 0x20) is escaped as '\\xHH' so it is preserved and visible rather than
    silently dropped or left as an invisible/unsafe raw byte.
    """
    out = []
    for ch in line:
        if ch in _CONTROL_CHAR_ESCAPES:
            out.append(_CONTROL_CHAR_ESCAPES[ch])
        elif ord(ch) < 0x20:
            out.append(f"\\x{ord(ch):02x}")
        else:
            out.append(ch)
    return "".join(out)


def _normalize_and_split_lines(text: str) -> list[str]:
    """Normalize CRLF/CR line endings to '\n', then split into lines.

    Without this, a source file using Windows line endings would leave a stray literal
    '\r' glued to the end of every line once we split on '\n' alone.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.split("\n")


def _indent_with_underscores(line: str) -> str:
    """Replace a line's leading run of literal spaces with the same number of '_'.

    Only leading spaces are touched; spaces anywhere else in the line (inside values,
    around punctuation, etc.) are left untouched.
    """
    stripped = line.lstrip(" ")
    n_leading = len(line) - len(stripped)
    return ("_" * n_leading) + stripped


def _csv_serialized_len(field: str, quotechar: str = '"') -> int:
    """Length `field` will actually occupy as a line in the CSV file once csv.writer
    serializes it, given csv.QUOTE_ALL: every field is ALWAYS wrapped in quotechar
    (2 extra characters), and every internal quotechar is doubled - unlike
    QUOTE_MINIMAL, there's no "only if it contains a delimiter/quote/CR/LF" case to
    check, quoting always applies. JSON/XML text is almost always full of '"'
    characters, so the serialized length can run well past the raw string length -
    that gap, not the wrapping logic itself, was the source of the >400-char rows.
    """
    return len(field) + field.count(quotechar) + 2


def _greedy_chunk_for_csv_budget(s: str, max_len: int, prefix: str = "") -> tuple[str, str]:
    """Return (piece, remainder): the longest leading slice of `s` such that
    `prefix + piece`, once csv.writer serializes it, is <= max_len characters.

    Scans one character at a time rather than assuming raw-length == serialized-length,
    since the quoting overhead (doubled '"' plus 2 wrapping quotes) grows as more
    quote characters are added. With csv.QUOTE_ALL, the 2 wrapping quotes always
    apply (every field is quoted, regardless of content) - only the internal
    quote-doubling count still depends on what characters are in the piece so far.
    """
    quote_count = prefix.count('"')
    consumed = len(prefix)
    end = 0
    for ch in s:
        new_quote_count = quote_count + (1 if ch == '"' else 0)
        serialized_len = (consumed + end + 1) + new_quote_count + 2
        if serialized_len > max_len:
            break
        quote_count = new_quote_count
        end += 1

    if end == 0 and s:
        # A single character already exceeds the budget (pathological, e.g. prefix
        # alone is near the limit) - take it anyway so we always make forward progress
        # rather than looping forever.
        end = 1

    return s[:end], s[end:]


def _wrap_line(line: str, max_len: int = MAX_LINE_LEN,
                continuation_prefix: str = CONTINUATION_PREFIX) -> list[str]:
    """Split a single line into chunks that each fit max_len once CSV-serialized.

    The first chunk carries no prefix; every subsequent chunk is prefixed with
    continuation_prefix, which counts toward that chunk's budget. A wrap boundary
    that would leave a chunk ending in a space instead pushes that space (and any
    run of spaces at the cut point) into the next chunk, since Commons .tab rejects
    a cell with trailing whitespace. A trailing space at the very end of the whole
    line - with no next chunk to move it into - is simply dropped.
    """
    line = line.rstrip(" ")
    if not line:
        return [line]

    chunks: list[str] = []
    remaining = line
    first = True
    while remaining:
        prefix = "" if first else continuation_prefix
        piece, remaining = _greedy_chunk_for_csv_budget(remaining, max_len, prefix)

        if remaining:
            # Not the last chunk: don't let it end in a space - hand any trailing
            # run of spaces back to `remaining` for the next chunk to pick up.
            trimmed = piece.rstrip(" ")
            if trimmed:
                remaining = piece[len(trimmed):] + remaining
                piece = trimmed

        chunks.append(prefix + piece)
        first = False

    return chunks


def _rows_from_lines(lines: list[str]) -> list[str]:
    """Apply control-char escaping, underscore-indentation, and 400-char wrapping to a
    list of source lines, in that order:
    1. escape control chars first, since escaping can change a line's length (e.g. a
       literal tab becomes the 2-char '\\t') and that final length is what must fit the
       400-char limit;
    2. underscore-indentation next, purely cosmetic, operating on literal leading
       spaces only (control chars are already gone by this point);
    3. 400-char wrapping last, computed on the fully escaped + indented line.
    """
    rows: list[str] = []
    for line in lines:
        escaped = _escape_control_chars(line)
        indented = _indent_with_underscores(escaped)
        rows.extend(_wrap_line(indented))
    return rows


def _write_rows_csv(rows: list[str], csv_path: Path) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["line"])
        for row in rows:
            writer.writerow([row])

    print(f"  wrote {csv_path.name} ({len(rows)} rows)")


def metadata_json_to_csv(json_path: Path, csv_path: Path) -> None:
    """Pretty-print a JSON file (2-space indent) and write one CSV row per line,
    with underscore-indentation and 400-char wrapping applied."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    pretty = json.dumps(data, indent=2, ensure_ascii=False)
    lines = _normalize_and_split_lines(pretty)
    rows = _rows_from_lines(lines)
    _write_rows_csv(rows, csv_path)


def metadata_xml_to_csv(xml_path: Path, csv_path: Path) -> None:
    """Pretty-print an XML file and write one CSV row per line, with underscore-
    indentation and 400-char wrapping applied.

    Uses the standard library's minidom pretty-printer. minidom tends to introduce
    blank lines from whitespace-only text nodes between elements - those are dropped,
    since they carry no content and would just be noise as CSV rows.
    """
    xml_text = xml_path.read_text(encoding="utf-8")
    dom = xml.dom.minidom.parseString(xml_text)
    pretty = dom.toprettyxml(indent="  ")

    lines = [line for line in _normalize_and_split_lines(pretty) if line.strip() != ""]
    rows = _rows_from_lines(lines)
    _write_rows_csv(rows, csv_path)

# .tab (Wikimedia Commons Tabular Data) versions of the two functions above.
#
# Same one-line-per-row content as the CSV versions - built from the exact
# same `_rows_from_lines()` (so the same control-char escaping, underscore
# indentation, and 400-char wrapping applies identically to both formats -
# only the container differs (CSV file vs. a Data:...tab-ready JSON dict).
#
# Additionally sets the .tab-specific fields Wikimedia Commons requires:
# "license", "sources" (the real API URL the file came from, not just a
# filename label), "description" (in English and Basque - auto-translated
# via translate_to_basque() if the Basque text isn't supplied), and
# "mediawikiCategories".

def _rows_to_tab_data(
    rows: list[str],
    source_url: str,
    description: str,
    description_eu: str = None,
    license_id: str = LICENSE_ID,
    categories: list = None,
) -> dict:
    """Assemble the common .tab JSON structure (single "line" string column)
    shared by metadata_json_to_tab() and metadata_xml_to_tab()."""
    if description_eu is None:
        description_eu = translate_to_basque(description)

    tab_data = {
        "license": license_id,
        "description": {"en": description, "eu": description_eu},
        "sources": source_url,
    }

    if categories:
        tab_data["mediawikiCategories"] = [{"name": cat, "sort": ""} for cat in categories]

    tab_data["schema"] = {
        "fields": [
            {"name": "line", "type": "string", "title": {"en": "Line"}},
        ]
    }
    tab_data["data"] = [[row] for row in rows]

    return tab_data


def metadata_json_to_tab(
    json_path: Path,
    tab_path: Path,
    source_url: str,
    description: str,
    description_eu: str = None,
    license_id: str = LICENSE_ID,
    categories: list = None,
) -> None:
    """Pretty-print a JSON file (2-space indent) and write a Wikimedia Commons
    Tabular Data (.tab) file with one row per line of the beautified text -
    same content as metadata_json_to_csv(), as a ready-to-paste Data:...tab
    JSON file instead of a CSV.

    Args:
        source_url: the exact API URL this JSON was downloaded from, so
            anyone can verify/re-fetch it (NOT just a human-readable label).
        description: real English description of what this file contains.
        description_eu: Basque translation; auto-generated via
            translate_to_basque() if not supplied.
        license_id: defaults to the module-level LICENSE_ID (CC-BY-4.0).
        categories: optional list of Commons category names to attach via
            "mediawikiCategories"; defaults to no categories if omitted.
    """
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    pretty = json.dumps(data, indent=2, ensure_ascii=False)
    lines = _normalize_and_split_lines(pretty)
    rows = _rows_from_lines(lines)

    tab_data = _rows_to_tab_data(rows, source_url, description, description_eu, license_id, categories)
    with open(tab_path, "w", encoding="utf-8") as f:
        json.dump(tab_data, f, ensure_ascii=False, indent="\t")

    print(f"  wrote {tab_path.name} ({len(rows)} rows)")


def metadata_xml_to_tab(
    xml_path: Path,
    tab_path: Path,
    source_url: str,
    description: str,
    description_eu: str = None,
    license_id: str = LICENSE_ID,
    categories: list = None,
) -> None:
    """Pretty-print an XML file and write a Wikimedia Commons Tabular Data
    (.tab) file with one row per line - same content as metadata_xml_to_csv(),
    mirroring metadata_json_to_tab() above.
    """
    xml_text = xml_path.read_text(encoding="utf-8")
    dom = xml.dom.minidom.parseString(xml_text)
    pretty = dom.toprettyxml(indent="  ")

    lines = [line for line in _normalize_and_split_lines(pretty) if line.strip() != ""]
    rows = _rows_from_lines(lines)

    tab_data = _rows_to_tab_data(rows, source_url, description, description_eu, license_id, categories)
    with open(tab_path, "w", encoding="utf-8") as f:
        json.dump(tab_data, f, ensure_ascii=False, indent="\t")

    print(f"  wrote {tab_path.name} ({len(rows)} rows)")
