"""Generic Excel parser for sweepstake prediction sheets.

Reads raw Excel files and extracts group-stage and playoff predictions
according to the championship's ExcelLayout configuration.
"""

from __future__ import annotations

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
    return name.replace(".xls", "").replace(".xlsx", "")


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
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def _make_match_key(df: pd.DataFrame) -> pd.DataFrame:
    """Add a 'match' column from home_team and away_team."""
    df = df.copy()
    df["match"] = (
        df["home_team"].str.strip() + "-vs-" + df["away_team"].str.strip()
    )
    df["match"] = df["match"].str.replace(" ", "_").str.lower()
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


def parse_playoffs(path: str, config: ChampionshipConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse playoff predictions and striker pick from an Excel file.

    Returns:
        (playoff_df, striker_df)
        - playoff_df: long format with columns date, hour, home_team, home_pen,
          home_goals, x, away_goals, away_pen, away_team, who, playoff
        - striker_df: columns boleiro, striker
    """
    layout = config.excel_layout
    who = _extract_who(path, config)

    df = pd.read_excel(path, skiprows=layout.first_round.skiprows)
    df = df[df.columns[:9]]
    df.columns = _EXCEL_COLUMNS

    df = _clean_dataframe(df, who)

    # Extract each playoff round using tail/head offsets from config
    round_dfs = []
    for pr in layout.playoff_rows:
        round_df = df.tail(pr["tail_offset"]).head(pr["head_count"]).copy()
        round_df["playoff"] = pr["key"]
        round_dfs.append(round_df)

    df_playoff = pd.concat(round_dfs, ignore_index=True)
    df_playoff = _normalize_types(df_playoff)

    # Extract striker (last row)
    df_striker_raw = df.tail(layout.playoffs.striker_row_offset).copy()
    df_striker = df_striker_raw[["who", "home_team"]].copy()
    df_striker.columns = ["boleiro", "striker"]

    return df_playoff, df_striker
