"""Medallion pipeline: bronze -> silver -> gold.

All stages are driven by ChampionshipConfig so the same code works
for any championship.

Structure:
  Bronze:
    bronze/first_round/group_phase_{boleiro}.csv
    bronze/first_round/bonus_teams_{boleiro}.csv
    bronze/first_round/striker_{boleiro}.csv
    bronze/playoffs/  (future separate playoff Excel files)

  Silver:
    silver/first_round/group_phase_{boleiro}.csv
    silver/playoffs/  (future)

  Gold:
    gold/first_round/group_phase_{boleiro}.csv
    gold/first_round/{label}_all.csv
    gold/first_round/{label}_valido_all.csv
    gold/first_round/striker_{boleiro}.csv
    gold/first_round/playoffs_strikers.csv
    gold/playoffs/  (future)
"""

from __future__ import annotations

import os
import shutil
from glob import glob

import pandas as pd

from datetime import datetime
from pathlib import Path

import numpy as np

from src.core.config import ChampionshipConfig
from src.core.loader import (
    parse_group_stage,
    parse_playoff_stage,
    parse_bonus_playoffs,
    _extract_playoff_phase_and_who as _extract_phase_who_from_path,
)
from src.core.printing import print_colored
from src.core.scoring import score_prediction, score_playoff_bonus, score_strikers
from src.core.get_results import get_results

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


def _recreate_dirs(paths: list[str]) -> None:
    """Delete and recreate a list of directories."""
    root = _norm(paths[0]) if paths else ""
    if root and os.path.exists(root):
        shutil.rmtree(root)
        print_colored(f"Folder '{root}' deleted.", "green")
    for p in paths:
        os.makedirs(_norm(p), exist_ok=True)


