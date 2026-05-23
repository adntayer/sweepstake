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

from src.core.config import ChampionshipConfig
from src.core.loader import parse_group_stage, parse_bonus_playoffs
from src.core.printing import print_colored
from src.core.scoring import score_prediction
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

    boleiros = _boleiros_from_raw(config)
    for idx, (path_excel, boleiro) in enumerate(boleiros, 1):
        print_colored(f"\t[{idx:2}/{len(boleiros)}] parsing {boleiro}", "ice")

        df_group = parse_group_stage(path_excel, config)
        df_bonus, df_striker = parse_bonus_playoffs(path_excel, config)

        df_group.sort_values(by=["date", "hour"], inplace=True)
        _save_csv(df_group, config.bronze_group_path(boleiro))

        _save_csv(df_bonus, config.bronze_bonus_path(boleiro))
        _save_csv(df_striker, config.bronze_striker_path(boleiro))

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

    # Process each boleiro — first_round only
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

    print_colored("silver to gold completed", "green")


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

def run_pipeline(config: ChampionshipConfig) -> None:
    """Run the full medallion pipeline."""
    get_results(config)
    run_raw_to_bronze(config)
    run_bronze_to_silver(config)
    run_silver_to_gold(config)
