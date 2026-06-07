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
    """Extract participant name from the Excel filename.

    Uses ``os.path.basename`` so that splitting by ``name_split_char``
    operates only on the filename, not the full file path.
    """
    layout = config.excel_layout
    fname = os.path.basename(path)
    name_no_ext = fname.replace(".xlsx", "").replace(".xls", "").strip()
    parts = name_no_ext.split(layout.playoffs.name_split_char)
    name = parts[layout.playoffs.name_split_index].strip()
    return name


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
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m-%d")
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


def _slug(name: str) -> str:
    """Slugify a team name: lowercase, no spaces, no hyphens."""
    s = name.lower().strip()
    s = s.replace(" ", "_").replace("-", "_")
    return s


def parse_group_standings(path: str, config: ChampionshipConfig) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Parse group-standings Excel into bronze CSVs.

    Returns (df_predictions, df_bonus, df_striker).
    """
    who = _extract_who(path, config)
    df_raw = pd.read_excel(path, skiprows=config.standings_skiprows, header=None)

    # --- Parse group standings ---
    teams_data = _parse_standings_rows(df_raw)

    if not teams_data:
        raise ValueError(
            f"No group standings found in {path}. "
            "Expected a standings-format Excel with 'Grupo X' headers."
        )

    # --- Clear stale scores from group stage only (preserve playoff results) ---
    df_games = pd.read_csv(config.games_file, sep=",")
    group_mask = df_games["round"].astype(str).str.strip().isin(["1", "2", "3"])
    for col in ["home_goals", "away_goals", "home_pen", "away_pen"]:
        if col in df_games.columns:
            df_games.loc[group_mask, col] = None
    df_games.to_csv(config.games_file, sep=",", decimal=".", index=False)

    # --- Normalize round names ---
    _round_map = {
        "round of 32": "segunda_fase",
        "round of 16": "oitavas",
        "quarter finals": "quartas",
        "semi finals": "semi",
        "third place": "terceiro_lugar",
        "final": "final",
        "finals": "final",
    }
    df_games["round"] = df_games["round"].astype(str).str.strip().str.lower()
    df_games["round"] = df_games["round"].map(lambda r: _round_map.get(r, r))
    group_games = df_games[df_games["round"].isin(["1", "2", "3"])].copy()

    # --- Generate match predictions from standings ---
    team_strength = {}
    for t in teams_data:
        strength = t["pts"] / max(t["j"], 1) + t["sg"] * 0.1
        team_strength[t["team"]] = strength

    predictions = []
    for _, game in group_games.iterrows():
        home, away = game["home_team"], game["away_team"]
        s_h = team_strength.get(home, 1)
        s_a = team_strength.get(away, 1)
        if s_h > s_a + 0.5:
            pred_h, pred_a = 2, 0
        elif s_a > s_h + 0.5:
            pred_h, pred_a = 0, 1
        else:
            pred_h, pred_a = 1, 0
        raw_date = str(game["date"])
        if " " in raw_date and "h" in raw_date:
            pred_date = raw_date[:10]
            pred_hour = raw_date.split(" ")[1]
        else:
            pred_date = raw_date[:10]
            pred_hour = ""
        predictions.append({
            "date": pred_date,
            "hour": pred_hour,
            "home_team": home,
            "home_pen": "",
            "home_goals": float(pred_h),
            "x": "x",
            "away_goals": float(pred_a),
            "away_pen": "",
            "away_team": away,
            "who": who,
            "match": _slug(home) + "-vs-" + _slug(away),
        })
    df_pred = pd.DataFrame(predictions)

    # --- Parse bonus playoff picks and striker ---
    df_bonus, df_striker = _parse_playoffs_and_striker(path, who, config, df_raw)

    return df_pred, df_bonus, df_striker


def _parse_standings_rows(df_raw: pd.DataFrame) -> list[dict]:
    """Extract (group, team, pts, j, v, e, d, gp, gc, sg) from raw standings."""
    teams_data = []
    current_group = None
    for _, row in df_raw.iterrows():
        col0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        col1_str = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""

        if col1_str.startswith("Grupo"):
            current_group = col1_str
            continue
        if not current_group:
            continue
        if not col0 or col0 in ("Seleção", "nan", "NaN", ""):
            continue

        try:
            pts = int(float(row.iloc[1]))
        except (ValueError, TypeError):
            continue

        try:
            fields = [int(row.iloc[i]) if pd.notna(row.iloc[i]) else 0 for i in range(2, 9)]
        except (ValueError, TypeError):
            continue

        if fields[0] == 0 or all(f == 0 for f in fields):
            continue

        teams_data.append({
            "group": current_group,
            "team": col0,
            "pts": pts, "j": fields[0], "v": fields[1], "e": fields[2],
            "d": fields[3], "gp": fields[4], "gc": fields[5], "sg": fields[6],
        })

    # Deduplicate
    seen = set()
    unique = []
    for t in teams_data:
        if t["team"] not in seen:
            seen.add(t["team"])
            unique.append(t)
    return unique


def _parse_playoffs_and_striker(
    path: str, who: str, config: ChampionshipConfig, df_raw: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extract bonus playoff picks and striker name from the Excel.

    Reads the configured playoffs sheet (or falls back to df_raw), then
    scans for phase labels (e.g. "Oitavas", "Final") and the striker label
    (e.g. "Artilheiro") to locate the corresponding picks.
    """
    po_layout = config.excel_layout.playoffs

    # Use dedicated playoffs sheet if configured (e.g. "Tabela Jogos")
    if po_layout.playoffs_sheet_name:
        try:
            df_po = pd.read_excel(path, sheet_name=po_layout.playoffs_sheet_name, header=None)
        except Exception:
            df_po = df_raw
    else:
        df_po = df_raw

    phase_labels = {r.name: r.key for r in config.playoff_rounds}
    striker_label = po_layout.striker_label.lower().strip()
    nc, fc = po_layout.striker_name_column, po_layout.striker_name_fallback_column
    label_cols = list(range(min(9, len(df_po.columns) if not df_po.empty else 9)))

    bonus_rows = []
    current_phase = None
    striker_name = ""
    skip_next = False

    for idx in range(len(df_po)):
        if skip_next:
            skip_next = False
            continue

        row = df_po.iloc[idx]
        col0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        col1 = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        col2 = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
        col8 = str(row.iloc[8]).strip() if len(row) > 8 and pd.notna(row.iloc[8]) else ""

        # Phase label
        phase_key = phase_labels.get(col0) or phase_labels.get(col1)
        if phase_key:
            current_phase = phase_key
            continue

        # Striker label
        striker_col = _find_label_col(row, striker_label, label_cols)
        if striker_col >= 0:
            striker_name = _extract_striker_name(row, df_po, idx, striker_col, striker_label, nc, fc, label_cols)
            if striker_name:
                skip_next = True
            current_phase = None
            continue

        # Team pick — both home (col2) and away (col8) are bonus picks for this phase
        if current_phase and col2 and col2 not in ("", "nan", "NaN"):
            bonus_rows.append({"boleiro": who, "phase": current_phase, "team": col2})
        if current_phase and col8 and col8 not in ("", "nan", "NaN") and col8 != col2:
            bonus_rows.append({"boleiro": who, "phase": current_phase, "team": col8})

    df_bonus = pd.DataFrame(bonus_rows, columns=["boleiro", "phase", "team"])
    df_striker = pd.DataFrame([{"boleiro": who, "striker": striker_name}])
    return df_bonus, df_striker


