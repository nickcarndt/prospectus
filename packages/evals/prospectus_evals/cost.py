"""Per-query cost estimates (USD) for eval reporting.

Prices are approximate list rates used for relative comparison across configs.
Update if providers change pricing — the runner persists the assumptions used.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from prospectus_shared import RetrievalStrategy

# Approximate USD rates (document in EVAL_REPORT).
EMBED_PER_MTOK = 0.13  # text-embedding-3-large
RERANK_PER_QUERY = 0.001  # ~$1 / 1K Cohere rerank searches
CLAUDE_IN_PER_MTOK = 3.0
CLAUDE_OUT_PER_MTOK = 15.0

# Typical query embedding size for our questions.
AVG_QUERY_EMBED_TOKENS = 40


@dataclass(frozen=True)
class CostBreakdown:
    """Estimated USD cost components for one eval query."""

    embedding_usd: float
    rerank_usd: float
    generation_usd: float

    @property
    def total_usd(self) -> float:
        """Sum of component costs."""
        return self.embedding_usd + self.rerank_usd + self.generation_usd

    def as_dict(self) -> dict[str, float]:
        """JSON-serializable dict including total."""
        data = asdict(self)
        data["total_usd"] = self.total_usd
        return data


def estimate_cost(
    strategy: RetrievalStrategy,
    *,
    answer_chars: int,
    context_chars: int,
) -> CostBreakdown:
    """Estimate cost for one retrieve+generate call.

    Args:
        strategy: Retrieval config used.
        answer_chars: Length of generated answer text.
        context_chars: Approx chars of evidence sent to Claude.
    """
    embed = (AVG_QUERY_EMBED_TOKENS / 1_000_000.0) * EMBED_PER_MTOK
    # Keyword-only would skip embed; our three eval configs all use dense or hybrid.
    if strategy is RetrievalStrategy.KEYWORD:
        embed = 0.0

    rerank = (
        RERANK_PER_QUERY
        if strategy is RetrievalStrategy.HYBRID_RERANK
        else 0.0
    )

    # Rough chars→tokens.
    in_toks = max(1, (context_chars + 800) // 4)
    out_toks = max(1, answer_chars // 4)
    generation = (in_toks / 1_000_000.0) * CLAUDE_IN_PER_MTOK + (
        out_toks / 1_000_000.0
    ) * CLAUDE_OUT_PER_MTOK

    return CostBreakdown(
        embedding_usd=embed,
        rerank_usd=rerank,
        generation_usd=generation,
    )
