"""Extract readable text (and tables) from SEC filing HTML/iXBRL."""

from __future__ import annotations

import json
import re
import warnings
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from bs4 import BeautifulSoup, NavigableString, Tag, XMLParsedAsHTMLWarning

from prospectus_ingest.fetch import DEFAULT_OUT_DIR, FilingRef, REPO_ROOT

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class ExtractedFiling:
    """Plain-text extraction of a single filing, ready for chunking."""

    ticker: str
    cik: str
    company_name: str
    form_type: Literal["10-K", "10-Q"]
    filing_date: date
    accession_number: str
    source_url: str
    local_path: str
    text: str
    char_count: int
    table_count: int


def _cell_text(cell: Tag) -> str:
    """Normalize a table cell to a single line of text."""
    raw = cell.get_text(" ", strip=True)
    return _WHITESPACE_RE.sub(" ", raw).strip()


def _table_to_text(table: Tag) -> str:
    """Render an HTML table as pipe-delimited rows.

    Keeps numeric cells searchable for keyword retrieval without retaining
    layout tags that would pollute embeddings.
    """
    rows: list[str] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        if not cells:
            continue
        values = [_cell_text(c) for c in cells]
        if not any(values):
            continue
        rows.append(" | ".join(values))
    if not rows:
        return ""
    return "\n".join(["[TABLE]", *rows, "[/TABLE]"])


def _replace_tables(soup: BeautifulSoup) -> int:
    """Replace every <table> in-place with a text node; return count replaced."""
    tables = soup.find_all("table")
    for table in tables:
        rendered = _table_to_text(table)
        replacement = NavigableString(f"\n{rendered}\n" if rendered else "\n")
        table.replace_with(replacement)
    return len(tables)


def extract_html(html: bytes | str) -> tuple[str, int]:
    """Extract normalized plain text from filing HTML.

    Args:
        html: Raw filing bytes or string.

    Returns:
        (text, table_count)
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    table_count = _replace_tables(soup)
    text = soup.get_text("\n", strip=True)

    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    cleaned = _BLANK_LINES_RE.sub("\n\n", "\n".join(lines)).strip() + "\n"
    return cleaned, table_count


def _load_ref_from_meta(meta_path: Path) -> FilingRef:
    """Load a FilingRef written by the fetch step."""
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    return FilingRef(
        ticker=payload["ticker"],
        cik=payload["cik"],
        company_name=payload["company_name"],
        form_type=payload["form_type"],
        filing_date=date.fromisoformat(payload["filing_date"]),
        accession_number=payload["accession_number"],
        primary_document=payload["primary_document"],
        source_url=payload["source_url"],
        local_path=payload["local_path"],
    )


def extract_filing(ref: FilingRef, *, repo_root: Path = REPO_ROOT) -> ExtractedFiling:
    """Extract one filing referenced by fetch metadata."""
    html_path = repo_root / ref.local_path
    text, table_count = extract_html(html_path.read_bytes())
    return ExtractedFiling(
        ticker=ref.ticker,
        cik=ref.cik,
        company_name=ref.company_name,
        form_type=ref.form_type,
        filing_date=ref.filing_date,
        accession_number=ref.accession_number,
        source_url=ref.source_url,
        local_path=ref.local_path,
        text=text,
        char_count=len(text),
        table_count=table_count,
    )


def extract_all(
    *,
    filings_dir: Path = DEFAULT_OUT_DIR,
    repo_root: Path = REPO_ROOT,
) -> list[ExtractedFiling]:
    """Extract every filing under data/filings that has a meta.json.

    Writes `extracted.txt` next to each filing's primary document.
    """
    results: list[ExtractedFiling] = []
    for meta_path in sorted(filings_dir.glob("*/*/meta.json")):
        ref = _load_ref_from_meta(meta_path)
        extracted = extract_filing(ref, repo_root=repo_root)
        out_path = meta_path.parent / "extracted.txt"
        out_path.write_text(extracted.text, encoding="utf-8")
        (meta_path.parent / "extracted_meta.json").write_text(
            json.dumps(
                {
                    **{k: v for k, v in asdict(extracted).items() if k != "text"},
                },
                indent=2,
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )
        results.append(extracted)
    return results
