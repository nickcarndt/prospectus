"""Cited generation for Prospectus — structured output + grounding checks."""

from prospectus_generation.answer import answer_query
from prospectus_generation.generate import generate_from_retrieval

__all__ = ["answer_query", "generate_from_retrieval"]