def _save_csv(df: pd.DataFrame, path: str) -> None:
    """Save a DataFrame to CSV with consistent settings."""
    p = _norm(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    df.to_csv(p, sep=",", decimal=".", index=False)


def _boleiros_from_raw(config: ChampionshipConfig) -> list[tuple[str, str]]:
    """Return sorted list of (excel_path, boleiro_name) from raw dir."""
    group_label = config.group_phase_label
    raw_pattern = _norm(os.path.join(config.raw_dir, group_label, "*"))
    excel_paths = sorted(glob(raw_pattern, recursive=True))
    result = []
    for path_excel in excel_paths:
        layout = config.excel_layout
        parts = path_excel.split(layout.playoffs.name_split_char)
        name = parts[layout.playoffs.name_split_index].strip()
        boleiro = name.replace(".xlsx", "").replace(".xls", "").strip()
        result.append((path_excel, boleiro))
    return result


def _extract_playoff_phase_and_boleiro(path_csv: str, config: ChampionshipConfig) -> tuple[str, str]:
    """Extract (phase, boleiro) from a bronze/silver playoff CSV filename.

    Expects format: ``group_phase_{phase}_{boleiro}.csv``
    """
    basename = os.path.basename(path_csv).replace("group_phase_", "").replace(".csv", "")
    # Match known phase key at the start
    for pr in config.playoff_rounds:
        prefix = pr.key + "_"
        if basename.startswith(prefix):
            return pr.key, basename[len(prefix):]
    raise ValueError(f"Cannot extract phase from playoff file: {path_csv}")


def _playoff_files_from_raw(config: ChampionshipConfig) -> list[tuple[str, str, str]]:
    """Return sorted list of (excel_path, phase_key, boleiro_name) from raw/playoffs/."""
    raw_playoff_dir = config._raw_playoffs()
    if not os.path.isdir(raw_playoff_dir):
        return []
    pattern = _norm(os.path.join(raw_playoff_dir, "*"))
    excel_paths = sorted(glob(pattern))
    result = []
    for path_excel in excel_paths:
        ext = os.path.splitext(path_excel)[1].lower()
        if ext not in (".xls", ".xlsx"):
            continue
        phase, boleiro = _extract_phase_who_from_path(path_excel, config)
        result.append((path_excel, phase, boleiro))
    return result


# ------------------------------------------------------------------
# Result merge helpers
# ------------------------------------------------------------------

def _merge_with_results(df_pred: pd.DataFrame, df_results: pd.DataFrame) -> pd.DataFrame:
    """Merge predictions with official results on 'match' key.

    Adds real goals and result description columns.
    """
    df = df_pred.merge(df_results, on="match", how="left", suffixes=("_bol", "_real"))

    # Build result strings
    df["resultado_bol_placar"] = (
        df["home_goals_bol"].astype("Int64").astype(str)
        + " x "
        + df["away_goals_bol"].astype("Int64").astype(str)
    )
    df["resultado_bol_time"] = df.apply(
        lambda r: r["home_team_bol"]
        if r["home_goals_bol"] > r["away_goals_bol"]
        else r["away_team_bol"]
        if r["away_goals_bol"] > r["home_goals_bol"]
        else "empate",
        axis=1,
    )
    df["resultado_real_placar"] = df.apply(
        lambda r: f"{int(r['home_goals_real'])} x {int(r['away_goals_real'])}"
        if pd.notna(r.get("home_goals_real")) and pd.notna(r.get("away_goals_real"))
        else "",
        axis=1,
    )
    df["resultado_real_time"] = df.apply(
        lambda r: r["home_team_real"]
        if pd.notna(r.get("home_goals_real")) and pd.notna(r.get("away_goals_real"))
        and r["home_goals_real"] > r["away_goals_real"]
        else r["away_team_real"]
        if pd.notna(r.get("home_goals_real")) and pd.notna(r.get("away_goals_real"))
        and r["away_goals_real"] > r["home_goals_real"]
        else "empate"
        if pd.notna(r.get("home_goals_real")) and pd.notna(r.get("away_goals_real"))
        else "",
        axis=1,
    )

    return df


# ------------------------------------------------------------------
# Scoring helpers
# ------------------------------------------------------------------

def _apply_scoring(df: pd.DataFrame, config: ChampionshipConfig) -> pd.DataFrame:
    """Score each prediction and add scoring columns.

    Adds: pontos, criterio, valido, plus one-hot columns for each rule name.
    """
    pontos_list: list = []
    criterio_list: list = []
    valido_list: list = []

    for _, row in df.iterrows():
        try:
            result = score_prediction(
                row["home_goals_bol"],
                row["away_goals_bol"],
                row.get("home_goals_real"),
                row.get("away_goals_real"),
                config,
            )
            pontos_list.append(result.iloc[0])
            criterio_list.append(result.iloc[1])
            valido_list.append(result.iloc[2])
        except Exception:
            pontos_list.append(0)
            criterio_list.append("5-Nenhum acerto")
            valido_list.append(1)

    df["pontos"] = pontos_list
    df["criterio"] = criterio_list
    df["valido"] = valido_list

    # One-hot encode criteria
    rule_names = config.scoring_rule_names()
    for rule in rule_names:
        df[rule] = df["criterio"] == rule

    return df


# ------------------------------------------------------------------
# Bronze: raw Excel -> first_round/ + playoffs/
# ------------------------------------------------------------------

def run_raw_to_bronze(config: ChampionshipConfig) -> None:
    """Parse all raw Excel files and write bronze CSVs."""
    print_colored("raw to bronze", "sand")

    dirs = [
        config.bronze_dir,
        config._br_first_round(),
        config._br_playoffs(),
    ]
    _recreate_dirs(dirs)

    # --- First round (group stage) ---
    boleiros = _boleiros_from_raw(config)
    for idx, (path_excel, boleiro) in enumerate(boleiros, 1):
        print_colored(f"\t[{idx:2}/{len(boleiros)}] parsing {boleiro}", "ice")

        df_group = parse_group_stage(path_excel, config)
        df_bonus, df_striker = parse_bonus_playoffs(path_excel, config)

        df_group.sort_values(by=["date", "hour"], inplace=True)
        _save_csv(df_group, config.bronze_group_path(boleiro))

        _save_csv(df_bonus, config.bronze_bonus_path(boleiro))
        _save_csv(df_striker, config.bronze_striker_path(boleiro))

    # --- Playoff rounds (separate Excel per phase) ---
    playoff_files = _playoff_files_from_raw(config)
    for idx, (path_excel, phase, boleiro) in enumerate(playoff_files, 1):
        print_colored(f"\t[{idx:2}/{len(playoff_files)}] parsing {phase} {boleiro}", "ice")
        df_playoff = parse_playoff_stage(path_excel, config)
        df_playoff.sort_values(by=["date", "hour"], inplace=True)
        _save_csv(df_playoff, config.bronze_playoff_path(boleiro, phase))

    print_colored("raw to bronze completed", "green")


# ------------------------------------------------------------------
# Silver: bronze first_round + official results -> merged predictions
# ------------------------------------------------------------------

def run_bronze_to_silver(config: ChampionshipConfig) -> None:
    """Merge bronze first_round predictions with official results (per boleiro).

    Playoffs are bonus-only and do not flow to silver.
    """
    print_colored("bronze to silver", "sand")

    dirs = [
        config.silver_dir,
        config._ag_first_round(),
        config._ag_playoffs(),
    ]
    _recreate_dirs(dirs)

    # Load official results
    df_results = pd.read_csv(config.games_file, sep=",")

    # --- First round (group stage) ---
    group_pattern = _norm(os.path.join(config._br_first_round(), "group_phase_*"))
    group_paths = sorted(glob(group_pattern))

    for path_csv in group_paths:
        boleiro = os.path.basename(path_csv).replace("group_phase_", "").replace(".csv", "")
        print_colored(f"\tmerging {boleiro}", "ice")

        df_boleiro = pd.read_csv(path_csv, sep=",")
        df_merged = _merge_with_results(df_boleiro, df_results)

        # Rename suffixed columns back to canonical names
        df_merged.rename(
            columns={
                "date_bol": "date",
                "home_team_bol": "home_team",
                "away_team_bol": "away_team",
            },
            inplace=True,
        )

        # Select and order columns
        df_merged = df_merged.reindex(
            columns=[
                "date",
                "hour",
                "match",
                "home_team",
                "away_team",
                "home_goals_bol",
                "away_goals_bol",
                "home_goals_real",
                "away_goals_real",
                "resultado_bol_placar",
                "resultado_bol_time",
                "resultado_real_placar",
                "resultado_real_time",
                "who",
            ]
        )
        df_merged.sort_values(by=["date", "hour"], inplace=True)
        _save_csv(df_merged, config.silver_group_path(boleiro))

    # --- Playoff rounds ---
    playoff_pattern = _norm(os.path.join(config._br_playoffs(), "group_phase_*"))
    playoff_paths = sorted(glob(playoff_pattern))

    for path_csv in playoff_paths:
        phase, boleiro = _extract_playoff_phase_and_boleiro(path_csv, config)
        print_colored(f"\tmerging {phase} {boleiro}", "ice")

        df_boleiro = pd.read_csv(path_csv, sep=",")

        # Filter results to only this playoff phase
        df_results_phase = df_results[df_results["round"] == phase].copy()

        df_merged = _merge_with_results(df_boleiro, df_results_phase)

        # Rename suffixed columns back to canonical names
        df_merged.rename(
            columns={
                "date_bol": "date",
                "home_team_bol": "home_team",
                "away_team_bol": "away_team",
            },
            inplace=True,
        )

        # Select and order columns
        df_merged = df_merged.reindex(
            columns=[
                "date",
                "hour",
                "match",
                "home_team",
                "away_team",
                "home_goals_bol",
                "away_goals_bol",
                "home_goals_real",
                "away_goals_real",
                "resultado_bol_placar",
                "resultado_bol_time",
                "resultado_real_placar",
                "resultado_real_time",
                "who",
            ]
        )
        df_merged.sort_values(by=["date", "hour"], inplace=True)
        _save_csv(df_merged, config.silver_playoff_path(boleiro, phase))

    print_colored("bronze to silver completed", "green")


# ------------------------------------------------------------------
# Gold: silver -> scoring applied + aggregated views
# ------------------------------------------------------------------

def run_silver_to_gold(config: ChampionshipConfig) -> None:
    """Create gold-layer analytical datasets (per-boleiro + aggregated).

    Playoffs are bonus-only and do not flow to gold.
    """
    print_colored("silver to gold", "sand")

    dirs = [
        config.gold_dir,
        config.gold_first_round_dir(),
        config.gold_playoffs_dir(),
    ]
    _recreate_dirs(dirs)

    # --- First round ---
    silver_pattern = _norm(os.path.join(config._ag_first_round(), "group_phase_*"))
    silver_paths = sorted(glob(silver_pattern))

    df_all_parts = []
    df_valid_parts = []

    for path_csv in silver_paths:
        boleiro = os.path.basename(path_csv).replace("group_phase_", "").replace(".csv", "")
        print_colored(f"\tscoring first_round {boleiro}", "ice")

        df_silver = pd.read_csv(path_csv, sep=",")
        df_gold = _apply_scoring(df_silver, config)

        # Save per-boleiro gold file
        _save_csv(df_gold, config.gold_group_boleiro_path(boleiro))

        df_all_parts.append(df_gold)
        df_valid_parts.append(df_gold.query("valido == 1"))

    # Aggregate first round
    if df_all_parts:
        df_all = pd.concat(df_all_parts, ignore_index=True)
        df_all.sort_values(by=["date", "hour", "who"], inplace=True)
        _save_csv(df_all, config.gold_all_path("group"))

        df_valid = pd.concat(df_valid_parts, ignore_index=True)
        df_valid.sort_values(by=["date", "hour", "who"], inplace=True)
        _save_csv(df_valid, config.gold_valid_path("group"))

    # --- Copy strikers to gold ---
    striker_pattern = _norm(os.path.join(config._br_first_round(), "striker_*"))
    striker_paths = sorted(glob(striker_pattern))

    df_strikers_parts = []
    for path_csv in striker_paths:
        df_st = pd.read_csv(path_csv, sep=",")
        df_strikers_parts.append(df_st)

    if df_strikers_parts:
        df_strikers = pd.concat(df_strikers_parts, ignore_index=True)
        df_strikers.sort_values(by=["boleiro"], inplace=True)
        _save_csv(df_strikers, config.playoff_strikers_path("gold"))

        # Also copy individual striker files to gold
        for path_csv in striker_paths:
            boleiro = os.path.basename(path_csv).replace("striker_", "").replace(".csv", "")
            df_st = pd.read_csv(path_csv, sep=",")
            _save_csv(df_st, config.gold_striker_path(boleiro))

    # --- Playoff rounds ---
    playoff_silver_pattern = _norm(os.path.join(config._ag_playoffs(), "group_phase_*"))
    playoff_silver_paths = sorted(glob(playoff_silver_pattern))

    # Group paths by phase so we can aggregate per phase
    playoff_by_phase: dict[str, list[str]] = {}
    for path_csv in playoff_silver_paths:
        phase, _ = _extract_playoff_phase_and_boleiro(path_csv, config)
        playoff_by_phase.setdefault(phase, []).append(path_csv)

    for phase, phase_paths in sorted(playoff_by_phase.items()):
        print_colored(f"\tscoring playoff phase: {phase}", "ice")
        all_phase_parts = []
        valid_phase_parts = []

        for path_csv in phase_paths:
            _, boleiro = _extract_playoff_phase_and_boleiro(path_csv, config)
            df_silver = pd.read_csv(path_csv, sep=",")
            if df_silver.empty:
                continue
            df_gold = _apply_scoring(df_silver, config)

            # Save per-boleiro gold file for this phase
            _save_csv(df_gold, config.gold_playoff_boleiro_path(boleiro, phase))

            all_phase_parts.append(df_gold)
            valid_phase_parts.append(df_gold.query("valido == 1"))

        # Aggregate per phase
        if all_phase_parts:
            df_all = pd.concat(all_phase_parts, ignore_index=True)
            df_all.sort_values(by=["date", "hour", "who"], inplace=True)
            _save_csv(df_all, config.gold_playoff_all_path(phase))

            df_valid = pd.concat(valid_phase_parts, ignore_index=True)
            df_valid.sort_values(by=["date", "hour", "who"], inplace=True)
            _save_csv(df_valid, config.gold_playoff_valid_path(phase))

    # --- New analytics ---
    _generate_playoff_scoring(config)
    _generate_striker_scoring(config)
    _generate_consistency(df_valid, config)
    _generate_upset_tracker(df_all, config)
    _generate_round_by_round(df_valid, config)
    _generate_team_accuracy(df_valid, config)

    # --- New v2 analytics ---
    _generate_ranking_history(df_valid, config)
    _generate_boldness_index(df_all, config)
    _generate_prediction_timing(config)
    _generate_goal_error_by_team(df_valid, config)

    print_colored("silver to gold completed", "green")


# ------------------------------------------------------------------
# Derived analytics (generated from gold data)
# ------------------------------------------------------------------


def _generate_playoff_scoring(config: ChampionshipConfig) -> None:
    """Score playoff bonus team picks and save to gold."""
    if not config.playoff_scoring:
        print_colored("\tskipping playoff scoring (no config)", "yellow")
        return
    print_colored("\tgenerating playoff scoring", "ice")
    df = score_playoff_bonus(config)
    _save_csv(df, _norm(os.path.join(config._au_first_round(), "playoffs_scored.csv")))
    print_colored(f"\tplayoffs_scored.csv: {len(df)} rows", "green")


def _generate_striker_scoring(config: ChampionshipConfig) -> None:
    """Score striker picks and save to gold."""
    if not config.actual_top_scorer or not config.striker_points:
        print_colored("\tskipping striker scoring (no config)", "yellow")
        return
    print_colored("\tgenerating striker scoring", "ice")
    df = score_strikers(config)
    _save_csv(df, _norm(os.path.join(config._au_first_round(), "strikers_scored.csv")))
    print_colored(f"\tstrikers_scored.csv: {len(df)} rows", "green")


def _generate_consistency(df_valid: pd.DataFrame, config: ChampionshipConfig) -> None:
    """Derive streak/consistency data from gold predictions."""
    print_colored("\tgenerating consistency tracking", "ice")
    df = df_valid.copy()
    df = df.sort_values(["who", "date", "hour"])
    df["hit"] = df["pontos"] > 0

    rows = []
    for boleiro, group in df.groupby("who"):
        streak_type = None
        streak_len = 0
        for _, row in group.iterrows():
            is_hit = row["hit"]
            if is_hit and streak_type == "hit":
                streak_len += 1
            elif not is_hit and streak_type == "miss":
                streak_len += 1
            else:
                streak_type = "hit" if is_hit else "miss"
                streak_len = 1

            # Running avg of last 5 games
            recent = group.loc[:row.name, "pontos"].tail(5).mean() if "pontos" in group.columns else 0

            rows.append({
                "boleiro": boleiro,
                "date": row["date"],
                "match": row.get("match", ""),
                "streak_type": streak_type,
                "streak_length": streak_len,
                "running_avg_5": round(recent, 1),
            })

    df_out = pd.DataFrame(rows)
    _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "consistency.csv")))
    print_colored(f"\tconsistency.csv: {len(df_out)} rows", "green")


