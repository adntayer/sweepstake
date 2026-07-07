"""Data Vault 2.0 for Sweepstake — Silver layer + Gold OBTs.

Architecture:
  Bronze (CSV imutável)
      → Silver (Data Vault Parquet: hubs / links / satellites)
      → Gold (OBTs Parquet: one big tables com scoring pré-computado)

Classic Data Vault columns:
  Hubs:      {hub}_hk (PK), {business_key}, load_date, record_source
  Links:     {link}_hk (PK), {hub1}_hk (FK), {hub2}_hk (FK), load_date, record_source
  Satellites: {parent}_hk (FK), load_date (PK), hash_diff, record_source, attributes...

  OBTs:      Flat, denormalized, scored, ready for consumption.
             Zero on-the-fly calculation in the backend.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from glob import glob
from typing import Any

import numpy as np
import pandas as pd

from src.core.config import ChampionshipConfig
from src.core.printing import print_colored

# ------------------------------------------------------------------
# Hash utilities
# ------------------------------------------------------------------


def dv_hash(*values: str) -> str:
    """Deterministic MD5 hash (32 hex chars) from one or more values.

    Uses ``|`` separator to avoid collisions between
    ``("ab", "c")`` and ``("a", "bc")``.
    """
    combined = "|".join(str(v) for v in values)
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


def _now() -> str:
    """Current UTC timestamp string for load_date columns."""
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Classic Data Vault base builders
# ------------------------------------------------------------------


def _hub_base(
    business_keys: list[str],
    hub_name: str,
    bk_col: str,
    record_source: str = "BRONZE_CSV",
) -> pd.DataFrame:
    """Create a classic Hub DataFrame.

    Columns:
        ``{hub_name}_hk`` — hash key (PK)
        ``{bk_col}`` — business key
        ``load_date`` — when loaded
        ``record_source`` — source system identification
    """
    if not business_keys:
        return pd.DataFrame(
            columns=[f"{hub_name}_hk", bk_col, "load_date", "record_source"],
        )
    dedup = sorted(set(business_keys))
    return pd.DataFrame(
        {
            f"{hub_name}_hk": [dv_hash(k) for k in dedup],
            bk_col: dedup,
            "load_date": _now(),
            "record_source": record_source,
        },
    )


def _link_base(
    rows: list[dict[str, Any]],
    link_name: str,
    hk_cols: list[str],
    attr_cols: list[str] | None = None,
) -> pd.DataFrame:
    """Create a classic Link DataFrame.

    The link hash key (``{link_name}_hk``) is computed from all hub FK columns.

    Args:
        rows: list of dicts with hub FK values + optional attributes.
        link_name: link entity name.
        hk_cols: column names that form the hub FK set.
        attr_cols: additional attribute columns (e.g. source_file).

    Returns:
        DataFrame with ``{link_name}_hk``, hub FKs, ``load_date``, ``record_source``.
    """
    if not rows:
        all_cols = [f"{link_name}_hk"] + hk_cols + ["load_date", "record_source"]
        if attr_cols:
            all_cols += attr_cols
        return pd.DataFrame(columns=all_cols)

    for row in rows:
        hk_values = [str(row.get(c, "")) for c in hk_cols]
        row[f"{link_name}_hk"] = dv_hash(*hk_values)
        if "load_date" not in row:
            row["load_date"] = _now()
        if "record_source" not in row:
            row["record_source"] = "BRONZE_CSV"

    all_cols = [f"{link_name}_hk"] + hk_cols + ["load_date", "record_source"]
    if attr_cols:
        all_cols += [c for c in attr_cols if c not in all_cols]

    return pd.DataFrame(rows, columns=all_cols)


def _sat_base(
    rows: list[dict[str, Any]],
    parent_hk_col: str,
    sat_name: str,
    exclude_from_hash: list[str] | None = None,
) -> pd.DataFrame:
    """Create a classic Satellite DataFrame.

    Columns:
        ``{parent_hk_col}`` — FK to parent hub/link
        ``load_date`` — PK component
        ``hash_diff`` — MD5 of all descriptive columns (change detection)
        ``record_source`` — source system
        ...attributes

    Args:
        rows: list of dicts with attribute values.
        parent_hk_col: name of the parent hash key column.
        sat_name: satellite name (for logging).
        exclude_from_hash: columns to exclude from hash_diff computation.
    """
    if not rows:
        base = [parent_hk_col, "load_date", "hash_diff", "record_source"]
        return pd.DataFrame(columns=base)

    excl = set(exclude_from_hash or []) | {parent_hk_col, "load_date", "record_source"}
    for row in rows:
        if "load_date" not in row:
            row["load_date"] = _now()
        if "record_source" not in row:
            row["record_source"] = "BRONZE_CSV"
        # Compute hash_diff from all descriptive columns
        desc_keys = [k for k in sorted(row.keys()) if k not in excl]
        desc_vals = [str(row.get(k, "")) for k in desc_keys]
        row["hash_diff"] = dv_hash(*desc_vals) if desc_vals else dv_hash("empty")

    all_cols = [parent_hk_col, "load_date", "hash_diff", "record_source"]
    # Add remaining columns in sorted order
    extra = sorted([c for c in rows[0].keys() if c not in set(all_cols)])
    all_cols += extra
    return pd.DataFrame(rows, columns=all_cols)


# ------------------------------------------------------------------
# Internal helpers — scan bronze data
# ------------------------------------------------------------------


def _scan_bronze_group_paths(config: ChampionshipConfig) -> list[str]:
    """Return sorted list of bronze group_phase_*.csv paths."""
    pattern = os.path.normpath(
        os.path.join(config._br_first_round(), "group_phase_*.csv")
    )
    return sorted(glob(pattern))


def _scan_bronze_bonus_paths(config: ChampionshipConfig) -> list[str]:
    """Return sorted list of bronze bonus_teams_*.csv paths."""
    pattern = os.path.normpath(
        os.path.join(config._br_first_round(), "bonus_teams_*.csv")
    )
    return sorted(glob(pattern))


def _scan_bronze_striker_paths(config: ChampionshipConfig) -> list[str]:
    """Return sorted list of bronze striker_*.csv paths."""
    pattern = os.path.normpath(
        os.path.join(config._br_first_round(), "striker_*.csv")
    )
    return sorted(glob(pattern))


def _load_results(config: ChampionshipConfig) -> pd.DataFrame:
    """Load games.csv and normalize columns."""
    df = pd.read_csv(config.games_file, sep=",")
    if "round" in df.columns:
        df["round"] = df["round"].astype(str).str.strip().str.lower()
    return df


# ------------------------------------------------------------------
# Hub builders — classic DV columns: {hub}_hk, {bk}, load_date, record_source
# ------------------------------------------------------------------


def build_hub_jogador(config: ChampionshipConfig) -> pd.DataFrame:
    """Build Hub Jogador — business key: ``boleiro_name``."""
    names: set[str] = set()
    for p in _scan_bronze_group_paths(config):
        df = pd.read_csv(p, sep=",")
        if "who" in df.columns:
            names.update(df["who"].dropna().unique())
    for p in _scan_bronze_bonus_paths(config):
        df = pd.read_csv(p, sep=",")
        if "boleiro" in df.columns:
            names.update(df["boleiro"].dropna().unique())
    for p in _scan_bronze_striker_paths(config):
        df = pd.read_csv(p, sep=",")
        if "boleiro" in df.columns:
            names.update(df["boleiro"].dropna().unique())
    names.update(config.boleiros.keys())

    df_out = _hub_base(list(names), "jogador", "boleiro_name", "BRONZE_CSV+CONFIG")
    print_colored(f"\thub_jogador: {len(df_out)} registros", "ice")
    return df_out


def build_hub_partida(config: ChampionshipConfig) -> pd.DataFrame:
    """Build Hub Partida — business key: ``match_slug``."""
    slugs: set[str] = set()
    for p in _scan_bronze_group_paths(config):
        df = pd.read_csv(p, sep=",")
        if "match" in df.columns:
            slugs.update(df["match"].dropna().unique())
    df_results = _load_results(config)
    if "match" in df_results.columns:
        slugs.update(df_results["match"].dropna().unique())
    df_out = _hub_base(list(slugs), "partida", "match_slug", "GAMES_CSV+BRONZE")
    print_colored(f"\thub_partida: {len(df_out)} registros", "ice")
    return df_out


def build_hub_time(config: ChampionshipConfig) -> pd.DataFrame:
    """Build Hub Time — business key: ``team_name`` (Portuguese)."""
    names: set[str] = set()
    for p in _scan_bronze_group_paths(config):
        df = pd.read_csv(p, sep=",")
        for col in ("home_team", "away_team"):
            if col in df.columns:
                names.update(df[col].dropna().unique())
    for pt_name in config.team_name_mapping.values():
        if pt_name:
            names.add(pt_name)
    for grp in config.groups:
        for t in grp.get("teams", []):
            if t:
                names.add(t)
    df_results = _load_results(config)
    for col in ("home_team", "away_team"):
        if col in df_results.columns:
            names.update(df_results[col].dropna().unique())
    df_out = _hub_base(list(names), "time", "team_name", "CONFIG+GAMES_CSV+BRONZE")
    print_colored(f"\thub_time: {len(df_out)} registros", "ice")
    return df_out


def build_hub_fase(config: ChampionshipConfig) -> pd.DataFrame:
    """Build Hub Fase — business key: ``phase_key``."""
    keys: set[str] = set()
    keys.add(config.group_phase_label)
    for pr in config.playoff_rounds:
        keys.add(pr.key)
    keys.add(config.champion_phase_key)
    for p in _scan_bronze_bonus_paths(config):
        df = pd.read_csv(p, sep=",")
        if "phase" in df.columns:
            keys.update(df["phase"].dropna().unique())
    df_out = _hub_base(list(keys), "fase", "phase_key", "CONFIG+BRONZE")
    print_colored(f"\thub_fase: {len(df_out)} registros", "ice")
    return df_out


def build_hub_campeonato(config: ChampionshipConfig) -> pd.DataFrame:
    """Build Hub Campeonato — business key: ``championship_id``."""
    df_out = _hub_base([config.id], "campeonato", "championship_id", "CONFIG")
    print_colored(f"\thub_campeonato: {config.id}", "ice")
    return df_out


def build_all_hubs(config: ChampionshipConfig) -> dict[str, pd.DataFrame]:
    """Build all 5 hubs and return as dict keyed by hub name."""
    hubs: dict[str, pd.DataFrame] = {}
    hubs["jogador"] = build_hub_jogador(config)
    hubs["partida"] = build_hub_partida(config)
    hubs["time"] = build_hub_time(config)
    hubs["fase"] = build_hub_fase(config)
    hubs["campeonato"] = build_hub_campeonato(config)
    return hubs


# ------------------------------------------------------------------
# Link builders — classic DV columns: {link}_hk, hub FKs, load_date, record_source
# ------------------------------------------------------------------


def build_link_palpite(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build Link Palpite — relationship Jogador → Partida."""
    jogador_map = dict(
        zip(hubs["jogador"]["boleiro_name"], hubs["jogador"]["jogador_hk"])
    )
    partida_map = dict(
        zip(hubs["partida"]["match_slug"], hubs["partida"]["partida_hk"])
    )

    rows: list[dict[str, Any]] = []
    for p in _scan_bronze_group_paths(config):
        df = pd.read_csv(p, sep=",")
        source = os.path.basename(p)
        for _, row in df.iterrows():
            who = str(row.get("who", "")).strip()
            match = str(row.get("match", "")).strip()
            jhk = jogador_map.get(who)
            phk = partida_map.get(match)
            if jhk and phk:
                rows.append({
                    "jogador_hk": jhk,
                    "partida_hk": phk,
                    "record_source": f"BRONZE:{source}",
                })

    df_out = _link_base(rows, "palpite", ["jogador_hk", "partida_hk"])
    print_colored(f"\tlink_palpite: {len(df_out)} registros", "ice")
    return df_out


