"""Generic football sweepstake scoring engine.

Evaluates a predicted score against the real score and returns
(points, criterion_name, is_valid) based on configurable rules.
"""

from __future__ import annotations

import pandas as pd

from src.core.config import ChampionshipConfig


def _winner(home: float, away: float) -> str:
    """Return 'home', 'away', or 'draw'."""
    if home > away:
        return "home"
    if away > home:
        return "away"
    return "draw"


def score_prediction(
    home_pred: float,
    away_pred: float,
    home_real: float,
    away_real: float,
    config: ChampionshipConfig,
) -> pd.Series:
    """Score a single prediction against the real result.

    Returns pd.Series([points, criterion_name, is_valid]).
    """
    # Missing data
    if (
        pd.isna(home_pred)
        or pd.isna(away_pred)
        or pd.isna(home_real)
        or pd.isna(away_real)
    ):
        no_score = next(
            (r for r in config.scoring_rules if "sem jogo" in r.name.lower()),
            None,
        )
        name = no_score.name if no_score else "9-Sem jogo"
        pts = no_score.points if no_score else 0
        return pd.Series([pts, name, 0])

    # Build a lookup: {criterion_key: (points, name, priority)}
    # The existing 5-tier logic is hard to express purely from config
    # because the criteria are hierarchical (exact score > winner+goals > ...).
    # We evaluate them in priority order and return the first match.

    pred_w = _winner(home_pred, away_pred)
    real_w = _winner(home_real, away_real)

    exact_score = home_pred == home_real and away_pred == away_real
    correct_winner = pred_w == real_w
    one_team_goals = home_pred == home_real or away_pred == away_real

    # Evaluate in priority order (lower priority number = checked first)
    sorted_rules = sorted(config.scoring_rules, key=lambda r: r.priority)

    for rule in sorted_rules:
        key = rule.name.lower()

        # 1. Exact score
        if "placar exato" in key and exact_score:
            return pd.Series([rule.points, rule.name, 1])

        # 2. Winner + one team's goals
        if "vencedor" in key and "gols" in key:
            if correct_winner and one_team_goals:
                return pd.Series([rule.points, rule.name, 1])

        # 3. Correct winner only
        if "vencedor" in key and "gols" not in key:
            if correct_winner:
                return pd.Series([rule.points, rule.name, 1])

        # 4. One team's goals only
        if "gols de um time" in key:
            if one_team_goals:
                return pd.Series([rule.points, rule.name, 1])

        # 5. No match / none correct
        if "nenhum" in key or "sem jogo" in key:
            return pd.Series([rule.points, rule.name, 1])

    # Fallback: no rule matched
    return pd.Series([0, "5-Nenhum acerto", 1])