def _generate_upset_tracker(df_all: pd.DataFrame, config: ChampionshipConfig) -> None:
    """Identify upset matches and who correctly predicted them."""
    print_colored("\tgenerating upset tracker", "ice")
    df = df_all.copy()
    df_results = pd.read_csv(config.games_file, sep=",")

    # Merge round info
    df_games_round = df_results[["match", "round"]].drop_duplicates()
    df = df.merge(df_games_round, on="match", how="left")

    rows = []
    for match, group in df.groupby("match"):
        first = group.iloc[0]
        home = first["home_team"]
        away = first["away_team"]
        real_winner = first.get("resultado_real_time", "")

        # Determine favorite (most predicted winner)
        vote_counts = group["resultado_bol_time"].value_counts()
        favorite = vote_counts.index[0] if not vote_counts.empty else ""
        favorite_votes = int(vote_counts.iloc[0]) if not vote_counts.empty else 0
        total_votes = len(group)

        is_upset = 0
        if real_winner and real_winner != "empate" and favorite and favorite != "empate":
            if real_winner != favorite:
                is_upset = 1

        # Which players got the upset
        players_correct = []
        for _, p_row in group.iterrows():
            if str(p_row.get("resultado_bol_time", "")) == real_winner:
                players_correct.append(p_row["who"])

        rows.append({
            "match": match,
            "home_team": home,
            "away_team": away,
            "real_winner": real_winner,
            "favorite": favorite,
            "favorite_votes": favorite_votes,
            "total_votes": total_votes,
            "is_upset": is_upset,
            "num_correct": len(players_correct),
            "players_correct": " | ".join(players_correct),
        })

    df_out = pd.DataFrame(rows)
    _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "upset_tracker.csv")))
    print_colored(f"\tupset_tracker.csv: {len(df_out)} rows", "green")


