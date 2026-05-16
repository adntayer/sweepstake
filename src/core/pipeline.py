"""Medallion pipeline: bronze -> silver -> gold.

All stages are driven by ChampionshipConfig so the same code works
for any championship.
"""

from __future__ import annotations

import os
import shutil
from glob import glob

import pandas as pd

from src.core.config import ChampionshipConfig
from src.core.loader import parse_group_stage, parse_playoffs
from src.core.scoring import score_prediction
from src.services.printing import print_colored


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


def _recreate_dirs(paths: list[str]) -> None:
    """Delete and recreate a list of directories."""
    # Delete the root if it exists
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


# ------------------------------------------------------------------
# Bronze: raw Excel -> per-participant CSVs
# ------------------------------------------------------------------

def run_raw_to_bronze(config: ChampionshipConfig) -> None:
    """Parse all raw Excel files and write bronze CSVs."""
    print_colored("raw to bronze", "sand")

    group_label = config.group_phase_label

    # Build directory tree
    dirs = [
        config.bronze_dir,
        os.path.join(config.bronze_dir, group_label),
        os.path.join(config.bronze_dir, "playoffs", "full", "games"),
        os.path.join(config.bronze_dir, "playoffs", "full"),
    ]
    # Add per-round directories
    for pr in config.playoff_rounds:
        dirs.append(os.path.join(config.bronze_dir, "playoffs", pr.key))
        dirs.append(os.path.join(config.bronze_dir, "playoffs", pr.key, "games"))
    dirs.append(os.path.join(config.bronze_dir, "playoffs", "striker"))

    _recreate_dirs(dirs)

    # Find all Excel files
    raw_pattern = _norm(os.path.join(config.raw_dir, group_label, "*"))
    excel_paths = sorted(glob(raw_pattern, recursive=True))

    df_strikers = pd.DataFrame(columns=["boleiro", "striker"])
    for idx, path_excel in enumerate(excel_paths, 1):
        print_colored(f"\t[{idx:2}/{len(excel_paths)}] parsing {path_excel}", "ice")

        df_group = parse_group_stage(path_excel, config)
        df_playoffs, df_striker = parse_playoffs(path_excel, config)
        who = df_group["who"].unique()[0]

        # Save group stage
        path_bronze_group = os.path.join(
            config.bronze_dir, group_label, f"{group_label}_{who}.csv"
        )
        df_group.sort_values(by=["date", "hour"], inplace=True)
        _save_csv(df_group, path_bronze_group)

        # Save playoff games
        path_bronze_playoffs = os.path.join(
            config.bronze_dir, "playoffs", "full", "games",
            f"playoffs_games_{who}.csv"
        )
        df_playoffs.sort_values(by=["date", "hour"], inplace=True)
        _save_csv(df_playoffs, path_bronze_playoffs)

        df_strikers = pd.concat([df_strikers, df_striker], ignore_index=True)

    # Save aggregated strikers
    path_strikers = os.path.join(
        config.bronze_dir, "playoffs", "full", "playoffs_strikers.csv"
    )
    if not df_strikers.empty:
        df_strikers.sort_values(by=["boleiro"], inplace=True)
    _save_csv(df_strikers, path_strikers)

    print_colored("raw to bronze completed", "green")


# ------------------------------------------------------------------
# Silver: bronze CSVs + official results -> scored predictions
# ------------------------------------------------------------------

