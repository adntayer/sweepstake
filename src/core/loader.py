"""Generic Excel parser for sweepstake prediction sheets.

Reads raw Excel files and extracts group-stage predictions and
bonus playoff team picks according to the championship's ExcelLayout.
"""

from __future__ import annotations

import os

import pandas as pd

from src.core.config import ChampionshipConfig

# Column names expected in the first 9 columns of the Excel sheet
_EXCEL_COLUMNS = [
    "date",
    "hour",
    "home_team",
    "home_pen",
    "home_goals",
    "x",
    "away_goals",
    "away_pen",
    "away_team",
]


def _extract_who(path: str, config: ChampionshipConfig) -> str:
    """Extract participant name from the Excel filename."""
    layout = config.excel_layout
    parts = path.split(layout.playoffs.name_split_char)
    name = parts[layout.playoffs.name_split_index].strip()
    return name.replace(".xlsx", "").replace(".xls", "").strip()


def _clean_dataframe(df: pd.DataFrame, who: str) -> pd.DataFrame:
    """Apply common cleaning steps to a parsed Excel dataframe."""
    df = df.copy()
    df.dropna(how="all", inplace=True)
    df["who"] = who
    df = df.loc[df["date"].notna()]
    df = df.loc[~df["date"].str.contains("GRUPO", na=False)]
    return df


def _normalize_types(df: pd.DataFrame) -> pd.DataFrame:
    """Cast numeric and date columns to proper types."""
    df = df.copy()
    for col in ["home_goals", "home_pen", "away_goals", "away_pen"]:
        if col in df.columns:
            df[col] = df[col].astype(float)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df = df.loc[df["date"].notna()]
    return df


def _make_match_key(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'match' column from home_team and away_team.

    Enforces: lowercase, no spaces, no hyphens — only underscores.
    This must stay in sync with _slug() in get_results.py.
    """
    df = df.copy()

    def _slug(name: str) -> str:
        s = name.lower().strip()
        s = s.replace(" ", "_").replace("-", "_")
        return s

    df["match"] = df["home_team"].apply(_slug) + "-vs-" + df["away_team"].apply(_slug)
    return df


def parse_group_stage(path: str, config: ChampionshipConfig) -> pd.DataFrame:
    """Parse the group-stage predictions from an Excel file.

    Returns a DataFrame with columns:
        date, hour, home_team, home_pen, home_goals, x, away_goals, away_pen,
        away_team, who, match
    """
    layout = config.excel_layout
    who = _extract_who(path, config)

    df = pd.read_excel(path, skiprows=layout.first_round.skiprows)
    df = df[df.columns[:9]]
    df.columns = _EXCEL_COLUMNS

    df = _clean_dataframe(df, who)
    df = df.head(layout.first_round.matches).copy()
    df = _normalize_types(df)
    df = _make_match_key(df)

    return df


def _extract_playoff_phase_and_who(path: str, config: ChampionshipConfig) -> tuple[str, str]:
    """Extract (phase_key, boleiro_name) from a playoff Excel filename.

    Expects format: ``{phase}_{boleiro}.xlsx`` where phase is one of
    the configured playoff round keys (oitavas, quartas, semi, final).
    """
    fname = os.path.basename(path)
    name_no_ext = fname.replace(".xlsx", "").replace(".xls", "").strip()

    # Try to match a known phase key at the start of the filename
    for pr in config.playoff_rounds:
        prefix = pr.key + "_"
        if name_no_ext.startswith(prefix):
            boleiro = name_no_ext[len(prefix):].strip()
            return pr.key, boleiro

    # Fallback: use first part before first '_' as phase, rest as name
    if "_" in name_no_ext:
        parts = name_no_ext.split("_", 1)
        return parts[0].strip(), parts[1].strip()

    raise ValueError(
        f"Cannot extract phase and boleiro from filename: {fname}. "
        f"Expected format: {{phase}}_{{boleiro}}.xlsx"
    )


def parse_playoff_stage(path: str, config: ChampionshipConfig) -> pd.DataFrame:
    """Parse playoff-round predictions from a dedicated Excel file.

    Each file contains only the matches for a single knockout round
    (e.g. 8 oitavas matches, 4 quartas matches, etc.).

    Returns a DataFrame with columns:
        date, hour, home_team, home_pen, home_goals, x, away_goals, away_pen,
        away_team, who, match, phase
    """
    phase, who = _extract_playoff_phase_and_who(path, config)

    df = pd.read_excel(path)
    df = df[df.columns[:9]]
    df.columns = _EXCEL_COLUMNS

    df = _clean_dataframe(df, who)
    df = _normalize_types(df)
    df = _make_match_key(df)
    df["phase"] = phase

    return df


def parse_bonus_playoffs(path: str, config: ChampionshipConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse bonus playoff team picks and striker from an Excel file.

    The first_round Excel contains a "playoffs" section where each boleiro
    picks one team per knockout phase (oitavas, quartas, semi, final).
    These are bonus picks — not scored predictions.

    Returns:
        (bonus_teams_df, striker_df)
        - bonus_teams_df: columns boleiro, phase, team
        - striker_df: columns boleiro, striker
    """
    layout = config.excel_layout
    who = _extract_who(path, config)

    df = pd.read_excel(path, skiprows=layout.first_round.skiprows)
    df = df[df.columns[:9]]
    df.columns = _EXCEL_COLUMNS

    df = _clean_dataframe(df, who)

    # Extract one team per playoff round (home_team is the pick)
    bonus_rows = []
    for pr in layout.playoff_rows:
        round_df = df.tail(pr["tail_offset"]).head(pr["head_count"])
        for _, row in round_df.iterrows():
            team = str(row["home_team"]).strip()
            if team:
                bonus_rows.append({"boleiro": who, "phase": pr["key"], "team": team})

    df_bonus = pd.DataFrame(bonus_rows, columns=["boleiro", "phase", "team"])

    # Extract striker (last row)
    df_striker_raw = df.tail(layout.playoffs.striker_row_offset).copy()
    df_striker = df_striker_raw[["who", "home_team"]].copy()
    df_striker.columns = ["boleiro", "striker"]

    return df_bonus, df_striker
