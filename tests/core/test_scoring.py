"""Tests for src.core.scoring."""

from __future__ import annotations

import pandas as pd
import pytest

from src.core.config import ChampionshipConfig, ScoringRule
from src.core.scoring import (
    _matches_condition,
    _total_error,
    _winner,
    score_prediction,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_cfg(rules: list[ScoringRule]) -> ChampionshipConfig:
    return ChampionshipConfig(
        id="test", name="Test", year=2025,
        scoring_rules=rules,
    )


def _default_rules_2025() -> list[ScoringRule]:
    return [
        ScoringRule(name="1-Placar exato", points=12, priority=1, rule="exact_score"),
        ScoringRule(
            name="2-Vencedor + gols de um time", points=7, priority=2,
            rule="correct_winner_and_goals", max_total_error=2,
        ),
        ScoringRule(
            name="3-Vencedor correto", points=5, priority=3,
            rule="correct_winner",
        ),
        ScoringRule(name="4-Gols de um time", points=1, priority=4, rule="one_team_goals"),
        ScoringRule(name="5-Nenhum acerto", points=0, priority=5, rule="no_score"),
        ScoringRule(name="9-Sem jogo", points=0, priority=99, rule="missing_data"),
    ]


# ------------------------------------------------------------------
# _winner
# ------------------------------------------------------------------

class TestWinner:
    def test_home_wins(self):
        assert _winner(3, 1) == "home"

    def test_away_wins(self):
        assert _winner(0, 2) == "away"

    def test_draw(self):
        assert _winner(1, 1) == "draw"

    def test_zero_zero(self):
        assert _winner(0, 0) == "draw"


# ------------------------------------------------------------------
# _total_error
# ------------------------------------------------------------------

class TestTotalError:
    def test_exact(self):
        assert _total_error(2, 1, 2, 1) == 0

    def test_one_off(self):
        assert _total_error(2, 1, 2, 2) == 1

    def test_both_off(self):
        assert _total_error(1, 0, 3, 2) == 4

    def test_negative(self):
        assert _total_error(0, 0, 2, 2) == 4


# ------------------------------------------------------------------
# _matches_condition
# ------------------------------------------------------------------

class TestMatchesCondition:
    def test_exact_score_match(self):
        rule = ScoringRule(name="exact", points=15, priority=1, rule="exact_score")
        assert _matches_condition(rule, 2, 1, 2, 1, "home", "home") is True

    def test_exact_score_miss(self):
        rule = ScoringRule(name="exact", points=15, priority=1, rule="exact_score")
        assert _matches_condition(rule, 2, 1, 3, 1, "home", "home") is False

    def test_correct_winner_and_goals_match_low_error(self):
        rule = ScoringRule(
            name="w+g", points=10, priority=2,
            rule="correct_winner_and_goals", max_total_error=2,
        )
        assert _matches_condition(rule, 3, 1, 2, 1, "home", "home") is True

    def test_correct_winner_and_goals_match_correct_diff(self):
        rule = ScoringRule(
            name="w+g", points=10, priority=2,
            rule="correct_winner_and_goals", max_total_error=2,
        )
        assert _matches_condition(rule, 3, 2, 2, 1, "home", "home") is True

    def test_correct_winner_and_goals_wrong_winner(self):
        rule = ScoringRule(
            name="w+g", points=10, priority=2,
            rule="correct_winner_and_goals", max_total_error=2,
        )
        assert _matches_condition(rule, 1, 2, 2, 1, "away", "home") is False

    def test_correct_winner_and_goals_no_goals_no_diff(self):
        rule = ScoringRule(
            name="w+g", points=10, priority=2,
            rule="correct_winner_and_goals", max_total_error=2,
        )
        assert _matches_condition(rule, 4, 2, 2, 1, "home", "home") is False

    def test_correct_winner_and_goals_error_too_high(self):
        rule = ScoringRule(
            name="w+g", points=10, priority=2,
            rule="correct_winner_and_goals", max_total_error=2,
        )
        assert _matches_condition(rule, 5, 1, 2, 1, "home", "home") is False

    def test_correct_winner_and_goals_error_too_low(self):
        rule = ScoringRule(
            name="w+g", points=7, priority=3,
            rule="correct_winner_and_goals", min_total_error=3,
        )
        assert _matches_condition(rule, 3, 1, 2, 1, "home", "home") is False

    def test_correct_winner_match(self):
        rule = ScoringRule(name="winner", points=5, priority=4, rule="correct_winner")
        assert _matches_condition(rule, 3, 0, 2, 1, "home", "home") is True

    def test_correct_winner_miss(self):
        rule = ScoringRule(name="winner", points=5, priority=4, rule="correct_winner")
        assert _matches_condition(rule, 1, 2, 2, 1, "away", "home") is False

    def test_one_team_goals_match_home(self):
        rule = ScoringRule(name="goals", points=1, priority=5, rule="one_team_goals")
        assert _matches_condition(rule, 2, 0, 2, 3, "home", "home") is True

    def test_one_team_goals_match_away(self):
        rule = ScoringRule(name="goals", points=1, priority=5, rule="one_team_goals")
        assert _matches_condition(rule, 0, 3, 2, 3, "away", "away") is True

    def test_one_team_goals_miss(self):
        rule = ScoringRule(name="goals", points=1, priority=5, rule="one_team_goals")
        assert _matches_condition(rule, 1, 0, 2, 3, "home", "away") is False

    def test_missing_data(self):
        rule = ScoringRule(name="no", points=0, priority=99, rule="missing_data")
        assert _matches_condition(rule, 0, 0, 0, 0, "draw", "draw") is True


# ------------------------------------------------------------------
# score_prediction — 2025 rules
# ------------------------------------------------------------------

class TestScorePrediction2025:
    # -- Exact score --
    def test_exact_score(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, 1, 2, 1, cfg)
        assert result[0] == 12
        assert result[1] == "1-Placar exato"
        assert result[2] == 1

    def test_exact_score_0_0(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(0, 0, 0, 0, cfg)
        assert result[0] == 12

    def test_exact_score_high(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(5, 3, 5, 3, cfg)
        assert result[0] == 12

    # -- Winner + goals (error <= 2, 7pts) --
    def test_winner_and_goals_low_error(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(3, 1, 2, 1, cfg)
        assert result[0] == 7
        assert result[1] == "2-Vencedor + gols de um time"

    def test_winner_and_goals_correct_diff(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(3, 2, 2, 1, cfg)
        assert result[0] == 7
        assert result[1] == "2-Vencedor + gols de um time"

    def test_winner_and_goals_error_boundary_2(self):
        """Error exactly 2 should still match (max_total_error=2)."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(4, 1, 2, 1, cfg)
        assert result[0] == 7
        assert result[1] == "2-Vencedor + gols de um time"

    def test_winner_and_goals_error_boundary_3(self):
        """Error 3 should fall to correct_winner (5pts)."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(4, 2, 2, 1, cfg)
        assert result[0] == 5
        assert result[1] == "3-Vencedor correto"

    def test_winner_and_goals_away_win(self):
        cfg = _make_cfg(_default_rules_2025())
        # Correct winner (away), but no exact goals and wrong diff (-3 vs -1)
        result = score_prediction(0, 3, 1, 2, cfg)
        assert result[0] == 5
        assert result[1] == "3-Vencedor correto"

    def test_winner_and_goals_one_off_home(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, 0, 2, 1, cfg)
        assert result[0] == 7

    def test_winner_and_goals_one_off_away(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(0, 2, 1, 2, cfg)
        assert result[0] == 7

    # -- Correct winner only (5pts) --
    def test_correct_winner_only(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(3, 0, 2, 1, cfg)
        assert result[0] == 5
        assert result[1] == "3-Vencedor correto"

    def test_correct_winner_away(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(0, 3, 1, 2, cfg)
        assert result[0] == 5

    def test_correct_winner_high_error(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(10, 0, 2, 1, cfg)
        assert result[0] == 5

    # -- One team goals only (1pt) --
    def test_one_team_goals_only(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, 0, 2, 3, cfg)
        assert result[0] == 1
        assert result[1] == "4-Gols de um time"

    def test_one_team_goals_away_only(self):
        cfg = _make_cfg(_default_rules_2025())
        # Correct winner (away), away exact goals → matches correct_winner_and_goals
        result = score_prediction(0, 3, 2, 3, cfg)
        assert result[0] == 7
        assert result[1] == "2-Vencedor + gols de um time"

    def test_one_team_goals_wrong_winner_home(self):
        cfg = _make_cfg(_default_rules_2025())
        # Wrong winner (pred home, real away), no exact goals → no match
        result = score_prediction(3, 1, 1, 2, cfg)
        assert result[0] == 0
        assert result[1] == "5-Nenhum acerto"

    def test_rigth_winner_wrong_score_one_goal_team(self):
        """Rigth winner, one team's exact goals matches → 7pt."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, 1, 3, 1, cfg)
        assert result[0] == 7
        assert result[1] == "2-Vencedor + gols de um time"

    # -- No match (0pts) --
    def test_no_match(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(1, 0, 2, 3, cfg)
        assert result[0] == 0
        assert result[1] == "5-Nenhum acerto"

    def test_no_match_wrong_winner_wrong_goals(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(3, 0, 0, 2, cfg)
        assert result[0] == 0

    # -- Missing data --
    def test_missing_pred_home(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(float("nan"), 1, 2, 1, cfg)
        assert result[0] == 0
        assert result[1] == "9-Sem jogo"
        assert result[2] == 0

    def test_missing_pred_away(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, float("nan"), 2, 1, cfg)
        assert result[2] == 0

    def test_missing_real_home(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, 1, float("nan"), 1, cfg)
        assert result[2] == 0

    def test_missing_real_away(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, 1, 2, float("nan"), cfg)
        assert result[2] == 0

    def test_missing_both(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(float("nan"), float("nan"), float("nan"), float("nan"), cfg)
        assert result[2] == 0

    # -- Draw scenarios --
    def test_draw_exact(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(1, 1, 1, 1, cfg)
        assert result[0] == 12

    def test_draw_correct_winner(self):
        """Predicted draw, real draw, correct diff (0==0) → correct_winner_and_goals (7pts)."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, 2, 1, 1, cfg)
        assert result[0] == 7
        assert result[1] == "2-Vencedor + gols de um time"

    def test_draw_correct_winner_high_error(self):
        """Predicted draw, real draw, correct diff (0==0) → correct_winner_and_goals (7pts).
        Note: score_prediction does NOT check error bounds; that's only in _matches_condition."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(3, 3, 1, 1, cfg)
        assert result[0] == 7
        assert result[1] == "2-Vencedor + gols de um time"

    def test_draw_winner_wrong(self):
        """Predicted draw, real home win → no match."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(1, 1, 2, 0, cfg)
        assert result[0] == 0

    def test_draw_winner_wrong_away(self):
        """Predicted draw, real away win → no match."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(1, 1, 0, 2, cfg)
        assert result[0] == 0

    def test_draw_one_team_goals(self):
        """Predicted draw, real home win, one team exact goals."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, 2, 2, 0, cfg)
        assert result[0] == 1

    # -- Int conversion --
    def test_int_conversion(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2.0, 1.0, 2.0, 1.0, cfg)
        assert result[0] == 12

    def test_int_conversion_float_inputs(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(3.0, 1.0, 2.0, 1.0, cfg)
        assert result[0] == 7

    # -- Edge cases --
    def test_zero_vs_zero_prediction(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(0, 0, 1, 0, cfg)
        assert result[0] == 1  # one team goals (away=0)

    def test_zero_vs_zero_real(self):
        """Predicted 1-0 (home win), real 0-0 (draw) → away exact goals (0==0) → one_team_goals."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(1, 0, 0, 0, cfg)
        assert result[0] == 1
        assert result[1] == "4-Gols de um time"

    def test_same_score_different_winner(self):
        """Predicted 2-1 (home), real 1-2 (away) → no match."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, 1, 1, 2, cfg)
        assert result[0] == 0

    def test_same_goals_different_teams(self):
        """Predicted 1-2, real 2-1 → no match (wrong winner, no exact goals)."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(1, 2, 2, 1, cfg)
        assert result[0] == 0

    def test_high_scoring_exact(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(4, 4, 4, 4, cfg)
        assert result[0] == 12

    def test_high_scoring_winner_goals(self):
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(5, 3, 4, 3, cfg)
        assert result[0] == 7

    def test_draw_predicted_home_win_real(self):
        """Predicted 1-1, real 2-0 → one team goals (home=1? no, home=2). No match."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(1, 1, 2, 0, cfg)
        assert result[0] == 0

    def test_draw_predicted_away_win_real_one_team(self):
        """Predicted 1-1, real 0-2 → one team goals (away=1? no, away=2). No match."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(1, 1, 0, 2, cfg)
        assert result[0] == 0

    def test_predicted_home_draw_real_draw(self):
        """Predicted 0-0, real 1-1 → correct_winner (draw), correct_diff (0==0) → 7pts."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(0, 0, 1, 1, cfg)
        assert result[0] == 7
        assert result[1] == "2-Vencedor + gols de um time"
