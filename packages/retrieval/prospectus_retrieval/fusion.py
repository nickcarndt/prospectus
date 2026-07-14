"""Reciprocal Rank Fusion (RRF) — rank-based merging of retrieval lists.

RRF score for a document d across ranked lists is:

    sum over lists L of  1 / (k + rank_L(d))

where rank is 1-based. Default k=60 (Cormack et al. / common RAG default).

Why ranks, not score averaging:
  Dense cosine (~0.0–1.0) and FTS ts_rank (~tiny floats) are not on the same
  scale. Averaging lets one metric dominate arbitrarily. RRF only cares about
  *position* in each list, so complementary evidence stacks fairly.
"""

from __future__ import annotations

from prospectus_shared import Chunk

# Spec-locked RRF constant.
RRF_K = 60


def reciprocal_rank_fusion(
    ranked_lists: list[list[Chunk]],
    *,
    k: int = RRF_K,
    top_k: int | None = None,
) -> tuple[list[Chunk], list[float]]:
    """Fuse multiple ranked chunk lists with Reciprocal Rank Fusion.

    Independently testable: pass any lists of Chunks (no DB / OpenAI needed).

    Args:
        ranked_lists: Each inner list is best-first (index 0 = rank 1).
        k: RRF smoothing constant (spec default 60).
        top_k: Optional truncate after fusion.

    Returns:
        (chunks, rrf_scores) sorted by descending RRF score.
    """
    if k < 1:
        raise ValueError("k must be >= 1")

    scores: dict[str, float] = {}
    by_id: dict[str, Chunk] = {}

    for ranked in ranked_lists:
        for index, chunk in enumerate(ranked):
            rank = index + 1  # 1-based
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (
                k + rank
            )
            # First time we see a chunk wins for metadata/text identity.
            by_id.setdefault(chunk.chunk_id, chunk)

    ordered_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    if top_k is not None:
        ordered_ids = ordered_ids[:top_k]

    chunks = [by_id[cid] for cid in ordered_ids]
    rrf_scores = [scores[cid] for cid in ordered_ids]
    return chunks, rrf_scores