def _generate_round_by_round(df_valid: pd.DataFrame, config: ChampionshipConfig) -> None:
    """Aggregate points per round for each player."""
    print_colored("\tgenerating round-by-round tracking", "ice")
    df = df_valid.copy()
    df_results = pd.read_csv(config.games_file, sep=",")

    # Merge round info from games.csv
    df_games_round = df_results[["match", "round"]].drop_duplicates()
    df = df.merge(df_games_round, on="match", how="left")
    df["round"] = df["round"].fillna("0")

    # Map round labels to numeric ordering
    round_order = {}
    for i, r in enumerate(["1", "2", "3", "oitavas", "quartas", "semi", "final"]):
        round_order[r] = i + 1
    df["round_number"] = df["round"].map(round_order).fillna(0).astype(int)

    rows = []
    for boleiro, group in df.groupby("who"):
        group = group.sort_values("round_number")
        cum = 0
        for rn, rgroup in group.groupby("round_number"):
            pts = int(rgroup["pontos"].sum())
            cum += pts
            rows.append({
                "boleiro": boleiro,
                "round_number": rn,
                "round_label": rgroup.iloc[0]["round"],
                "points": pts,
                "cumulative_points": cum,
            })

    # Add rank per round
    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        for rn in df_out["round_number"].unique():
            mask = df_out["round_number"] == rn
            df_out.loc[mask, "rank"] = df_out.loc[mask, "cumulative_points"].rank(
                ascending=False, method="min"
            ).astype(int)

    _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "round_by_round.csv")))
    print_colored(f"\tround_by_round.csv: {len(df_out)} rows", "green")


