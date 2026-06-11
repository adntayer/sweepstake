"""Generic football sweepstake scoring engine.

Evaluates a predicted score against the real score and returns
(points, criterion_name, is_valid) based on configurable rules.

Supports hierarchical rules with optional conditions:
  - exact_score
   - correct_winner_and_goals (with max_total_error / min_total_error)
   - correct_winner_and_goals_or_diff (like above, but also accepts correct goal difference)
   - correct_winner
  - one_team_goals
  - missing_data
"""

from __future__ import annotations

from glob import glob

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
    home_pred: int,
    away_pred: int,
    home_real: int,
    away_real: int,
    pred_w: str,
    real_w: str,
    has_draw_rule: bool = False,
) -> bool:
    """Check whether a ScoringRule's condition is satisfied.

    Evaluates the rule's type (rule.rule) against the computed prediction
    outcomes AND enforces max_total_error / min_total_error bounds.
    """
    if rule.rule == "exact_score":
        return home_pred == home_real and away_pred == away_real

    if rule.rule in ("correct_winner_and_one_goal", "correct_winner_and_goals"):
        if has_draw_rule and pred_w == "draw":
            return False
        if pred_w != real_w:
            return False
        if not (home_pred == home_real or away_pred == away_real):
            return False
        total_err = int(abs(home_pred - home_real) + abs(away_pred - away_real))
        if rule.max_total_error is not None and total_err > rule.max_total_error:
            return False
        if rule.min_total_error is not None and total_err < rule.min_total_error:
            return False
        return True

    if rule.rule == "correct_winner_and_goal_diff":
        if has_draw_rule and pred_w == "draw":
            return False
        if pred_w != real_w:
            return False
        if not ((home_pred - away_pred) == (home_real - away_real)):
            return False
        total_err = int(abs(home_pred - home_real) + abs(away_pred - away_real))
        if rule.max_total_error is not None and total_err > rule.max_total_error:
            return False
        if rule.min_total_error is not None and total_err < rule.min_total_error:
            return False
        return True

    if rule.rule == "correct_winner_and_goals_or_diff":
        if has_draw_rule and pred_w == "draw":
            return False
        if pred_w != real_w:
            return False
        if not (home_pred == home_real or away_pred == away_real or (home_pred - away_pred) == (home_real - away_real)):
            return False
        total_err = int(abs(home_pred - home_real) + abs(away_pred - away_real))
        if rule.max_total_error is not None and total_err > rule.max_total_error:
            return False
        if rule.min_total_error is not None and total_err < rule.min_total_error:
            return False
        return True

    if rule.rule == "correct_draw_and_low_error":
        if pred_w != "draw" or real_w != "draw":
            return False
        total_err = int(abs(home_pred - home_real) + abs(away_pred - away_real))
        if rule.max_total_error is not None and total_err > rule.max_total_error:
            return False
        return True
        
    if rule.rule == "correct_draw":
        return pred_w == "draw" and real_w == "draw"

    if rule.rule == "correct_winner":
        if has_draw_rule and pred_w == "draw":
            return False
        return pred_w == real_w

    if rule.rule == "one_team_goals":
        return home_pred == home_real or away_pred == away_real

    if rule.rule in ("no_score", "missing_data"):
        return True

    return False


def score_prediction(
    home_pred: float,
    away_pred: float,
    home_real: float,
    away_real: float,
    config: ChampionshipConfig,
) -> pd.Series:
    """Score a single prediction against the real result.

    Evaluates all scoring rules in priority order, applying error bounds
    where configured. Returns pd.Series([points, criterion_name, is_valid]).
    """
    # Missing data
    if (
        pd.isna(home_pred)
        or pd.isna(away_pred)
        or pd.isna(home_real)
        or pd.isna(away_real)
    ):
        no_score = next(
            (r for r in config.scoring_rules if r.rule == "missing_data"),
            None,
        )
        name = no_score.name if no_score else "9-Sem jogo"
        pts = no_score.points if no_score else 0
        return pd.Series([pts, name, 0])

    pred_w = _winner(home_pred, away_pred)
    real_w = _winner(home_real, away_real)

    home_pred_i = int(home_pred)
    home_real_i = int(home_real)
    away_pred_i = int(away_pred)
    away_real_i = int(away_real)

    # Sort rules by priority ascending — lower number = evaluated first
    sorted_rules = sorted(config.scoring_rules, key=lambda r: r.priority)

    has_draw_rule = any(
        r.rule in ("correct_draw", "correct_draw_and_low_error")
        for r in config.scoring_rules
    )

    for rule in sorted_rules:
        if rule.rule == "missing_data":
            continue  # handled above; not a scoring outcome
        if _matches_condition(
            rule,
            home_pred_i, away_pred_i, home_real_i, away_real_i,
            pred_w, real_w,
            has_draw_rule=has_draw_rule,
        ):
            return pd.Series([rule.points, rule.name, 1])

    # Fallback — should not be reached if a no_score rule exists
    return pd.Series([0, "5-Nenhum acerto", 1])


