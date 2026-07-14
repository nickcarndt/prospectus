"""Structure-aware chunking for SEC 10-K / 10-Q filings.

Split on Item headings first (citation boundaries), then pack each section
into 256–512 token windows. Naive fixed-size splitting is rejected because it
crosses Item borders and makes section-level citations unreliable.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import tiktoken

from prospectus_shared import Chunk

from prospectus_ingest.extract import ExtractedFiling, _load_ref_from_meta, extract_filing
from prospectus_ingest.fetch import DEFAULT_OUT_DIR, REPO_ROOT

# OpenAI cl100k_base is a stable tokenizer for length budgeting (embedding
# model may differ slightly; we only need approximate token counts here).
_ENCODING = tiktoken.get_encoding("cl100k_base")

MIN_TOKENS = 256
MAX_TOKENS = 512
OVERLAP_TOKENS = 64

# TOC stubs sit close together; gaps below this (tokens) are treated as TOC.
_TOC_GAP_TOKENS = 40

# Item line with optional title. Matches "Item 1A." and "Item 1A. Risk Factors".
_ITEM_LINE_RE = re.compile(
    r"(?im)^(Item\s+(\d+[A-Z]?)\.?)(?:\s+(.+))?$"
)


def count_tokens(text: str) -> int:
    """Return approximate token count for budgeting chunk sizes."""
    return len(_ENCODING.encode(text))


def _normalize_extracted_text(text: str) -> str:
    """Normalize NBSP / odd spaces so Item headings match reliably."""
    return (
        text.replace("\u00a0", " ")
        .replace("\u2003", " ")
        .replace("\u2009", " ")
    )


def _slug_title(title: str) -> str:
    """Slug a section title for disambiguating reused Item numbers (10-Q)."""
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return slug[:60] if slug else "section"


def _normalize_section_id(item_code: str, title: str) -> str:
    """Build section id: item_1a_risk_factors (title disambiguates 10-Q Parts)."""
    rest = re.sub(r"(?i)^item\s+\d+[a-z]?\.?\s*", "", title).strip()
    if rest:
        return f"item_{item_code.lower()}_{_slug_title(rest)}"
    return f"item_{item_code.lower()}"


def _resolve_title(item_token: str, inline_title: str | None, following: str) -> str:
    """Choose a human-readable section title for citations."""
    if inline_title:
        cleaned = inline_title.strip().strip(".")
        # Ignore garbage titles that are clearly body sentences.
        if cleaned and len(cleaned) <= 120 and not cleaned.endswith(","):
            return f"{item_token} {cleaned}".strip()
    # Peek at the next line if it looks like a short title.
    next_line = following.strip().splitlines()[0].strip() if following.strip() else ""
    if next_line and len(next_line) <= 120 and not next_line.lower().startswith("item "):
        return f"{item_token} {next_line}".strip()
    return item_token


def _split_into_sections(text: str) -> list[tuple[str, str, str]]:
    """Split filing text into (section_id, section_title, body) triples.

    Uses Item headings as boundaries. Clusters of headings with tiny gaps are
    treated as table-of-contents and skipped so Part I body is not swallowed
    into 'preface'. 10-Q reuses Item numbers across Part I/II — titles disambiguate.
    """
    text = _normalize_extracted_text(text)
    matches = list(_ITEM_LINE_RE.finditer(text))
    if not matches:
        return [("unknown", "Unknown Section", text.strip())]

    # Drop TOC entries: heading whose following gap until next Item is tiny.
    real_matches: list[re.Match[str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        gap = text[match.end() : end]
        # Keep if there is substantive body after this heading, or it's the last.
        if index + 1 == len(matches) or count_tokens(gap) >= _TOC_GAP_TOKENS:
            real_matches.append(match)

    if not real_matches:
        real_matches = matches[-1:]

    sections: list[tuple[str, str, str]] = []
    first_start = real_matches[0].start()
    preface = text[:first_start].strip()
    # Keep preface only if modest — cover pages/TOC residue, not half the filing.
    if preface and 32 <= count_tokens(preface) <= 1500:
        sections.append(("preface", "Preface / Front Matter", preface))

    for index, match in enumerate(real_matches):
        item_token = match.group(1).strip()
        item_code = match.group(2).upper()
        inline_title = (match.group(3) or "").strip() or None
        start = match.end()
        end = (
            real_matches[index + 1].start()
            if index + 1 < len(real_matches)
            else len(text)
        )
        body = text[start:end].strip()
        if not body:
            continue
        title = _resolve_title(item_token, inline_title, body)
        sections.append((_normalize_section_id(item_code, title), title, body))

    return sections


def _pack_section(
    section_text: str,
    *,
    min_tokens: int = MIN_TOKENS,
    max_tokens: int = MAX_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[str]:
    """Pack a section into windows targeting [min_tokens, max_tokens].

    Short sections stay as a single chunk (even if under min) so we never
    invent cross-section merges. Long sections split on paragraph boundaries
    when possible, with a small token overlap for continuity.
    """
    if count_tokens(section_text) <= max_tokens:
        return [section_text]

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", section_text) if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [ln.strip() for ln in section_text.splitlines() if ln.strip()]

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    def flush() -> None:
        nonlocal current, current_tokens
        if not current:
            return
        chunk_text = "\n\n".join(current).strip()
        chunks.append(chunk_text)
        if overlap_tokens > 0:
            overlap_text = _tail_tokens(chunk_text, overlap_tokens)
            current = [overlap_text] if overlap_text else []
            current_tokens = count_tokens(overlap_text) if overlap_text else 0
        else:
            current = []
            current_tokens = 0

    for para in paragraphs:
        para_tokens = count_tokens(para)
        if para_tokens > max_tokens:
            if current:
                flush()
            chunks.extend(_split_tokens(para, max_tokens))
            current = []
            current_tokens = 0
            continue

        if current and current_tokens + para_tokens > max_tokens:
            flush()

        current.append(para)
        current_tokens += para_tokens

    if current:
        trailing = "\n\n".join(current).strip()
        chunks.append(trailing)

    # Drop empty; hard-cap any accidental oversize from overlap seeding.
    capped: list[str] = []
    for chunk_text in chunks:
        if not chunk_text.strip():
            continue
        if count_tokens(chunk_text) > max_tokens:
            capped.extend(_split_tokens(chunk_text, max_tokens))
        else:
            capped.append(chunk_text)
    return capped


def _split_tokens(text: str, max_tokens: int) -> list[str]:
    """Hard-split text into <= max_tokens pieces (last resort)."""
    tokens = _ENCODING.encode(text)
    pieces: list[str] = []
    for start in range(0, len(tokens), max_tokens):
        pieces.append(_ENCODING.decode(tokens[start : start + max_tokens]))
    return pieces


def _tail_tokens(text: str, n: int) -> str:
    """Return the last n tokens of text as a string."""
    tokens = _ENCODING.encode(text)
    if len(tokens) <= n:
        return text
    return _ENCODING.decode(tokens[-n:])


def _chunk_id(
    ticker: str,
    accession_number: str,
    section_id: str,
    chunk_index: int,
    text: str,
) -> str:
    """Stable id from filing + section + content hash."""
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]
    return f"{ticker.lower()}_{accession_number}_{section_id}_{chunk_index}_{digest}"


def chunk_extracted(
    extracted: ExtractedFiling,
    *,
    min_tokens: int = MIN_TOKENS,
    max_tokens: int = MAX_TOKENS,
) -> list[Chunk]:
    """Turn an extracted filing into structure-aware Chunk models."""
    sections = _split_into_sections(extracted.text)
    chunks: list[Chunk] = []
    global_index = 0

    for section_id, section_title, body in sections:
        for part in _pack_section(
            body, min_tokens=min_tokens, max_tokens=max_tokens
        ):
            token_count = count_tokens(part)
            if token_count == 0:
                continue
            # Hard ceiling — never emit oversized chunks.
            if token_count > max_tokens:
                for piece in _split_tokens(part, max_tokens):
                    piece_tokens = count_tokens(piece)
                    chunks.append(
                        Chunk(
                            chunk_id=_chunk_id(
                                extracted.ticker,
                                extracted.accession_number,
                                section_id,
                                global_index,
                                piece,
                            ),
                            text=piece,
                            token_count=piece_tokens,
                            ticker=extracted.ticker,
                            cik=extracted.cik,
                            company_name=extracted.company_name,
                            form_type=extracted.form_type,
                            filing_date=extracted.filing_date,
                            accession_number=extracted.accession_number,
                            source_url=extracted.source_url,
                            section_id=section_id,
                            section_title=section_title,
                            chunk_index=global_index,
                        )
                    )
                    global_index += 1
                continue

            chunks.append(
                Chunk(
                    chunk_id=_chunk_id(
                        extracted.ticker,
                        extracted.accession_number,
                        section_id,
                        global_index,
                        part,
                    ),
                    text=part,
                    token_count=token_count,
                    ticker=extracted.ticker,
                    cik=extracted.cik,
                    company_name=extracted.company_name,
                    form_type=extracted.form_type,
                    filing_date=extracted.filing_date,
                    accession_number=extracted.accession_number,
                    source_url=extracted.source_url,
                    section_id=section_id,
                    section_title=section_title,
                    chunk_index=global_index,
                )
            )
            global_index += 1

    return chunks


def chunk_all(
    *,
    filings_dir: Path = DEFAULT_OUT_DIR,
    out_dir: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> list[Chunk]:
    """Chunk every extracted filing; write JSONL under data/chunks.

    Prefers existing extracted.txt; re-extracts from HTML if missing.
    """
    destination = out_dir or (repo_root / "data" / "chunks")
    destination.mkdir(parents=True, exist_ok=True)

    all_chunks: list[Chunk] = []
    for meta_path in sorted(filings_dir.glob("*/*/meta.json")):
        ref = _load_ref_from_meta(meta_path)
        extracted_path = meta_path.parent / "extracted.txt"
        if extracted_path.exists():
            text = extracted_path.read_text(encoding="utf-8")
            extracted = ExtractedFiling(
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
                table_count=0,
            )
        else:
            extracted = extract_filing(ref, repo_root=repo_root)

        filing_chunks = chunk_extracted(extracted)
        out_path = destination / f"{ref.ticker}_{ref.accession_number}.jsonl"
        with out_path.open("w", encoding="utf-8") as handle:
            for chunk in filing_chunks:
                handle.write(chunk.model_dump_json() + "\n")
        all_chunks.extend(filing_chunks)

    manifest = {
        "chunk_count": len(all_chunks),
        "filing_count": len(list(filings_dir.glob("*/*/meta.json"))),
        "min_tokens": MIN_TOKENS,
        "max_tokens": MAX_TOKENS,
        "overlap_tokens": OVERLAP_TOKENS,
    }
    (destination / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return all_chunks