def _generate_team_accuracy(df_valid: pd.DataFrame, config: ChampionshipConfig) -> None:
    """Calculate prediction accuracy per team for each player."""
    print_colored("\tgenerating team accuracy tracking", "ice")
    df = df_valid.copy()

    rows = []
    # For home team role
    for team_col, opp_col in [("home_team", "away_team"), ("away_team", "home_team")]:
        for team, group in df.groupby(team_col):
            for boleiro, bg in group.groupby("who"):
                total = len(bg)
                correct_winner = sum(
                    1 for _, r in bg.iterrows()
                    if str(r.get("resultado_bol_time", "")) == str(r.get("resultado_real_time", ""))
                )
                exact_score = sum(
                    1 for _, r in bg.iterrows()
                    if r.get("home_goals_bol", -1) == r.get("home_goals_real", -2)
                    and r.get("away_goals_bol", -1) == r.get("away_goals_real", -2)
                )
                rows.append({
                    "team": team,
                    "role": team_col.replace("_team", ""),
                    "boleiro": boleiro,
                    "total_bets": total,
                    "correct_winner": correct_winner,
                    "exact_score": exact_score,
                    "accuracy_pct": round(correct_winner / total * 100, 1) if total > 0 else 0,
                })

    df_out = pd.DataFrame(rows)
    _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "team_accuracy.csv")))
    print_colored(f"\tteam_accuracy.csv: {len(df_out)} rows", "green")


