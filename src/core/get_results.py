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
from src.core.printing import print_colored


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


def _parse_date(raw: str, date_format: str = "%d/%m/%Y %H:%M") -> str:
    """Convert date string → 'YYYY-MM-DD HHh'.

    Uses ``date_format`` for parsing (default ``%%d/%%m/%%Y %%H:%%M``).
    Returns empty string for missing or unparseable dates.
    """
    if not raw or not str(raw).strip():
        return ""
    try:
        dt = pd.to_datetime(raw, format=date_format)
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


_DEFAULT_ROUND_MAP = {
    "Round of 32": "segunda_fase",
    "Round of 16": "oitavas",
    "Quarter Finals": "quartas",
    "Semi Finals": "semi",
    "Third Place": "terceiro_lugar",
    "Final": "final",
    "Finals": "final",
}


def _parse_round(raw, round_map: dict[str, str] | None = None) -> str:
    """Map Round Number to internal phase key.

    Group rounds (1, 2, 3) stay as integers.
    Knockout rounds are translated via ``round_map``.
    Falls back to ``_DEFAULT_ROUND_MAP`` if not provided.
    """
    val = str(raw).strip()
    mapping = round_map or _DEFAULT_ROUND_MAP
    if val in mapping:
        return mapping[val]
    return val


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def get_results(config: ChampionshipConfig) -> None:
    """Download official results, translate team names, and save games.csv.

    The output format matches the internal convention expected by the
    bronze→silver pipeline:
        date, home_team, home_pen, home_goals, x, away_goals, away_pen, away_team, match

    If the download fails and a games.csv already exists, the existing
    file is reused so the pipeline does not break before the tournament
    starts or when the remote endpoint is unreachable.
    """
    url = config.results_endpoint
    if not url:
        raise ValueError("results_endpoint not configured")

    # Fetch raw CSV
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
    except Exception as e:
        if os.path.exists(config.games_file):
            print_colored(
                f"Warning: could not download results ({e}), "
                f"using existing {config.games_file}",
                "yellow",
            )
            return
        print_colored(f"Error: could not download results and no existing file: {e}", "red")
        raise

    # Determine CSV column names (from config or fixturedownload defaults)
    cc = config.csv_columns or {}
    col_match = cc.get("match_number", "Match Number")
    col_round = cc.get("round_number", "Round Number")
    col_date = cc.get("date", "Date")
    col_location = cc.get("location", "Location")
    col_home = cc.get("home_team", "Home Team")
    col_away = cc.get("away_team", "Away Team")
    col_group = cc.get("group", "Group")
    col_result = cc.get("result", "Result")

    df = pd.read_csv(
        StringIO(response.text),
        skipinitialspace=True,
    )

    # Translate team names
    mapping = config.team_name_mapping
    df["home_team"] = df[col_home].apply(lambda n: _translate(str(n), mapping))
    df["away_team"] = df[col_away].apply(lambda n: _translate(str(n), mapping))

    # Parse date and result
    df["date"] = df[col_date].apply(lambda d: _parse_date(str(d), config.csv_date_format))
    df[["home_goals", "away_goals"]] = df[col_result].apply(
        lambda r: pd.Series(_parse_result(str(r)))
    )

    # Build match slug from translated names
    df["match"] = df["home_team"].apply(_slug) + "-vs-" + df["away_team"].apply(_slug)

    # Map round numbers/names to internal phase keys
    round_map = config.external_round_mapping or None
    df["round"] = df[col_round].apply(lambda r: _parse_round(r, round_map))

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