def build_link_partida_times(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build Link Partida Times — relationship Partida → Home Team + Away Team."""
    partida_map = dict(
        zip(hubs["partida"]["match_slug"], hubs["partida"]["partida_hk"])
    )
    time_map = dict(zip(hubs["time"]["team_name"], hubs["time"]["time_hk"]))

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []

    df_results = _load_results(config)
    for _, row in df_results.iterrows():
        match = str(row.get("match", "")).strip()
        home = str(row.get("home_team", "")).strip()
        away = str(row.get("away_team", "")).strip()
        if not match or not home or not away:
            continue
        phk = partida_map.get(match)
        hhk = time_map.get(home)
        ahk = time_map.get(away)
        if phk and hhk and ahk:
            key = dv_hash(phk, hhk, ahk)
            if key not in seen:
                seen.add(key)
                rows.append({
                    "partida_hk": phk,
                    "time_home_hk": hhk,
                    "time_away_hk": ahk,
                    "record_source": "GAMES_CSV",
                })

    # Also from bronze predictions for match-teams not in games.csv
    for p in _scan_bronze_group_paths(config):
        df = pd.read_csv(p, sep=",")
        source = os.path.basename(p)
        for _, row in df.iterrows():
            match = str(row.get("match", "")).strip()
            home = str(row.get("home_team", "")).strip()
            away = str(row.get("away_team", "")).strip()
            if not match or not home or not away:
                continue
            phk = partida_map.get(match)
            hhk = time_map.get(home)
            ahk = time_map.get(away)
            if phk and hhk and ahk:
                key = dv_hash(phk, hhk, ahk)
                if key not in seen:
                    seen.add(key)
                    rows.append({
                        "partida_hk": phk,
                        "time_home_hk": hhk,
                        "time_away_hk": ahk,
                        "record_source": f"BRONZE:{source}",
                    })

    df_out = _link_base(
        rows, "partida_times",
        ["partida_hk", "time_home_hk", "time_away_hk"],
    )
    print_colored(f"\tlink_partida_times: {len(df_out)} registros", "ice")
    return df_out


def build_link_bonus_time(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build Link Bonus Time — relationship Jogador → Fase → Time."""
    jogador_map = dict(
        zip(hubs["jogador"]["boleiro_name"], hubs["jogador"]["jogador_hk"])
    )
    fase_map = dict(zip(hubs["fase"]["phase_key"], hubs["fase"]["fase_hk"]))
    time_map = dict(zip(hubs["time"]["team_name"], hubs["time"]["time_hk"]))

    rows: list[dict[str, Any]] = []
    for p in _scan_bronze_bonus_paths(config):
        df = pd.read_csv(p, sep=",")
        source = os.path.basename(p)
        for _, row in df.iterrows():
            boleiro = str(row.get("boleiro", "")).strip()
            phase = str(row.get("phase", "")).strip()
            team = str(row.get("team", "")).strip()
            jhk = jogador_map.get(boleiro)
            fhk = fase_map.get(phase)
            thk = time_map.get(team)
            if jhk and fhk and thk:
                rows.append({
                    "jogador_hk": jhk,
                    "fase_hk": fhk,
                    "time_hk": thk,
                    "record_source": f"BRONZE:{source}",
                })

    df_out = _link_base(
        rows, "bonus_time",
        ["jogador_hk", "fase_hk", "time_hk"],
    )
    print_colored(f"\tlink_bonus_time: {len(df_out)} registros", "ice")
    return df_out


def build_link_artilheiro(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build Link Artilheiro — relationship Jogador → Striker (degenerate)."""
    jogador_map = dict(
        zip(hubs["jogador"]["boleiro_name"], hubs["jogador"]["jogador_hk"])
    )

    rows: list[dict[str, Any]] = []
    for p in _scan_bronze_striker_paths(config):
        df = pd.read_csv(p, sep=",")
        source = os.path.basename(p)
        for _, row in df.iterrows():
            boleiro = str(row.get("boleiro", "")).strip()
            striker = str(row.get("striker", "")).strip()
            jhk = jogador_map.get(boleiro)
            if jhk and striker:
                rows.append({
                    "jogador_hk": jhk,
                    "striker_name": striker,
                    "record_source": f"BRONZE:{source}",
                })

    df_out = _link_base(
        rows, "artilheiro",
        ["jogador_hk", "striker_name"],
        attr_cols=["striker_name"],
    )
    print_colored(f"\tlink_artilheiro: {len(df_out)} registros", "ice")
    return df_out


def build_all_links(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Build all 4 links and return as dict."""
    links: dict[str, pd.DataFrame] = {}
    links["palpite"] = build_link_palpite(config, hubs)
    links["partida_times"] = build_link_partida_times(config, hubs)
    links["bonus_time"] = build_link_bonus_time(config, hubs)
    links["artilheiro"] = build_link_artilheiro(config, hubs)
    return links


# ------------------------------------------------------------------
# Satellite builders — classic DV columns: parent_hk, load_date, hash_diff, record_source
# ------------------------------------------------------------------


def build_sat_palpite(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
    links: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build Sat Palpite — prediction details attached to Link Palpite."""
    link_df = links["palpite"]
    if link_df.empty:
        return pd.DataFrame(columns=[
            "palpite_hk", "load_date", "hash_diff", "record_source",
            "home_goals_pred", "away_goals_pred",
            "home_pen_pred", "away_pen_pred", "date_pred", "hour_pred",
        ])

    # Build (jogador_hk, partida_hk) → palpite_hk lookup
    palpite_map: dict[tuple[str, str], str] = {}
    for _, r in link_df.iterrows():
        palpite_map[(r["jogador_hk"], r["partida_hk"])] = r["palpite_hk"]

    jogador_map = dict(
        zip(hubs["jogador"]["boleiro_name"], hubs["jogador"]["jogador_hk"])
    )
    partida_map = dict(
        zip(hubs["partida"]["match_slug"], hubs["partida"]["partida_hk"])
    )

    rows: list[dict[str, Any]] = []
    for p in _scan_bronze_group_paths(config):
        df = pd.read_csv(p, sep=",")
        source = os.path.basename(p)
        for _, row in df.iterrows():
            who = str(row.get("who", "")).strip()
            match = str(row.get("match", "")).strip()
            jhk = jogador_map.get(who)
            phk = partida_map.get(match)
            if not jhk or not phk:
                continue
            lhk = palpite_map.get((jhk, phk))
            if not lhk:
                continue
            rows.append({
                "palpite_hk": lhk,
                "home_goals_pred": row.get("home_goals"),
                "away_goals_pred": row.get("away_goals"),
                "home_pen_pred": row.get("home_pen"),
                "away_pen_pred": row.get("away_pen"),
                "date_pred": row.get("date"),
                "hour_pred": row.get("hour"),
                "record_source": f"BRONZE:{source}",
            })

    df_out = _sat_base(rows, "palpite_hk", "sat_palpite",
                       exclude_from_hash=["palpite_hk", "load_date", "record_source"])
    for col in ["home_goals_pred", "away_goals_pred", "home_pen_pred", "away_pen_pred"]:
        if col in df_out.columns:
            df_out[col] = pd.to_numeric(df_out[col], errors="coerce")
    print_colored(f"\tsat_palpite: {len(df_out)} registros", "ice")
    return df_out


def build_sat_partida(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build Sat Partida — match results/details attached to Hub Partida."""
    partida_map = dict(
        zip(hubs["partida"]["match_slug"], hubs["partida"]["partida_hk"])
    )

    df_results = _load_results(config)
    rows: list[dict[str, Any]] = []
    for _, row in df_results.iterrows():
        match = str(row.get("match", "")).strip()
        phk = partida_map.get(match)
        if not phk:
            continue
        rows.append({
            "partida_hk": phk,
            "date_real": row.get("date"),
            "hour_real": row.get("hour"),
            "home_goals_real": row.get("home_goals"),
            "away_goals_real": row.get("away_goals"),
            "home_pen_real": row.get("home_pen"),
            "away_pen_real": row.get("away_pen"),
            "round": row.get("round"),
            "time_elapsed": row.get("time_elapsed"),
            "record_source": f"GAMES_CSV:{os.path.basename(config.games_file)}",
        })

    df_out = _sat_base(rows, "partida_hk", "sat_partida",
                       exclude_from_hash=["partida_hk", "load_date", "record_source"])
    for col in ["home_goals_real", "away_goals_real", "home_pen_real", "away_pen_real"]:
        if col in df_out.columns:
            df_out[col] = pd.to_numeric(df_out[col], errors="coerce")
    print_colored(f"\tsat_partida: {len(df_out)} registros", "ice")
    return df_out


def build_sat_jogador(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build Sat Jogador — player penalties/config attached to Hub Jogador."""
    jogador_map = dict(
        zip(hubs["jogador"]["boleiro_name"], hubs["jogador"]["jogador_hk"])
    )

    rows: list[dict[str, Any]] = []
    for name, bcfg in config.boleiros.items():
        jhk = jogador_map.get(name)
        if not jhk:
            continue
        rows.append({
            "jogador_hk": jhk,
            "total_penalty": bcfg.total_penalty,
            "penalties_json": json.dumps([
                {"value": p.value, "reason": p.reason, "phase": p.phase}
                for p in bcfg.penalties
            ]),
            "record_source": "CONFIG",
        })

    df_out = _sat_base(rows, "jogador_hk", "sat_jogador",
                       exclude_from_hash=["jogador_hk", "load_date", "record_source"])
    print_colored(f"\tsat_jogador: {len(df_out)} registros", "ice")
    return df_out


def build_sat_time(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build Sat Time — team metadata attached to Hub Time."""
    time_map = dict(zip(hubs["time"]["team_name"], hubs["time"]["time_hk"]))

    # Build reverse mapping: Portuguese name → (en, slug, logo, geo)
    team_meta: dict[str, dict[str, str]] = {}
    for en_name, pt_name in config.team_name_mapping.items():
        team_meta[pt_name] = {
            "team_name_en": en_name,
            "slug": config.team_slugs.get(en_name, ""),
            "logo_url": config.team_logos.get(en_name, ""),
            "geo_continent": config.team_geo.get(pt_name, ""),
        }

    rows: list[dict[str, Any]] = []
    for team_name, thk in time_map.items():
        meta = team_meta.get(team_name, {})
        rows.append({
            "time_hk": thk,
            "slug": meta.get("slug", ""),
            "logo_url": meta.get("logo_url", ""),
            "geo_continent": meta.get("geo_continent", ""),
            "team_name_en": meta.get("team_name_en", ""),
            "record_source": "CONFIG",
        })

    df_out = _sat_base(rows, "time_hk", "sat_time",
                       exclude_from_hash=["time_hk", "load_date", "record_source"])
    print_colored(f"\tsat_time: {len(df_out)} registros", "ice")
    return df_out


def build_sat_fase(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build Sat Fase — phase metadata attached to Hub Fase."""
    fase_map = dict(zip(hubs["fase"]["phase_key"], hubs["fase"]["fase_hk"]))

    phase_info: dict[str, dict[str, Any]] = {
        config.group_phase_label: {
            "name_display": config.group_phase_label,
            "matches": 0,
            "points_per_correct": None,
        },
        config.champion_phase_key: {
            "name_display": "Campeão",
            "matches": 0,
            "points_per_correct": config.playoff_scoring.get(config.champion_phase_key, 0),
        },
    }
    for pr in config.playoff_rounds:
        phase_info[pr.key] = {
            "name_display": pr.name,
            "matches": pr.matches,
            "points_per_correct": config.playoff_scoring.get(pr.key, 0),
        }

    rows: list[dict[str, Any]] = []
    for phase_key, fhk in fase_map.items():
        info = phase_info.get(phase_key, {})
        rows.append({
            "fase_hk": fhk,
            "name_display": info.get("name_display", phase_key),
            "matches": info.get("matches", 0),
            "points_per_correct": info.get("points_per_correct"),
            "record_source": "CONFIG",
        })

    df_out = _sat_base(rows, "fase_hk", "sat_fase",
                       exclude_from_hash=["fase_hk", "load_date", "record_source"])
    print_colored(f"\tsat_fase: {len(df_out)} registros", "ice")
    return df_out


def build_all_satellites(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
    links: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Build all satellites and return as dict."""
    sats: dict[str, pd.DataFrame] = {}
    sats["palpite"] = build_sat_palpite(config, hubs, links)
    sats["partida"] = build_sat_partida(config, hubs)
    sats["jogador"] = build_sat_jogador(config, hubs)
    sats["time"] = build_sat_time(config, hubs)
    sats["fase"] = build_sat_fase(config, hubs)
    return sats


# ------------------------------------------------------------------
# Save / Load helpers for DV parquet
# ------------------------------------------------------------------


def _dv_dir(config: ChampionshipConfig, layer: str) -> str:
    """Return the Data Vault directory for a layer (hubs/links/sats)."""
    return os.path.normpath(os.path.join(config.silver_dir, layer))


def _dv_path(config: ChampionshipConfig, layer: str, name: str) -> str:
    """Return full path for a DV parquet file."""
    d = _dv_dir(config, layer)
    return os.path.normpath(os.path.join(d, f"{name}.parquet"))


def save_hubs(config: ChampionshipConfig, hubs: dict[str, pd.DataFrame]) -> None:
    """Save all hub DataFrames to parquet."""
    _recreate_dir(_dv_dir(config, "hubs"))
    for name, df in hubs.items():
        path = _dv_path(config, "hubs", f"hub_{name}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_parquet(path, index=False, compression="zstd")
    print_colored(f"\tHubs salvos em {_dv_dir(config, 'hubs')}", "green")


def save_links(config: ChampionshipConfig, links: dict[str, pd.DataFrame]) -> None:
    """Save all link DataFrames to parquet."""
    _recreate_dir(_dv_dir(config, "links"))
    for name, df in links.items():
        path = _dv_path(config, "links", f"link_{name}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_parquet(path, index=False, compression="zstd")
    print_colored(f"\tLinks salvos em {_dv_dir(config, 'links')}", "green")


def save_satellites(config: ChampionshipConfig, sats: dict[str, pd.DataFrame]) -> None:
    """Save all satellite DataFrames to parquet."""
    _recreate_dir(_dv_dir(config, "satellites"))
    for name, df in sats.items():
        path = _dv_path(config, "satellites", f"sat_{name}")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_parquet(path, index=False, compression="zstd")
    print_colored(f"\tSatellites salvos em {_dv_dir(config, 'satellites')}", "green")


def load_hubs(config: ChampionshipConfig) -> dict[str, pd.DataFrame]:
    """Load all hub parquets into a dict."""
    return _load_dv_dir(config, "hubs", "hub_")


def load_links(config: ChampionshipConfig) -> dict[str, pd.DataFrame]:
    """Load all link parquets into a dict."""
    return _load_dv_dir(config, "links", "link_")


def load_satellites(config: ChampionshipConfig) -> dict[str, pd.DataFrame]:
    """Load all satellite parquets into a dict."""
    return _load_dv_dir(config, "satellites", "sat_")


def _load_dv_dir(config: ChampionshipConfig, layer: str, prefix: str) -> dict[str, pd.DataFrame]:
    """Load all parquets from a DV directory into a dict keyed by entity name."""
    result: dict[str, pd.DataFrame] = {}
    base = _dv_dir(config, layer)
    if not os.path.isdir(base):
        return result
    for fname in sorted(os.listdir(base)):
        if fname.endswith(".parquet"):
            name = fname.replace(".parquet", "").replace(prefix, "")
            result[name] = pd.read_parquet(os.path.join(base, fname))
    return result


def load_all_dv(config: ChampionshipConfig) -> dict[str, dict[str, pd.DataFrame]]:
    """Load all DV layers into nested dict: {hubs: ..., links: ..., sats: ...}."""
    return {
        "hubs": load_hubs(config),
        "links": load_links(config),
        "sats": load_satellites(config),
    }


def _recreate_dir(path: str) -> None:
    """Delete and recreate a single directory."""
    p = os.path.normpath(path)
    if os.path.exists(p):
        shutil.rmtree(p)
        print_colored(f"Pasta '{p}' recriada.", "green")
    os.makedirs(p, exist_ok=True)


# ------------------------------------------------------------------
# OBT (One Big Table) builders — Gold layer
# ------------------------------------------------------------------

_RS = "record_source"
_LD = "load_date"


def _strip_accents(text: str) -> str:
    """Remove diacritics/accents from a string."""
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if not unicodedata.combining(c)
    )


def _slug(name: str) -> str:
    """Slugify a team name: lowercase, no spaces, no hyphens."""
    s = str(name).lower().strip()
    s = s.replace(" ", "_").replace("-", "_")
    return s


def _winner(home: float, away: float) -> str:
    """Return 'home', 'away', or 'draw'."""
    if pd.isna(home) or pd.isna(away):
        return ""
    if home > away:
        return "home"
    if away > home:
        return "away"
    return "draw"


# ------------------------------------------------------------------


def build_obt_palpites(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
    links: dict[str, pd.DataFrame],
    sats: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build OBT Palpites — main fact table with scoring pre-computed.

    Joins: link_palpite → hub_jogador → hub_partida → sat_palpite
           → sat_partida → link_partida_times → hub_time (home+away) → sat_time
    """
    from src.core.scoring import score_prediction

    df_link = links["palpite"].copy()
    if df_link.empty:
        print_colored("\tOBT palpites: 0 registros (sem links)", "yellow")
        return pd.DataFrame()

    # ---- Assemble base fact ----
    df = df_link.copy()

    # Drop DV administrative columns from all sources before merging
    _dv_admin = {"load_date", "record_source", "hash_diff"}

    # Join jogador (name)
    df_j = hubs["jogador"][["jogador_hk", "boleiro_name"]].copy()
    df = df.merge(df_j, on="jogador_hk", how="left")

    # Join partida (slug)
    df_p = hubs["partida"][["partida_hk", "match_slug"]].copy()
    df = df.merge(df_p, on="partida_hk", how="left")

    # Join sat_palpite (prediction details) — drop DV admin cols
    df_sat_p = sats["palpite"].copy()
    df_sat_p = df_sat_p.drop(columns=[c for c in _dv_admin if c in df_sat_p.columns], errors="ignore")
    df = df.merge(df_sat_p, on="palpite_hk", how="left")

    # Join sat_partida (real results) — drop DV admin cols
    df_sat_r = sats["partida"].copy()
    df_sat_r = df_sat_r.drop(columns=[c for c in _dv_admin if c in df_sat_r.columns], errors="ignore")
    df = df.merge(df_sat_r, on="partida_hk", how="left")

    # Join link_partida_times (home/away team FKs) — drop DV admin cols
    df_pt = links["partida_times"].copy()
    df_pt = df_pt.drop(columns=[c for c in _dv_admin if c in df_pt.columns], errors="ignore")
    df = df.merge(df_pt, on="partida_hk", how="left")

    # Join team names
    df_th = hubs["time"][["time_hk", "team_name"]].copy()
    df_th.columns = ["time_home_hk", "home_team"]
    df = df.merge(df_th, on="time_home_hk", how="left")

    df_ta = hubs["time"][["time_hk", "team_name"]].copy()
    df_ta.columns = ["time_away_hk", "away_team"]
    df = df.merge(df_ta, on="time_away_hk", how="left")

    # Join sat_time for home team — drop DV admin cols
    df_st_home = sats["time"].copy()
    df_st_home = df_st_home.drop(columns=[c for c in _dv_admin if c in df_st_home.columns], errors="ignore")
    df_st_home.columns = [f"home_{c}" if c != "time_hk" else "time_home_hk" for c in df_st_home.columns]
    df = df.merge(df_st_home, on="time_home_hk", how="left")

    # Join sat_time for away team — drop DV admin cols
    df_st_away = sats["time"].copy()
    df_st_away = df_st_away.drop(columns=[c for c in _dv_admin if c in df_st_away.columns], errors="ignore")
    df_st_away.columns = [f"away_{c}" if c != "time_hk" else "time_away_hk" for c in df_st_away.columns]
    df = df.merge(df_st_away, on="time_away_hk", how="left")

    # ---- Apply scoring ----
    pontos_list: list = []
    criterio_list: list = []
    valido_list: list = []

    for _, row in df.iterrows():
        try:
            result = score_prediction(
                row.get("home_goals_pred"),
                row.get("away_goals_pred"),
                row.get("home_goals_real"),
                row.get("away_goals_real"),
                config,
            )
            pontos_list.append(result.iloc[0])
            criterio_list.append(result.iloc[1])
            valido_list.append(result.iloc[2])
        except Exception:
            pontos_list.append(0)
            criterio_list.append("9-Nenhum acerto")
            valido_list.append(1)

    df["pontos"] = pontos_list
    df["criterio"] = criterio_list
    df["valido"] = valido_list

    # ---- One-hot encode criteria ----
    rule_names = config.scoring_rule_names()
    for rule in rule_names:
        df[rule] = df["criterio"] == rule

    # ---- Derived columns ----
    df["match"] = df["match_slug"].apply(_strip_accents)

    # Result strings
    df["resultado_bol_placar"] = (
        df["home_goals_pred"].fillna(0).astype(int).astype(str)
        + " x "
        + df["away_goals_pred"].fillna(0).astype(int).astype(str)
    )
    df["resultado_bol_time"] = df.apply(
        lambda r: (
            r["home_team"] if _winner(r["home_goals_pred"], r["away_goals_pred"]) == "home"
            else r["away_team"] if _winner(r["home_goals_pred"], r["away_goals_pred"]) == "away"
            else "empate"
        ),
        axis=1,
    )
    df["resultado_real_placar"] = df.apply(
        lambda r: (
            f"{int(r['home_goals_real'])} x {int(r['away_goals_real'])}"
            if pd.notna(r.get("home_goals_real")) and pd.notna(r.get("away_goals_real"))
            else ""
        ),
        axis=1,
    )
    df["resultado_real_time"] = df.apply(
        lambda r: (
            r["home_team"] if _winner(r["home_goals_real"], r["away_goals_real"]) == "home"
            else r["away_team"] if _winner(r["home_goals_real"], r["away_goals_real"]) == "away"
            else "empate" if pd.notna(r.get("home_goals_real"))
            else ""
        ),
        axis=1,
    )

    # ---- Select final columns ----
    keep_cols = [
        "boleiro_name", "match", "match_slug",
        "home_team", "away_team",
        "home_goals_pred", "away_goals_pred",
        "home_pen_pred", "away_pen_pred",
        "home_goals_real", "away_goals_real",
        "home_pen_real", "away_pen_real",
        "date_pred", "hour_pred",
        "date_real", "hour_real",
        "round", "time_elapsed",
        "home_slug", "home_logo_url", "home_geo_continent", "home_team_name_en",
        "away_slug", "away_logo_url", "away_geo_continent", "away_team_name_en",
        "pontos", "criterio", "valido",
    ] + rule_names

    # Add extra useful columns
    extra = [
        "resultado_bol_placar", "resultado_bol_time",
        "resultado_real_placar", "resultado_real_time",
    ]
    available = [c for c in keep_cols + extra if c in df.columns]
    df_out = df[available].copy()
    # Add legacy aliases for backward compatibility with report code
    df_out["who"] = df_out["boleiro_name"]
    df_out["date"] = df_out["date_pred"]
    df_out["hour"] = df_out["hour_pred"]
    df_out["home_goals_bol"] = df_out["home_goals_pred"]
    df_out["away_goals_bol"] = df_out["away_goals_pred"]
    df_out["home_pen_bol"] = df_out["home_pen_pred"]
    df_out["away_pen_bol"] = df_out["away_pen_pred"]
    # Add 'phase' column — derived from 'round' for backward compatibility
    group_labels = set(config.group_round_labels)
    playoff_keys = {pr.key for pr in (config.playoff_rounds or [])}
    df_out["phase"] = df_out["round"].apply(
        lambda r: config.group_phase_label if str(r) in group_labels
        else str(r) if str(r) in playoff_keys
        else config.group_phase_label
    )
    df_out.sort_values(by=["date_pred", "hour_pred", "boleiro_name"], inplace=True)
    df_out.reset_index(drop=True, inplace=True)

    print_colored(
        f"\tOBT palpites: {len(df_out)} linhas, "
        f"{len(df_out['boleiro_name'].unique())} jogadores",
        "green",
    )
    return df_out


def build_obt_bonus(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
    links: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build OBT Bonus — bonus team picks with scoring."""
    from src.core.scoring import score_playoff_bonus

    df_scored = score_playoff_bonus(config)
    if df_scored.empty:
        return df_scored

    jogador_map = dict(
        zip(hubs["jogador"]["boleiro_name"], hubs["jogador"]["jogador_hk"])
    )
    fase_map = dict(zip(hubs["fase"]["phase_key"], hubs["fase"]["fase_hk"]))
    time_map = dict(zip(hubs["time"]["team_name"], hubs["time"]["time_hk"]))

    df_scored["jogador_hk"] = df_scored["boleiro"].map(jogador_map)
    df_scored["fase_hk"] = df_scored["phase"].map(fase_map)
    df_scored["time_hk"] = df_scored["team_picked"].map(time_map)

    print_colored(f"\tOBT bonus: {len(df_scored)} registros", "green")
    return df_scored


def build_obt_artilheiros(
    config: ChampionshipConfig,
    hubs: dict[str, pd.DataFrame],
    links: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Build OBT Artilheiros — striker picks with scoring."""
    from src.core.scoring import score_strikers

    df_scored = score_strikers(config)
    if df_scored.empty:
        return df_scored

    jogador_map = dict(
        zip(hubs["jogador"]["boleiro_name"], hubs["jogador"]["jogador_hk"])
    )
    df_scored["jogador_hk"] = df_scored["boleiro"].map(jogador_map)

    print_colored(f"\tOBT artilheiros: {len(df_scored)} registros", "green")
    return df_scored


# ------------------------------------------------------------------
# Analytics OBT builders
# ------------------------------------------------------------------


def build_obt_ranking_history(
    df_palpites: pd.DataFrame,
    config: ChampionshipConfig,
) -> pd.DataFrame:
    """Pre-compute daily ranking history."""
    if df_palpites.empty:
        return pd.DataFrame()

    df = df_palpites[df_palpites["valido"] == 1].copy()
    if df.empty:
        return pd.DataFrame()
    df = df.sort_values(["boleiro_name", "date_pred"])

    penalty_map = {
        name: config.total_penalty(name)
        for name in df["boleiro_name"].unique()
    }

    rows = []
    date_col = "date_real" if "date_real" in df.columns and df["date_real"].notna().any() else "date_pred"
    for date, day_group in df.groupby(date_col):
        daily_pts = day_group.groupby("boleiro_name")["pontos"].sum()
        all_cum = df[df[date_col] <= date].groupby("boleiro_name")["pontos"].sum()
        all_cum = all_cum - all_cum.index.map(lambda w: penalty_map.get(w, 0))
        if all_cum.empty:
            continue
        leader_pts = int(all_cum.max())
        leader_name = str(all_cum.idxmax())

        for boleiro in all_cum.index:
            cum = int(all_cum.get(boleiro, 0))
            rank = int(all_cum.rank(ascending=False, method="min").get(boleiro, 0))
            daily_val = int(daily_pts.get(boleiro, 0))
            rows.append({
                "boleiro": boleiro,
                "date": date,
                "daily_points": daily_val,
                "cumulative_points": cum,
                "rank": rank,
                "leader_name": leader_name,
                "leader_distance": leader_pts - cum,
            })

    df_out = pd.DataFrame(rows)
    print_colored(f"\tOBT ranking_history: {len(df_out)} linhas", "green")
    return df_out


def build_obt_consistency(df_palpites: pd.DataFrame) -> pd.DataFrame:
    """Pre-compute streak/consistency data."""
    if df_palpites.empty:
        return pd.DataFrame()
    df = df_palpites[df_palpites["valido"] == 1].copy()
    if df.empty:
        return pd.DataFrame()

    date_col = "date_real" if "date_real" in df.columns and df["date_real"].notna().any() else "date_pred"
    df["_date_num"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.sort_values(["boleiro_name", "_date_num"])
    df["hit"] = df["pontos"] > 0

    rows = []
    for boleiro, group in df.groupby("boleiro_name"):
        group = group.reset_index(drop=True)
        streak_type = None
        streak_len = 0
        for idx, (_, row) in enumerate(group.iterrows()):
            is_hit = row["hit"]
            if is_hit and streak_type == "hit":
                streak_len += 1
            elif not is_hit and streak_type == "miss":
                streak_len += 1
            else:
                streak_type = "hit" if is_hit else "miss"
                streak_len = 1
            recent = group.loc[:idx, "pontos"].tail(5).mean()
            rows.append({
                "boleiro": boleiro,
                "date": str(row.get(date_col, "")),
                "match": row.get("match", ""),
                "streak_type": streak_type,
                "streak_length": streak_len,
                "running_avg_5": round(recent, 1),
            })
    df_out = pd.DataFrame(rows)
    print_colored(f"\tOBT consistency: {len(df_out)} linhas", "green")
    return df_out


def build_obt_boldness(df_palpites: pd.DataFrame) -> pd.DataFrame:
    """Pre-compute boldness index."""
    if df_palpites.empty:
        return pd.DataFrame()
    bolao_avg = (df_palpites["home_goals_pred"] + df_palpites["away_goals_pred"]).mean()
    rows = []
    for boleiro, group in df_palpites.groupby("boleiro_name"):
        total_goals = group["home_goals_pred"] + group["away_goals_pred"]
        avg_total = total_goals.mean()
        games = len(group)
        extreme_pct = (total_goals >= 5).sum() / games * 100 if games > 0 else 0
        rows.append({
            "boleiro": boleiro,
            "avg_total_goals_bol": round(avg_total, 2),
            "avg_home_goals_bol": round(group["home_goals_pred"].mean(), 2),
            "avg_away_goals_bol": round(group["away_goals_pred"].mean(), 2),
            "max_home_bol": int(group["home_goals_pred"].max()),
            "max_away_bol": int(group["away_goals_pred"].max()),
            "extreme_score_pct": round(extreme_pct, 1),
            "games": games,
            "boldness_score": round(avg_total - bolao_avg, 2),
        })
    df_out = pd.DataFrame(rows).sort_values("boldness_score", ascending=False)
    print_colored(f"\tOBT boldness: {len(df_out)} linhas", "green")
    return df_out


def build_obt_team_accuracy(df_palpites: pd.DataFrame) -> pd.DataFrame:
    """Pre-compute prediction accuracy per team per player."""
    if df_palpites.empty:
        return pd.DataFrame()
    df = df_palpites[df_palpites["valido"] == 1].copy()
    if df.empty:
        return pd.DataFrame()

    rows = []
    for team_col, opp_col in [("home_team", "away_team"), ("away_team", "home_team")]:
        for team, group in df.groupby(team_col):
            for boleiro, bg in group.groupby("boleiro_name"):
                total = len(bg)
                correct_winner = sum(
                    1 for _, r in bg.iterrows()
                    if str(r.get("resultado_bol_time", "")) == str(r.get("resultado_real_time", ""))
                )
                exact_score = sum(
                    1 for _, r in bg.iterrows()
                    if r.get("home_goals_pred", -1) == r.get("home_goals_real", -2)
                    and r.get("away_goals_pred", -1) == r.get("away_goals_real", -2)
                )
                rows.append({
                    "boleiro": boleiro,
                    "team": team,
                    "role": team_col.replace("_team", ""),
                    "total_bets": total,
                    "correct_winner": correct_winner,
                    "exact_score": exact_score,
                    "accuracy_pct": round(correct_winner / total * 100, 1) if total > 0 else 0,
                })
    df_out = pd.DataFrame(rows)
    print_colored(f"\tOBT team_accuracy: {len(df_out)} linhas", "green")
    return df_out


def build_obt_round_by_round(
    df_palpites: pd.DataFrame,
    config: ChampionshipConfig,
) -> pd.DataFrame:
    """Pre-compute points per round per player."""
    if df_palpites.empty:
        return pd.DataFrame()
    df = df_palpites[df_palpites["valido"] == 1].copy()
    if df.empty:
        return pd.DataFrame()

    # OBT already has 'round' from sat_partida; just fill missing
    df["round"] = df["round"].fillna("0")

    round_keys = list(config.group_round_labels)
    for pr in config.playoff_rounds:
        round_keys.append(pr.key)
    round_order = {r: i + 1 for i, r in enumerate(round_keys)}
    df["round_number"] = df["round"].map(round_order).fillna(0).astype(int)

    rows = []
    for boleiro, group in df.groupby("boleiro_name"):
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

    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        for rn in df_out["round_number"].unique():
            mask = df_out["round_number"] == rn
            df_out.loc[mask, "rank"] = df_out.loc[mask, "cumulative_points"].rank(
                ascending=False, method="min"
            ).astype(int)
    print_colored(f"\tOBT round_by_round: {len(df_out)} linhas", "green")
    return df_out


def build_obt_upsets(
    df_palpites: pd.DataFrame,
    config: ChampionshipConfig,
) -> pd.DataFrame:
    """Pre-compute upset tracker (OBT already has round from sat_partida)."""
    if df_palpites.empty:
        return pd.DataFrame()
    df = df_palpites.copy()

    rows = []
    for match, group in df.groupby("match"):
        first = group.iloc[0]
        home = first["home_team"]
        away = first["away_team"]
        real_winner_raw = first.get("resultado_real_time", "")
        real_winner = "" if pd.isna(real_winner_raw) else str(real_winner_raw)
        time_elapsed_raw = first.get("time_elapsed", "")
        time_elapsed = "" if pd.isna(time_elapsed_raw) else str(time_elapsed_raw).strip().lower()

        if not real_winner or time_elapsed in ("live", "notstarted"):
            continue

        vote_counts = group["resultado_bol_time"].value_counts()
        favorite = vote_counts.index[0] if not vote_counts.empty else ""
        favorite_votes = int(vote_counts.iloc[0]) if not vote_counts.empty else 0
        total_votes = len(group)

        players_correct = []
        for _, p_row in group.iterrows():
            if str(p_row.get("resultado_bol_time", "")) == real_winner:
                players_correct.append(p_row["boleiro_name"])

        num_correct = len(players_correct)
        winner_wrong_pct = 100 - round(num_correct / total_votes * 100) if total_votes else 0
        is_upset = 1 if (favorite != real_winner and num_correct <= config.upset_threshold_correct_count) else 0

        rows.append({
            "match": match,
            "date": first.get("date_pred", ""),
            "hour": first.get("hour_pred", ""),
            "home_team": home,
            "away_team": away,
            "real_winner": real_winner,
            "favorite": favorite,
            "favorite_votes": favorite_votes,
            "total_votes": total_votes,
            "winner_wrong_pct": winner_wrong_pct,
            "is_upset": is_upset,
            "num_correct": num_correct,
            "players_correct": " | ".join(players_correct),
        })

    df_out = pd.DataFrame(rows)
    print_colored(f"\tOBT upsets: {len(df_out)} linhas", "green")
    return df_out


def build_obt_goal_error(df_palpites: pd.DataFrame) -> pd.DataFrame:
    """Pre-compute Mean Absolute Error per team per player."""
    if df_palpites.empty:
        return pd.DataFrame()
    df = df_palpites[df_palpites["valido"] == 1].copy()
    if df.empty:
        return pd.DataFrame()

    rows = []
    for team_col in ("home_team", "away_team"):
        role = team_col.replace("_team", "")
        goals_bol_col = f"{role}_goals_pred"
        goals_real_col = f"{role}_goals_real"
        if goals_bol_col not in df.columns or goals_real_col not in df.columns:
            continue

        for team, group in df.groupby(team_col):
            for boleiro, bg in group.groupby("boleiro_name"):
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

    # Add totals
    df_part = pd.DataFrame(rows)
    if not df_part.empty:
        totals = []
        for (boleiro, team), group in df_part.groupby(["boleiro", "team"]):
            total_games = group["games"].sum()
            total_mae = round((group["mae"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0
            totals.append({
                "boleiro": boleiro, "team": team, "role": "total",
                "games": total_games, "mae": total_mae,
                "goal_bias": round((group["goal_bias"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0,
                "avg_predicted": round((group["avg_predicted"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0,
                "avg_real": round((group["avg_real"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0,
            })
        df_totals = pd.DataFrame(totals)
        df_out = pd.concat([df_part, df_totals], ignore_index=True).sort_values(["boleiro", "team", "role"])
    else:
        df_out = pd.DataFrame(rows)

    print_colored(f"\tOBT goal_error: {len(df_out)} linhas", "green")
    return df_out


def build_obt_group_standings(config: ChampionshipConfig) -> pd.DataFrame:
    """Pre-compute real group standings from games.csv."""
    if not config.groups:
        print_colored("\tOBT group_standings: 0 linhas (sem grupos config)", "yellow")
        return pd.DataFrame()

    df_games = _load_results(config)
    df_group = df_games[df_games["round"].astype(str).str.strip().isin(config.group_round_labels)]

    rows = []
    for grp in config.groups:
        group_name = grp.get("name", "?")
        teams = grp.get("teams", [])
        standings = {}
        for t in teams:
            standings[t] = {"team": t, "group": group_name,
                            "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
        for _, row in df_group.iterrows():
            home = str(row.get("home_team", ""))
            away = str(row.get("away_team", ""))
            if home not in standings or away not in standings:
                continue
            try:
                hg = int(row["home_goals"]) if pd.notna(row.get("home_goals")) else None
                ag = int(row["away_goals"]) if pd.notna(row.get("away_goals")) else None
            except (ValueError, TypeError):
                continue
            if hg is None or ag is None:
                continue
            standings[home]["p"] += 1
            standings[away]["p"] += 1
            standings[home]["gf"] += hg
            standings[home]["ga"] += ag
            standings[away]["gf"] += ag
            standings[away]["ga"] += hg
            if hg > ag:
                standings[home]["w"] += 1
                standings[home]["pts"] += 3
                standings[away]["l"] += 1
            elif ag > hg:
                standings[away]["w"] += 1
                standings[away]["pts"] += 3
                standings[home]["l"] += 1
            else:
                standings[home]["d"] += 1
                standings[away]["d"] += 1
                standings[home]["pts"] += 1
                standings[away]["pts"] += 1
        for t, s in standings.items():
            s["gd"] = s["gf"] - s["ga"]
            rows.append(s)

    df_out = pd.DataFrame(rows)
    if not df_out.empty:
        df_out = df_out.sort_values(["group", "pts", "gd", "gf"],
                                     ascending=[True, False, False, False])
    print_colored(f"\tOBT group_standings: {len(df_out)} linhas", "green")
    return df_out


def build_obt_prediction_timing(config: ChampionshipConfig) -> pd.DataFrame:
    """Pre-compute lead days from raw Excel mtime."""
    import unicodedata
    from datetime import datetime

    df_games = _load_results(config)
    if "date" in df_games.columns and not df_games["date"].empty:
        first_match = pd.to_datetime(df_games["date"].dropna().min())
    else:
        first_match = datetime.now()

    raw_pattern = os.path.normpath(
        os.path.join(config.raw_dir, config.group_phase_label, "*")
    )
    raw_paths = sorted(glob(raw_pattern))

    rows = []
    for path_excel in raw_paths:
        fname = os.path.basename(path_excel)
        name_no_ext = fname.replace(".xlsx", "").replace(".xls", "").strip()
        boleiro = name_no_ext
        try:
            mtime = os.path.getmtime(path_excel)
            mtime_dt = datetime.fromtimestamp(mtime)
            lead_days = (first_match - pd.Timestamp(mtime_dt)).days if first_match is not pd.NaT else 0
        except Exception:
            mtime_dt = datetime.now()
            lead_days = 0
        rows.append({
            "boleiro": boleiro,
            "file_mtime": mtime_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "first_match_date": first_match.strftime("%Y-%m-%d") if not pd.isna(first_match) else "",
            "lead_days": max(lead_days, 0),
        })

    df_out = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["boleiro", "file_mtime", "first_match_date", "lead_days"]
    )
    if not df_out.empty:
        df_out = df_out.sort_values("lead_days", ascending=False)
    print_colored(f"\tOBT prediction_timing: {len(df_out)} linhas", "green")
    return df_out


# ------------------------------------------------------------------
# OBT save/load
# ------------------------------------------------------------------


def save_all_obts(config: ChampionshipConfig, obts: dict[str, pd.DataFrame]) -> None:
    """Save all OBT DataFrames to parquet in gold/obt/."""
    obt_dir = os.path.normpath(os.path.join(config.gold_dir, "obt"))
    os.makedirs(obt_dir, exist_ok=True)
    for name, df in obts.items():
        path = os.path.join(obt_dir, f"{name}.parquet")
        if not df.empty:
            df.to_parquet(path, index=False, compression="zstd")
            print_colored(f"\tOBT {name}.parquet: {len(df)} linhas", "green")
        else:
            df_empty = pd.DataFrame()
            df_empty.to_parquet(path, index=False)
            print_colored(f"\tOBT {name}.parquet: vazio", "yellow")


def load_obt(config: ChampionshipConfig, name: str) -> pd.DataFrame:
    """Load a single OBT parquet from gold/obt/."""
    path = os.path.normpath(os.path.join(config.gold_dir, "obt", f"{name}.parquet"))
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_parquet(path)


def load_multi_obt(config: ChampionshipConfig, names: list[str]) -> dict[str, pd.DataFrame]:
    """Load multiple OBTs into a dict."""
    return {n: load_obt(config, n) for n in names}


# ------------------------------------------------------------------
# Pipeline orchestrators
# ------------------------------------------------------------------


def run_bronze_to_silver_dv(config: ChampionshipConfig) -> dict[str, dict[str, pd.DataFrame]]:
    """Build full Data Vault silver layer — hubs, links, satellites.

    Returns nested dict::

        {"hubs": {...}, "links": {...}, "sats": {...}}
    """
    print_colored("bronze → silver (Data Vault)", "sand")

    for layer in ("hubs", "links", "satellites"):
        _recreate_dir(_dv_dir(config, layer))

    print_colored("\tConstruindo hubs...", "ice")
    hubs = build_all_hubs(config)
    save_hubs(config, hubs)

    print_colored("\tConstruindo links...", "ice")
    links = build_all_links(config, hubs)
    save_links(config, links)

    print_colored("\tConstruindo satellites...", "ice")
    sats = build_all_satellites(config, hubs, links)
    save_satellites(config, sats)

    print_colored("bronze → silver (DV) concluído", "green")
    return {"hubs": hubs, "links": links, "sats": sats}


def run_silver_to_gold_dv(
    config: ChampionshipConfig,
    silver: dict[str, dict[str, pd.DataFrame]] | None = None,
) -> dict[str, pd.DataFrame]:
    """Build all Gold OBTs from Silver Data Vault.

    Pre-computes EVERYTHING — scoring, ranking history, consistency,
    boldness, team accuracy, round-by-round, upsets, goal errors,
    group standings, prediction timing.

    Args:
        config: Championship configuration.
        silver: Optional pre-loaded DV data. If None, loads from parquet.

    Returns dict of all OBT DataFrames.
    """
    print_colored("silver (DV) → gold (OBT)", "sand")

    if silver is None:
        silver = load_all_dv(config)

    hubs = silver["hubs"]
    links = silver["links"]
    sats = silver["sats"]

    obts: dict[str, pd.DataFrame] = {}

    # 1. Main OBT
    print_colored("\tConstruindo OBT palpites...", "ice")
    df_palpites = build_obt_palpites(config, hubs, links, sats)
    obts["obt_palpites"] = df_palpites

    # 2. Bonus and strikers
    print_colored("\tConstruindo OBT bonus...", "ice")
    obts["obt_bonus"] = build_obt_bonus(config, hubs, links)

    print_colored("\tConstruindo OBT artilheiros...", "ice")
    obts["obt_artilheiros"] = build_obt_artilheiros(config, hubs, links)

    # 3. Analytics OBTs derived from palpites
    if not df_palpites.empty:
        print_colored("\tConstruindo OBT ranking_history...", "ice")
        obts["obt_ranking_history"] = build_obt_ranking_history(df_palpites, config)

        print_colored("\tConstruindo OBT consistency...", "ice")
        obts["obt_consistency"] = build_obt_consistency(df_palpites)

        print_colored("\tConstruindo OBT boldness...", "ice")
        obts["obt_boldness"] = build_obt_boldness(df_palpites)

        print_colored("\tConstruindo OBT team_accuracy...", "ice")
        obts["obt_team_accuracy"] = build_obt_team_accuracy(df_palpites)

        print_colored("\tConstruindo OBT round_by_round...", "ice")
        obts["obt_round_by_round"] = build_obt_round_by_round(df_palpites, config)

        print_colored("\tConstruindo OBT upsets...", "ice")
        obts["obt_upsets"] = build_obt_upsets(df_palpites, config)

        print_colored("\tConstruindo OBT goal_error...", "ice")
        obts["obt_goal_error"] = build_obt_goal_error(df_palpites)

    # 4. Analytics OBTs from config/games only
    print_colored("\tConstruindo OBT group_standings...", "ice")
    obts["obt_group_standings"] = build_obt_group_standings(config)

    print_colored("\tConstruindo OBT prediction_timing...", "ice")
    obts["obt_prediction_timing"] = build_obt_prediction_timing(config)

    # 5. Save all
    save_all_obts(config, obts)

    print_colored("silver → gold (OBTs) concluído", "green")
    return obts
