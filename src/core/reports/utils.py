from __future__ import annotations

import os
import re
from datetime import datetime

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig


# ── Match href cache (built once per process) ──
_match_href_cache: dict[str, str] | None = None


def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


def _strip_accents(text: str) -> str:
    """Remove common accented characters (quick approach, no dependency)."""
    replacements = {
        "á": "a", "à": "a", "ã": "a", "â": "a", "ä": "a",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "í": "i", "ì": "i", "î": "i", "ï": "i",
        "ó": "o", "ò": "o", "õ": "o", "ô": "o", "ö": "o",
        "ú": "u", "ù": "u", "û": "u", "ü": "u",
        "ç": "c",
        "ñ": "n",
        "Á": "A", "À": "A", "Ã": "A", "Â": "A", "Ä": "A",
        "É": "E", "È": "E", "Ê": "E", "Ë": "E",
        "Í": "I", "Ì": "I", "Î": "I", "Ï": "I",
        "Ó": "O", "Ò": "O", "Õ": "O", "Ô": "O", "Ö": "O",
        "Ú": "U", "Ù": "U", "Û": "U", "Ü": "U",
        "Ç": "C",
        "Ñ": "N",
    }
    for a, n in replacements.items():
        text = text.replace(a, n)
    return text


def _build_match_key(home_team: str, away_team: str) -> str:
    """Build a normalised lookup key for a match (lowercase, no accents, underscores)."""
    def _norm(t):
        t = _strip_accents(t.lower())
        t = t.replace(" ", "_").replace("'", "").replace("-", "_")
        return t
    return f"{_norm(home_team)}-vs-{_norm(away_team)}"


def _rebuild_match_href_cache(config: ChampionshipConfig) -> dict[str, str]:
    """Scan all jogos/<phase>/*.html files and return {match_key: href}."""
    _map: dict[str, str] = {}
    html_base = _norm(os.path.join(config.reports_dir, "html"))
    jogos_base = _norm(os.path.join(html_base, "jogos"))
    if not os.path.isdir(jogos_base):
        return _map
    for phase_dir in os.listdir(jogos_base):
        phase_path = _norm(os.path.join(jogos_base, phase_dir))
        if not os.path.isdir(phase_path):
            continue
        for fname in os.listdir(phase_path):
            if not fname.endswith(".html"):
                continue
            fpath = _norm(os.path.join(phase_path, fname))
            # Parse the filename to extract teams
            fname_noext = fname.replace(".html", "")
            # Parse the filename — handle both "2026-07-05_17h_" (old) and "2026-07-05_" (new)
            m = re.search(r"\d{4}-\d{2}-\d{2}(_\d{1,2}h)?_", fname_noext)
            if not m:
                continue
            rest = fname_noext[m.end():]
            parts = rest.split("-vs-")
            if len(parts) < 2:
                continue
            home_raw = parts[0].replace("_", " ").strip()
            away_raw = parts[1].replace("_", " ").strip()
            if not home_raw or not away_raw:
                continue
            key = _build_match_key(home_raw, away_raw)
            href = fpath.replace("\\", "/").replace(
                f"{config.reports_dir.replace(chr(92), '/')}/html/", ""
            )
            _map[key] = href
    return _map


def get_match_href(config: ChampionshipConfig, home_team: str, away_team: str,
                   *, phase: str = "", match_slug: str = "", date: str = "", hour: str = "") -> str:
    """Return the href (relative to reports/html/) for a match.

    Uses the actual HTML files on disk (fast, cached). Falls back to construction
    when the file doesn't exist yet (future/placeholder matches).
    """
    global _match_href_cache
    if _match_href_cache is None:
        _match_href_cache = _rebuild_match_href_cache(config)

    key = _build_match_key(home_team, away_team)
    href = _match_href_cache.get(key)
    if href:
        return href

    # Fallback: construct from parameters
    if match_slug and date:
        # Sanitise: some CSVs embed the hour in the date column
        # (e.g. "2026-07-15 15h"), but the actual filename uses
        # the bare date only.  Strip any trailing hour suffix.
        _date_clean = date.split()[0]
        # Only need phase + date + match_slug to produce a unique link;
        # hour is excluded so the href is stable even if CSV hour values
        # differ from the actual match file hour on disk.
        if phase:
            return f"jogos/{phase}/{_date_clean}_{match_slug}.html"
        else:
            return f"jogos/_/{_date_clean}_{match_slug}.html"

    return ""


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
    _parts: list[pd.DataFrame] = []
    if os.path.exists(all_path):
        df_g = pd.read_csv(all_path, sep=",")
        if not df_g.empty:
            _parts.append(df_g)
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_all_path(pr.key)
        if os.path.exists(pp):
            df_p = pd.read_csv(pp, sep=",")
            if not df_p.empty:
                _parts.append(df_p)
    if not _parts:
        return _empty_result()

    df = pd.concat(_parts, ignore_index=True)
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


def reset_match_href_cache() -> None:
    """Force the filesystem-scan cache to be rebuilt on next get_match_href call."""
    global _match_href_cache
    _match_href_cache = None