def run_bronze_to_silver(config: ChampionshipConfig) -> None:
    """Merge bronze predictions with official results and score them."""
    print_colored("bronze to silver", "sand")

    group_label = config.group_phase_label

    # Build directory tree
    dirs = [
        config.silver_dir,
        os.path.join(config.silver_dir, group_label),
        os.path.join(config.silver_dir, "playoffs", "full"),
    ]
    for pr in config.playoff_rounds:
        dirs.append(os.path.join(config.silver_dir, "playoffs", pr.key))
    _recreate_dirs(dirs)

    # Load official results
    df_results = pd.read_csv(config.results_file, sep=",")

    # Load all bronze group CSVs
    bronze_pattern = _norm(os.path.join(config.bronze_dir, group_label, "*"))
    bronze_paths = sorted(glob(bronze_pattern, recursive=True))

    df_all = pd.DataFrame()
    for path_csv in bronze_paths:
        df_boleiro = pd.read_csv(path_csv, sep=",")
        df_merge = df_boleiro.merge(df_results, on="match", suffixes=("_bol", "_real"))

        # Score each prediction
        df_merge[["pontos", "criterio", "valido"]] = df_merge.apply(
            lambda row: score_prediction(
                row["home_goals_bol"],
                row["away_goals_bol"],
                row["home_goals_real"],
                row["away_goals_real"],
                config,
            ),
            axis=1,
        )

        # Rename columns
        df_merge.rename(
            columns={
                "date_bol": "date",
                "match_bol": "match",
                "home_team_bol": "home_team",
                "away_team_bol": "away_team",
            },
            inplace=True,
        )

        # Build result strings
        df_merge["resultado_bol_placar"] = (
            df_merge["home_goals_bol"].astype("Int64").astype(str)
            + " x "
            + df_merge["away_goals_bol"].astype("Int64").astype(str)
        )
        df_merge["resultado_bol_time"] = df_merge.apply(
            lambda row: row["home_team"]
            if row["home_goals_bol"] > row["away_goals_bol"]
            else row["away_team"]
            if row["away_goals_bol"] > row["home_goals_bol"]
            else "empate",
            axis=1,
        )
        df_merge["resultado_real_placar"] = (
            df_merge["home_goals_real"].astype("Int64").astype(str)
            + " x "
            + df_merge["away_goals_real"].astype("Int64").astype(str)
        )
        df_merge["resultado_real_time"] = df_merge.apply(
            lambda row: row["home_team"]
            if row["home_goals_real"] > row["away_goals_real"]
            else row["away_team"]
            if row["away_goals_real"] > row["home_goals_real"]
            else "empate",
            axis=1,
        )

        # Select and order columns
        df_merge = df_merge.reindex(
            columns=[
                "date",
                "hour",
                "match",
                "home_team",
                "away_team",
                "resultado_bol_placar",
                "resultado_bol_time",
                "resultado_real_placar",
                "resultado_real_time",
                "criterio",
                "pontos",
                "valido",
                "who",
            ]
        )
        df_all = pd.concat([df_all, df_merge], ignore_index=True)

    # Save silver group
    path_silver_group = os.path.join(
        config.silver_dir, group_label, "all_games.csv"
    )
    df_all.sort_values(by=["date", "hour", "who"], inplace=True)
    _save_csv(df_all, path_silver_group)

    # Process playoff predictions into long format
    df_playoff_pre_full = pd.DataFrame()
    playoff_pattern = _norm(os.path.join(
        config.bronze_dir, "playoffs", "full", "games", "*"
    ))
    playoff_paths = sorted(glob(playoff_pattern, recursive=True))

    for path_playoffs in playoff_paths:
        df_playoff_pre = pd.read_csv(path_playoffs, sep=",")
        df_playoff_loop = pd.concat(
            [
                df_playoff_pre[["home_team", "who", "playoff"]].rename(
                    columns={"home_team": "team"}
                ),
                df_playoff_pre[["away_team", "who", "playoff"]].rename(
                    columns={"away_team": "team"}
                ),
            ],
            ignore_index=True,
        )
        df_playoff_pre_full = pd.concat(
            [df_playoff_pre_full, df_playoff_loop], ignore_index=True
        )

    df_playoff_pre_full.sort_values(["who", "playoff", "team"], inplace=True)
    path_playoff_silver = os.path.join(
        config.silver_dir, "playoffs", "full", "playoffs_full_games.csv"
    )
    _save_csv(df_playoff_pre_full, path_playoff_silver)

    # Copy strikers to silver
    df_striker = pd.read_csv(config.playoff_strikers_path(layer="bronze"), sep=",")
    _save_csv(df_striker, config.playoff_strikers_path(layer="silver"))

    print_colored("bronze to silver completed", "green")


# ------------------------------------------------------------------
# Gold: silver -> one-hot encoded criteria + filtered views
# ------------------------------------------------------------------

def run_silver_to_gold(config: ChampionshipConfig) -> None:
    """Create gold-layer analytical datasets."""
    print_colored("silver to gold", "sand")

    group_label = config.group_phase_label

    # Build directory tree
    dirs = [
        config.gold_dir,
        os.path.join(config.gold_dir, group_label),
        os.path.join(config.gold_dir, "playoffs", "full"),
    ]
    for pr in config.playoff_rounds:
        dirs.append(os.path.join(config.gold_dir, "playoffs", pr.key))
    _recreate_dirs(dirs)

    # Load silver data
    df_all = pd.read_csv(config.silver_all_path(group_label), sep=",")

    # One-hot encode scoring criteria
    df_criterios = pd.get_dummies(df_all["criterio"])
    df_all = pd.concat([df_all, df_criterios], axis=1)

    # Save all records
    _save_csv(
        df_all.sort_values(by=["date", "hour", "who"]),
        config.gold_all_path(group_label),
    )

    # Save valid-only records
    df_valid = df_all.query("valido==1").sort_values(by=["date", "hour", "who"])
    _save_csv(df_valid, config.gold_valid_path(group_label))

    # Copy playoff data to gold
    df_playoffs = pd.read_csv(config.playoff_games_path(layer="silver"), sep=",")
    _save_csv(df_playoffs, config.playoff_games_path(layer="gold"))

    df_strikers = pd.read_csv(config.playoff_strikers_path(layer="silver"), sep=",")
    _save_csv(df_strikers, config.playoff_strikers_path(layer="gold"))

    print_colored("silver to gold completed", "green")


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

def run_pipeline(config: ChampionshipConfig) -> None:
    """Run the full medallion pipeline."""
    run_raw_to_bronze(config)
    run_bronze_to_silver(config)
    run_silver_to_gold(config)
