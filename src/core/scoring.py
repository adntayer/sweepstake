"""Generic football sweepstake scoring engine.

Evaluates a predicted score against the real score and returns
(points, criterion_name, is_valid) based on configurable rules.

Supports hierarchical rules with optional conditions:
  - exact_score
  - correct_winner_and_goals (with max_total_error / min_total_error)
  - correct_winner
  - one_team_goals
  - missing_data
"""

from __future__ import annotations

import pandas as pd

from src.core.config import ChampionshipConfig, ScoringRule


def _winner(home: float, away: float) -> str:
    """Return 'home', 'away', or 'draw'."""
    if home > away:
        return "home"
    if away > home:
        return "away"
    return "draw"


def _total_error(
    home_pred: float, away_pred: float, home_real: float, away_real: float
) -> int:
    """Absolute difference between predicted and real total goals."""
    return int(abs(home_pred - home_real) + abs(away_pred - away_real))


def _matches_condition(
    rule: ScoringRule,
    home_pred: float,
    away_pred: float,
    home_real: float,
    away_real: float,
    pred_w: str,
    real_w: str,
) -> bool:
    """Check if a rule's rule matches the prediction."""
    cond = getattr(rule, "rule", "")
    exact = home_pred == home_real and away_pred == away_real
    correct_w = pred_w == real_w
    one_team = home_pred == home_real or away_pred == away_real
    err = _total_error(home_pred, away_pred, home_real, away_real)

    if cond == "exact_score":
        return exact

    if cond == "correct_winner_and_goals":
        if not correct_w:
            return False
        # Must also have either one team's exact goals OR correct goal difference
        correct_diff = (home_pred - away_pred) == (home_real - away_real)
        if not (one_team or correct_diff):
            return False
        # Check error bounds
        max_err = getattr(rule, "max_total_error", None)
        min_err = getattr(rule, "min_total_error", None)
        if max_err is not None and err > max_err:
            return False
        if min_err is not None and err < min_err:
            return False
        return True

    if cond == "correct_winner":
        return correct_w

    if cond == "one_team_goals":
        return one_team

    if cond == "missing_data":
        return True  # handled before this function

    return False


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

    pred_w = _winner(home_pred, away_pred)
    real_w = _winner(home_real, away_real)

    home_pred = int(home_pred)
    home_real = int(home_real)
    away_pred = int(away_pred)
    away_real = int(away_real)

    exact_score = home_pred == home_real and away_pred == away_real
    correct_winner = pred_w == real_w
    one_team_goals = home_pred == home_real or away_pred == away_real
    correct_diff = (home_pred - away_pred) == (home_real - away_real)

    if exact_score:
        rule_name = "exact_score"
    elif correct_winner and (one_team_goals or correct_diff):
        rule_name = "correct_winner_and_goals"
    elif correct_winner:
        rule_name = "correct_winner"
    elif one_team_goals:
        rule_name = "one_team_goals"
    else:
        rule_name = "no_score"

    dict_rule = {}
    for rule in config.scoring_rules:
        if rule.rule not in dict_rule:
            dict_rule[rule.rule] = rule

    rule = dict_rule.get(rule_name)
    if rule is None:
        return pd.Series([0, "5-Nenhum acerto", 1])
    return pd.Series([rule.points, rule.name, 1])