# ------------------------------------------------------------------
# New analytics #1: Ranking history (daily rank position)
# ------------------------------------------------------------------


def _generate_ranking_history(df_valid: pd.DataFrame, config: ChampionshipConfig) -> None:
    """Daily rank position for each player (cumulative ranking)."""
    print_colored("\tgenerating ranking history", "ice")
    df = df_valid.copy()
    df = df.sort_values(["who", "date"])

    rows = []
    for date, day_group in df.groupby("date"):
        # Cumulative points up to this date for each player
        daily_pts = day_group.groupby("who")["pontos"].sum()
        # Get all players' cumulative up to this date
        all_cum = df[df["date"] <= date].groupby("who")["pontos"].sum()
        leader_pts = int(all_cum.max()) if not all_cum.empty else 0
        leader_name = str(all_cum.idxmax()) if not all_cum.empty else ""

        for boleiro, pts in daily_pts.items():
            cum = int(all_cum.get(boleiro, 0))
            rank = int(all_cum.rank(ascending=False, method="min").get(boleiro, 0))
            rows.append({
                "boleiro": boleiro,
                "date": date,
                "daily_points": int(pts),
                "cumulative_points": cum,
                "rank": rank,
                "leader_name": leader_name,
                "leader_distance": leader_pts - cum,
            })

    df_out = pd.DataFrame(rows)
    _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "ranking_history.csv")))
    print_colored(f"\tranking_history.csv: {len(df_out)} rows", "green")


