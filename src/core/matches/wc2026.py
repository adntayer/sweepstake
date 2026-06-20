# uv run src\core\matches\wc2026.py
import os
import re
import time
import unicodedata
from datetime import datetime

import pandas as pd
import requests
import urllib3
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def normalizar_slug(texto):
    """Cria slug compatível com o formato interno do bolão.

    Remove acentos, converte para minúsculas e substitui
    espaços/pontuação por sublinhados — compatível com a
    função ``_slug`` do loader e com o formato histórico de
    ``games.csv`` (ex.: ``mexico-vs-africa_do_sul``).
    Devolve string vazia para entradas nulas ou não-string (ex.: NaN).
    """
    if not isinstance(texto, str) or not texto:
        return ""
    s = unicodedata.normalize("NFKD", texto)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _load_config_mapping():
    """Load the {API_en: pt} mapping from the 2026 World Cup config YAML.

    The config's ``en`` keys are now aligned with the API's
    ``home_team_name_en`` / ``away_team_name_en`` values.
    """
    config_path = "src/championships/2026_world_cup/config.yaml"
    with open(config_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    mapping = {}
    for entry in raw.get("team_name_mapping", []):
        en = entry.get("en", "").strip()
        pt = entry.get("pt", "").strip()
        if en and pt:
            mapping[en] = pt
    return mapping


# Type → round label mapping for non-group matches
_TYPE_TO_ROUND = {
    "round_of_32": "segunda_fase",
    "round_of_16": "oitavas",
    "quarterfinal": "quartas",
    "quarter_final": "quartas",
    "semifinal": "semi",
    "semi_final": "semi",
    "third_place": "terceiro_lugar",
    "final": "final",
}


def _assign_group_rounds(df):
    """Assign round number (1, 2, 3) to group games.

    For each team in the group stage, counts its appearances in
    chronological order.  Every team plays exactly 3 group games,
    so the count per team directly gives the round.
    """
    group_idx = df.index[df["type"] == "group"].tolist()
    if not group_idx:
        return

    # Build an ordered list of all team appearances in group games
    records = []
    for idx in group_idx:
        row = df.loc[idx]
        records.append({"sort_key": row["date"], "game_idx": idx, "team": row["home_team"]})
        records.append({"sort_key": row["date"], "game_idx": idx, "team": row["away_team"]})

    appearances = pd.DataFrame(records).sort_values(["team", "sort_key"])
    appearances["round"] = appearances.groupby("team").cumcount() + 1  # 1, 2, 3

    # Each game's round is the round of either team (they should agree).
    # Pick the home team's round as authoritative.
    home_appearances = (
        appearances.drop_duplicates(subset="game_idx", keep="first")
        .set_index("game_idx")["round"]
    )
    for idx, rnd in home_appearances.items():
        df.at[idx, "round"] = rnd


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _fetch_games_json(headers: dict) -> dict:
    """Fetch games JSON with retry (5 attempts), exponential backoff, and SSL fallback."""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))

    for attempt in range(5):
        try:
            kwargs = dict(headers=headers, timeout=(10, 30))
            if attempt >= 1:
                kwargs["verify"] = False
            res = session.get("https://worldcup26.ir/get/games", **kwargs)
            res.raise_for_status()
            return res.json()
        except requests.exceptions.RequestException:
            if attempt < 4:
                wait = 2 ** attempt
                print(f"  ⚠️  tentativa {attempt + 1}/5 falhou, tentando novamente em {wait}s...")
                time.sleep(wait)
    raise


def build_world_cup_csv(games_file: str | None = None):
    """Fetch games from the API, normalise, and return a DataFrame.

    Parameters
    ----------
    games_file : str, optional
        Path to write the CSV.  Defaults to
        ``src/championships/2026_world_cup/data/games.csv``.

    Returns a DataFrame with columns matching the internal games.csv
    format plus ``time_elapsed``, or ``None`` on failure.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }

        # ---- team name translation map (API en → Portuguese) ----
        api_en_to_pt = _load_config_mapping()

        # ---- fetch games with retry + SSL fallback ----
        games_json = _fetch_games_json(headers)
        games_list = games_json.get("games") or games_json.get("matches")
        df = pd.DataFrame(games_list)

        # ---- translate team names ----
        df["home_team"] = df["home_team_name_en"].map(api_en_to_pt).fillna(df["home_team_name_en"])
        df["away_team"] = df["away_team_name_en"].map(api_en_to_pt).fillna(df["away_team_name_en"])

        # ---- date: "06/11/2026 13:00" → "2026-06-11 13h" ----
        df["date"] = df["local_date"].apply(
            lambda x: datetime.strptime(str(x).strip(), "%m/%d/%Y %H:%M").strftime("%Y-%m-%d %Hh")
        )

        # ---- goals ----
        df["home_goals"] = pd.to_numeric(df["home_score"], errors="coerce").astype("Int64")
        df["away_goals"] = pd.to_numeric(df["away_score"], errors="coerce").astype("Int64")

        # ---- penalties (always empty — API doesn't provide this) ----
        df["home_pen"] = ""
        df["away_pen"] = ""

        df["x"] = "x"

        # ---- match slug ----
        df["match"] = df.apply(
            lambda r: f"{normalizar_slug(r['home_team'])}-vs-{normalizar_slug(r['away_team'])}",
            axis=1,
        )

        # ---- round ----
        df["round"] = None  # placeholder

        # Group games: compute round 1/2/3 from team appearance order
        _assign_group_rounds(df)

        # Non-group games: map type to round label
        non_group = df["type"] != "group"
        df.loc[non_group, "round"] = df.loc[non_group, "type"].map(_TYPE_TO_ROUND).fillna(df.loc[non_group, "type"])

        # ---- time_elapsed ----
        df["time_elapsed"] = df.get("time_elapsed", "").fillna("")

        # Nullify scores for matches that haven't started yet
        not_started = df["time_elapsed"] == "notstarted"
        df.loc[not_started, "home_goals"] = pd.NA
        df.loc[not_started, "away_goals"] = pd.NA

        # ---- sort ----
        df = df.sort_values("date").reset_index(drop=True)

        # ---- select output columns ----
        colunas_finais = [
            "date",
            "round",
            "home_team",
            "home_pen",
            "home_goals",
            "x",
            "away_goals",
            "away_pen",
            "away_team",
            "match",
            "time_elapsed",
        ]
        df_out = df[colunas_finais]

        # ---- save CSV (side effect so pipeline calls also persist) ----
        output_path = games_file or "src/championships/2026_world_cup/data/games.csv"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_out.to_csv(output_path, index=False)

        return df_out

    except Exception as e:
        print(f"❌ Erro ao processar parser: {e}")
        return None


if __name__ == "__main__":
    for attempt in range(5):
        df_resultado = build_world_cup_csv()
        if df_resultado is not None:
            print(f"✅ {len(df_resultado)} jogos salvos")
            break
        if attempt < 4:
            wait = 2 ** attempt
            print(f"  ⚠️  tentativa {attempt + 1}/5 falhou, tentando novamente em {wait}s...")
            time.sleep(wait)
    else:
        print("❌ Erro ao processar parser")
