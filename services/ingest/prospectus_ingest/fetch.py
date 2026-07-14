"""Download recent 10-K / 10-Q primary documents into data/filings."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

from prospectus_ingest.companies import TARGET_FORMS, TICKERS
from prospectus_ingest.edgar import EdgarClient

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "filings"


@dataclass(frozen=True)
class FilingRef:
    """Pointer to a downloaded (or downloadable) SEC filing document."""

    ticker: str
    cik: str
    company_name: str
    form_type: Literal["10-K", "10-Q"]
    filing_date: date
    accession_number: str
    primary_document: str
    source_url: str
    local_path: str


def _parse_recent_filings(
    submissions: dict[str, Any],
    *,
    ticker: str,
    cik: str,
    per_form: int,
) -> list[dict[str, Any]]:
    """Pick the newest `per_form` filings for each target form type."""
    company_name = str(submissions.get("name") or ticker)
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    filing_dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    selected: list[dict[str, Any]] = []
    counts: dict[str, int] = {form: 0 for form in TARGET_FORMS}

    for form, accession, filing_date, primary_doc in zip(
        forms, accessions, filing_dates, primary_docs, strict=False
    ):
        if form not in TARGET_FORMS:
            continue
        if counts[form] >= per_form:
            if all(counts[f] >= per_form for f in TARGET_FORMS):
                break
            continue
        selected.append(
            {
                "ticker": ticker,
                "cik": cik,
                "company_name": company_name,
                "form_type": form,
                "filing_date": filing_date,
                "accession_number": accession,
                "primary_document": primary_doc,
            }
        )
        counts[form] += 1

    return selected


def fetch_filings(
    *,
    tickers: tuple[str, ...] = TICKERS,
    out_dir: Path = DEFAULT_OUT_DIR,
    per_form: int = 1,
    client: EdgarClient | None = None,
) -> list[FilingRef]:
    """Fetch latest 10-K/10-Q primary docs for each ticker.

    Writes:
      data/filings/{ticker}/{accession}/{primary_document}
      data/filings/{ticker}/{accession}/meta.json

    Args:
        tickers: Issuer tickers to fetch.
        out_dir: Root directory for downloaded filings.
        per_form: How many newest filings per form type (default 1 each).
        client: Optional shared EdgarClient.

    Returns:
        Metadata for each downloaded filing.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    owns_client = client is None
    edgar = client or EdgarClient()
    refs: list[FilingRef] = []

    try:
        ticker_to_cik = edgar.load_ticker_to_cik()
        for ticker in tickers:
            key = ticker.upper()
            if key not in ticker_to_cik:
                raise KeyError(f"Ticker not found in SEC company_tickers.json: {key}")
            cik = ticker_to_cik[key]
            submissions = edgar.fetch_submissions(cik)
            for row in _parse_recent_filings(
                submissions, ticker=key, cik=cik, per_form=per_form
            ):
                source_url = EdgarClient.document_url(
                    cik, row["accession_number"], row["primary_document"]
                )
                dest_dir = out_dir / key / row["accession_number"]
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest_path = dest_dir / row["primary_document"]
                meta_path = dest_dir / "meta.json"

                if not dest_path.exists():
                    dest_path.write_bytes(edgar.get_bytes(source_url))

                ref = FilingRef(
                    ticker=key,
                    cik=cik,
                    company_name=row["company_name"],
                    form_type=row["form_type"],
                    filing_date=date.fromisoformat(row["filing_date"]),
                    accession_number=row["accession_number"],
                    primary_document=row["primary_document"],
                    source_url=source_url,
                    local_path=str(dest_path.relative_to(REPO_ROOT)),
                )
                meta_path.write_text(
                    json.dumps(asdict(ref), indent=2, default=str) + "\n",
                    encoding="utf-8",
                )
                refs.append(ref)
    finally:
        if owns_client:
            edgar.close()

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps([asdict(r) for r in refs], indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return refs
