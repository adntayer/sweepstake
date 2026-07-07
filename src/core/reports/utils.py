"""Utility functions for reports — OBT parquet loading only (no CSV)."""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig


def load_obt(config: ChampionshipConfig, obt_name: str) -> pd.DataFrame:
    """Load a Gold OBT parquet.

    Tries ``gold/obt/{obt_name}.parquet``.
    Returns empty DataFrame if not found.
    """
    obt_path = config.gold_obt_path(obt_name)
    if os.path.exists(obt_path):
        try:
            return pd.read_parquet(obt_path)
        except Exception:
            pass
    # Also try with obt_ prefix
    if not obt_name.startswith("obt_"):
        obt_path2 = config.gold_obt_path(f"obt_{obt_name}")
        if os.path.exists(obt_path2):
            try:
                return pd.read_parquet(obt_path2)
            except Exception:
                pass
    return pd.DataFrame()


def load_obt_palpites(config: ChampionshipConfig) -> pd.DataFrame:
    """Load obt_palpites with valido filter preference."""
    df = load_obt(config, "obt_palpites")
    if df.empty:
        return df
    if "valido" in df.columns and (df["valido"] == 1).any():
        return df[df["valido"] == 1].copy()
    return df


def compute_pending_matches(config: ChampionshipConfig) -> dict:
    """Compute match result status summary from OBT palpites."""
    tz = pytz.timezone(config.timezone)
    today = datetime.now(tz).date()

    df = load_obt(config, "obt_palpites")
    if df.empty or "match" not in df.columns:
        return _empty_result()

    df_matches = df.drop_duplicates(subset=["match"]).copy()
    total = len(df_matches)

    if "valido" not in df_matches.columns:
        return _empty_result()

    with_result = int(df_matches["valido"].sum())

    # Use date_pred as match date
    df_matches["date_dt"] = pd.to_datetime(
        df_matches.get("date_pred", df_matches.get("date")),
        dayfirst=False, errors="coerce",
    )
    df_matches["date_only"] = df_matches["date_dt"].dt.date

    mask_no_result = df_matches["valido"] == 0
    mask_future = df_matches["date_only"] > today
    mask_pending = mask_no_result & ~mask_future

    pending = int(mask_pending.sum())
    future = int((mask_no_result & mask_future).sum())

    pending_df = df_matches[mask_pending]
    pending_info = []
    for _, row in pending_df.iterrows():
        pending_info.append({
            "slug": str(row["match"]),
            "home_team": str(row.get("home_team", "")),
            "away_team": str(row.get("away_team", "")),
            "date": str(row.get("date_pred", row.get("date", ""))),
            "hour": str(row.get("hour_pred", row.get("hour", ""))),
        })

    future_df = df_matches[mask_no_result & (df_matches["date_only"] > today)]

    return {
        "total_matches": total,
        "with_result": with_result,
        "pending": pending,
        "future": future,
        "pending_slugs": pending_df["match"].tolist(),
        "pending_info": pending_info,
        "future_slugs": future_df["match"].tolist(),
    }


def _empty_result() -> dict:
    return {
        "total_matches": 0,
        "with_result": 0,
        "pending": 0,
        "future": 0,
        "pending_slugs": [],
        "pending_info": [],
        "future_slugs": [],
    }