def _find_label_col(row: pd.Series, label: str, label_cols: list[int]) -> int:
    """Return the column index where *label* is found (case-insensitive), else -1.

    Matches exact label or ``label + space`` prefix (e.g. "artilheiro do mundial"
    matches label "artilheiro").
    """
    for c in label_cols:
        val = str(row.iloc[c]).strip().lower() if pd.notna(row.iloc[c]) else ""
        normalised = val.rstrip(":.").strip()
        if normalised == label or normalised.startswith(label + " "):
            return c
    return -1


def _extract_striker_name(
    row: pd.Series,
    df_po: pd.DataFrame,
    idx: int,
    striker_col: int,
    label: str,
    nc: int,
    fc: int,
    label_cols: list[int],
) -> str:
    """Extract the striker name from a row where the label was found.

    Priority: dedicated name column → same cell after colon/label →
    other columns on same row → next row.
    """
    # 1) Dedicated name columns (most reliable for structured sheets)
    for c in [nc, fc]:
        val = str(row.iloc[c]).strip() if pd.notna(row.iloc[c]) else ""
        if val and val.lower() not in ("", "nan", "none", label):
            return val

    # 2) Same cell after colon ("Artilheiro: Nome")
    cell_val = str(row.iloc[striker_col]).strip() if pd.notna(row.iloc[striker_col]) else ""
    if ":" in cell_val:
        return cell_val.split(":", 1)[-1].strip()

    # 3) Same cell after label text ("Artilheiro Nome")
    name_part = cell_val[len(label):].strip().lstrip(":- ")
    if name_part:
        return name_part

    # 4) Other columns on same row
    for c in [x for x in label_cols if x not in (nc, fc)]:
        val = str(row.iloc[c]).strip() if pd.notna(row.iloc[c]) else ""
        if val and val.lower() not in ("", "nan", "none", label):
            return val

    # 5) Next row
    if idx + 1 < len(df_po):
        next_row = df_po.iloc[idx + 1]
        for c in [nc, fc] + label_cols:
            val = str(next_row.iloc[c]).strip() if pd.notna(next_row.iloc[c]) else ""
            if val and val.lower() not in ("", "nan", "none", label):
                return val

    return ""


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