# ------------------------------------------------------------------
# New analytics #2: Boldness index
# ------------------------------------------------------------------


def _generate_boldness_index(df_all: pd.DataFrame, config: ChampionshipConfig) -> None:
    """Measure how 'bold' each player's predictions are."""
    print_colored("\tgenerating boldness index", "ice")
    df = df_all.copy()

    # Bolão average total goals per game
    bolao_avg = (df["home_goals_bol"] + df["away_goals_bol"]).mean()

    rows = []
    for boleiro, group in df.groupby("who"):
        total_goals = group["home_goals_bol"] + group["away_goals_bol"]
        avg_total = total_goals.mean()
        games = len(group)

        # How often they predict extreme scores (>= 5 total goals)
        extreme_pct = (total_goals >= 5).sum() / games * 100 if games > 0 else 0

        rows.append({
            "boleiro": boleiro,
            "avg_total_goals_bol": round(avg_total, 2),
            "avg_home_goals_bol": round(group["home_goals_bol"].mean(), 2),
            "avg_away_goals_bol": round(group["away_goals_bol"].mean(), 2),
            "max_home_bol": int(group["home_goals_bol"].max()),
            "max_away_bol": int(group["away_goals_bol"].max()),
            "extreme_score_pct": round(extreme_pct, 1),
            "games": games,
            "boldness_score": round(avg_total - bolao_avg, 2),
        })

    df_out = pd.DataFrame(rows)
    df_out = df_out.sort_values("boldness_score", ascending=False)
    _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "boldness_index.csv")))
    print_colored(f"\tboldness_index.csv: {len(df_out)} rows", "green")


# ------------------------------------------------------------------
# New analytics #3: Prediction timing (lead days from raw Excel mtime)
# ------------------------------------------------------------------