def get_playoff_advancing_teams(
    games_csv: str,
    playoff_round_keys: list[str] | None = None,
) -> dict[str, list[str]]:
    """Extract which teams advanced from each playoff phase.

    Args:
        games_csv: Path to the games.csv results file.
        playoff_round_keys: List of round keys to look for in ``round`` column.
            Defaults to the keys used by the 2025 Club World Cup.

    Returns dict mapping phase_key -> list of teams that advanced
    (e.g. {'oitavas': [...], 'quartas': [...], 'semi': [...], 'final': [...]}).
    """
    df = pd.read_csv(games_csv, sep=",")
    if playoff_round_keys is None:
        playoff_round_keys = ["oitavas", "quartas", "semi", "final"]
    advancing: dict[str, list[str]] = {}

    # Normalize round column
    df["round"] = df["round"].astype(str).str.strip().str.lower()

    for pr in playoff_round_keys:
        pr_lower = pr.lower()
        phase_matches = df[df["round"] == pr_lower]
        winners = []
        for _, row in phase_matches.iterrows():
            hg = float(row["home_goals"]) if pd.notna(row["home_goals"]) else 0
            ag = float(row["away_goals"]) if pd.notna(row["away_goals"]) else 0
            if hg > ag:
                winners.append(str(row["home_team"]))
            elif ag > hg:
                winners.append(str(row["away_team"]))
            else:
                pen_h = row.get("home_pen", "")
                pen_a = row.get("away_pen", "")
                try:
                    pen_h_val = (
                        float(pen_h)
                        if pd.notna(pen_h) and str(pen_h).strip()
                        else None
                    )
                    pen_a_val = (
                        float(pen_a)
                        if pd.notna(pen_a) and str(pen_a).strip()
                        else None
                    )
                except (ValueError, TypeError):
                    pen_h_val = None
                    pen_a_val = None
                if pen_h_val is not None and pen_a_val is not None:
                    if pen_h_val > pen_a_val:
                        winners.append(str(row["home_team"]))
                    elif pen_a_val > pen_h_val:
                        winners.append(str(row["away_team"]))
                elif pen_h_val is not None:
                    winners.append(str(row["home_team"]))
                elif pen_a_val is not None:
                    winners.append(str(row["away_team"]))
        advancing[pr] = winners

    # The teams that advance FROM oitavas ARE the quarter-finalists.
    # The teams that advance FROM quartas ARE the semi-finalists.
    # The teams that advance FROM semi ARE the finalists.
    # The team that advances FROM final IS the champion.
    return advancing


def score_playoff_bonus(config: ChampionshipConfig) -> pd.DataFrame:
    """Score all players' playoff bonus team picks.

    Reads bronze bonus_teams_*.csv and games.csv, then returns
    a DataFrame: boleiro, phase, team_picked, team_actual, correct, points.
    """
    # Get actual advancing teams — use config playoff round keys
    playoff_keys = [pr.key for pr in config.playoff_rounds]
    advancing = get_playoff_advancing_teams(config.games_file, playoff_keys)

    # Load all bonus picks
    pattern = config.bronze_group_path("*").replace("group_phase_*", "bonus_teams_*.csv")
    bonus_paths = sorted(glob(pattern))

    rows = []
    for path_csv in bonus_paths:
        df_bonus = pd.read_csv(path_csv, sep=",")
        for _, row in df_bonus.iterrows():
            boleiro = str(row["boleiro"])
            phase = str(row["phase"])
            team_picked = str(row["team"])
            
            # Resolve actual teams for this phase
            if phase == "campeao":
                actual_teams = advancing.get("final", [])
            else:
                actual_teams = advancing.get(phase, [])
                
            correct = 1 if team_picked in actual_teams else 0
            pts = config.playoff_scoring.get(phase, 0) if correct else 0
            rows.append({
                "boleiro": boleiro,
                "phase": phase,
                "team_picked": team_picked,
                "team_actual": ", ".join(actual_teams),
                "correct": correct,
                "points": pts,
            })

    df_result = pd.DataFrame(rows, columns=[
        "boleiro", "phase", "team_picked", "team_actual", "correct", "points"
    ])
    return df_result


def score_strikers(config: ChampionshipConfig) -> pd.DataFrame:
    """Score all players' striker picks against the actual top scorer.

    Returns a DataFrame: boleiro, striker_picked, actual_top_scorer, correct, points.
    """
    pattern = config.bronze_group_path("*").replace("group_phase_*", "striker_*.csv")
    striker_paths = sorted(glob(pattern))

    rows = []
    for path_csv in striker_paths:
        df_st = pd.read_csv(path_csv, sep=",")
        for _, row in df_st.iterrows():
            boleiro = str(row["boleiro"])
            picked = str(row["striker"]).strip()
            actual = config.actual_top_scorer
            correct = 1 if picked.lower() == actual.lower() else 0
            pts = config.striker_points if correct else 0
            rows.append({
                "boleiro": boleiro,
                "striker_picked": picked,
                "actual_top_scorer": actual,
                "correct": correct,
                "points": pts,
            })

    return pd.DataFrame(rows, columns=[
        "boleiro", "striker_picked", "actual_top_scorer", "correct", "points"
    ])
