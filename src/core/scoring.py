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
        # Must have at least one team's exact goals
        if not one_team:
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
    correct_winner_and_scores_one_time = pred_w == real_w and (home_pred == home_real or  away_pred == away_real)
    correct_winner = pred_w == real_w
    one_team_goals = home_pred == home_real or away_pred == away_real

    series_score = pd.Series([0, "5-Nenhum acerto", 1])

    if exact_score:
        rule_name = 'exact_score'
    elif correct_winner_and_scores_one_time:
        rule_name = 'correct_winner_and_goals'
    elif correct_winner:
        rule_name = 'correct_winner'
    elif one_team_goals:
        rule_name = 'one_team_goals'
    else:
        rule_name = 'no_score'

    dict_rule = {rule.rule: rule for rule in config.scoring_rules}

    rule = dict_rule.get(rule_name)
    return pd.Series([rule.points, rule.name, 1])


def get_playoff_advancing_teams(games_csv: str) -> dict[str, list[str]]:
    """Extract which teams advanced from each playoff phase.

    Returns dict mapping phase_key -> list of teams that advanced
    (e.g. {'oitavas': [...], 'quartas': [...], 'semi': [...], 'final': [...]}).
    """
    df = pd.read_csv(games_csv, sep=",")
    playoff_rounds = ["oitavas", "quartas", "semi", "final"]
    advancing: dict[str, list[str]] = {}

    for pr in playoff_rounds:
        phase_matches = df[df["round"] == pr]
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
                if pd.notna(pen_h) and str(pen_h).strip():
                    winners.append(str(row["home_team"]))
                elif pd.notna(pen_a) and str(pen_a).strip():
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
    # Get actual advancing teams
    advancing = get_playoff_advancing_teams(config.games_file)

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