def _generate_prediction_timing(config: ChampionshipConfig) -> None:
    """Estimate how early each player submitted picks (via raw Excel mtime)."""
    print_colored("\tgenerating prediction timing", "ice")

    # Load games to know first match date
    df_games = pd.read_csv(config.games_file, sep=",")
    if "date" in df_games.columns and not df_games["date"].empty:
        first_match = pd.to_datetime(df_games["date"].dropna().min())
    else:
        first_match = datetime.now()

    # Scan raw Excel files for modification time
    raw_pattern = _norm(os.path.join(config.raw_dir, config.group_phase_label, "*"))
    raw_paths = sorted(glob(raw_pattern))

    rows = []
    for path_excel in raw_paths:
        layout = config.excel_layout
        parts = path_excel.split(layout.playoffs.name_split_char)
        name = parts[layout.playoffs.name_split_index].strip()
        boleiro = name.replace(".xlsx", "").replace(".xls", "").strip()

        mtime = os.path.getmtime(path_excel)
        mtime_dt = datetime.fromtimestamp(mtime)
        lead_days = (first_match - pd.Timestamp(mtime_dt)).days if first_match else 0

        rows.append({
            "boleiro": boleiro,
            "file_mtime": mtime_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "first_match_date": first_match.strftime("%Y-%m-%d") if not pd.isna(first_match) else "",
            "lead_days": max(lead_days, 0),
        })

    df_out = pd.DataFrame(rows)
    df_out = df_out.sort_values("lead_days", ascending=False)
    _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "prediction_timing.csv")))
    print_colored(f"\tprediction_timing.csv: {len(df_out)} rows", "green")


# ------------------------------------------------------------------
# New analytics #4: Goal error by team
# ------------------------------------------------------------------


def _generate_goal_error_by_team(df_valid: pd.DataFrame, config: ChampionshipConfig) -> None:
    """Mean Absolute Error per team for each player's goal predictions."""
    print_colored("\tgenerating goal error by team", "ice")
    df = df_valid.copy()

    rows = []
    for team_col in ("home_team", "away_team"):
        role = team_col.replace("_team", "")
        goals_bol_col = f"{role}_goals_bol"
        goals_real_col = f"{role}_goals_real"

        for team, group in df.groupby(team_col):
            for boleiro, bg in group.groupby("who"):
                games = len(bg)
                if games == 0:
                    continue
                errors = abs(bg[goals_bol_col] - bg[goals_real_col])
                mae = round(errors.mean(), 2)
                bias = round((bg[goals_bol_col] - bg[goals_real_col]).mean(), 2)

                rows.append({
                    "boleiro": boleiro,
                    "team": team,
                    "role": role,
                    "games": games,
                    "mae": mae,
                    "goal_bias": bias,
                    "avg_predicted": round(bg[goals_bol_col].mean(), 2),
                    "avg_real": round(bg[goals_real_col].mean(), 2),
                })

    # Also total MAE (home + away combined)
    # Group by (boleiro, team) and merge home/away rows
    df_out = pd.DataFrame(rows)
    # Add a "total" row per boleiro+team
    totals = []
    for (boleiro, team), group in df_out.groupby(["boleiro", "team"]):
        total_games = group["games"].sum()
        total_mae = round((group["mae"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0
        totals.append({
            "boleiro": boleiro,
            "team": team,
            "role": "total",
            "games": total_games,
            "mae": total_mae,
            "goal_bias": round(group["goal_bias"].mean(), 2),
            "avg_predicted": round((group["avg_predicted"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0,
            "avg_real": round((group["avg_real"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0,
        })
    df_totals = pd.DataFrame(totals)
    df_out = pd.concat([df_out, df_totals], ignore_index=True)
    df_out = df_out.sort_values(["boleiro", "team", "role"])

    _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "goal_error_by_team.csv")))
    print_colored(f"\tgoal_error_by_team.csv: {len(df_out)} rows", "green")


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

def run_pipeline(config: ChampionshipConfig) -> None:
    """Run the full medallion pipeline."""
    get_results(config)
    run_raw_to_bronze(config)
    run_bronze_to_silver(config)
    run_silver_to_gold(config)
