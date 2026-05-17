"""DEPRECATED: Markdown report generation has been removed.

HTML reports are now generated directly from gold-layer CSV data.
See src.core.reports.html for the new implementation.
"""

from __future__ import annotations

from src.core.config import ChampionshipConfig


def generate_markdown_reports(config: ChampionshipConfig) -> None:
    """No-op. Markdown generation has been removed."""
    pass
