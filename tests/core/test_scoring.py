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

 
def _default_rules_invented() -> list[ScoringRule]:
    """Invented scoring config with tiered error bounds.

    Two correct_winner_and_goals rules at different priority levels:
      - Rule A (priority 2): max_total_error=1, 10pts  (tight)
      - Rule B (priority 3): 2<=error<=3,          6pts  (loose)
    score_prediction iterates rules by priority and evaluates each
    against the prediction outcome AND its error bounds, so the
    correct rule is selected based on both type AND bound matching.
    """
    return [
        ScoringRule(name="1-Placar exato", points=20, priority=1, rule="exact_score"),
        ScoringRule(
            name="2-Vencedor + diff exata", points=10, priority=2,
            rule="correct_winner_and_goals", max_total_error=1,
        ),
        ScoringRule(
            name="3-Vencedor + gols proximos", points=6, priority=3,
            rule="correct_winner_and_goals", max_total_error=3, min_total_error=2,
        ),
        ScoringRule(
            name="4-Vencedor correto", points=3, priority=4,
            rule="correct_winner",
        ),
        ScoringRule(name="5-Gols de um time", points=1, priority=5, rule="one_team_goals"),
        ScoringRule(name="6-Nenhum acerto", points=0, priority=6, rule="no_score"),
        ScoringRule(name="9-Sem jogo", points=0, priority=99, rule="missing_data"),
    ]


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
        # correct_diff alone no longer qualifies; must have one team's exact goals
        assert _matches_condition(rule, 3, 2, 2, 1, "home", "home") is False

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
        # correct_diff alone no longer qualifies; falls to correct_winner (5pts)
        result = score_prediction(3, 2, 2, 1, cfg)
        assert result[0] == 5
        assert result[1] == "3-Vencedor correto"

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

    def test_right_winner_wrong_score_one_goal_team(self):
        """Right winner, one team's exact goals matches → 7pt."""
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
        """Predicted draw, real draw, no exact goals → correct_winner (5pts)."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(2, 2, 1, 1, cfg)
        assert result[0] == 5
        assert result[1] == "3-Vencedor correto"

    def test_draw_correct_winner_high_error(self):
        """Predicted draw, real draw, no exact goals → correct_winner (5pts)."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(3, 3, 1, 1, cfg)
        assert result[0] == 5
        assert result[1] == "3-Vencedor correto"

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
        """Predicted 0-0, real 1-1 → correct_winner (draw), no exact goals → 5pts."""
        cfg = _make_cfg(_default_rules_2025())
        result = score_prediction(0, 0, 1, 1, cfg)
        assert result[0] == 5
        assert result[1] == "3-Vencedor correto"


# ------------------------------------------------------------------
# score_prediction — invented rules
# ------------------------------------------------------------------

