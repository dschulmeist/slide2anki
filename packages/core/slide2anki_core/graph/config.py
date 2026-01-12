"""Configuration helpers for LangGraph pipelines."""

from dataclasses import dataclass


@dataclass(frozen=True)
class GraphConfig:
    """Configuration values for graph loops and concurrency."""

    max_claim_repairs: int = 2
    max_card_repairs: int = 2
    max_slide_concurrency: int = 2
