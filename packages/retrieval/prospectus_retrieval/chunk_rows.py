"""Map Postgres chunk rows → shared Chunk models."""

from __future__ import annotations

from datetime import date
from typing import Any, Sequence

from prospectus_shared import Chunk


def row_to_chunk(row: Sequence[Any]) -> Chunk:
    """Convert a SELECT row (standard column order) into a Chunk.

    Expected order:
      chunk_id, text, token_count, ticker, cik, company_name, form_type,
      filing_date, accession_number, source_url, section_id, section_title,
      chunk_index
    """
    (
        chunk_id,
        text,
        token_count,
        ticker,
        cik,
        company_name,
        form_type,
        filing_date,
        accession_number,
        source_url,
        section_id,
        section_title,
        chunk_index,
    ) = row
    return Chunk(
        chunk_id=chunk_id,
        text=text,
        token_count=token_count,
        ticker=ticker,
        cik=cik,
        company_name=company_name,
        form_type=form_type,
        filing_date=filing_date
        if isinstance(filing_date, date)
        else date.fromisoformat(str(filing_date)),
        accession_number=accession_number,
        source_url=source_url,
        section_id=section_id,
        section_title=section_title,
        chunk_index=chunk_index,
    )
