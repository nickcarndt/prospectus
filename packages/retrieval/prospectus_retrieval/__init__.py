"""Prospectus retrieval package.

Retrieval strategy is a parameter
(dense | keyword | hybrid | hybrid_rerank).
Each stage (dense, keyword, RRF, rerank) is independently testable.
"""

from prospectus_retrieval.dense import dense_retrieve
from prospectus_retrieval.fusion import reciprocal_rank_fusion
from prospectus_retrieval.hybrid import hybrid_retrieve
from prospectus_retrieval.hybrid_rerank import hybrid_rerank_retrieve
from prospectus_retrieval.keyword import keyword_retrieve
from prospectus_retrieval.rerank import rerank_chunks
from prospectus_retrieval.retrieve import retrieve

__all__ = [
    "dense_retrieve",
    "hybrid_retrieve",
    "hybrid_rerank_retrieve",
    "keyword_retrieve",
    "reciprocal_rank_fusion",
    "rerank_chunks",
    "retrieve",
]
