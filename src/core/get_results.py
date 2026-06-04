"""Download and transform official fixture results into the internal format.

Produces a single ``games.csv`` with all matches (group stage + playoffs)
translated from English to the championship's configured team names.
"""

from __future__ import annotations

import os
import re
from io import StringIO

import pandas as pd
import requests

from src.core.config import ChampionshipConfig


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _translate(name: str, mapping: dict[str, str]) -> str:
    """Return the Portuguese name for an English team name.

    Falls back to the original name if no mapping exists.
    """
    return mapping.get(name, name)


def _slug(name: str) -> str:
    """Create a URL-safe slug from a team name.

    Matches the existing convention: lowercase, spaces/accents → underscores.
    """
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9áàâãéèêíïóôõöúùûüç]+", "_", s)
    s = s.strip("_")
    return s


def _parse_date(raw: str) -> str:
    """Convert 'DD/MM/YYYY HH:MM' → 'YYYY-MM-DD HHh'.

    Matches the internal date format used by jogos_1afase.csv.
    Returns empty string for missing or unparseable dates.
    """
    if not raw or not str(raw).strip():
        return ""
    try:
        dt = pd.to_datetime(raw, format="%d/%m/%Y %H:%M")
        return dt.strftime("%Y-%m-%d %Hh")
    except (ValueError, TypeError):
        return ""


def _parse_result(result: str) -> tuple[int | None, int | None]:
    """Parse 'X - Y' → (home_goals, away_goals).

    Returns (None, None) for unplayed matches.
    """
    if not result or not result.strip():
        return None, None
    parts = result.strip().split(" - ")
    if len(parts) != 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


_ROUND_MAP = {
    "Round of 16": "oitavas",
    "Quarter Finals": "quartas",
    "Semi Finals": "semi",
    "Final": "final",
}


def _parse_round(raw) -> str:
    """Map Round Number to internal phase key.

    Group rounds (1, 2, 3) stay as integers.
    Knockout rounds are translated to Portuguese keys.
    """
    val = str(raw).strip()
    if val in _ROUND_MAP:
        return _ROUND_MAP[val]
    return val


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def get_results(config: ChampionshipConfig) -> None:
    """Download official results, translate team names, and save games.csv.

    The output format matches the internal convention expected by the
    bronze→silver pipeline:
        date, home_team, home_pen, home_goals, x, away_goals, away_pen, away_team, match
    """
    url = config.results_endpoint
    if not url:
        raise ValueError("results_endpoint not configured")

    # Fetch raw CSV
    response = requests.get(url)
    response.raise_for_status()

    # Parse the fixturedownload CSV
    # Columns: Match Number, Round Number, Date, Location, Home Team, Away Team, Group, Result
    df = pd.read_csv(
        StringIO(response.text),
        skipinitialspace=True,
    )

    # Translate team names
    mapping = config.team_name_mapping
    df["home_team"] = df["Home Team"].apply(lambda n: _translate(str(n), mapping))
    df["away_team"] = df["Away Team"].apply(lambda n: _translate(str(n), mapping))

    # Parse date and result
    df["date"] = df["Date"].apply(_parse_date)
    df[["home_goals", "away_goals"]] = df["Result"].apply(
        lambda r: pd.Series(_parse_result(str(r)))
    )

    # Build match slug from translated names
    df["match"] = df["home_team"].apply(_slug) + "-vs-" + df["away_team"].apply(_slug)

    # Map round numbers/names to internal phase keys
    df["round"] = df["Round Number"].apply(_parse_round)

    # Build output DataFrame in internal format
    df_out = pd.DataFrame({
        "date": df["date"],
        "round": df["round"],
        "home_team": df["home_team"],
        "home_pen": "",
        "home_goals": df["home_goals"],
        "x": "x",
        "away_goals": df["away_goals"],
        "away_pen": "",
        "away_team": df["away_team"],
        "match": df["match"],
    })

    # Save
    output_path = config.games_file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_out.to_csv(output_path, sep=",", decimal=".", index=False)
    print(f"Arquivo {output_path} criado com sucesso! ({len(df_out)} jogos)")


if __name__ == "__main__":
    from src.core.config import load_config

    cfg = load_config("2025_club_world_cup")
    get_results(cfg)
