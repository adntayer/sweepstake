"""Shared pytest fixtures for sweepstake tests."""

from __future__ import annotations

import pytest

from src.core.config import ChampionshipConfig, ScoringRule, load_config


@pytest.fixture
def cfg():
    """Load the real 2025 Club World Cup config."""
    return load_config("2025_club_world_cup")


@pytest.fixture
def minimal_cfg():
    """A minimal config for isolated tests."""
    return ChampionshipConfig(
        id="test", name="Test", year=2025,
        scoring_rules=[
            ScoringRule(name="exact", points=15, rule="exact_score"),
            ScoringRule(name="winner", points=5, rule="correct_winner"),
        ],
    )
