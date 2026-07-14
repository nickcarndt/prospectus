"""Build data/eval/cases.jsonl from labeled question templates + live DB gold rows.

Run:
  PYTHONPATH=packages/evals:... python packages/evals/scripts/build_eval_set.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "packages" / "retrieval"))
load_dotenv(REPO / ".env")

from prospectus_retrieval.db import connect  # noqa: E402

OUT = REPO / "data" / "eval" / "cases.jsonl"

# (id, query, ticker, phrase_in_gold_chunk, notes)
# phrase locates the gold chunk; section fields come from that row.
TEMPLATES: list[tuple[str, str, str, str]] = [
    (
        "nvda-cowos-01",
        "What packaging technology does NVIDIA say it utilizes for semiconductors?",
        "NVDA",
        "CoWoS technology",
    ),
    (
        "nvda-fabless-02",
        "How does NVIDIA describe its manufacturing strategy with suppliers and foundries?",
        "NVDA",
        "fabless and contracting manufacturing",
    ),
    (
        "nvda-risk-supply-03",
        "What supply chain or manufacturing risks does NVIDIA discuss in Item 1A?",
        "NVDA",
        "manufacturing",
    ),
    (
        "amd-tsmc-04",
        "Which foundry does AMD identify for producing wafers for its products?",
        "AMD",
        "TSMC",
    ),
    (
        "amd-cyber-05",
        "What does AMD disclose about its cybersecurity risk management program?",
        "AMD",
        "cybersecurity risk management program",
    ),
    (
        "aapl-hq-06",
        "Where is Apple's headquarters located according to its 10-K?",
        "AAPL",
        "Cupertino, California",
    ),
    (
        "aapl-dma-07",
        "What does Apple say about the Digital Markets Act investigations?",
        "AAPL",
        "Digital Markets Act",
    ),
    (
        "aapl-10b5-08",
        "What Rule 10b5-1 trading arrangement information does Apple disclose?",
        "AAPL",
        "Rule 10b5-1",
    ),
    (
        "tsla-fsd-09",
        "How does Tesla describe Full Self-Driving in its business overview?",
        "TSLA",
        "Full Self-Driving",
    ),
    (
        "tsla-asc606-10",
        "How does Tesla reference ASC 606 in accounting for transactions?",
        "TSLA",
        "ASC 606",
    ),
    (
        "msft-azure-11",
        "What does Microsoft say about Azure in its filing?",
        "MSFT",
        "Azure",
    ),
    (
        "googl-yt-12",
        "What does Alphabet disclose about YouTube in its business description?",
        "GOOGL",
        "YouTube",
    ),
    (
        "amzn-aws-13",
        "How does Amazon describe AWS in its business section?",
        "AMZN",
        "AWS",
    ),
    (
        "meta-rl-14",
        "What does Meta disclose about Reality Labs?",
        "META",
        "Reality Labs",
    ),
    (
        "crm-agentforce-15",
        "What is Agentforce according to Salesforce's filing?",
        "CRM",
        "Agentforce",
    ),
    (
        "orcl-cloud-16",
        "What does Oracle say about Oracle Cloud offerings?",
        "ORCL",
        "Oracle Cloud",
    ),
    (
        "ma-biz-17",
        "How does Mastercard describe its business in Item 1?",
        "MA",
        "Mastercard",
    ),
    (
        "v-payments-18",
        "What does Visa disclose about how it earns revenue on its payment network?",
        "V",
        "payment network",
    ),
    (
        "jpm-credit-19",
        "What credit risk factors does JPMorgan Chase discuss?",
        "JPM",
        "credit risk",
    ),
    (
        "nflx-content-20",
        "What content-related risks or disclosures does Netflix discuss?",
        "NFLX",
        "content",
    ),
    # Semantic / paraphrase variants (still gold-labeled to a known section)
    (
        "nvda-cowos-21",
        "Does NVIDIA mention CoWoS packaging with TSMC or other suppliers?",
        "NVDA",
        "CoWoS technology",
    ),
    (
        "amd-tsmc-22",
        "Who manufactures wafers for AMD's HPC and GPU products?",
        "AMD",
        "TSMC",
    ),
    (
        "aapl-hq-23",
        "In which California city is Apple headquartered?",
        "AAPL",
        "Cupertino, California",
    ),
    (
        "tsla-fsd-24",
        "What AI products does Tesla say it is bringing into the real world?",
        "TSLA",
        "Full Self-Driving",
    ),
    (
        "meta-rl-25",
        "Which Meta segment is associated with Reality Labs spending or strategy?",
        "META",
        "Reality Labs",
    ),
    (
        "amzn-aws-26",
        "What cloud computing business does Amazon operate according to its 10-K?",
        "AMZN",
        "AWS",
    ),
    (
        "googl-ads-27",
        "What advertising-related risks does Alphabet discuss?",
        "GOOGL",
        "advertising",
    ),
    (
        "msft-cloud-28",
        "What cloud competition or Dynamics/Azure related points appear in Microsoft's filing?",
        "MSFT",
        "Azure",
    ),
    (
        "crm-ai-29",
        "How does Salesforce describe Agentforce capabilities?",
        "CRM",
        "Agentforce",
    ),
    (
        "orcl-cloud-30",
        "How does Oracle describe delivering applications via cloud?",
        "ORCL",
        "Oracle Cloud",
    ),
    (
        "aapl-dma-31",
        "What European Commission action related to the Digital Markets Act does Apple mention?",
        "AAPL",
        "Digital Markets Act",
    ),
    (
        "amd-cyber-32",
        "Who at AMD is responsible for cybersecurity risk oversight in the disclosure?",
        "AMD",
        "cybersecurity",
    ),
    (
        "nvda-season-33",
        "What end markets does NVIDIA say its computing platforms serve?",
        "NVDA",
        "data centers, gaming",
    ),
    (
        "jpm-risk-34",
        "Where does JPMorganChase outline material risk factors affecting its operations?",
        "JPM",
        "material risk factors",
    ),
    (
        "tsla-asc-35",
        "Under which accounting standard does Tesla say a transaction was accounted for as a sale?",
        "TSLA",
        "ASC 606",
    ),
]


def lookup_gold(ticker: str, phrase: str) -> dict | None:
    """Find the first chunk containing phrase for ticker."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT ticker, form_type, section_id, section_title, chunk_id,
                   filing_date::text, accession_number
            FROM chunks
            WHERE ticker = %s AND text ILIKE %s
            ORDER BY chunk_index
            LIMIT 1
            """,
            (ticker, f"%{phrase}%"),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {
        "gold_ticker": row[0],
        "gold_form_type": row[1],
        "gold_section_id": row[2],
        "gold_section_title": row[3],
        "gold_chunk_id": row[4],
        "gold_filing_date": row[5],
        "gold_accession_number": row[6],
        "gold_phrase": phrase,
    }


def main() -> None:
    """Write labeled eval cases to data/eval/cases.jsonl."""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cases: list[dict] = []
    missing: list[str] = []
    for case_id, query, ticker, phrase in TEMPLATES:
        gold = lookup_gold(ticker, phrase)
        if gold is None:
            missing.append(case_id)
            continue
        cases.append({"id": case_id, "query": query, **gold})

    with OUT.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case) + "\n")

    print(f"Wrote {len(cases)} cases → {OUT}")
    if missing:
        print("Missing gold for:", ", ".join(missing))


if __name__ == "__main__":
    main()