class TestScorePredictionInvented:
    # -- Exact score (20pts) --
    def test_exact_score(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, 1, 2, 1, cfg)
        assert result[0] == 20
        assert result[1] == "1-Placar exato"
        assert result[2] == 1

    def test_exact_score_0_0(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(0, 0, 0, 0, cfg)
        assert result[0] == 20

    def test_exact_score_high(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(4, 3, 4, 3, cfg)
        assert result[0] == 20

    # -- Winner + diff exact, error <= 1 (10pts) --
    def test_winner_and_diff_exact_error_0(self):
        """Correct winner, one team exact goals, total_error=1 ≤ max_error=1 → 10pts."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 1, 2, 1, cfg)
        assert result[0] == 10
        assert result[1] == "2-Vencedor + diff exata"

    def test_winner_and_diff_exact_error_1(self):
        """Correct winner, no exact goals → correct_winner → 3pts."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, 0, 3, 1, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    def test_winner_and_diff_exact_boundary_error_1(self):
        """Correct winner, one team exact goals, total_error=1 ≤ max_error=1 → 10pts."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, 1, 2, 0, cfg)
        assert result[0] == 10
        assert result[1] == "2-Vencedor + diff exata"

    def test_winner_and_diff_exact_correct_diff_error_1(self):
        """Correct winner, no exact goals → correct_winner → 3pts."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 1, 2, 0, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    def test_winner_and_diff_exact_error_0_one_team(self):
        """Exact score → caught by tier 1 (20pts), not correct_winner_and_goals."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, 1, 2, 1, cfg)
        assert result[0] == 20

    # -- Winner + goals nearby, 2 <= error <= 3 (6pts) --
    def test_winner_goals_nearby_error_2(self):
        """Correct winner, one team exact goals, total_error=1 ≤ max_error=1 → 10pts (Rule A)."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 1, 2, 1, cfg)
        assert result[0] == 10
        assert result[1] == "2-Vencedor + diff exata"

    def test_winner_goals_nearby_error_3(self):
        """Correct winner, one team exact goals, total_error=2, min=2≤2≤max=3 → 6pts (Rule B)."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(4, 1, 2, 1, cfg)
        assert result[0] == 6
        assert result[1] == "3-Vencedor + gols proximos"

    def test_winner_goals_nearby_error_boundary_2(self):
        """Correct winner, no one_team, no correct_diff → correct_winner → 3pts."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 0, 2, 1, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    def test_winner_goals_nearby_error_boundary_3(self):
        """Correct winner, one team exact goals, total_error=3, min=2≤3≤max=3 → 6pts (Rule B)."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(5, 1, 2, 1, cfg)
        assert result[0] == 6
        assert result[1] == "3-Vencedor + gols proximos"

    def test_winner_goals_nearby_error_4_falls_through(self):
        """Correct winner, no one_team, no correct_diff → correct_winner → 3pts.
        total_error=4 exceeds both Rule A (max=1) and Rule B (max=3) bounds."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(6, 1, 2, 1, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    # -- Correct winner only (3pts) --
    def test_correct_winner_only(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 0, 2, 1, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    def test_correct_winner_away(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(0, 3, 1, 2, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    def test_correct_winner_high_error(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(10, 0, 2, 1, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    # -- One team goals only (1pt) --
    def test_one_team_goals_only(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, 0, 2, 3, cfg)
        assert result[0] == 1
        assert result[1] == "5-Gols de um time"

    def test_one_team_goals_away_only(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(0, 3, 2, 3, cfg)
        # correct winner (away), away exact goals, total_error=2
        # Rule A max=1 → no. Rule B min=2≤2≤max=3 → matches → 6pts
        assert result[0] == 6
        assert result[1] == "3-Vencedor + gols proximos"

    def test_wrong_winner_no_goals(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 1, 1, 2, cfg)
        assert result[0] == 0
        assert result[1] == "6-Nenhum acerto"

    # -- No match (0pts) --
    def test_no_match(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(1, 0, 2, 3, cfg)
        assert result[0] == 0
        assert result[1] == "6-Nenhum acerto"

    def test_no_match_wrong_winner_wrong_goals(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 0, 0, 2, cfg)
        assert result[0] == 0

    # -- Missing data --
    def test_missing_pred_home(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(float("nan"), 1, 2, 1, cfg)
        assert result[0] == 0
        assert result[1] == "9-Sem jogo"
        assert result[2] == 0

    def test_missing_pred_away(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, float("nan"), 2, 1, cfg)
        assert result[2] == 0

    def test_missing_real_home(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, 1, float("nan"), 1, cfg)
        assert result[2] == 0

    def test_missing_real_away(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, 1, 2, float("nan"), cfg)
        assert result[2] == 0

    def test_missing_both(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(float("nan"), float("nan"), float("nan"), float("nan"), cfg)
        assert result[2] == 0

    # -- Draw scenarios --
    def test_draw_exact(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(1, 1, 1, 1, cfg)
        assert result[0] == 20

    def test_draw_correct_diff_error_0(self):
        """Predicted draw, real draw, no exact goals → correct_winner → 3pts."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, 2, 1, 1, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    def test_draw_correct_diff_error_4(self):
        """Predicted draw, real draw, no exact goals → correct_winner → 3pts."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 3, 1, 1, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    def test_draw_winner_wrong(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(1, 1, 2, 0, cfg)
        assert result[0] == 0

    def test_draw_winner_wrong_away(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(1, 1, 0, 2, cfg)
        assert result[0] == 0

    def test_draw_one_team_goals(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, 2, 2, 0, cfg)
        # correct winner? pred=draw, real=home → no. one_team_goals(home=2) → yes
        assert result[0] == 1
        assert result[1] == "5-Gols de um time"

    # -- Int conversion --
    def test_int_conversion(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2.0, 1.0, 2.0, 1.0, cfg)
        assert result[0] == 20

    def test_int_conversion_float_inputs(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3.0, 1.0, 2.0, 1.0, cfg)
        assert result[0] == 6

    # -- Edge cases --
    def test_zero_vs_zero_prediction(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(0, 0, 1, 0, cfg)
        # correct winner? pred=draw, real=home → no. one_team_goals(away=0==0) → yes
        assert result[0] == 1

    def test_zero_vs_zero_real(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(1, 0, 0, 0, cfg)
        # correct winner? pred=home, real=draw → no. one_team_goals(away=0==0) → yes
        assert result[0] == 1
        assert result[1] == "5-Gols de um time"

    def test_same_score_different_winner(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(2, 1, 1, 2, cfg)
        assert result[0] == 0

    def test_same_goals_different_teams(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(1, 2, 2, 1, cfg)
        assert result[0] == 0

    def test_high_scoring_exact(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(4, 4, 4, 4, cfg)
        assert result[0] == 20

    def test_high_scoring_winner_goals(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(5, 3, 4, 3, cfg)
        # correct winner(home), one_team_goals(away=3), total_error=1 ≤ 1 → 10pts (Rule A)
        assert result[0] == 10
        assert result[1] == "2-Vencedor + diff exata"

    def test_predicted_home_draw_real_draw(self):
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(0, 0, 1, 1, cfg)
        # correct winner(draw), no exact goals → correct_winner → 3pts
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    # -- Invented-specific: error-bound tiered behavior --
    def test_duplicate_rule_key_first_priority_wins(self):
        """Two correct_winner_and_goals rules, lower error (total=1 ≤ max=1) → Rule A (10pts)."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 1, 2, 1, cfg)
        assert result[0] == 10
        assert result[1] == "2-Vencedor + diff exata"

    def test_min_total_error_enforces_lower_bound(self):
        """score_prediction enforces min_total_error=2; error=1 → Rule A (max=1) not Rule B."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 1, 2, 1, cfg)
        assert result[0] == 10
        assert result[1] == "2-Vencedor + diff exata"

    def test_min_total_error_includes_error_2(self):
        """Correct winner, one team exact goals, total_error=2, min=2≤2≤max=3 → Rule B (6pts)."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(4, 1, 2, 1, cfg)
        assert result[0] == 6
        assert result[1] == "3-Vencedor + gols proximos"

    def test_tier_gap_error_1_falls_to_correct_winner(self):
        """No one_team, no correct_diff → correct_winner → 3pts."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(3, 0, 2, 1, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    def test_away_win_tier_2(self):
        """Away win, no exact goals → correct_winner → 3pts."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(0, 2, 1, 3, cfg)
        assert result[0] == 3
        assert result[1] == "4-Vencedor correto"

    def test_away_win_tier_2_error_1(self):
        """Away win, one team exact goals, total_error=1 ≤ max_error=1 → 10pts (Rule A)."""
        cfg = _make_cfg(_default_rules_invented())
        result = score_prediction(1, 3, 1, 2, cfg)
        assert result[0] == 10
        assert result[1] == "2-Vencedor + diff exata"
