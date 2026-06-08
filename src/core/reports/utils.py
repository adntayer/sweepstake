from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig


def compute_pending_matches(config: ChampionshipConfig) -> dict:
    """Compute match result status summary.

    Returns a dict with:
      - total_matches: total unique matches in the gold_all file
      - with_result: matches that have a real result loaded (valido == 1)
      - pending: matches whose date has passed but have no result yet
      - future: matches whose date is still in the future
      - pending_slugs: list of match slugs pending results
      - pending_info: list of dicts (slug, home_team, away_team, date, hour)
    """
    tz = pytz.timezone(config.timezone)
    today = datetime.now(tz).date()

    all_path = config.gold_all_path()
    if not os.path.exists(all_path):
        return _empty_result()

    df = pd.read_csv(all_path, sep=",")
    if df.empty or "match" not in df.columns:
        return _empty_result()

    df_matches = df.drop_duplicates(subset=["match"]).copy()
    total = len(df_matches)

    if "valido" not in df_matches.columns:
        return _empty_result()

    with_result = int(df_matches["valido"].sum())

    df_matches["date_dt"] = pd.to_datetime(df_matches["date"], dayfirst=False, errors="coerce")
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
            "home_team": str(row["home_team"]),
            "away_team": str(row["away_team"]),
            "date": str(row["date"]),
            "hour": str(row.get("hour", "")),
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
