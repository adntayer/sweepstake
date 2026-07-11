"""Generate rich mobile-first HTML reports directly from gold-layer CSV data.

Produces:
  - Per-participant boleiros/<name>.html (X-ray analysis)
  - Per-match jogos/<phase>/<match>.html (prediction analysis)
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig
from src.core.printing import print_colored
from src.core.reports.new_views import (
    build_all_team_pages,
    build_group_standings_page,
    build_round_matrix_page,
    build_round_predictions_page,
    build_similarity_matrix_page,
)
from src.core.reports.arquetipos import (
    classificar_jogadores,
    build_arquetipos_page,
)


# Zebra magnitude constants — used across all report pages
ZEBRA_MONSTRA_EMOJI = "\U0001f993\U0001f4a5"   # 🦓💥
ZEBRA_GRANDE_EMOJI  = "\U0001f993\u26a1"        # 🦓⚡
ZEBRA_MONSTRA_LABEL = f"{ZEBRA_MONSTRA_EMOJI} ZEBRA MONSTRA"
ZEBRA_GRANDE_LABEL  = f"{ZEBRA_GRANDE_EMOJI} Zebra Grande"


def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


def _short_name(name: str, config: ChampionshipConfig | None = None) -> str:
    """Shorten phase names for table headers.

    If ``config`` is provided, its ``phase_abbreviations`` mapping is
    checked first (exact match).  Falls back to Portuguese substring matching
    for legacy compatibility.
    """
    n = name.strip()
    if config and n in config.phase_abbreviations:
        return config.phase_abbreviations[n]
    nl = n.lower()
    if "segunda" in nl:
        return "2\u00aa Fase"
    if "oitavas" in nl:
        return "8as"
    if "quartas" in nl:
        return "4as"
    if "semi" in nl:
        return "Semi"
    if "terceiro" in nl or nl == "3\u00ba lugar":
        return "3\u00ba"
    if "final" in nl:
        return "Final"
    return n


# ------------------------------------------------------------------
# Shared CSS block (theme-driven) — now loaded from external styles/base.css
# ------------------------------------------------------------------

_CSS_BASE = """
* { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Typography ── */
@font-face {
    font-family: 'Space Grotesk';
    src: local('Space Grotesk'), local('SpaceGrotesk-Regular');
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: 'Space Grotesk';
    src: local('Space Grotesk SemiBold'), local('SpaceGrotesk-SemiBold');
    font-weight: 600;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: 'Space Grotesk';
    src: local('Space Grotesk Bold'), local('SpaceGrotesk-Bold');
    font-weight: 700;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: 'JetBrains Mono';
    src: local('JetBrains Mono'), local('JetBrainsMono-Regular');
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}
@font-face {
    font-family: 'JetBrains Mono';
    src: local('JetBrains Mono Bold'), local('JetBrainsMono-Bold');
    font-weight: 700;
    font-style: normal;
    font-display: swap;
}

:root {
    --font-display: 'Space Grotesk', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
}

body {
    font-family: var(--font-body);
    background: var(--bg);
    color: var(--text);
    font-size: 16px;
    line-height: 1.6;
    -webkit-text-size-adjust: 100%;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

h1, h2, h3, h4 {
    font-family: var(--font-display);
    font-weight: 600;
    letter-spacing: -0.01em;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }

select:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

/* ── Temperature bar (page signature) ── */
.temp-bar {
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: var(--temp-color, var(--accent));
    border-radius: 0 2px 2px 0;
    transition: opacity 0.3s;
}
.temp-bar-container {
    position: relative;
}

/* ── Hero banner ── */
.hero {
    background: var(--bg);
    padding: 1.75rem 1rem 1.25rem;
    text-align: center;
    color: var(--text);
    border-bottom: 1px solid var(--card-border);
    position: relative;
}
.hero h1 {
    font-family: var(--font-display);
    font-size: 1.5rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    margin-bottom: 0.2rem;
}
.hero .subtitle {
    font-family: var(--font-body);
    font-size: 0.85rem;
    color: var(--text-muted);
    font-weight: 400;
}
.hero .timestamp {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    color: var(--text-muted);
    margin-top: 0.5rem;
    letter-spacing: 0.02em;
}

/* ── Back navigation ── */
.back-nav {
    position: sticky;
    top: 0;
    z-index: 10;
    background: var(--card-bg);
    border-bottom: 1px solid var(--card-border);
    padding: 0.6rem 1rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-family: var(--font-mono);
    font-size: 0.75rem;
    letter-spacing: 0.02em;
}
.back-nav a {
    color: var(--text-muted);
    font-weight: 400;
    min-height: 44px;
    display: flex;
    align-items: center;
    transition: color 0.15s;
}
.back-nav a:hover { color: var(--accent); text-decoration: none; }

/* ── Cards ── */
.card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    padding: 1rem;
    margin: 0.75rem;
}
.card-title {
    font-family: var(--font-display);
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.5rem;
    font-weight: 600;
}

/* ── Stat cards row ── */
.stat-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    padding: 0.75rem;
}
.stat-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    padding: 0.75rem;
    text-align: center;
}
.stat-card .value {
    font-family: var(--font-display);
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: -0.02em;
}
.stat-card .label {
    font-family: var(--font-body);
    font-size: 0.65rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 0.25rem;
}

/* ── Score display ── */
.score-card {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    padding: 1.25rem 1rem;
}
.score-card .team { flex: 1; text-align: center; font-size: 1rem; font-weight: 500; }
.score-card .score {
    font-family: var(--font-mono);
    color: var(--accent);
    font-size: 1.75rem;
    font-weight: 700;
    white-space: nowrap;
    letter-spacing: 0.02em;
}
.score-card .vs { color: var(--text-muted); font-size: 0.85rem; font-family: var(--font-body); }

/* ── Badge ── */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.7rem;
    font-weight: 600;
    font-family: var(--font-body);
}
.badge-success { background: var(--success); color: #fff; }
.badge-warning { background: var(--warning); color: var(--text-inverse); }
.badge-danger { background: var(--danger); color: #fff; }

/* ── CSS bar charts ── */
.bar-chart { padding: 0.5rem 0; }
.bar-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
    font-size: 0.85rem;
}
.bar-label {
    width: 100px;
    color: var(--text-muted);
    text-align: right;
    font-size: 0.65rem;
    flex-shrink: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: var(--font-mono);
}
.bar-track {
    flex: 1;
    height: 16px;
    background: var(--card-border);
    border-radius: 3px;
    overflow: hidden;
}
.bar-fill {
    height: 100%;
    background: var(--primary);
    border-radius: 3px;
    transition: width 0.3s;
}
.bar-pct { min-width: 36px; text-align: right; color: var(--text-muted); font-family: var(--font-mono); font-size: 0.7rem; }
.bar-row { cursor: pointer; }
.bar-players { display: none; width: 100%; padding: 0.3rem 0 0 100px; font-size: 0.7rem; color: var(--text-muted); }
.bar-row.expanded .bar-players { display: flex; flex-direction: column; gap: 0.15rem; }
.bar-player { padding: 0.1rem 0; }
.bar-player::before { content: "\2022 "; }

/* ── Player prediction rows ── */
.pred-row {
    display: flex;
    align-items: center;
    padding: 0.75rem;
    border-bottom: 1px solid var(--card-border);
    gap: 0.75rem;
}
.pred-row:last-child { border-bottom: none; }
.pred-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--primary);
    color: var(--accent);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.85rem;
    flex-shrink: 0;
}
.pred-info { flex: 1; min-width: 0; }
.pred-name { font-family: var(--font-display); font-weight: 600; font-size: 0.9rem; }
.pred-date { font-weight: 400; font-size: 0.7rem; color: var(--text-muted); display: inline-block; font-family: var(--font-mono); }
.pred-detail { font-size: 0.8rem; color: var(--text-muted); }
.boleiro-link { color: var(--text); text-decoration: none; font-weight: 600; }
.boleiro-link:hover { color: var(--accent); text-decoration: underline; }
.pred-points {
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 1rem;
    flex-shrink: 0;
    min-width: 50px;
    text-align: right;
}

/* ── Ranking table ── */
.rank-table {
    width: 100%;
    border-collapse: collapse;
}
.rank-table th {
    font-family: var(--font-mono);
    background: var(--card-border);
    color: var(--text-muted);
    padding: 0.5rem 0.75rem;
    text-align: left;
    font-size: 0.65rem;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    position: sticky;
    top: 0;
    z-index: 2;
}
.rank-table td {
    font-family: var(--font-body);
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid var(--card-border);
    font-size: 0.85rem;
}
.rank-table tr:nth-child(even) { background: var(--zebra-stripe); }
.rank-table .rank-1 td { background: var(--accent-highlight); }
.rank-table .rank-2 td { background: var(--silver-highlight); }
.rank-table .rank-3 td { background: var(--bronze-highlight); }
.rank-table th.sort-asc::after,
table[data-sortable] th.sort-asc::after { content:" \u25b2"; font-size:0.6rem; }
.rank-table th.sort-desc::after,
table[data-sortable] th.sort-desc::after { content:" \u25bc"; font-size:0.6rem; }

/* ── Section spacing ── */
.section { margin: 1rem 0; }
.section-title {
    font-family: var(--font-display);
    font-size: 0.9rem;
    font-weight: 600;
    padding: 0 0.75rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    letter-spacing: -0.01em;
}

/* ── Accordion / details ── */
details {
    margin: 0.5rem 0.75rem;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    overflow: hidden;
}
summary {
    padding: 0.85rem 1rem;
    cursor: pointer;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 0.85rem;
    min-height: 44px;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    user-select: none;
}
summary:hover { background: var(--hover-overlay); }
details[open] summary { border-bottom: 1px solid var(--card-border); }
details .content { padding: 0.75rem 1rem; }

/* ── Striker badge ── */
.striker-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--card-bg);
    border: 1px solid var(--accent);
    border-radius: 6px;
    padding: 0.5rem 1rem;
    margin: 0.75rem;
    font-size: 0.85rem;
}
.striker-badge .icon { font-size: 1.2rem; }

/* ── Score pill ── */
.score-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 1rem;
    white-space: nowrap;
}

/* ── Utility ── */
.text-center { text-align: center; }
.text-muted { color: var(--text-muted); }
.mt-0 { margin-top: 0; }
.mb-1 { margin-bottom: 0.5rem; }
.grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; }
.stat-card-sm { padding: 0.5rem; }
.stat-card-sm .value { font-size: 1.1rem; }
.stat-card-sm .label { font-size: 0.6rem; }
.card-link {
    display: block;
    margin: 0 0.75rem;
    text-align: center;
    font-family: var(--font-display);
    font-weight: 600;
}
.card-link.accent { border-color: var(--accent); }
.arena-select {
    width: 100%;
    padding: 0.5rem;
    background: var(--card-bg);
    color: var(--text);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    font-size: 0.9rem;
    font-family: var(--font-body);
}
.arena-select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.arena-label { font-size: 0.8rem; color: var(--text-muted); display: block; margin-bottom: 0.25rem; }
.compare-date { color: var(--text-muted); margin-bottom: 0.15rem; font-family: var(--font-mono); font-size: 0.7rem; }
.compare-row { margin-bottom: 0.4rem; font-size: 0.8rem; }
.compare-label-p1 { min-width: 30px; color: var(--accent); font-size: 0.75rem; font-family: var(--font-mono); }
.compare-label-p2 { min-width: 30px; color: var(--text-muted); font-size: 0.75rem; font-family: var(--font-mono); }
.compare-bar-track { height: 10px; }
.compare-bar-fill-accent { background: var(--accent); }
.compare-bar-fill-voce { background: var(--voce); }
.compare-bar-fill-bolao { background: var(--bolao); }
.compare-val { min-width: 25px; text-align: right; font-size: 0.75rem; font-family: var(--font-mono); }
.compare-diff { text-align: right; font-size: 0.7rem; font-weight: 700; font-family: var(--font-mono); }

/* ── Heatmap ── */
.heat-container { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.heat-row { display: flex; gap: 0; margin-bottom: 2px; }
.heat-label { width: 80px; min-width: 80px; font-size: 0.65rem; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 4px; line-height: 28px; text-align: right; font-family: var(--font-mono); }
.heat-label-right { width: 80px; min-width: 80px; font-size: 0.65rem; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-left: 4px; line-height: 28px; text-align: left; font-family: var(--font-mono); }
.heat-cells { display: flex; gap: 2px; }
.heat-cell { width: 28px; min-width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 0.55rem; font-weight: 600; color: var(--text); border-radius: 3px; flex-shrink: 0; font-family: var(--font-mono); }
.heat-cell-header { width: 28px; min-width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 0.5rem; font-weight: 600; color: var(--text-muted); flex-shrink: 0; border-radius: 3px; font-family: var(--font-mono); }
.heat-total-label { width: 80px; min-width: 80px; font-size: 0.6rem; color: var(--text-muted); white-space: nowrap; padding-right: 4px; line-height: 28px; text-align: right; border-top: 1px solid var(--card-border); font-family: var(--font-mono); }
.heat-cell-lg { width: 34px; min-width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; font-size: 0.65rem; font-weight: 600; color: var(--text); border-radius: 4px; flex-shrink: 0; font-family: var(--font-mono); }
.heatmap-match { display:flex; flex-direction:column; gap:6px; }
.heatmap-top { display:flex; align-items:center; justify-content:center; gap:6px; font-weight:600; font-size:0.85rem; padding:6px 0 2px 0; }
.heatmap-top img { width:28px; height:28px; }
.heatmap-body { display:flex; gap:10px; }
.heatmap-away { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; font-weight:600; font-size:0.75rem; min-width:56px; text-align:center; font-family: var(--font-mono); }
.heatmap-away img { width:28px; height:28px; }
.heatmap-grid { flex:1; min-width:0; }
.heat-cell-lg { cursor: pointer; }
.heat-legend { font-size: 0.6rem; color: var(--text-muted); text-align: center; padding: 0.25rem 0; font-family: var(--font-mono); }
.heat-popup {
    display: none; position: fixed; z-index: 999;
    background: var(--card-bg); border: 1px solid var(--card-border);
    border-radius: 6px; padding: 0.6rem 0.8rem;
    font-size: 0.7rem; color: var(--text);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    max-width: 200px;
    font-family: var(--font-mono);
}
.heat-popup.show { display: block; }

/* ── Bottom navigation bar ── */
.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 100;
    background: var(--card-bg);
    border-top: 1px solid var(--card-border);
    display: flex;
    justify-content: space-around;
    align-items: center;
    padding: 0.15rem 0;
    padding-bottom: max(0.15rem, env(safe-area-inset-bottom));
    box-shadow: 0 -2px 10px var(--shadow-color);
}
.bottom-nav a {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.05rem;
    padding: 0.25rem 0.5rem;
    font-family: var(--font-body);
    font-size: 0.55rem;
    font-weight: 500;
    color: var(--text-muted);
    text-decoration: none;
    min-height: 44px;
    justify-content: center;
    border-radius: 6px;
    transition: color 0.15s;
    -webkit-tap-highlight-color: transparent;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}
.bottom-nav a:active { background: var(--hover-overlay); }
.bottom-nav a .nav-icon { font-size: 1rem; line-height: 1; }
.bottom-nav a.active { color: var(--accent); }
body { padding-bottom: 65px; }

/* ── Zebra cards ── */
.zebra-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 6px;
    padding: 1rem;
    margin: 0.75rem;
}
.zebra-card.upset { border-color: var(--danger); border-width: 1.5px; }
.zebra-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}
.zebra-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    font-family: var(--font-mono);
}
.zebra-badge.upset { background: var(--danger); color: #fff; }
.zebra-badge.favorite { background: var(--success); color: #fff; }
.zebra-matchup { font-family: var(--font-display); font-size: 1rem; font-weight: 600; margin-bottom: 0.25rem; letter-spacing: -0.01em; }
.zebra-detail { font-size: 0.8rem; color: var(--text-muted); line-height: 1.6; }
.zebra-players { margin-top: 0.5rem; font-size: 0.8rem; }
.zebra-players .tag {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    margin: 0.1rem;
    background: var(--accent-highlight);
    border-radius: 999px;
    font-size: 0.65rem;
    color: var(--accent);
    font-family: var(--font-mono);
}

/* ── Momentum / streak styles ── */
.streak-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid var(--card-border);
    font-size: 0.85rem;
}
.streak-row:last-child { border-bottom: none; }
.streak-name { flex: 1; font-weight: 600; font-family: var(--font-body); }
.streak-bar-mini {
    height: 5px;
    border-radius: 2px;
    flex: 0 0 80px;
    background: var(--card-border);
    overflow: hidden;
}
.streak-bar-mini .fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s;
}
.streak-bar-mini .fill.hot { background: var(--success); }
.streak-bar-mini .fill.cold { background: var(--danger); }
.streak-val { min-width: 30px; text-align: right; font-size: 0.7rem; font-weight: 700; font-family: var(--font-mono); }

/* ── Profile badge ── */
.profile-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    border: 1px solid var(--accent);
    background: var(--accent-highlight);
}

/* ── Trend indicators ── */
.trend-up { color: var(--success); }
.trend-down { color: var(--danger); }
.trend-flat { color: var(--text-muted); }

/* ── Hot streak indicator ── */
.hot-streak {
    display: inline-block;
    font-size: 0.85rem;
    animation: pulse-fire 1.5s ease-in-out infinite;
}
@keyframes pulse-fire {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.15); }
}

/* ── Mini stat columns ── */
.mini-stat { text-align: center; padding: 0.3rem; }
.mini-stat .val { font-family: var(--font-display); font-size: 1.2rem; font-weight: 600; color: var(--accent); letter-spacing: -0.02em; }
.mini-stat .lbl { font-size: 0.55rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }

/* ── Team logos ── */
.team-logo { width: 28px; height: 28px; object-fit: contain; vertical-align: middle; border-radius: 3px; }
.team-logo-sm { width: 24px; height: 24px; object-fit: contain; vertical-align: middle; border-radius: 2px; }
.team-logo-lg { width: 48px; height: 48px; object-fit: contain; vertical-align: middle; border-radius: 4px; }

/* ── Responsive ── */
@media (max-width: 359px) {
    .hero h1 { font-size: 1.3rem; }
    .hero .subtitle { font-size: 0.75rem; }
    .bottom-nav a { font-size: 0.5rem; }
    .bottom-nav a .nav-icon { font-size: 0.9rem; }
}
@media (min-width: 768px) {
    body { max-width: 800px; margin: 0 auto; }
    .stat-row { grid-template-columns: repeat(3, 1fr); }
}

/* ── Match hero ── */
.match-hero {
    background: var(--bg);
    padding: 1.25rem 1rem;
    text-align: center;
    border-bottom: 1px solid var(--card-border);
    position: relative;
}
.match-hero-teams {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
}
.match-hero-team {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.35rem;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 1.1rem;
    min-width: 80px;
}
.match-hero-link {
    color: var(--text);
    text-decoration: none;
}
.match-hero-link:hover {
    color: var(--accent);
    text-decoration: underline;
}
.score-hero {
    font-family: var(--font-mono);
    color: var(--accent);
    font-size: 2rem;
    font-weight: 700;
    min-width: 3rem;
    letter-spacing: 0.03em;
}
.score-hero--pending {
    color: var(--text-muted);
    font-size: 1.5rem;
    font-weight: 400;
}
.match-hero-meta {
    margin-top: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    flex-wrap: wrap;
}
.hero-date {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-muted);
}
.penalty-score {
    text-align: center;
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: -0.5rem;
    padding-bottom: 0.5rem;
    font-family: var(--font-mono);
}

/* ── Section divider ── */
.section-divider {
    border: none;
    border-top: 1px solid var(--card-border);
    margin: 0.75rem 0;
    opacity: 0.4;
}
.section-divider--wide {
    border: none;
    border-top: 1px solid var(--card-border);
    margin: 0.5rem 0.75rem;
    opacity: 0.3;
}

/* ── Section count badge ── */
.section-count {
    font-family: var(--font-mono);
    font-size: 0.6rem;
    color: var(--text-muted);
    background: var(--card-border);
    border-radius: 999px;
    padding: 0.1rem 0.5rem;
    font-weight: 600;
    margin-left: 0.35rem;
}
.section-subtitle {
    font-size: 0.7rem;
    color: var(--text-muted);
    padding: 0 0.75rem;
    margin-top: -0.25rem;
    margin-bottom: 0.5rem;
}

/* ── Compact card (player list) ── */
.card-compact .pred-row {
    padding: 0.5rem 0.75rem;
}

/* ── Group separator ── */
.score-group-sep {
    height: 1px;
    margin: 0.25rem 0.75rem;
    background: var(--card-border);
    opacity: 0.35;
}

/* ── Score pill small ── */
.score-pill--sm {
    font-size: 0.8rem;
    padding: 0.15rem 0.45rem;
    gap: 0.2rem;
}

/* ── Shared team img ── */
.score-card .team img,
.match-hero-team img {
    width:28px; height:28px;
    object-fit:contain; vertical-align:middle; border-radius:3px;
}
"""


def _bottom_nav_html(active: str = "", prefix: str = "", nav_items: list[dict] | None = None) -> str:
    """Build the fixed bottom navigation bar. 'active' should match a href.

    If ``nav_items`` is provided, it should be a list of dicts with keys
    ``href`` and ``label``.  Falls back to a hardcoded default list.
    """
    if nav_items:
        items = [(ni["href"], ni.get("icon", ""), ni["label"]) for ni in nav_items]
    else:
        items = [
            ("index.html", "\U0001f3e0", "In\u00edcio"),
            ("bolao_xray.html", "\U0001f50d", "Raio-X"),
            ("arena.html", "\u2694\ufe0f", "Arena"),
            ("zebras.html", "\U0001f993", "Zebras"),
            ("palpites.html", "\U0001f4cb", "Palpites"),
            ("boleiros.html", "\U0001f465", "Boleiros"),
        ]
    links = ""
    for href, icon, label in items:
        cls = ' class="active"' if active == href else ""
        links += f'<a href="{prefix}{href}"{cls}><span class="nav-icon">{icon}</span>{label}</a>\n'
    return f'<nav class="bottom-nav">{links}</nav>'


def _page_frame(config: ChampionshipConfig, title: str, body: str, back_link: str = "", active_nav: str = "", temperature: str = "") -> str:
    """Wrap body content in the standard HTML page frame.

    ``temperature`` can be a CSS color value; if provided, a 4px vertical
    bar is rendered at the left edge of the hero section as the page's
    signature element.
    """
    back_html = ""
    nav_prefix = ""
    if back_link:
        back_html = f'<div class="back-nav"><span style="color:var(--text-muted);">\u2192</span> <a href="{back_link}">Voltar</a></div>'
        idx = back_link.rfind("index.html")
        if idx >= 0:
            nav_prefix = back_link[:idx]

    tz = pytz.timezone(config.timezone)
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")

    script_src = nav_prefix + "sorttable.js" if back_link else "sorttable.js"

    # Temperature bar inline style: injected on the hero if present
    temp_style = f' style="--temp-color:{temperature};"' if temperature else ""

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
    {config.theme.to_css_vars()}
    {_CSS_BASE}
    </style>
</head>
<body{temp_style}>
{back_html}
{body}
<div style="text-align:center;padding:2rem 1rem 5rem;color:var(--text-muted);font-size:0.65rem;font-family:var(--font-mono);letter-spacing:0.02em;">
    atualizado \u00e0s {now_str}
</div>
{_bottom_nav_html(active_nav, nav_prefix, config.nav_items)}
<script src="{script_src}"></script>
</body>
</html>"""


def _save(filepath: str, content: str) -> None:
    """Write an HTML file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _initials(name: str) -> str:
    """Get initials from a name (max 2 chars)."""
    if not name or not name.strip():
        return ""
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def _avatar_html(name: str) -> str:
    """Generate an avatar circle with initials."""
    return f'<div class="pred-avatar">{_initials(name)}</div>'


def _max_points_per_game(config: ChampionshipConfig) -> int:
    """Return the maximum possible points for a single game."""
    if not config.scoring_rules:
        return 12
    return max(r.points for r in config.scoring_rules)


# ------------------------------------------------------------------
# Gold Dashboard — visual summary of gold-layer data per player
# ------------------------------------------------------------------


def _build_gold_dashboard(
    config: ChampionshipConfig,
    boleiro: str,
    df_bol: pd.DataFrame,
    total_pts: int,
    bonus_total: int,
    bonus_by_phase: dict[str, int],
    grand_total: int,
    avg_per_game: float,
    num_games: int,
    max_pts: int,
    player_zebra_cnt: int,
    phase_emoji_map: dict[str, str],
    gold_dir: str,
    exact_count: int = 0,
    avg_per_day: float = 0,
    rank: int = 0,
) -> str:
    """Build a compact KPI dashboard — phase breakdown + 3×3 KPI grid."""
    # ── Phase breakdown (subtle bars) ──
    phase_points: dict[str, int] = {}
    if not df_bol.empty and "phase" in df_bol.columns:
        for ph, grp in df_bol.groupby("phase", dropna=False):
            key = "1\u00aa Fase" if pd.isna(ph) else _short_name(ph, config)
            phase_points[key] = int(grp["pontos"].sum())
    else:
        phase_points["1\u00aa Fase"] = total_pts

    phase_bonus_display: dict[str, int] = {}
    for raw_key, bpts in bonus_by_phase.items():
        label = _short_name(raw_key, config) if raw_key else raw_key
        phase_bonus_display[label] = phase_bonus_display.get(label, 0) + bpts

    phase_order = ["1\u00aa Fase"] + [_short_name(pr.name, config) for pr in (config.playoff_rounds or [])]
    phase_order = [p for p in phase_order if p in phase_points or p in phase_bonus_display]
    if not phase_order:
        phase_order = list(phase_points.keys())
    phase_cards = ""
    for p in phase_order:
        pts = phase_points.get(p, 0)
        bns = phase_bonus_display.get(p, 0)
        if pts + bns == 0:
            continue
        phase_cards += (
            f'<span style="font-size:0.65rem;background:var(--card-border);'
            f'border-radius:4px;padding:0.15rem 0.4rem;white-space:nowrap;">'
            f'{p} j{pts}{f" b{bns}" if bns else ""}</span>\n'
        )

    phase_row_html = (
        f'<div style="display:flex;flex-wrap:wrap;gap:0.25rem;padding-bottom:0.2rem;">'
        f'{phase_cards}</div>'
    )

    # ── Key KPIs (3×3 grid) ──
    # Use the full ranking (match + playoff + bonus - penalty) computed upstream
    # so the boleiro page shows the same rank as the index page.
    rank_val = f"{rank}\u00ba" if rank > 0 else "-"

    # Ousadia (boldness)
    boldness_label = "\u2014"
    bold_path = _norm(os.path.join(gold_dir, "boldness_index.csv"))
    if os.path.exists(bold_path):
        df_b = pd.read_csv(bold_path, sep=",")
        df_bp = df_b[df_b["boleiro"] == boleiro]
        if not df_bp.empty:
            bv = float(df_bp.iloc[0]["boldness_score"])
            if bv > 0.3:
                boldness_label = f"+{bv:.2f}"
            elif bv < -0.3:
                boldness_label = f"{bv:.2f}"
            else:
                boldness_label = f"{bv:+.2f}"

    approval_pct = round(total_pts / (num_games * max_pts) * 100, 1) if num_games > 0 else 0

    kpis = [
        ("\U0001f3c6", "Total", str(grand_total)),
        ("\U0001f4ca", "M\u00e9dia", f"{avg_per_game}"),
        ("\U0001f3af", "Rank", rank_val),
        ("\U0001f4c8", "Aprov%", f"{approval_pct}%"),
        ("\U0001f993", "Zebras", str(player_zebra_cnt)),
        ("\U0001f3af", "Placar Exato", str(exact_count)),
        ("\U0001f4a5", "Ousadia", boldness_label),
        ("\U0001f3c6", "B\u00f4nus", f"+{bonus_total}"),
        ("\u26bd", "Jogos", str(num_games)),
    ]

    kpi_html = ""
    for icon, label, value in kpis:
        kpi_html += (
            f'<div class="stat-card">'
            f'<div style="font-size:0.6rem;color:var(--text-muted);margin-bottom:0.05rem;">{icon} {label}</div>'
            f'<div class="value" style="font-size:0.95rem;">{value}</div>'
            f'</div>\n'
        )

    return f"""
<div class="section">
    <div class="section-title">\U0001f4ca Resumo</div>
    <div class="card" style="padding:0.5rem;">
        {phase_row_html}
        <div class="stat-row" style="grid-template-columns:repeat(3,1fr);margin-top:0.35rem;padding:0;">
            {kpi_html}
        </div>
    </div>
</div>
"""


from src.core.logo_fetcher import _team_logo_tag


# ------------------------------------------------------------------
# Per-player page
# ------------------------------------------------------------------

def _build_boleiro(config: ChampionshipConfig, boleiro: str, rank: int = 0) -> str:
    """Build a per-player HTML report."""
    if os.path.exists(config.gold_valid_path()):
        df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
        if df_valid.empty:
            df_valid = pd.read_csv(config.gold_all_path(), sep=",")
    else:
        df_valid = pd.read_csv(config.gold_all_path(), sep=",")
    striker_path = config.playoff_strikers_path()
    if os.path.exists(striker_path):
        df_striker = pd.read_csv(striker_path, sep=",")
    else:
        df_striker = pd.DataFrame(columns=["boleiro", "striker"])
    max_pts = _max_points_per_game(config)
    gold_dir = config._au_first_round()

    df_bol = df_valid.loc[df_valid["who"] == boleiro].copy()

    # --- Load playoff predictions for this player ---
    playoff_parts = []
    playoff_all_parts: list[pd.DataFrame] = []  # all players' valid data for bolão avg
    for pr in (config.playoff_rounds or []):
        phase_valid_path = config.gold_playoff_valid_path(pr.key)
        if os.path.exists(phase_valid_path):
            df_phase = pd.read_csv(phase_valid_path, sep=",")
            df_phase_player = df_phase[df_phase["who"] == boleiro]
            if not df_phase_player.empty:
                playoff_parts.append(df_phase_player)
            playoff_all_parts.append(df_phase)

    if playoff_parts:
        df_playoff = pd.concat(playoff_parts, ignore_index=True)
        df_bol = pd.concat([df_bol, df_playoff], ignore_index=True)

    sort_col_bol = ["id"] if "id" in df_bol.columns else ["date", "hour"]
    df_bol = df_bol.sort_values(sort_col_bol, ascending=True)
    df_bol["pontos_acumulados"] = df_bol["pontos"].cumsum()

    # Load bonus points (playoff team picks) — not included in df_bol/pontos
    bonus_total = 0
    bonus_by_phase: dict[str, int] = {}
    bonus_csv = _norm(os.path.join(config._au_first_round(), "playoffs_scored.csv"))
    if os.path.exists(bonus_csv):
        df_bonus_all = pd.read_csv(bonus_csv, sep=",")
        df_bonus_player = df_bonus_all[df_bonus_all["boleiro"] == boleiro]
        if not df_bonus_player.empty:
            bonus_total = int(df_bonus_player["points"].sum())
            for _, row in df_bonus_player.iterrows():
                ph = str(row["phase"])
                bonus_by_phase[ph] = bonus_by_phase.get(ph, 0) + int(row["points"])

    total_pts = int(df_bol["pontos"].sum())
    penalty_pts = config.total_penalty(boleiro)
    avg_per_game = round(df_bol["pontos"].mean(), 1) if len(df_bol) > 0 else 0
    num_games = len(df_bol)
    num_days = df_bol["date"].nunique()
    avg_per_day = round(total_pts / num_days, 1) if num_days > 0 else 0

    # Striker
    striker_name = ""
    df_st = df_striker.loc[df_striker["boleiro"] == boleiro]
    if not df_st.empty:
        striker_name = str(df_st.iloc[0]["striker"])

    # Points by date with max possible context
    df_by_date = df_bol.groupby("date", as_index=False)["pontos"].sum()
    df_by_date["date_dt"] = pd.to_datetime(df_by_date["date"])
    df_by_date["date_str"] = df_by_date["date_dt"].dt.strftime("%d/%m")

    # Calculate max possible per day for this player
    df_games_count = df_bol.groupby("date").size().reset_index(name="num_games")
    df_games_count["max_possible"] = df_games_count["num_games"] * max_pts
    df_by_date = df_by_date.merge(df_games_count[["date", "max_possible"]], on="date")

    timeline_bars = ""
    if not df_by_date.empty:
        max_date_pts = df_by_date["pontos"].max()
        if max_date_pts > 0:
            for _, row in df_by_date.iterrows():
                pts = int(row["pontos"])
                max_p = int(row["max_possible"])
                pct_of_max = round(pts / max_p * 100) if max_p > 0 else 0
                pct_bar = pct_of_max
                timeline_bars += (
                    f'<div class="bar-row">'
                    f'<span class="bar-label">{row["date_str"]}</span>'
                    f'<div class="bar-track"><div class="bar-fill" style="width:{pct_bar}%"></div></div>'
                    f'<span class="bar-pct">{pts}/{max_p} ({pct_of_max}%)</span>'
                    f'</div>\n'
                )

    # Build combined valid dataset for bolão average (group + playoffs)
    parts_to_concat = [df_valid] + [p for p in playoff_all_parts if not p.empty]
    if parts_to_concat:
        df_all_valid = pd.concat(parts_to_concat, ignore_index=True)
    else:
        df_all_valid = df_valid

    # Ensure numeric dtype for pontos (empty playoff CSVs cause object dtype)
    df_all_valid["pontos"] = pd.to_numeric(df_all_valid["pontos"], errors="coerce").fillna(0).astype(int)

    # Player pts/day vs bolão avg/day (raw, not moving average)
    df_all_by_date = df_all_valid.groupby("date", as_index=False).agg(
        total_pts=("pontos", "sum"),
        num_players=("who", "nunique")
    )
    df_all_by_date["bolao_avg"] = (df_all_by_date["total_pts"] / df_all_by_date["num_players"]).round(1)
    df_all_by_date["date_str"] = pd.to_datetime(df_all_by_date["date"]).dt.strftime("%d/%m")

    df_player_by_date = df_bol.groupby("date", as_index=False)["pontos"].sum()
    df_player_by_date.columns = ["date", "player_pts"]

    df_compare = df_all_by_date[["date", "date_str", "bolao_avg"]].merge(
        df_player_by_date[["date", "player_pts"]], on="date", how="left"
    )
    df_compare["player_pts"] = df_compare["player_pts"].fillna(0)
    df_compare = df_compare.sort_values("date")

    compare_bars = ""
    if not df_compare.empty:
        max_val = max(df_compare["player_pts"].max(), df_compare["bolao_avg"].max())
        if max_val > 0:
            for _, row in df_compare.iterrows():
                p_pts = row["player_pts"]
                b_avg = row["bolao_avg"]
                p_pct = round(p_pts / max_val * 100)
                b_pct = round(b_avg / max_val * 100)
                diff = p_pts - b_avg
                diff_color = "var(--voce)" if diff >= 0 else "var(--bolao)"
                diff_icon = "\u25b2" if diff >= 0 else "\u25bc"
                compare_bars += (
                    f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.3rem;font-size:0.8rem;">'
                    f'<span style="min-width:40px;color:var(--text-muted)">{row["date_str"]}</span>'
                    f'<div style="flex:1;">'
                    f'<div style="display:flex;align-items:center;gap:0.25rem;">'
                    f'<span style="min-width:40px;color:var(--voce)">Voce</span>'
                    f'<div class="bar-track" style="height:14px;"><div class="bar-fill" style="width:{p_pct}%;background:var(--voce)"></div></div>'
                    f'<span style="min-width:30px;text-align:right">{p_pts}</span>'
                    f'</div>'
                    f'<div style="display:flex;align-items:center;gap:0.25rem;">'
                    f'<span style="min-width:40px;color:var(--bolao)">Bolao</span>'
                    f'<div class="bar-track" style="height:14px;"><div class="bar-fill" style="width:{b_pct}%;background:var(--bolao)"></div></div>'
                    f'<span style="min-width:30px;text-align:right">{b_avg}</span>'
                    f'</div>'
                    f'</div>'
                    f'<span style="color:{diff_color};min-width:40px;text-align:right;font-weight:700">{diff_icon}{abs(diff):.1f}</span>'
                    f'</div>\n'
                )

    boleiro_dir = _norm(os.path.join(config.reports_dir, "html", "boleiros"))

    # --- Detect pending matches (past but no result) for this player ---
    # Covers group phase AND all playoff phases.
    n_pending = 0
    pending_rows = ""
    df_player_all = pd.DataFrame()
    _player_parts: list[pd.DataFrame] = []
    all_path = config.gold_all_path()
    if os.path.exists(all_path):
        df_all = pd.read_csv(all_path, sep=",")
        _player_parts.append(df_all[df_all["who"] == boleiro].copy())
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_all_path(pr.key)
        if os.path.exists(pp):
            df_pp = pd.read_csv(pp, sep=",")
            _player_parts.append(df_pp[df_pp["who"] == boleiro].copy())
    if _player_parts:
        df_player_all = pd.concat(_player_parts, ignore_index=True)
        tz = pytz.timezone(config.timezone)
        today_dt = datetime.now(tz).date()
        df_player_all["date_dt"] = pd.to_datetime(df_player_all["date"], errors="coerce")
        df_pending = df_player_all[
            (df_player_all.get("valido", 0) == 0)
            & (df_player_all["date_dt"].dt.date < today_dt)
        ].drop_duplicates(subset=["match"])
        n_pending = len(df_pending)
        if n_pending:
            rev_map = {v: k for k, v in config.team_name_mapping.items()}
            sort_col_pending = ["id"] if "id" in df_pending.columns else ["date", "hour"]
            for _, row in df_pending.sort_values(sort_col_pending, ascending=False).iterrows():
                date_str = pd.to_datetime(row["date"]).strftime("%d/%m") + (f" {row['hour']}" if pd.notna(row.get("hour")) and str(row.get("hour", "")).strip() else "")
                home_en = rev_map.get(row["home_team"], row["home_team"])
                away_en = rev_map.get(row["away_team"], row["away_team"])
                home_logo = _team_logo_tag(home_en, config, cls="team-logo-sm", start=boleiro_dir)
                away_logo = _team_logo_tag(away_en, config, cls="team-logo-sm", start=boleiro_dir)
                match_slug = str(row.get("match", ""))
                hour_p = str(row.get("hour", ""))
                phase_v = str(row.get("phase", "")) if row.get("phase") else config.group_phase_label
                game_href = f"../jogos/{phase_v}/{row['date'].strip()}_{hour_p}_{match_slug}.html"
                pending_rows += (
                    f'<div class="pred-row">'
                    f'<div class="pred-info">'
                    f'<div class="pred-name"><a href="{game_href}" style="color:var(--text);text-decoration:none;">{home_logo}{row["home_team"]} vs {away_logo}{row["away_team"]}</a> <span class="pred-date">{date_str}</span></div>'
                    f'<div class="pred-detail">Previsto: {row["resultado_bol_placar"]} | \u23f3 Aguardando resultado | <a href="{game_href}" style="color:var(--accent);">ver jogo</a></div>'
                    f'</div>'
                    f'<div class="score-pill" style="color:var(--warning);background:rgba(245,158,11,0.1);border:1px solid var(--warning)">+0 \u23f3</div>'
                    f'</div>\n'
                )

    # Match history rows (newest first)
    playoff_emoji_map = dict(config.phase_emojis) if config.phase_emojis else {"segunda_fase": "\U0001f3c6", "oitavas": "\U0001f3c1", "quartas": "\U0001f525", "semi": "\U0001f3af", "terceiro_lugar": "\U0001f949", "final": "\U0001f3c6"}
    sort_col_hist = ["id"] if "id" in df_bol.columns else ["date", "hour"]
    df_hist = df_bol.sort_values(sort_col_hist, ascending=False)

    def _format_real_placar(row: pd.Series) -> str:
        """Format the real scoreline, handling NaN gracefully."""
        rrp = row.get("resultado_real_placar", "")
        if pd.isna(rrp) or str(rrp).strip().lower() in ("nan", "", "none"):
            return f'{row["home_team"]} vs {row["away_team"]}'
        return f'{row["home_team"]} {rrp} {row["away_team"]}'

    # Pre-compute per-match ranking for all players (group + playoff)
    match_ranks: dict[str, dict[str, int]] = {}
    def _add_match_ranks(df: pd.DataFrame) -> None:
        if "match" not in df.columns:
            return
        for match_slug, grp in df[df["match"].notna()].groupby("match"):
            if not match_slug:
                continue
            ranked = grp.sort_values("pontos", ascending=False)
            rank_map: dict[str, int] = {}
            current_rank = 1
            prev_pts = None
            for i, (_, r) in enumerate(ranked.iterrows()):
                p = int(r["pontos"])
                if prev_pts is not None and p < prev_pts:
                    current_rank = i + 1
                rank_map[str(r["who"])] = current_rank
                prev_pts = p
            match_ranks[str(match_slug)] = rank_map
    _add_match_ranks(df_valid)
    for pr in (config.playoff_rounds or []):
        path = config.gold_playoff_valid_path(pr.key)
        if os.path.exists(path):
            _add_match_ranks(pd.read_csv(path, sep=","))

    # Load upset data for zebra indicators in match history
    upset_set: set[str] = set()
    upset_wwpct: dict[str, int] = {}
    upset_num_correct: dict[str, int] = {}
    player_zebra_cnt = 0
    player_zebra_correct_set: set[str] = set()
    upset_path_br = _norm(os.path.join(config._au_first_round(), "upset_tracker.csv"))
    if os.path.exists(upset_path_br):
        try:
            df_upset_br = pd.read_csv(upset_path_br, sep=",")
        except pd.errors.EmptyDataError:
            df_upset_br = pd.DataFrame()
        for _, ur in df_upset_br.iterrows():
            if int(ur.get("is_upset", 0)) == 1:
                ms = str(ur["match"])
                upset_set.add(ms)
                upset_wwpct[ms] = int(ur.get("winner_wrong_pct", 0))
                upset_num_correct[ms] = int(ur.get("num_correct", 0))
                if boleiro in [p.strip() for p in str(ur.get("players_correct", "")).split("|") if p.strip()]:
                    player_zebra_cnt += 1
                    player_zebra_correct_set.add(ms)

    def _build_history_rows(rows_df: pd.DataFrame) -> str:
        rev_map = {v: k for k, v in config.team_name_mapping.items()}
        out = ""
        for _, row in rows_df.iterrows():
            pts = int(row["pontos"])
            hour_str = str(row.get("hour", ""))
            date_str = pd.to_datetime(row["date"]).strftime("%d/%m") + (f" {hour_str}" if hour_str else "")
            criterio_emoji = config.scoring_emoji(row.get("criterio", ""))
            css_var, css_bg, css_border = config.scoring_css_var(row.get("criterio", ""))
            if css_var:
                pts_color = css_var
                pts_bg = css_bg
                pts_border = css_border
            else:
                hex_color = config.scoring_color(row.get("criterio", ""))
                if hex_color:
                    pts_color = hex_color
                    pts_bg = hex_color + "1a"
                    pts_border = hex_color + "40"
                else:
                    pts_color = "var(--text-muted)"
                    pts_bg = "transparent"
                    pts_border = "var(--card-border)"
            # Phase indicator for playoff matches
            phase_label = ""
            phase_val = row.get("phase", "")
            if phase_val and phase_val in playoff_emoji_map:
                phase_label = f"{playoff_emoji_map[phase_val]} {phase_val} | "
            home_en = rev_map.get(row["home_team"], row["home_team"])
            away_en = rev_map.get(row["away_team"], row["away_team"])
            home_logo = _team_logo_tag(home_en, config, cls="team-logo-sm", start=boleiro_dir)
            away_logo = _team_logo_tag(away_en, config, cls="team-logo-sm", start=boleiro_dir)
            # Game link
            match_slug = str(row.get("match", ""))
            phase_v = str(phase_val) if phase_val else config.group_phase_label
            game_href = f"../jogos/{phase_v}/{row['date']}_{hour_str}_{match_slug}.html"
            # Player rank for this match
            rank_str = ""
            if match_slug in match_ranks:
                player_rank = match_ranks[match_slug].get(boleiro)
                if player_rank is not None:
                    rank_str = f"{player_rank}\u00ba lugar | "
            # Zebra badge for upset matches — indicates if THIS player got it right
            zebra_tag = ""
            if match_slug in upset_set:
                nc = upset_num_correct.get(match_slug, 999)
                zebra_emoji = ZEBRA_MONSTRA_EMOJI if nc <= 2 else ZEBRA_GRANDE_EMOJI
                if match_slug in player_zebra_correct_set:
                    zebra_tag = f' <span style="font-size:0.7rem;color:var(--accent);font-weight:600;">{zebra_emoji} Acertou!</span>'
                else:
                    zebra_tag = f' <span style="font-size:0.7rem;color:var(--text-muted);">{zebra_emoji}</span>'
            out += (
                f'<div class="pred-row">'
                f'<div class="pred-info">'
                f'<div class="pred-name"><a href="{game_href}" style="color:var(--text);text-decoration:none;">{_format_real_placar(row)}</a> <span class="pred-date">{phase_label}{date_str}</span></div>'
            f'<div class="pred-detail">{home_logo} {row["resultado_bol_placar"]} {away_logo} | {criterio_emoji} {row["criterio"]}{zebra_tag} | {rank_str}<a href="{game_href}" style="color:var(--accent);">ver jogo</a></div>'
                f'</div>'
                f'<div class="score-pill" style="color:{pts_color};background:{pts_bg};border:1px solid {pts_border}">+{pts} {criterio_emoji}</div>'
                f'</div>\n'
            )
        return out

    tz = pytz.timezone(config.timezone)
    today = datetime.now(tz).date()

    # Sort key: prefer 'id' column if available, fall back to date+hour
    sort_col_future = ["id"] if "id" in df_hist.columns else ["date", "hour"]
    sort_col_all    = ["id"] if "id" in df_player_all.columns else ["date", "hour"]

    # Matches with results (valido == 1) go to past, even if today (finished/live).
    # Unvalidated matches (valido == 0) with future date go to future.
    df_by_date_dt = df_hist["date"].apply(lambda d: pd.to_datetime(d).date())
    df_hist_past = df_hist[df_hist.get("valido", 0) == 1].copy()
    df_hist_future = df_hist[
        (df_hist.get("valido", 0) == 0) & (df_by_date_dt >= today)
    ].sort_values(sort_col_future, ascending=True)

    # Include ALL future predictions (valido=0, date >= today) from gold_all + playoffs as "Jogos Futuros"
    if not df_player_all.empty:
        df_future_preds = df_player_all[
            (df_player_all.get("valido", 0) == 0)
            & (pd.to_datetime(df_player_all["date"], errors="coerce").dt.date >= today)
        ].drop_duplicates(subset=["match"]).sort_values(sort_col_all, ascending=True)
        if len(df_future_preds):
            # Merge any matches not already in df_hist_future
            existing_slugs = set(df_hist_future["match"].unique()) if len(df_hist_future) else set()
            new_preds = df_future_preds[~df_future_preds["match"].isin(existing_slugs)]
            df_hist_future = pd.concat(
                [df_hist_future, new_preds], ignore_index=True
            ).sort_values(sort_col_future, ascending=True)

    # Exclude pending matches from past (they'll be shown in pending section)
    pending_slug_set = set()
    if n_pending and not df_player_all.empty:
        df_pending_p = df_player_all[
            (df_player_all.get("valido", 0) == 0)
        ]
        pending_slug_set = set(df_pending_p["match"].unique())
        if pending_slug_set:
            df_hist_past = df_hist_past[~df_hist_past["match"].isin(pending_slug_set)]

    n_past = len(df_hist_past)
    n_future = len(df_hist_future)

    history_rows_past = _build_history_rows(df_hist_past) if n_past else ""
    history_rows_future = _build_history_rows(df_hist_future) if n_future else '<div style="color:var(--text-muted);font-size:0.85rem;padding:0.3rem 0;">Nenhum jogo futuro.</div>'

    # ── Compute extra player metrics ──
    scored_games = int((df_bol["pontos"] > 0).sum()) if len(df_bol) else 0
    bonus_pts_only = bonus_total  # already separate bonus total

    grand_total = total_pts + bonus_total - penalty_pts

    penalty_section = ""
    if penalty_pts > 0:
        boleiro_cfg = config.boleiros.get(boleiro)
        detail_rows = ""
        if boleiro_cfg and boleiro_cfg.penalties:
            for p in boleiro_cfg.penalties:
                if p.value <= 0:
                    continue
                phase_tag = (
                    f'<span style="font-size:0.65rem;color:var(--text-muted);'
                    f'background:var(--card-bg);border:1px solid var(--card-border);'
                    f'padding:0.1rem 0.45rem;border-radius:999px;white-space:nowrap;">'
                    f'{p.phase}</span>'
                ) if p.phase else ""
                reason_html = (
                    f'<span style="flex:1;font-size:0.8rem;">{p.reason}</span>'
                ) if p.reason else '<span style="flex:1;"></span>'
                detail_rows += (
                    f'<div style="display:flex;align-items:center;gap:0.5rem;'
                    f'padding:0.45rem 0;">'
                    f'<span style="background:var(--danger);color:white;'
                    f'font-size:0.7rem;font-weight:700;padding:0.15rem 0.45rem;'
                    f'border-radius:999px;white-space:nowrap;">-{p.value}</span>'
                    f'{reason_html}{phase_tag}</div>\n'
                )
            if detail_rows:
                detail_rows = f'<div style="border-top:1px solid var(--card-border);margin-top:0.35rem;padding-top:0.15rem;">{detail_rows}</div>'
        penalty_section = (
            f'<div class="card" style="margin-top:0.5rem;border-color:var(--danger);">'
            f'<div style="display:flex;align-items:center;justify-content:space-between;">'
            f'<span style="font-size:0.85rem;font-weight:600;color:var(--danger);">'
            f'\u26a0 Penalidade</span>'
            f'<span style="font-size:1.1rem;font-weight:700;color:var(--danger);">-{penalty_pts}</span>'
            f'</div>{detail_rows}</div>'
        )

    body = f"""
<div class="hero">
    <h1>\U0001f464 {boleiro}</h1>
    <div class="subtitle">{config.report_title}</div>
</div>

{penalty_section}
"""

    # --- Scoring distribution per criteria (bar chart) ---
    rule_order = config.scoring_rule_names()
    rule_map = config.scoring_dict()
    n_preds = len(df_bol)
    criteria_counts = df_bol["criterio"].value_counts()
    largest_cnt = max((int(criteria_counts.get(t, 0)) for t in rule_order), default=1)
    dist_rows = ""
    for t in rule_order:
        cnt = int(criteria_counts.get(t, 0))
        pts_per = rule_map.get(t, 0)
        pct = round(cnt / n_preds * 100, 1) if n_preds else 0
        bar_w = max(cnt / largest_cnt * 100, 1)
        name_part = t.split("-", 1)[1] if "-" in t else t
        label = f"{name_part} (+{pts_per}p)" if pts_per > 0 else name_part
        color = config.scoring_color(t)
        emoji = config.scoring_emoji(t)
        dist_rows += f"""
        <tr>
            <td style="padding:0.3rem 0.5rem;"><span style="color:{color};font-weight:700;">{emoji}</span> {label}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;font-weight:600;">{cnt}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;color:var(--text-muted);">{pct}%</td>
            <td style="padding:0.3rem 0.5rem;width:30%;"><div class="bar-track"><div class="bar-fill" style="width:{bar_w:.0f}%;background:{color};height:10px;"></div></div></td>
        </tr>"""
    # Zebra row in distribution
    z_pct = round(player_zebra_cnt / n_preds * 100, 1) if n_preds else 0
    z_bar_w = max(player_zebra_cnt / largest_cnt * 100, 1) if player_zebra_cnt else 0
    dist_rows += f"""
        <tr>
            <td style="padding:0.3rem 0.5rem;"><span style="color:var(--danger);font-weight:700;">\U0001f993</span> Zebra acertada</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;font-weight:600;color:var(--danger);">{player_zebra_cnt}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;color:var(--text-muted);">{z_pct}%</td>
            <td style="padding:0.3rem 0.5rem;width:30%;"><div class="bar-track"><div class="bar-fill" style="width:{z_bar_w:.0f}%;background:var(--danger);height:10px;"></div></div></td>
        </tr>"""
    # Store scoring distribution HTML for later (show after phase table)
    _dist_html = f"""
<div class="section">
    <div class="section-title">\U0001f3af Distribui\u00e7\u00e3o de Acertos ({n_preds})</div>
    <div class="card">
        <table data-sortable style="width:100%;border-collapse:collapse;">
            {dist_rows}
        </table>
    </div>
</div>
"""

    # ------------------------------------------------------------------
    # Bonus teams for knockout phases — at top, colored by result, scored
    # ------------------------------------------------------------------
    bonus_html = ""
    champion_team = ""  # Must be defined here — used later (line ~1224) outside if blocks
    bonus_path = config.bronze_bonus_path(boleiro)
    if os.path.exists(bonus_path):
        df_bonus = pd.read_csv(bonus_path, sep=",")
        if not df_bonus.empty and os.path.exists(config.games_file):
            df_games = pd.read_csv(config.games_file, sep=",")
            df_games["round"] = df_games["round"].astype(str).str.strip()
            playoff_keys = [pr.key for pr in (config.playoff_rounds or [])]

            # Determine today's date in the configured timezone
            tz = pytz.timezone(config.timezone)
            today = datetime.now(tz).date()

            # For each phase: find participants (teams that have a match),
            # latest match date, winners, and whether all matches finished.
            phase_participants: dict[str, set[str]] = {}
            phase_latest_date: dict[str, datetime | None] = {}
            advancing: dict[str, list[str]] = {}
            phase_consumed: dict[str, bool] = {}
            phase_team_known: dict[str, dict[str, bool]] = {}  # per-team result-known map
            participants_complete: dict[str, bool] = {}
            for pk in playoff_keys:
                phase_matches = df_games[df_games["round"] == pk]
                winners: list[str] = []
                dates: list[datetime] = []
                all_finished = True
                participants: set[str] = set()
                team_result_known: dict[str, bool] = {}
                for _, row in phase_matches.iterrows():
                    ht = str(row["home_team"])
                    at = str(row["away_team"])
                    participants.add(ht)
                    participants.add(at)

                    # Use goals data as primary source of truth for match completion
                    hg = float(row["home_goals"]) if pd.notna(row.get("home_goals")) else None
                    ag = float(row["away_goals"]) if pd.notna(row.get("away_goals")) else None
                    has_goals = hg is not None and ag is not None
                    team_result_known[ht] = has_goals
                    team_result_known[at] = has_goals
                    if not has_goals:
                        all_finished = False

                    raw_date = str(row.get("date", ""))
                    date_part = raw_date[:10] if " " in raw_date else raw_date
                    try:
                        d = pd.to_datetime(date_part).date()
                        dates.append(d)
                    except (ValueError, TypeError):
                        pass
                    if has_goals:
                        if hg > ag:
                            winners.append(ht)
                        elif ag > hg:
                            winners.append(at)
                        else:
                            hp = row.get("home_pen", "")
                            ap = row.get("away_pen", "")
                            try:
                                hp_v = float(hp) if pd.notna(hp) and str(hp).strip() else None
                                ap_v = float(ap) if pd.notna(ap) and str(ap).strip() else None
                            except (ValueError, TypeError):
                                hp_v = ap_v = None
                            if hp_v is not None and ap_v is not None:
                                if hp_v > ap_v:
                                    winners.append(ht)
                                elif ap_v > hp_v:
                                    winners.append(at)
                            elif hp_v is not None:
                                winners.append(ht)
                            elif ap_v is not None:
                                winners.append(at)
                phase_participants[pk] = participants
                advancing[pk] = winners
                phase_latest_date[pk] = max(dates) if dates else None
                phase_consumed[pk] = all_finished
                phase_team_known[pk] = team_result_known
                # Check if all match slots have defined team names (no -vs- placeholder)
                participants_complete[pk] = all(
                    str(row.get("home_team", "")).strip() not in ("-vs-", "", "nan")
                    and str(row.get("away_team", "")).strip() not in ("-vs-", "", "nan")
                    for _, row in phase_matches.iterrows()
                )

            phase_order = [pr.key for pr in (config.playoff_rounds or [])]
            # Map each phase to its immediate predecessor in playoff order
            prev_phase_map = {}
            for i, pk in enumerate(phase_order):
                if i > 0:
                    prev_phase_map[pk] = phase_order[i - 1]
            phase_label_map = {pr.key: pr.name for pr in (config.playoff_rounds or [])}
            phase_emoji_map = dict(config.phase_emojis) if config.phase_emojis else {
                "segunda_fase": "\U0001f3c6",
                "oitavas": "\U0001f3c1",
                "quartas": "\U0001f525",
                "semi": "\U0001f3af",
                "terceiro_lugar": "\U0001f949",
                "final": "\U0001f3c6",
            }
            playoff_scoring = getattr(config, "playoff_scoring", {})

            df_bonus["phase_order"] = df_bonus["phase"].map(
                {k: i for i, k in enumerate(phase_order)}
            ).fillna(99)
            df_bonus = df_bonus.sort_values(["phase_order", "team"])

            total_bonus_pts = 0
            phase_blocks = ""
            champion_team = ""
            # Exclude champion phase from the general phase blocks loop to handle it separately
            for phase_key, group in df_bonus[df_bonus["phase"] != config.champion_phase_key].groupby("phase", sort=False):
                label = phase_label_map.get(phase_key, phase_key)
                emoji = phase_emoji_map.get(phase_key, "\u26bd")
                pts_per_correct = playoff_scoring.get(phase_key, 0)
                advancing_teams = advancing.get(phase_key, [])

                is_first_knockout = (phase_key == config.playoff_rounds[0].key) if config.playoff_rounds else False
                participants = phase_participants.get(phase_key, set())

                # For the first knockout round, checkable is always True
                # (group stage is done, we know which teams qualified).
                # "Display passed" = team is a participant (qualified for this round).
                # Scoring uses participants for all non-champion phases (matches scoring.py).
                if is_first_knockout:
                    checkable = True
                else:
                    checkable = phase_consumed.get(phase_key, False)

                # Visual coloring: use participants to determine green/red even before phase finishes
                # If we know which teams are in this phase, show green/red; otherwise yellow.
                has_phase_teams = bool(participants)

                phase_pts = 0
                correct_count = 0
                total_count = 0
                teams_list = ""
                for _, row in group.iterrows():
                    team = row["team"]
                    total_count += 1
                    # All non-champion phases: points based on participation (team reached this phase)
                    # This matches score_playoff_bonus() in scoring.py which uses participants for
                    # all phases except champion (which uses advancing winners).
                    if is_first_knockout:
                        passed = team in participants
                    else:
                        passed = team in participants
                    if passed:
                        phase_pts += pts_per_correct
                        correct_count += 1

                    # Visual coloring:
                    #   has_phase_teams=False → orange (no info / phase not set up)
                    #   passed=True           → green  (team reached this phase)
                    #   participants_complete → red   (all slots filled, team not one of them)
                    #   previous-phase elimination known → red (team lost earlier round)
                    #   otherwise             → orange (fate still undecided)
                    if not has_phase_teams:
                        _bg, _border, _color = "rgba(234,179,8,0.15)", "var(--warning)", "var(--warning)"
                    elif is_first_knockout:
                        display_passed = team in participants
                        _bg, _border, _color = ("rgba(34,197,94,0.15)", "var(--success)", "var(--success)") if display_passed else ("rgba(239,68,68,0.15)", "var(--danger)", "var(--danger)")
                    else:
                        if passed:
                            _bg, _border, _color = "rgba(34,197,94,0.15)", "var(--success)", "var(--success)"
                        elif participants_complete.get(phase_key, False):
                            # All slots filled → non-participants are definitely out
                            _bg, _border, _color = "rgba(239,68,68,0.15)", "var(--danger)", "var(--danger)"
                        else:
                            # Check if team is known to be eliminated from any prior phase
                            _eliminated = False
                            _phase_idx = phase_order.index(phase_key) if phase_key in phase_order else -1
                            if _phase_idx > 0:
                                for _j in range(_phase_idx):
                                    _prev = phase_order[_j]
                                    _prev_part = phase_participants.get(_prev, set())
                                    _prev_adv = set(advancing.get(_prev, []))
                                    _prev_known = phase_team_known.get(_prev, {})
                                    _prev_complete = participants_complete.get(_prev, False)
                                    if _prev_complete and team not in _prev_part:
                                        _eliminated = True
                                        break
                                    if team in _prev_part and team not in _prev_adv and _prev_known.get(team, False):
                                        _eliminated = True
                                        break
                            if _eliminated:
                                _bg, _border, _color = "rgba(239,68,68,0.15)", "var(--danger)", "var(--danger)"
                            else:
                                _bg, _border, _color = "rgba(234,179,8,0.15)", "var(--warning)", "var(--warning)"
                    teams_list += (
                        f'<span style="display:inline-block;padding:0.2rem 0.6rem;margin:0.15rem;'
                        f'background:{_bg};border:1px solid {_border};border-radius:999px;'
                        f'font-size:0.75rem;color:{_color};">{team}</span>'
                    )

                total_bonus_pts += phase_pts
                acc_str = f'{correct_count}/{total_count}' if total_count else ''
                if checkable and not is_first_knockout:
                    pts_label = f'<span style="color:var(--accent);font-weight:700;">+{phase_pts}</span>'
                else:
                    pts_label = f'<span style="color:var(--warning);font-weight:700;">\u23f3 +{phase_pts}</span>'
                phase_blocks += (
                    f'<div style="margin-bottom:0.5rem;">'
                    f'<div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.3rem;">'
                    f'{emoji} {label} {pts_label}'
                    f'<span style="margin-left:0.5rem;font-size:0.75rem;">{acc_str}</span></div>'
                    f'<div>{teams_list}</div>'
                    f'</div>\n'
                )

            # Champion block is separate and should be shown if available, regardless of other phases
            champion_row = df_bonus[df_bonus["phase"] == config.champion_phase_key]
            champion_team = champion_row.iloc[0]["team"] if not champion_row.empty else ""
            if champion_team:
                final_winners = advancing.get("final", [])
                champ_passed = champion_team in final_winners
                champ_checkable = phase_consumed.get("final", False)
                if champ_checkable:
                    champ_bg = "rgba(34,197,94,0.15)" if champ_passed else "rgba(239,68,68,0.15)"
                    champ_border = "var(--success)" if champ_passed else "var(--danger)"
                    champ_color = "var(--success)" if champ_passed else "var(--danger)"
                else:
                    champ_bg = "rgba(234,179,8,0.15)"
                    champ_border = "var(--warning)"
                    champ_color = "var(--warning)"
                champion_block = (
                    f'<div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--card-border);">'
                    f'<div style="font-size:0.8rem;font-weight:600;color:var(--accent);margin-bottom:0.3rem;">'
                    f'\U0001f3c6 Campe\u00e3o</div>'
                    f'<span style="display:inline-block;padding:0.2rem 0.6rem;margin:0.15rem;'
                    f'background:{champ_bg};border:1px solid {champ_border};border-radius:999px;'
                    f'font-size:0.75rem;color:{champ_color};">{champion_team}</span>'
                    f'</div>\n'
                )
            else:
                champion_block = ""

            legend = ""
            total_label = ""
            if phase_blocks:
                total_label = f'<span style="color:var(--accent);margin-left:0.5rem;font-weight:700;">+{total_bonus_pts}</span>'
                legend = (
                    '<div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:0.5rem;'
                    'display:flex;gap:0.75rem;flex-wrap:wrap;">'
                    '<span>\U0001f7e1 sem informa\u00e7\u00f5es / fase n\u00e3o iniciada</span>'
                    '<span style="color:var(--success);">\u25cf time avan\u00e7ou / na fase</span>'
                    '<span style="color:var(--danger);">\u25cf time eliminado</span>'
                    '</div>'
                )

            bonus_html = ""
            if phase_blocks or champion_block:
                bonus_html = (
                    f'<details class="section" open>'
                    f'<summary style="font-size:1rem;font-weight:700;padding:0 0.75rem;margin-bottom:0.5rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;min-height:44px;">'
                    f'\U0001f3c6 Times Bonus {total_label}</summary>'
                    f'<div class="card">{legend}{phase_blocks}{champion_block}</div>'
                    f'</details>\n'
                )

            # Ensure champion_team is available for the top badges later in the function
            # Since champion_team is defined in this loop, we need to make sure it's accessible
            # The variable champion_team is already in the current scope.

    # ── Gold Dashboard (1st block after hero) ──
    phase_emoji_map_local = dict(config.phase_emojis) if config.phase_emojis else {}
    _score_names = config.scoring_rule_names()
    _exact_col = next((c for c in _score_names if c.startswith("1-")), "")
    _exact_count = int(df_bol[_exact_col].sum()) if _exact_col and _exact_col in df_bol.columns else 0
    gold_dashboard_html = _build_gold_dashboard(
        config=config,
        boleiro=boleiro,
        df_bol=df_bol,
        total_pts=total_pts,
        bonus_total=bonus_total,
        bonus_by_phase=bonus_by_phase,
        grand_total=grand_total,
        avg_per_game=avg_per_game,
        num_games=num_games,
        max_pts=max_pts,
        player_zebra_cnt=player_zebra_cnt,
        phase_emoji_map=phase_emoji_map_local,
        gold_dir=gold_dir,
        exact_count=_exact_count,
        avg_per_day=avg_per_day,
        rank=rank,
    )
    body += gold_dashboard_html

    # --- Build top-of-page: striker + champion + bonus + timeline + compare ---
    top_badges = ""
    if striker_name:
        top_badges += f'<div class="striker-badge"><span class="icon">\U0001f3af</span> Artilheiro: <strong>{striker_name}</strong></div>\n'
    if champion_team:
        top_badges += f'<div class="striker-badge"><span class="icon">\U0001f3c6</span> Campe\u00e3o: <strong>{champion_team}</strong></div>\n'
    body += top_badges

    if bonus_html:
        body += bonus_html

    # ------------------------------------------------------------------
    # Phase points table
    # ------------------------------------------------------------------
    phase_emoji_map = dict(config.phase_emojis) if config.phase_emojis else {
        "1afase": "\U0001f4ca",
        "segunda_fase": "\U0001f3c6",
        "oitavas": "\U0001f3c1",
        "quartas": "\U0001f525",
        "semi": "\U0001f3af",
        "terceiro_lugar": "\U0001f949",
        "final": "\U0001f3c6",
    }

    # Group stage: use df_valid (gold group CSV) directly for accurate group-only points
    # This avoids the round_by_round.csv catch-all bucket (round_number=0) which
    # can inadvertently include playoff r32 / terceiro_lugar matches.
    group_match_pts = int(df_valid.loc[df_valid["who"] == boleiro, "pontos"].sum())

    phase_rows = ""
    match_total = 0
    # 1st phase (group stage)
    df_group_player = df_valid[df_valid["who"] == boleiro]
    group_total_matches = len(df_group_player)
    group_correct_teams = (df_group_player["resultado_bol_time"] == df_group_player["resultado_real_time"]).sum()
    group_team_str = f'{group_correct_teams}/{group_total_matches}' if group_total_matches else '-'
    if group_match_pts > 0 or (total_pts > 0 and group_match_pts >= 0):
        phase_rows += (
            f'<tr><td>\U0001f4ca 1\u00aa Fase</td>'
            f'<td style="text-align:right;">+{group_match_pts}</td>'
            f'<td style="text-align:right;">-</td>'
            f'<td style="text-align:right;">{group_team_str}</td>'
            f'<td style="text-align:right;font-weight:600;color:var(--accent);">+{group_match_pts}</td></tr>\n'
        )
        match_total += group_match_pts

    # Playoff phases
    for pr in config.playoff_rounds or []:
        phase_key = pr.key
        phase_name = pr.name

        phase_valid_path = config.gold_playoff_valid_path(phase_key)
        phase_pts = 0
        has_match_data = False
        phase_team_str = '-'
        if os.path.exists(phase_valid_path):
            df_pp = pd.read_csv(phase_valid_path, sep=",")
            df_pp_player = df_pp[df_pp["who"] == boleiro]
            if not df_pp_player.empty:
                phase_pts = int(df_pp_player["pontos"].sum())
                has_match_data = True
                pp_valido = df_pp_player[df_pp_player.get("valido", 1) == 1]
                pp_total = len(pp_valido)
                if pp_total:
                    pp_correct = (pp_valido["resultado_bol_time"] == pp_valido["resultado_real_time"]).sum()
                    phase_team_str = f'{pp_correct}/{pp_total}'

        bns = bonus_by_phase.get(phase_key, 0)
        tot = phase_pts + bns
        if tot > 0 or phase_pts > 0 or bns > 0 or has_match_data:
            match_total += phase_pts
            emoji = phase_emoji_map.get(phase_key, "\u26bd")
            bonus_str = f'+{bns}' if bns else '-'
            phase_rows += (
                f'<tr><td>{emoji} {phase_name}</td>'
                f'<td style="text-align:right;">+{phase_pts}</td>'
                f'<td style="text-align:right;">{bonus_str}</td>'
                f'<td style="text-align:right;">{phase_team_str}</td>'
                f'<td style="text-align:right;font-weight:600;color:var(--accent);">+{tot}</td></tr>\n'
            )

    if phase_rows:
        # Recompute total_pts from the phase breakdown (robust against concat issues)
        total_pts = match_total
        grand_total = total_pts + bonus_total - penalty_pts
        body += (
            f'<div class="section">'
            f'<div class="section-title">\U0001f4ca Pontos por Fase</div>'
            f'<div class="card" style="overflow-x:auto;">'
f'<table data-sortable style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
             f'<thead><tr style="color:var(--text-muted);border-bottom:1px solid var(--card-border);">'
             f'<th style="text-align:left;padding:0.4rem;">Fase</th>'
             f'<th style="text-align:right;padding:0.4rem;">Jogos</th>'
             f'<th style="text-align:right;padding:0.4rem;">B\u00f4nus</th>'
             f'<th style="text-align:right;padding:0.4rem;">Times</th>'
             f'<th style="text-align:right;padding:0.4rem;">Total</th>'
            f'</tr></thead><tbody>'
            f'{phase_rows}'
            f'<tr style="border-top:2px solid var(--accent);font-weight:700;">'
            f'<td style="padding:0.4rem;">Total</td>'
            f'<td style="text-align:right;">+{total_pts}</td>'
            f'<td style="text-align:right;">+{bonus_total}</td>'
            f'<td style="text-align:right;">-</td>'
            f'<td style="text-align:right;color:var(--accent);">+{total_pts + bonus_total}</td></tr>'
            f'{"<tr style=\"color:var(--danger);\"><td style=\"padding:0.4rem;\">❌ Penalidade</td><td></td><td></td><td></td><td style=\"text-align:right;\">-" + str(penalty_pts) + "</td></tr>" if penalty_pts > 0 else ""}'
            f'<tr style="border-top:2px solid var(--card-border);font-weight:700;">'
            f'<td style="padding:0.4rem;">\U0001f3c6 Geral</td>'
            f'<td></td><td></td><td></td>'
            f'<td style="text-align:right;color:var(--accent);font-size:1.1rem;">+{grand_total}</td></tr>'
            f'</tbody></table>'
            f'<div style="font-size:0.7rem;color:var(--text-muted);margin-top:0.5rem;">'
            f'Jogos = pontos dos palpites \u00b7 B\u00f4nus = pontos dos times escolhidos por fase \u00b7 Times = acertos do vencedor / total de jogos'
            f'</div></div></div>\n'
        )

    # ── Scoring distribution ──
    body += _dist_html

    if timeline_bars:
        body += f'<div class="card"><div class="card-title">Pontos por dia</div><div class="bar-chart">{timeline_bars}</div></div>\n'

    if compare_bars:
        body += f'<div class="card"><div class="card-title">Pontos por Dia — Voce vs Bolao</div><div style="padding:0.5rem 0;">{compare_bars}</div></div>\n'

    # ------------------------------------------------------------------
    # Round-by-round performance table
    # ------------------------------------------------------------------
    rbr_html = ""
    rbr_path = _norm(os.path.join(gold_dir, "round_by_round.csv"))
    if os.path.exists(rbr_path):
        df_rbr = pd.read_csv(rbr_path, sep=",")
        df_rbr_p = df_rbr[df_rbr["boleiro"] == boleiro].sort_values("round_number")
        if not df_rbr_p.empty:
            rbr_rows = ""
            for _, rr in df_rbr_p.iterrows():
                rl = str(rr["round_label"])
                rp = int(rr["points"])
                rc = int(rr["cumulative_points"])
                rk = int(rr["rank"]) if pd.notna(rr.get("rank")) else 0
                rank_color = "var(--success)" if rk <= 3 else "var(--text-muted)"
                rbr_rows += f"<tr><td>{rl}</td><td style='text-align:right;'>{rp}</td><td style='text-align:right;color:var(--accent);'>{rc}</td><td style='text-align:right;color:{rank_color};'>{rk}\u00ba</td></tr>\n"
            rbr_html = f"""<div class="section">
    <div class="section-title">\U0001f4ca Rodada a Rodada</div>
    <div class="card" style="overflow-x:auto;">
        <table data-sortable style="width:100%;border-collapse:collapse;font-size:0.85rem;">
            <thead><tr style="color:var(--text-muted);border-bottom:1px solid var(--card-border);">
                <th style="text-align:left;padding:0.4rem;">Rodada</th>
                <th style="text-align:right;padding:0.4rem;">Pontos</th>
                <th style="text-align:right;padding:0.4rem;">Acumulado</th>
                <th style="text-align:right;padding:0.4rem;">Rank*</th>
            </tr></thead>
            <tbody>{rbr_rows}</tbody>
        </table>
        <div style="font-size:0.65rem;color:var(--text-muted);margin-top:0.4rem;">*Rank baseado apenas em pontos dos palpites (b\u00f4nus n\u00e3o incluso)</div>
    </div>
</div>"""
    body += rbr_html

    # --- Best and worst teams (goal_error_by_team) → before ta_parts ---
    error_path = _norm(os.path.join(gold_dir, "goal_error_by_team.csv"))
    best_team_html = ""
    worst_team_html = ""
    bias_html = ""
    if os.path.exists(error_path):
        df_err = pd.read_csv(error_path, sep=",")
        df_err_p_all = df_err[df_err["boleiro"] == boleiro].copy()
        if not df_err_p_all.empty:
            df_err_p = df_err_p_all[df_err_p_all["role"] == "total"].copy()
            if df_err_p.empty:
                df_err_p = df_err_p_all.copy()
            df_err_p_sorted = df_err_p.sort_values("mae")
            best_teams = df_err_p_sorted.head(3)
            worst_teams = df_err_p_sorted.tail(3)

            max_mae = max(df_err_p["mae"].max(), 1)
            best_team_html = "<div style='margin-top:0.5rem;'>"
            best_team_html += '<div style="font-size:0.8rem;font-weight:600;color:var(--success);margin-bottom:0.3rem;">\U0001f7e2 Menor erro — voc\u00ea quase acertou o placar</div>'
            for _, r in best_teams.iterrows():
                bw = max(r["mae"] / max_mae * 100, 2)
                best_team_html += f'<div style="display:flex;align-items:center;gap:0.4rem;font-size:0.8rem;padding:0.2rem 0;"><span style="min-width:90px;font-weight:600;">{r["team"]}</span><div style="flex:1;height:14px;background:var(--card-border);border-radius:6px;overflow:hidden;"><div style="width:{bw:.0f}%;height:100%;background:var(--success);border-radius:6px;"></div></div><span style="min-width:50px;text-align:right;color:var(--text-muted);">m\u00e9dia de {r["mae"]:.1f} gol(s) de erro</span></div>\n'
            best_team_html += "</div>"

            worst_team_html = "<div style='margin-top:0.5rem;'>"
            worst_team_html += '<div style="font-size:0.8rem;font-weight:600;color:var(--danger);margin-bottom:0.3rem;">\U0001f534 Maior erro — seus palpites para esses times foram longe do real</div>'
            for _, r in worst_teams.iterrows():
                bw = max(r["mae"] / max_mae * 100, 2)
                worst_team_html += f'<div style="display:flex;align-items:center;gap:0.4rem;font-size:0.8rem;padding:0.2rem 0;"><span style="min-width:90px;font-weight:600;">{r["team"]}</span><div style="flex:1;height:14px;background:var(--card-border);border-radius:6px;overflow:hidden;"><div style="width:{bw:.0f}%;height:100%;background:var(--danger);border-radius:6px;"></div></div><span style="min-width:50px;text-align:right;color:var(--text-muted);">m\u00e9dia de {r["mae"]:.1f} gol(s) de erro</span></div>\n'
            worst_team_html += "</div>"

            # bias section removed — too confusing for most users

    # ------------------------------------------------------------------
    # Team goal error (MAE) + bias — simplified
    # ------------------------------------------------------------------
    ta_html = ""
    ta_parts = best_team_html + worst_team_html + bias_html
    if ta_parts.strip():
        ta_html = f"""<div class="section">
    <div class="section-title">\U0001f3e0 Times — Precis\u00e3o dos Seus Placar</div>
    <div class="card" style="overflow-x:auto;padding:0.6rem 0.75rem;">
        <div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:0.5rem;line-height:1.4;">
            Abaixo, a m\u00e9dia de erro dos seus palpites de <strong>placar</strong> para cada time.
            Quanto menor o erro, mais perto voc\u00ea chegou do resultado real.
        </div>
        {ta_parts}
    </div>
</div>"""
    body += ta_html

    # ------------------------------------------------------------------
    # Radar chart data (5 axes: Points, Precision, Boldness, Zebras, Regularity)
    # ------------------------------------------------------------------
    max_possible_total = len(df_bol) * max_pts
    pts_pct = min(100, round(total_pts / max_possible_total * 100)) if max_possible_total else 0
    prec_pct = min(100, round(avg_per_game / max_pts * 100)) if max_pts else 0

    bold_path = _norm(os.path.join(gold_dir, "boldness_index.csv"))
    boldness_norm = 50
    boldness_score_val = 0.0
    if os.path.exists(bold_path):
        df_bold_tmp = pd.read_csv(bold_path, sep=",")
        df_bp = df_bold_tmp[df_bold_tmp["boleiro"] == boleiro]
        if not df_bp.empty:
            boldness_score_val = float(df_bp.iloc[0]["boldness_score"])
            boldness_norm = max(0, min(100, round(50 + boldness_score_val * 25)))

    upset_path = _norm(os.path.join(gold_dir, "upset_tracker.csv"))
    zebra_pct = 0
    if os.path.exists(upset_path):
        try:
            df_upset = pd.read_csv(upset_path, sep=",")
        except pd.errors.EmptyDataError:
            df_upset = pd.DataFrame()
        upset_matches = df_upset[df_upset.get("is_upset", 0) == 1]
        total_upsets = len(upset_matches)
        player_upsets = 0
        for _, r in upset_matches.iterrows():
            pc = str(r.get("players_correct", ""))
            if boleiro in [p.strip() for p in pc.split("|")]:
                player_upsets += 1
        zebra_pct = round(player_upsets / total_upsets * 100) if total_upsets else 0

    cons_path = _norm(os.path.join(gold_dir, "consistency.csv"))
    reg_pct = 50
    if os.path.exists(cons_path):
        df_cons_tmp = pd.read_csv(cons_path, sep=",")
        df_cp = df_cons_tmp[df_cons_tmp["boleiro"] == boleiro]
        if not df_cp.empty and "running_avg_5" in df_cp.columns:
            avg_run = df_cp["running_avg_5"].mean()
            reg_pct = min(100, round(avg_run / max_pts * 100)) if max_pts else 50

    radar_data_json = json.dumps([
        {"label": "Pontua\u00e7\u00e3o", "value": pts_pct},
        {"label": "Precis\u00e3o", "value": prec_pct},
        {"label": "Ousadia", "value": boldness_norm},
        {"label": "Zebras", "value": zebra_pct},
        {"label": "Regularidade", "value": reg_pct},
    ])

    radar_css = """
.radar-wrap { position: relative; width: 220px; height: 220px; margin: 0 auto; }
.radar-wrap canvas { width: 100%; height: 100%; }
.radar-legend { display: flex; flex-wrap: wrap; gap: 0.25rem 0.75rem; margin-top: 0.5rem; font-size: 0.7rem; color: var(--text-muted); justify-content: center; }
.radar-legend span::before { content: '\\25CF'; margin-right: 0.25rem; }
"""

    radar_js = f"""
<script>
(function() {{
    var data = {radar_data_json};
    var canvas = document.getElementById('radar-canvas');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var W = canvas.width = canvas.offsetWidth || 220;
    var H = canvas.height = canvas.offsetHeight || 220;
    var cx = W / 2, cy = H / 2;
    var R = Math.min(W, H) / 2 - 35;
    var n = data.length;

    function getPt(i, r) {{
        var a = Math.PI / 2 - i * 2 * Math.PI / n;
        return {{ x: cx + r * Math.cos(a), y: cy - r * Math.sin(a) }};
    }}

    // Grid
    for (var lv = 1; lv <= 4; lv++) {{
        ctx.beginPath();
        for (var i = 0; i <= n; i++) {{
            var p = getPt(i % n, R * lv / 4);
            i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
        }}
        ctx.strokeStyle = 'rgba(128,128,128,0.15)';
        ctx.stroke();
    }}

    // Axes
    for (var i = 0; i < n; i++) {{
        var p = getPt(i, R);
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(p.x, p.y);
        ctx.strokeStyle = 'rgba(128,128,128,0.2)';
        ctx.stroke();
    }}

    // Data polygon
    ctx.beginPath();
    for (var i = 0; i <= n; i++) {{
        var r = R * data[i % n].value / 100;
        var p = getPt(i % n, r);
        i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y);
    }}
    ctx.fillStyle = 'rgba(99,102,241,0.15)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(99,102,241,0.7)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Data points
    for (var i = 0; i < n; i++) {{
        var r = R * data[i].value / 100;
        var p = getPt(i, r);
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4, 0, 2 * Math.PI);
        ctx.fillStyle = '#6366f1';
        ctx.fill();
    }}

    // Labels
    ctx.fillStyle = 'var(--text)';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    for (var i = 0; i < n; i++) {{
        var p = getPt(i, R + 18);
        ctx.fillText(data[i].label, p.x, p.y + 4);
    }}
}})();
</script>
"""

    body += f"""
<style>{radar_css}</style>
<div class="section">
    <div class="section-title">\U0001f4ca Radar do Jogador</div>
    <div class="card" style="text-align:center;">
        <div class="radar-wrap"><canvas id="radar-canvas"></canvas></div>
        <div class="radar-legend">
            <span>Pontua\u00e7\u00e3o: {pts_pct}%</span>
            <span>Precis\u00e3o: {prec_pct}%</span>
            <span>Ousadia: {boldness_norm}%</span>
            <span>Zebras: {zebra_pct}%</span>
            <span>Regularidade: {reg_pct}%</span>
        </div>
        <div style="font-size:0.7rem;color:var(--text-muted);text-align:left;margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--card-border);">
            <strong style="font-size:0.75rem;">Legenda:</strong><br>
            \u2022 <strong>Pontua\u00e7\u00e3o</strong>: % de pontos em rela\u00e7\u00e3o ao m\u00e1ximo poss\u00edvel<br>
            \u2022 <strong>Precis\u00e3o</strong>: m\u00e9dia de pontos por jogo / pontos m\u00e1ximos por jogo<br>
            \u2022 <strong>Ousadia</strong>: qu\u00e3o diferente suas apostas s\u00e3o da m\u00e9dia do bol\u00e3o<br>
            \u2022 <strong>Zebras</strong>: % das surpresas que voc\u00ea acertou<br>
            \u2022 <strong>Regularidade</strong>: consist\u00eancia dos seus palpites ao longo do tempo<br>
            <span style="display:block;margin-top:0.3rem;">(\u00cdndices de 0% a 100%)</span>
        </div>
    </div>
</div>
{radar_js}
"""

    # ------------------------------------------------------------------
    # Perfil do Jogador (advanced stats + badges from gold layer)
    # ------------------------------------------------------------------
    profile_html = ""
    _ph = lambda msg: f'<div style="color:var(--text-muted);font-size:0.85rem;padding:0.3rem 0;">\u23f3 {msg}</div>\n'

    # --- Compute badges for this player ---
    badges: list[str] = []

    # 1. Current streak badge (already have streak_len, streak_type from above)
    streak_html_inner = ""
    if os.path.exists(cons_path):
        df_cons2 = pd.read_csv(cons_path, sep=",")
        df_cp2 = df_cons2[df_cons2["boleiro"] == boleiro].sort_values("date")
        streak_len2 = 0
        streak_type2 = ""
        if not df_cp2.empty:
            for _, r in reversed(list(df_cp2.iterrows())):
                st = r.get("streak_type", "")
                if st == "hit":
                    if streak_type2 == "" or streak_type2 == "hit":
                        streak_type2 = "hit"
                        streak_len2 += 1
                    else:
                        break
                elif st == "miss":
                    if streak_type2 == "" or streak_type2 == "miss":
                        streak_type2 = "miss"
                        streak_len2 += 1
                    else:
                        break
                else:
                    break
        if streak_type2 == "hit" and streak_len2 >= 3:
            badges.append(f'<span class="profile-badge" style="border-color:var(--success);background:rgba(34,197,94,0.15);">\U0001f525 Embrazado ({streak_len2})</span>')
            streak_html_inner = f'<div style="margin-top:0.25rem;"><span class="profile-badge" style="border-color:var(--success);background:rgba(34,197,94,0.15);">\U0001f525 Sequ\u00eancia: {streak_len2} acertos</span></div>\n'
        elif streak_type2 == "miss":
            streak_html_inner = f'<div style="margin-top:0.25rem;"><span class="profile-badge" style="border-color:var(--danger);background:rgba(239,68,68,0.15);">\U0001f4a9 Sequ\u00eancia: {streak_len2} erros</span></div>\n'
    if not streak_html_inner:
        streak_html_inner = _ph("Sequ\u00eancia atual dispon\u00edvel ap\u00f3s os primeiros jogos.")

    # 2. Zebra hunter badge
    if os.path.exists(upset_path):
        df_upset2 = pd.read_csv(upset_path, sep=",")
        upset_only = df_upset2[df_upset2.get("is_upset", 0) == 1]
        zebra_counts: dict[str, int] = {}
        for _, r in upset_only.iterrows():
            pc = str(r.get("players_correct", ""))
            for p in [x.strip() for x in pc.split("|") if x.strip()]:
                zebra_counts[p] = zebra_counts.get(p, 0) + 1
        sorted_zebras = sorted(zebra_counts.items(), key=lambda x: -x[1])
        if len(sorted_zebras) >= 3 and boleiro in [z[0] for z in sorted_zebras[:3]]:
            badges.append(f'<span class="profile-badge" style="border-color:var(--danger);background:rgba(239,68,68,0.15);">\U0001f993 Ca\u00e7ador de Zebras</span>')

    # 3. Boldness badge
    if os.path.exists(bold_path):
        df_bold2 = pd.read_csv(bold_path, sep=",")
        df_bp2 = df_bold2[df_bold2["boleiro"] == boleiro]
        if not df_bp2.empty:
            bs = float(df_bp2.iloc[0]["boldness_score"])
            if bs > 0.3:
                badges.append(f'<span class="profile-badge" style="border-color:var(--warning);background:rgba(245,158,11,0.15);">\U0001f4a5 Ousado</span>')
            elif bs < -0.3:
                badges.append(f'<span class="profile-badge" style="border-color:var(--bolao);background:rgba(59,130,246,0.15);">\U0001F9CA Conservador</span>')

    # 4. Leader badge
    rank_path = _norm(os.path.join(gold_dir, "ranking_history.csv"))
    if os.path.exists(rank_path):
        df_rank = pd.read_csv(rank_path, sep=",")
        df_rank = df_rank.sort_values("date")
        latest_date = df_rank["date"].iloc[-1] if not df_rank.empty else None
        if latest_date:
            df_latest = df_rank[df_rank["date"] == latest_date]
            top = df_latest.loc[df_latest["rank"].idxmin()] if not df_latest.empty else None
            if top is not None and top["boleiro"] == boleiro:
                badges.append(f'<span class="profile-badge" style="border-color:var(--accent);background:rgba(255,215,0,0.15);">\U0001f40d L\u00edder</span>')

    # 5. Team expert badge
    ta_path = _norm(os.path.join(gold_dir, "team_accuracy.csv"))
    if os.path.exists(ta_path):
        df_ta = pd.read_csv(ta_path, sep=",")
        df_ta["team"] = df_ta["team"].str.strip()
        best_team = ""
        best_pct = 0
        for team in df_ta["team"].unique():
            df_tt = df_ta[df_ta["team"] == team]
            if df_tt.empty:
                continue
            agg = df_tt.groupby("boleiro").agg(
                total_bets=("total_bets", "sum"),
                correct_winner=("correct_winner", "sum"),
            ).reset_index()
            agg["acc"] = agg["correct_winner"] / agg["total_bets"] * 100
            top_acc = agg.loc[agg["acc"].idxmax()] if not agg.empty else None
            if top_acc is not None and top_acc["boleiro"] == boleiro and top_acc["total_bets"] >= 3 and top_acc["acc"] > 50:
                if top_acc["acc"] > best_pct:
                    best_pct = top_acc["acc"]
                    best_team = team
        if best_team:
            badges.append(f'<span class="profile-badge" style="border-color:var(--success);background:rgba(34,197,94,0.15);">\U0001f3af Especialista em {best_team[:12]}</span>')

    badges_html = f'<div style="display:flex;flex-wrap:wrap;gap:0.4rem;margin-bottom:0.75rem;">{" ".join(badges)}</div>' if badges else ""

    # --- Profile type from boldness_index ---
    boldness_html = ""
    if os.path.exists(bold_path):
        df_bold3 = pd.read_csv(bold_path, sep=",")
        df_bp3 = df_bold3[df_bold3["boleiro"] == boleiro]
        if not df_bp3.empty:
            bs2 = float(df_bp3.iloc[0]["boldness_score"])
            if bs2 > 0.3:
                pt = "\U0001f680 Ousado"
                pdsc = "Voc\u00ea aposta em placares acima da m\u00e9dia do bol\u00e3o"
            elif bs2 < -0.3:
                pt = "\U0001F9CA Conservador"
                pdsc = "Voc\u00ea aposta em placares abaixo da m\u00e9dia do bol\u00e3o"
            else:
                pt = "\u2696\ufe0f Equilibrado"
                pdsc = "Voc\u00ea aposta na m\u00e9dia do bol\u00e3o"
            boldness_html = f'<div style="margin-bottom:0.5rem;"><span class="profile-badge">{pt}</span> <span style="font-size:0.8rem;color:var(--text-muted);">({pdsc})</span></div>\n'
    if not boldness_html:
        boldness_html = _ph("Perfil de ousadia dispon\u00edvel ap\u00f3s os primeiros jogos.")

    # --- Archetype badge (reads source-of-truth CSV) ---
    arq_html = ""
    arq_csv = _norm(os.path.join(config._au_first_round(), "arquetipos_classification.csv"))
    if os.path.exists(arq_csv):
        df_arq = pd.read_csv(arq_csv, sep=",")
        arq_row = df_arq[df_arq["boleiro"] == boleiro]
        if not arq_row.empty:
            r2 = arq_row.iloc[0]
            arq_emoji = str(r2.get("arquetipo_emoji", "?"))
            arq_nome = str(r2.get("arquetipo", "?"))
            arq_tier = str(r2.get("tier_label", "?"))
            arq_tier_emoji = str(r2.get("tier_emoji", ""))
            arq_score = int(r2.get("score", 0))
            arq_cor = str(r2.get("arquetipo_cor", "var(--text-muted)"))
            tier_cor = str(r2.get("tier_cor", "var(--text-muted)"))
            # GEO badge
            perfil_global = str(r2.get("perfil_global", ""))
            geo_badge = ""
            if perfil_global:
                geo_emojis = {
                    k: v.get("emoji", "") for k, v in (config.continent_display or {}).items()
                } if config.continent_display else {
                    "europeu": "\U0001f30d", "latino": "\U0001f30e",
                    "asiatico": "\U0001f30f", "africano": "\U0001f30c",
                    "anfitriao": "\U0001f3c6", "oceanico": "\U0001f30a",
                }
                geo_names = {
                    k: v.get("name", k) for k, v in (config.continent_display or {}).items()
                } if config.continent_display else {
                    "europeu": "europeu", "latino": "latino",
                    "asiatico": "asiatico", "africano": "africano",
                    "anfitriao": "anfitriao", "oceanico": "oceanico",
                }
                ge = geo_emojis.get(perfil_global, "")
                gn = geo_names.get(perfil_global, perfil_global)
                gc = int(r2.get("global_correct", 0))
                gt = int(r2.get("global_teams", 0))
                media = gc / gt if gt else 0
                geo_tip = f"{gc} pts em {gt} sel. (m\u00e9dia {media:.1f})" if gt else f"{gc} pts"
                geo_tip = geo_tip.replace(".", ",")
                geo_badge = f'<span style="font-size:0.7rem;padding:0.1rem 0.4rem;border-radius:4px;background:var(--card-border);color:var(--text-muted);" title="{geo_tip}">{ge} {gn} {geo_tip}</span>'
            arq_html = (
                f'<div style="margin-bottom:0.6rem;padding-bottom:0.5rem;border-bottom:1px solid var(--card-border);'
                f'display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">'
                f'<span style="font-size:1.5rem;">{arq_emoji}</span>'
                f'<span style="font-weight:700;color:{arq_cor};font-size:1.1rem;">{arq_nome}</span>'
                f'<span class="tier-badge" style="display:inline-block;font-size:0.7rem;font-weight:700;'
                f'padding:0.15rem 0.5rem;border-radius:999px;background:{tier_cor}22;color:{tier_cor};'
                f'border:1px solid {tier_cor};">{arq_tier_emoji} {arq_tier} \u00b7 {arq_score}%</span>'
                f'{geo_badge}'
                f'<a href="../arquetipos.html" style="font-size:0.7rem;color:var(--text-muted);margin-left:auto;">'
                f'\U0001f4d6 legenda</a>'
                f'</div>\n'
            )

    # --- Combine profile ---
    profile_parts = arq_html + badges_html + boldness_html + streak_html_inner
    profile_html = f'<div class="section"><div class="section-title">\U0001f9d0 Perfil do Jogador</div><div class="card">{profile_parts}</div></div>\n'

    body += profile_html

    # --- Last 5 games card (between profile and jogos encerrados) ---
    df_last5 = df_bol[df_bol.get("valido", 0) == 1].tail(5).iloc[::-1]
    if not df_last5.empty:
        rev_map_5 = {v: k for k, v in config.team_name_mapping.items()}
        last5_rows = ""
        for _, r5 in df_last5.iterrows():
            hg5 = r5.get("home_goals_real")
            ag5 = r5.get("away_goals_real")
            score_5 = f'<span style="font-weight:700;color:var(--accent);">{int(hg5)}</span> - <span style="font-weight:700;color:var(--accent);">{int(ag5)}</span>' if pd.notna(hg5) and pd.notna(ag5) else " vs "
            home_en_5 = rev_map_5.get(r5["home_team"], r5["home_team"])
            away_en_5 = rev_map_5.get(r5["away_team"], r5["away_team"])
            home_logo_5 = _team_logo_tag(home_en_5, config, cls="team-logo-sm", start=boleiro_dir)
            away_logo_5 = _team_logo_tag(away_en_5, config, cls="team-logo-sm", start=boleiro_dir)
            ms_5 = str(r5.get("match", ""))
            phase_val_5 = str(r5.get("phase", ""))
            phase_5 = phase_val_5 if phase_val_5 else config.group_phase_label
            hr_5 = str(r5.get("hour", ""))
            game_href_5 = f"../jogos/{phase_5}/{r5['date']}_{hr_5}_{ms_5}.html"
            date_part_5 = pd.to_datetime(r5["date"]).strftime("%d/%m") + (f" {hr_5}" if hr_5 else "")
            last5_rows += (
                f'<a href="{game_href_5}" style="display:flex;align-items:center;justify-content:space-between;'
                f'background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;'
                f'padding:0.45rem 0.7rem;font-size:0.75rem;font-weight:500;color:var(--text);'
                f'text-decoration:none;transition:border-color 0.15s;" '
                f'onmouseover="this.style.borderColor=\'var(--accent)\'" '
                f'onmouseout="this.style.borderColor=\'var(--card-border)\'">'
                f'<span style="display:flex;align-items:center;gap:0.3rem;">'
                f'<span style="font-size:0.65rem;color:var(--text-muted);">{date_part_5}</span>'
                f'{home_logo_5}{r5["home_team"]}'
                f' {score_5} '
                f'{away_logo_5}{r5["away_team"]}'
                f'</span>'
                f'</a>\n'
            )
        body += f'<div class="section"><div class="section-title">\U0001f4c5 Ultimos 5 Jogos</div><div class="card" style="display:flex;flex-direction:column;gap:0.25rem;padding:0.6rem 0.75rem;">{last5_rows}</div></div>\n'

    encerrados_total = n_past + n_pending
    body += f"""
<details class="section">
    <summary style="font-size:1rem;font-weight:700;padding:0 0.75rem;margin-bottom:0.5rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;min-height:44px;">
    \U0001f4cb Jogos Encerrados ({encerrados_total})</summary>
"""
    if n_pending:
        body += f"""    <div class="card" style="margin-bottom:0.5rem;">
        <div style="font-size:0.8rem;font-weight:600;color:var(--warning);margin-bottom:0.3rem;">\u23f3 Aguardando Resultado ({n_pending})</div>
        {pending_rows}</div>
"""
    if history_rows_past:
        body += f"""    <div class="card">
        <div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.3rem;">\u2705 Com Resultado ({n_past})</div>
        {history_rows_past}</div>
"""
    if not encerrados_total:
        body += """    <div class="card"><div style="color:var(--text-muted);font-size:0.85rem;padding:0.3rem 0;">Nenhum jogo encerrado.</div></div>"""

    body += f"""
</details>
<details class="section" open>
    <summary style="font-size:1rem;font-weight:700;padding:0 0.75rem;margin-bottom:0.5rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;min-height:44px;">
    \U0001f4cb Jogos Futuros ({n_future})</summary>
    <div class="card">{history_rows_future}</div>
</details>
"""
    return _page_frame(config, f"{boleiro} - {config.report_title}", body, back_link="../index.html")


# ------------------------------------------------------------------
# Per-match page
# ------------------------------------------------------------------

def _build_match(config: ChampionshipConfig, match: str, phase: str, df_match: pd.DataFrame) -> str:
    """Build a per-match HTML report."""
    df_match = df_match.copy()
    df_match = df_match.sort_values(["pontos", "who"], ascending=False)

    # Lookup upset data for this match
    upset_path = _norm(os.path.join(config._au_first_round(), "upset_tracker.csv"))
    upset_row = None
    if os.path.exists(upset_path):
        try:
            df_upset = pd.read_csv(upset_path, sep=",")
        except pd.errors.EmptyDataError:
            df_upset = pd.DataFrame()
        matches = df_upset[df_upset["match"] == match]
        if not matches.empty:
            upset_row = matches.iloc[0]

    home = str(df_match.iloc[0]["home_team"])
    away = str(df_match.iloc[0]["away_team"])
    date_str = str(df_match.iloc[0]["date"])
    hour_str = str(df_match.iloc[0].get("hour", ""))

    rev_map = {v: k for k, v in config.team_name_mapping.items()}
    home_en = rev_map.get(home, home)
    away_en = rev_map.get(away, away)
    match_dir = _norm(os.path.join(config.reports_dir, "html", "jogos", phase))
    home_logo = _team_logo_tag(home_en, config, cls="team-logo-sm", start=match_dir)
    away_logo = _team_logo_tag(away_en, config, cls="team-logo-sm", start=match_dir)

    # Determine if match is live (time_elapsed column may not exist for all championships)
    is_live = False
    if "time_elapsed" in df_match.columns:
        raw_time = df_match["time_elapsed"].iloc[0]
        is_live = pd.notna(raw_time) and str(raw_time).strip().lower() == "live"

    # Check if there is a score to display (partial or final).
    # A live match with a partial score (e.g. 0 x 0) still has a score.
    _rrp_raw = df_match["resultado_real_placar"].iloc[0] if "resultado_real_placar" in df_match.columns else ""
    has_score = (
        pd.notna(_rrp_raw)
        and str(_rrp_raw) not in ("nan", "", "none")
        and " x " in str(_rrp_raw)
    )

    # Check if result is final — only for finished (non-live) matches.
    # A live match with a partial score is NOT a final result.
    has_result = not is_live and has_score

    real_placar = ""
    if has_score:
        real_placar = str(df_match.iloc[0]["resultado_real_placar"])

    # ── Subset with valid prediction data (handle pending/notstarted matches) ──
    # For matches where valido=0 for all rows, home_goals_bol may be NaN.
    df_pred = df_match[
        df_match["home_goals_bol"].notna() & df_match["away_goals_bol"].notna()
    ].copy()
    has_predictions = not df_pred.empty
    df_placar = df_match[df_match["resultado_bol_placar"].notna()].copy()
    has_placar = not df_placar.empty

    # Pre-game: team vote distribution
    df_pre_time = df_match["resultado_bol_time"].value_counts().reset_index()
    df_pre_time.columns = ["vencedor", "#"]
    total_t = int(df_pre_time["#"].sum()) if not df_pre_time.empty else 0
    team_bars = ""
    for _, row in df_pre_time.iterrows():
        pct = round(row["#"] / total_t * 100) if total_t else 0
        count = int(row["#"])
        team_bars += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{row["vencedor"]}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
            f'<span class="bar-pct">{pct}% ({count}/{total_t})</span>'
            f'</div>\n'
        )

    # Pre-game: score heatmap
    if has_predictions:
        max_h = int(df_pred["home_goals_bol"].max())
        max_a = int(df_pred["away_goals_bol"].max())
    else:
        max_h = 4
        max_a = 4
    max_h = max(max_h, 4)
    max_a = max(max_a, 4)
    total_s = len(df_pred) if has_predictions else 0

    # Build player-per-score mapping for heatmap
    heat_players: dict[tuple[int, int], list[str]] = {}
    if has_predictions:
        for _, row in df_pred.iterrows():
            hg = int(row["home_goals_bol"])
            ag = int(row["away_goals_bol"])
            heat_players.setdefault((hg, ag), []).append(str(row["who"]))

    # Header row (away goals)
    header_row = '<div class="heat-row">'
    header_row += '<div class="heat-label" style="width:80px;min-width:80px;padding:0;"></div>'
    for a in range(max_a + 1):
        header_row += f'<div class="heat-cell-lg" style="font-size:0.6rem;font-weight:700;color:var(--text-muted);background:transparent;">{a}</div>'
    header_row += '</div>\n'

    # Data rows (home goals)
    data_rows = ""
    for h in range(max_h + 1):
        data_rows += '<div class="heat-row">'
        data_rows += f'<div class="heat-label">{h}</div>'
        for a in range(max_a + 1):
            if has_predictions:
                cnt = len(df_pred[(df_pred["home_goals_bol"] == h) & (df_pred["away_goals_bol"] == a)])
            else:
                cnt = 0
            pct = round(cnt / total_s * 100) if total_s else 0
            if cnt:
                if h > a:
                    z = "success"
                    zc = "34,197,94"
                elif h == a:
                    z = "warning"
                    zc = "245,158,11"
                else:
                    z = "danger"
                    zc = "239,68,68"
                if pct >= 30:
                    bg = f"var(--{z})"
                    fc = "#fff"
                elif pct >= 15:
                    bg = f"rgba({zc},0.7)"
                    fc = "#fff"
                elif pct >= 5:
                    bg = f"rgba({zc},0.4)"
                    fc = "var(--text)"
                else:
                    bg = f"rgba({zc},0.2)"
                    fc = "var(--text)"
            else:
                if h > a:
                    bg = "rgba(34,197,94,0.06)"
                elif h == a:
                    bg = "rgba(245,158,11,0.06)"
                else:
                    bg = "rgba(239,68,68,0.06)"
                fc = "var(--text-muted)"
            label = str(cnt) if cnt else ""
            players = heat_players.get((h, a), [])
            title = ", ".join(players).replace('"', "&quot;") if players else ""
            has_click = 'onclick="showHeatPlayers([&quot;' + '&quot;,&quot;'.join(players) + '&quot;],this)"' if players else ""
            data_rows += f'<div class="heat-cell-lg" style="background:{bg};color:{fc}" title="{title}" {has_click}>{label}</div>'
        data_rows += '</div>\n'

    score_heatmap = (
        '<div class="heatmap-match">'
        f'<div class="heatmap-top">{away_logo}<span>{away}</span></div>'
        '<div class="heatmap-body">'
        f'<div class="heatmap-away">{home_logo}<span>{home}</span></div>'
        f'<div class="heatmap-grid"><div class="heat-container">{header_row}{data_rows}</div></div>'
        '</div></div>'
        '<div class="heat-legend">👆 clique nos números para ver quem apostou</div>'
        '<div id="heatPopup" class="heat-popup" onclick="this.classList.remove(\'show\')"></div>'
        '<script>'
        'function showHeatPlayers(players,el){'
        "var p=document.getElementById('heatPopup');"
        "p.innerHTML='<strong>Boleiros:</strong><br>'+players.join('<br>');"
        'var r=el.getBoundingClientRect();'
        "p.style.left=Math.min(r.left,window.innerWidth-200)+'px';"
        "p.style.top=(r.bottom+4)+'px';"
        "p.classList.add('show');"
        'setTimeout(function(){document.addEventListener("click",function hide(e){if(!p.contains(e.target)&&e.target!=el){p.classList.remove("show");document.removeEventListener("click",hide)}})},0)}'
        '</script>'
    )

    # Build player-per-placar mapping
    placar_players: dict[str, list[str]] = {}
    if has_placar:
        for _, row in df_placar.iterrows():
            placar = str(row["resultado_bol_placar"])
            placar_players.setdefault(placar, []).append(str(row["who"]))

    # Pre-game: placar distribution bars
    placar_rows_resolved: list[dict] = []
    if has_placar:
        placar_counts = df_placar["resultado_bol_placar"].value_counts().reset_index()
        placar_counts.columns = ["placar", "#"]
        for _, pr in placar_counts.iterrows():
            parts = str(pr["placar"]).split(" x ")
            if len(parts) == 2:
                try:
                    hg = int(parts[0])
                    ag = int(parts[1])
                except ValueError:
                    continue
            else:
                continue
            if hg > ag:
                rtype = 0  # home win
            elif hg == ag:
                rtype = 1  # draw
            else:
                rtype = 2  # away win
            placar_rows_resolved.append({"placar": pr["placar"], "#": pr["#"], "rtype": rtype, "hg": hg, "ag": ag, "total": hg + ag})
        placar_rows_resolved.sort(key=lambda x: (x["rtype"], -x["total"], -x["ag"] if x["rtype"] == 0 else (-x["hg"] if x["rtype"] == 2 else x["hg"])))
    total_p = sum(r["#"] for r in placar_rows_resolved) if placar_rows_resolved else 0
    score_bars = ""
    bar_colors = {"home": "var(--success)", "draw": "var(--warning)", "away": "var(--danger)"}
    bar_bgs = {"home": "rgba(34,197,94,0.15)", "draw": "rgba(245,158,11,0.15)", "away": "rgba(239,68,68,0.15)"}
    for r in placar_rows_resolved:
        pct = round(r["#"] / total_p * 100)
        tcolor = "home" if r["rtype"] == 0 else ("draw" if r["rtype"] == 1 else "away")
        players = placar_players.get(r["placar"], [])
        title = ", ".join(players).replace('"', "&quot;") if players else ""
        escaped_players = [p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for p in players]
        player_list = "".join(f'<div class="bar-player">{ep}</div>' for ep in escaped_players)
        score_bars += (
            f'<div class="bar-row" onclick="this.classList.toggle(\'expanded\')" title="{title}">'
            f'<span class="bar-label">{r["placar"]}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{bar_colors[tcolor]}"></div></div>'
            f'<span class="bar-pct" style="color:{bar_colors[tcolor]}">{int(r["#"])} ({pct}%)</span>'
            f'<div class="bar-players">{player_list}</div>'
            f'</div>\n'
        )

    # Post-game: criteria distribution
    df_post = df_match["criterio"].value_counts().reset_index()
    df_post.columns = ["criterio", "#"]
    # Exclude empty criteria (e.g. placeholder rows with no predictions)
    df_post = df_post[df_post["criterio"].astype(str).str.strip() != ""]
    df_post.sort_values("criterio", inplace=True)
    criteria_bars = ""
    total_c = int(df_post["#"].sum())
    for _, row in df_post.iterrows():
        pct = round(row["#"] / total_c * 100)
        count = int(row["#"])
        criteria_bars += (
            f'<div class="bar-row">'
            f'<span class="bar-label">{row["criterio"]}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
            f'<span class="bar-pct">{pct}% ({count})</span>'
            f'</div>\n'
        )

    # Player predictions
    bonus_by_player = {}
    bonus_path = os.path.join(config._au_first_round(), "playoffs_scored.csv")
    if os.path.exists(bonus_path):
        df_bonus = pd.read_csv(bonus_path)
        df_bonus_phase = df_bonus[df_bonus["phase"] == phase]
        if not df_bonus_phase.empty:
            for _, br in df_bonus_phase.iterrows():
                who = str(br["boleiro"])
                if who not in bonus_by_player:
                    bonus_by_player[who] = {"correct": 0, "total": 0, "points": 0}
                bonus_by_player[who]["correct"] += int(br["correct"])
                bonus_by_player[who]["total"] += 1
                bonus_by_player[who]["points"] += int(br["points"])

    pred_rows = ""
    prev_pts = None
    for _, row in df_match.iterrows():
        who_val = str(row.get("who", "")).strip()
        if not who_val:
            continue  # skip placeholder synthetic rows
        pts = int(row["pontos"]) if pd.notna(row.get("pontos")) else 0
        # Insert score-group separator when points tier changes
        if prev_pts is not None and pts != prev_pts:
            pred_rows += f'<div class="score-group-sep"></div>\n'
        prev_pts = pts
        is_pending = row.get("valido", 1) == 0
        criterio_str = row.get("criterio", "")
        if pd.isna(criterio_str):
            criterio_str = ""
        if is_pending:
            # Show pending state instead of raw "99-Sem jogo"
            display_criterio = "\u23f3 Aguardando resultado"
            criterio_emoji = "\u23f3"
            pts_color = "var(--warning)"
            pts_bg = "rgba(245,158,11,0.1)"
            pts_border = "var(--warning)"
        else:
            display_criterio = criterio_str
            criterio_emoji = config.scoring_emoji(criterio_str)
            css_var, css_bg, css_border = config.scoring_css_var(criterio_str)
            if css_var:
                pts_color = css_var
                pts_bg = css_bg
                pts_border = css_border
            else:
                hex_color = config.scoring_color(criterio_str)
                if hex_color:
                    pts_color = hex_color
                    pts_bg = hex_color + "1a"
                    pts_border = hex_color + "40"
                else:
                    pts_color = "var(--text-muted)"
                    pts_bg = "transparent"
                    pts_border = "var(--card-border)"
        placar_str = row.get("resultado_bol_placar", "")
        if pd.isna(placar_str):
            placar_str = "? x ?"
        real_str = row.get("resultado_real_placar", "")
        if pd.isna(real_str) or str(real_str).strip().lower() in ("nan", "", "none"):
            real_str = ""
        else:
            real_str = f"Real: {real_str}"
        boleiro_href = f"../../boleiros/{who_val}.html"
        pill_display = f"+{pts}" if pts > 0 else ""
        pred_rows += (
            f'<div class="pred-row">'
            f'<div class="pred-info">'
            f'<div class="pred-name"><a href="{boleiro_href}" class="boleiro-link">{who_val}</a></div>'
            f'<div class="pred-detail">Previsto: {placar_str}{" | " + real_str if real_str else ""}</div>'
            f'</div>'
            f'<div class="score-pill score-pill--sm" style="color:{pts_color};background:{pts_bg};border:1px solid {pts_border}">{criterio_emoji}{pill_display}</div>'
            f'</div>\n'
        )

    # Score display — only returns status badge and optional details,
    # the actual scorecard is now part of the hero block below.
    if is_live:
        parts = real_placar.split(" x ") if has_score and " x " in real_placar else ["?", "?"]
        score_hero_parts = f"<span class=\"score-hero\">{parts[0]} - {parts[1]}</span>"
        status_badge = '<span class="badge badge-danger">\U0001f534 AO VIVO</span>'
    elif has_result:
        parts = real_placar.split(" x ")
        score_hero_parts = f"<span class=\"score-hero\">{parts[0]} - {parts[1]}</span>"
        pen_html = ""
        try:
            hp = df_match.iloc[0].get("home_pen_real")
            ap = df_match.iloc[0].get("away_pen_real")
            hp_str = str(hp).strip() if pd.notna(hp) else ""
            ap_str = str(ap).strip() if pd.notna(ap) else ""
            if hp_str and hp_str != "nan" and ap_str and ap_str != "nan":
                hp_val = int(float(hp_str))
                ap_val = int(float(ap_str))
                pen_html = f'<div class="penalty-score">{hp_val} - {ap_val} nos p\u00eAnaltis</div>'
        except (ValueError, TypeError):
            pass
        zebra_html = ""
        if upset_row is not None and int(upset_row.get("is_upset", 0)) == 1:
            nc = int(upset_row.get("num_correct", 999))
            fav = upset_row.get("favorite", "?")
            if nc <= 2:
                zebra_html = f'<span class="badge badge-danger" style="margin-left:0.5rem;">{ZEBRA_MONSTRA_LABEL}</span>'
            else:
                zebra_html = f'<span class="badge badge-danger" style="margin-left:0.5rem;">{ZEBRA_GRANDE_LABEL}</span>'
        status_badge = f'<span class="badge badge-success">Resultado Final</span>{zebra_html}'
    else:
        score_hero_parts = '<span class="score-hero score-hero--pending">vs</span>'
        status_badge = '<span class="badge badge-warning">Aguardando</span>'

    team_link = '../../times/{}.html'
    # Count players with predictions
    num_players = int(df_match['who'].astype(str).str.strip().ne('').sum())
    body = f"""
<div class="hero match-hero">
    <div class="match-hero-teams">
        <div class="match-hero-team">{home_logo}<a href="../../times/{home}.html" class="match-hero-link">{home}</a></div>
        {score_hero_parts}
        <div class="match-hero-team">{away_logo}<a href="../../times/{away}.html" class="match-hero-link">{away}</a></div>
    </div>
    <div class="match-hero-meta">
        {status_badge}
        <span class="hero-date">{date_str} {hour_str} &middot; {phase}</span>
    </div>
</div>

{pen_html if has_result else ""}

<div class="section">
    <div class="section-title">\U0001f52e Palpites</div>
    <div class="card">
        <div class="bar-chart">{team_bars}</div>
        <hr class="section-divider">
        {score_heatmap}
        <hr class="section-divider">
        <div class="bar-chart" style="margin-top:0;">{score_bars}</div>
        <div class="heat-legend">\U0001f446 clique na linha para ver quem apostou</div>
    </div>
</div>
"""

    if has_result:
        body += f"""
<div class="section">
    <div class="section-title">\U0001f4ca Pos-Jogo</div>
    <div class="card"><div class="bar-chart">{criteria_bars}</div></div>
</div>
"""

    has_any_pts = any(int(r.get("pontos", 0)) > 0 for _, r in df_match.iterrows())
    body += f"""
<div class="section-divider--wide"></div>

<div class="section">
    <div class="section-title">\U0001f4cb Palpites <span class="section-count">{num_players}</span></div>
    {"<div class=\"section-subtitle\">ordenados por pontua\u00e7\u00e3o</div>" if has_result else ""}
    <div class="card card-compact">{pred_rows}</div>
</div>
"""
    return _page_frame(config, f"{home} x {away} - {config.report_title}", body, back_link="../../index.html")


# ------------------------------------------------------------------
# Arena (player comparison)
# ------------------------------------------------------------------

def _build_arena(config: ChampionshipConfig, df_valid: pd.DataFrame) -> str:
    """Arena: toggle players to see stats, evolution chart, and match table."""
    players = sorted(df_valid["who"].unique())

    # ── Load bonus data (per phase) ──
    bonus_by_player = {}
    bonus_path = os.path.join(config._au_first_round(), "playoffs_scored.csv")
    if os.path.exists(bonus_path):
        df_bonus = pd.read_csv(bonus_path)
        if not df_bonus.empty:
            for _, br in df_bonus.iterrows():
                who = str(br["boleiro"])
                if who not in bonus_by_player:
                    bonus_by_player[who] = {"correct": 0, "total": 0, "points": 0, "by_phase": {}}
                bonus_by_player[who]["correct"] += int(br["correct"])
                bonus_by_player[who]["total"] += 1
                bonus_by_player[who]["points"] += int(br["points"])
                ph_raw = str(br.get("phase", ""))
                if ph_raw:
                    ph_key = _short_name(ph_raw, config) if ph_raw else ph_raw
                    bonus_by_player[who]["by_phase"][ph_key] = bonus_by_player[who]["by_phase"].get(ph_key, 0) + int(br["points"])

    # ── Load ranking history for evolution chart ──
    rh_data = {"dates": [], "players": {}, "max_rank": len(players)}
    rh_path = os.path.join(config._au_first_round(), "ranking_history.csv")
    if os.path.exists(rh_path):
        df_rh = pd.read_csv(rh_path)
        rh_data["dates"] = sorted(df_rh["date"].unique())
        for p in players:
            dp = df_rh[df_rh["boleiro"] == p].sort_values("date")
            if not dp.empty:
                rh_data["players"][p] = {
                    "ranks": [int(r) for r in dp["rank"]],
                    "cums": [int(c) for c in dp["cumulative_points"]],
                }

    # ── Build flag img map + slug map from config ──
    flag_map = {}
    slug_map = {}
    for en_name, pt_name in config.team_name_mapping.items():
        logo_url = config.team_logos.get(en_name, "")
        if logo_url:
            flag_map[pt_name] = f'<img src="{logo_url}" class="team-flag" alt="">'
        else:
            flag_map[pt_name] = ""
        sl = config.team_slugs.get(en_name, "")
        slug_map[pt_name] = sl if sl else pt_name

    def _flag(s: str) -> str:
        return flag_map.get(s.strip(), "")

    def _slug(s: str) -> str:
        return slug_map.get(s.strip(), s)

    # ── Phase display labels ──
    phase_emoji_map = dict(config.phase_emojis) if config.phase_emojis else {}

    def _phase_label(ph):
        if pd.isna(ph) or str(ph).strip() in ("", "1afase"):
            return phase_emoji_map.get("1afase", "\U0001f4ca") + " 1\u00aa Fase"
        s = str(ph).strip()
        emoji = phase_emoji_map.get(s, "")
        name = _short_name(s, config)
        return f"{emoji} {name}".strip()

    # ── Build all matches (sorted once) ──
    df_all = df_valid.copy()
    if "phase" in df_all.columns:
        df_all["phase_display"] = df_all["phase"].apply(_phase_label)
    else:
        df_all["phase_display"] = phase_emoji_map.get("1afase", "\U0001f4ca") + " 1\u00aa Fase"
    df_all["away_team"] = df_all["away_team"].astype(str)
    df_all["home_team"] = df_all["home_team"].astype(str)
    df_all["resultado_real_placar"] = df_all["resultado_real_placar"].fillna("")
    df_all["match_label"] = df_all.apply(lambda r: _flag(r["home_team"]) + " " + _slug(r["home_team"]) + " " + str(r["resultado_real_placar"]) + " " + _flag(r["away_team"]) + " " + _slug(r["away_team"]), axis=1)
    df_all["match_label"] = df_all["match_label"].str.replace(r"\s+", " ", regex=True).str.strip()
    df_all["date_phase"] = df_all["date"].str[5:] + " " + df_all["phase_display"]
    matches_df = df_all[["date", "match_label", "phase_display", "date_phase"]].drop_duplicates().sort_values("date", ascending=False)
    matches_list = matches_df.to_dict("records")

    # ── Per-phase display names ──
    if "phase" in df_all.columns:
        unique_phases = df_all["phase"].dropna().unique()
        phase_display = {str(ph): _short_name(str(ph), config) for ph in unique_phases}
    else:
        phase_display = {}
    phase_order = ["1\u00aa Fase"] + [_short_name(pr.name, config) for pr in (config.playoff_rounds or [])]

    # ── Per-player data ──
    player_json = {}
    for p in players:
        df_p = df_all[df_all["who"] == p]
        bdata = bonus_by_player.get(p, {})
        bonus_pts = bdata.get("points", 0)
        match_pts_total = int(df_p["pontos"].sum())
        games = len(df_p)
        total = match_pts_total + bonus_pts
        avg = round(total / games, 1) if games > 0 else 0
        match_pts = []
        match_picks = []
        for _, mr in matches_df.iterrows():
            row = df_p[(df_p["date"] == mr["date"]) & (df_p["match_label"] == mr["match_label"])]
            if len(row) > 0:
                match_pts.append(int(row["pontos"].sum()))
                r = row.iloc[0]
                hg = int(r["home_goals_bol"]) if pd.notna(r.get("home_goals_bol")) else "?"
                ag = int(r["away_goals_bol"]) if pd.notna(r.get("away_goals_bol")) else "?"
                match_picks.append(f"{hg}x{ag}")
            else:
                match_pts.append(None)
                match_picks.append(None)
        # per-match cumulative (running sum of match pts, NO bonus)
        # match_pts is newest-first; reverse to compute running total chronologically
        _chrono = list(reversed(match_pts))
        _running = 0
        _cum_chrono = []
        for pts in _chrono:
            if pts is not None:
                _running += pts
                _cum_chrono.append(_running)
            else:
                _cum_chrono.append(None if _running == 0 else _running)
        match_cums = list(reversed(_cum_chrono))
        # per-match rank (from ranking_history, includes bonus — real standing)
        rhp = rh_data["players"].get(p, {})
        rank_by_date = {}
        if rhp and "ranks" in rhp:
            for di, d in enumerate(rh_data["dates"]):
                if di < len(rhp["ranks"]):
                    rank_by_date[d] = rhp["ranks"][di]
        match_ranks = [rank_by_date.get(mr["date"]) for _, mr in matches_df.iterrows()]
        # ── Per-phase match points ──
        phase_pts = {}
        if "phase" in df_all.columns:
            grp_mask = df_p["phase"].isna()
            if grp_mask.any():
                phase_pts["1\u00aa Fase"] = int(df_p.loc[grp_mask, "pontos"].sum())
            for ph, grp in df_p.groupby("phase"):
                if pd.isna(ph):
                    continue
                display = phase_display.get(str(ph), str(ph))
                phase_pts[display] = int(grp["pontos"].sum())
        else:
            phase_pts = {"1\u00aa Fase": int(df_p["pontos"].sum())}
        sorted_phase_pts = {ph: phase_pts.get(ph, 0) for ph in phase_order if ph in phase_pts}
        player_json[p] = {
            "total": total,
            "match_total": match_pts_total,
            "avg": avg,
            "games": games,
            "bonus": bonus_pts,
            "bonus_correct": bdata.get("correct", 0),
            "bonus_total": bdata.get("total", 0),
            "match_pts": match_pts,
            "match_picks": match_picks,
            "match_cums": match_cums,
            "match_ranks": match_ranks,
            "phase_pts": sorted_phase_pts,
            "phase_bonus": bdata.get("by_phase", {}),
        }

    # ── short phase name → emoji ──
    short_emoji_map = {"1\u00aa Fase": (config.phase_emojis or {}).get("1afase", "\U0001f4ca")}
    for pr in (config.playoff_rounds or []):
        short = _short_name(pr.name, config)
        emoji = (config.phase_emojis or {}).get(pr.key, "")
        if emoji:
            short_emoji_map[short] = emoji

    import json
    json_str = json.dumps({
        "players": player_json,
        "matches": matches_list,
        "rh": rh_data,
        "phase_order": phase_order,
        "short_emoji_map": short_emoji_map,
    }, ensure_ascii=False)

    # ── Toggle buttons ──
    import re as _re
    toggle_btns = ""
    for p in players:
        safe = _re.sub(r"\s+", "_", p)
        toggle_btns += (
            f'<button id="tb-{safe}" class="toggle-btn" '
            f'onclick="togglePlayer(\'{p}\')">{p}</button>\n'
        )

    js_code = r"""
const DATA = DATA_PLACEHOLDER;
const P = DATA.players;
const M = DATA.matches;
const RH = DATA.rh;
const PHASE_ORDER = DATA.phase_order;
const SHORT_EMOJI = DATA.short_emoji_map;
const COLORS = ['#e6194b','#3cb44b','#4363d8','#f58231','#911eb4','#42d4f4','#f032e6','#469990','#e6beff','#9A6324'];
const MAX_PLAYERS = 10;
const activePlayers = new Set();

function togglePlayer(name) {
    const safe = name.replace(/\s+/g, '_');
    const btn = document.getElementById('tb-' + safe);
    if (activePlayers.has(name)) { activePlayers.delete(name); btn.classList.remove('active'); }
    else if (activePlayers.size >= MAX_PLAYERS) { return; }
    else { activePlayers.add(name); btn.classList.add('active'); }
    render();
}

function resetSelection() {
    activePlayers.forEach(function(name) {
        const safe = name.replace(/\s+/g, '_');
        document.getElementById('tb-' + safe).classList.remove('active');
    });
    activePlayers.clear();
    render();
}

function render() {
    drawStats();
    drawChart();
    drawTable();
}

// ── STAT CARDS ──
function drawStats() {
    const container = document.getElementById('arena-stats');
    if (activePlayers.size === 0) { container.innerHTML = '<div class="subtitle" style="padding:0.5rem;">Selecione jogadores acima</div>'; return; }
    let html = '<div style="display:flex;flex-wrap:wrap;gap:0.5rem;">';
    let idx = 0;
    activePlayers.forEach(function(name) {
        const d = P[name];
        const color = COLORS[idx % COLORS.length]; idx++;
        html += '<div class="stat-card" style="flex:1;min-width:200px;">' +
            '<div class="label" style="font-weight:600;font-size:0.8rem;color:' + color + ';">' + name + '</div>' +
            '<div style="font-size:0.65rem;color:var(--text-muted);margin-bottom:0.2rem;">' + d.total + ' pts | M\u00e9dia: ' + d.avg + ' | ' + d.games + ' jogos | B\u00f4nus times: +' + d.bonus + ' (' + d.bonus_correct + '/' + d.bonus_total + ')</div>' +
            '<div style="display:flex;flex-wrap:wrap;gap:0.2rem;">';
        PHASE_ORDER.forEach(function(ph) {
            var pts = (d.phase_pts && d.phase_pts[ph]) ? d.phase_pts[ph] : 0;
            var bns = (d.phase_bonus && d.phase_bonus[ph]) ? d.phase_bonus[ph] : 0;
            if (pts + bns === 0) return;
            var emoji = SHORT_EMOJI[ph] || '';
            html += '<span style="font-size:0.6rem;background:var(--card-border);border-radius:4px;padding:0.1rem 0.3rem;white-space:nowrap;">' + emoji + ' ' + ph + ' ' + pts + 'pts' + (bns ? ' +' + bns + ' b\u00f4nus' : '') + '</span>';
        });
        html += '</div></div>';
    });
    container.innerHTML = html + '</div>';
}

// ── EVOLUTION CHART ──
function drawChart() {
    const chartDiv = document.getElementById('arena-chart');
    if (activePlayers.size === 0) { chartDiv.innerHTML = ''; return; }
    chartDiv.innerHTML = '<div style="position:relative;"><canvas id="rank-chart" width="600" height="250" style="width:100%;height:250px;cursor:crosshair;"></canvas><div id="rank-tooltip" style="display:none;position:absolute;background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;padding:0.5rem 0.75rem;font-size:0.75rem;pointer-events:none;z-index:100;box-shadow:0 4px 12px var(--shadow-color);"></div></div>';
    const canvas = document.getElementById('rank-chart');
    const tooltip = document.getElementById('rank-tooltip');
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = 250 * dpr;
    ctx.scale(dpr, dpr);
    const W = rect.width;
    const H = 250;
    const padL = 44, padR = 44, padT = 24, padB = 30;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const dates = RH.dates;
    const maxRank = RH.max_rank;
    ctx.clearRect(0, 0, W, H);

    // Grid - Y in steps of 5
    ctx.strokeStyle = '#30363d';
    ctx.lineWidth = 0.5;
    const yTicks = [1];
    for (let t = 5; t <= maxRank; t += 5) yTicks.push(t);
    if (yTicks[yTicks.length-1] !== maxRank) yTicks.push(maxRank);
    yTicks.forEach(function(pos) {
        const y = padT + ((pos - 1) / maxRank) * plotH;
        ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
    });
    ctx.fillStyle = '#8899aa';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'right';
    yTicks.forEach(function(pos) {
        const y = padT + ((pos - 1) / maxRank) * plotH;
        ctx.fillText(pos + '\u00ba', padL - 4, y + 3);
        ctx.textAlign = 'left';
        ctx.fillText(pos + '\u00ba', W - padR + 4, y + 3);
        ctx.textAlign = 'right';
    });

    // X axis
    ctx.fillStyle = '#8899aa';
    ctx.font = '9px sans-serif';
    const labelW = 30;
    const dataGap = plotW / Math.max(dates.length - 1, 1);
    const xLabelStep = Math.max(1, Math.ceil(labelW * 1.3 / dataGap));
    dates.forEach(function(d, i) {
        if (i % xLabelStep === 0 || i === dates.length - 1) {
            const x = padL + (plotW / Math.max(dates.length - 1, 1)) * i;
            if (i === 0) { ctx.textAlign = 'left'; ctx.fillText(d.slice(5), padL, H - 6); }
            else if (i === dates.length - 1) { ctx.textAlign = 'right'; ctx.fillText(d.slice(5), W - padR, H - 6); }
            else { ctx.textAlign = 'center'; ctx.fillText(d.slice(5), x, H - 6); }
        }
    });

    function getX(i) { return padL + (plotW / Math.max(dates.length - 1, 1)) * i; }
    function getY(rank) { return padT + ((rank - 1) / maxRank) * plotH; }

    let idx = 0;
    activePlayers.forEach(function(name) {
        const p = RH.players[name];
        if (!p) return;
        const color = COLORS[idx % COLORS.length]; idx++;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        p.ranks.forEach(function(r, i) {
            const x = getX(i);
            const y = getY(r);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
        p.ranks.forEach(function(r, i) {
            const x = getX(i);
            const y = getY(r);
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(x, y, 3.5, 0, Math.PI * 2);
            ctx.fill();
        });
    });

    // Tooltip
    if (!canvas._listener) {
        canvas._listener = true;
        canvas.addEventListener('mousemove', function(e) {
            const r = canvas.getBoundingClientRect();
            const mx = e.clientX - r.left;
            const my = e.clientY - r.top;
            let closest = -1, closestDist = 20;
            for (let i = 0; i < dates.length; i++) {
                const dx = Math.abs(mx - getX(i));
                if (dx < closestDist) { closestDist = dx; closest = i; }
            }
            if (closest >= 0 && activePlayers.size > 0) {
                let tip = '<div style="color:var(--text-muted);margin-bottom:0.25rem;">' + dates[closest] + '</div>';
                let cIdx = 0;
                activePlayers.forEach(function(name) {
                    const rank = RH.players[name].ranks[closest];
                    const cum = RH.players[name].cums[closest];
                    const color = COLORS[cIdx % COLORS.length]; cIdx++;
                    tip += '<div style="color:' + color + ';">' + name + ': <strong>' + rank + '\u00ba</strong> (' + cum + ' pts)</div>';
                });
                tooltip.style.display = 'block';
                tooltip.innerHTML = tip;
                tooltip.style.left = Math.min(mx + 12, W - 140) + 'px';
                tooltip.style.top = Math.max(my - 10, 5) + 'px';
            } else {
                tooltip.style.display = 'none';
            }
        });
        canvas.addEventListener('mouseleave', function() { tooltip.style.display = 'none'; });
    }
}

// ── MATCH TABLE ──
function drawTable() {
    const container = document.getElementById('arena-table-wrap');
    if (activePlayers.size === 0) { container.innerHTML = ''; return; }
    const activeArr = Array.from(activePlayers);
    let html = '<div style="font-size:0.6rem;color:var(--text-muted);padding:0.2rem 0;display:flex;align-items:flex-start;gap:0.5rem;">' +
        '<div style="background:var(--card-border);border-radius:4px;padding:0.2rem 0.5rem;text-align:right;font-size:0.5rem;line-height:1.6;min-width:55px;font-family:var(--font-mono);">' +
        '2x1<br>\u26bd 5<br>313 / 3\u00ba<br>-15</div>' +
        '<div style="line-height:1.6;padding-top:0.05rem;">' +
        '<span style="display:block;font-size:0.55rem;">palpite</span>' +
        '<span style="display:block;font-size:0.55rem;">pts (\u26bd melhor do jogo)</span>' +
        '<span style="display:block;font-size:0.55rem;">acumulado (s\u00f3 palpites) / ranking</span>' +
        '<span style="display:block;font-size:0.55rem;">dif. do l\u00edder dos selecionados</span>' +
        '</div></div>';
    html += '<div style="overflow-x:auto;"><table style="width:100%;font-size:0.7rem;border-collapse:collapse;">';
    // Header
    html += '<thead><tr style="border-bottom:1px solid var(--card-border);">';
    html += '<th style="text-align:left;padding:0.25rem 0.3rem;white-space:nowrap;font-size:0.65rem;">Data / Fase</th>';
    html += '<th style="text-align:left;padding:0.25rem 0.3rem;font-size:0.65rem;">Jogo</th>';
    activeArr.forEach(function(name, i) {
        const color = COLORS[i % COLORS.length];
        html += '<th style="text-align:center;padding:0.25rem 0.15rem;color:' + color + ';white-space:nowrap;font-size:0.6rem;">\u25cf</th>';
    });
    html += '</tr></thead><tbody>';
    // Rows - subtle highlight for highest score per match
    M.forEach(function(match, mi) {
        let rowMax = -1;
        activeArr.forEach(function(name) {
            const pts = P[name].match_pts[mi];
            if (pts !== null && pts !== undefined && pts > rowMax) rowMax = pts;
        });
        // pre-compute max cum among selected at this match for diff
        let maxCum = -Infinity;
        activeArr.forEach(function(name) {
            const c = P[name].match_cums[mi];
            if (c !== null && c !== undefined && c > maxCum) maxCum = c;
        });
        html += '<tr style="border-bottom:1px solid var(--card-border);">';
        html += '<td style="padding:0.15rem 0.3rem;white-space:nowrap;color:var(--text-muted);font-size:0.55rem;">' + match.date_phase + '</td>';
        html += '<td style="padding:0.15rem 0.3rem;font-size:0.5rem;">' + match.match_label + '</td>';
        activeArr.forEach(function(name, i) {
            const color = COLORS[i % COLORS.length];
            const pts = P[name].match_pts[mi];
            const pick = P[name].match_picks[mi];
            const cum = P[name].match_cums[mi];
            const rank = P[name].match_ranks[mi];
            if (pts !== null && pts !== undefined) {
                const isBest = pts === rowMax && rowMax > 0;
                const prefix = isBest ? '\u26bd ' : '';
                const diff = cum - maxCum;
                const diffStr = '<span style="font-size:0.4rem;color:var(--text-muted);display:block;">' + diff + '</span>';
                html += '<td style="text-align:center;padding:0.1rem 0.1rem;color:' + color + ';font-weight:600;font-size:0.55rem;">' +
                    (pick ? '<span style="font-size:0.45rem;font-weight:400;color:var(--text-muted);display:block;">' + pick + '</span>' : '') +
                    prefix + pts +
                    (cum ? '<span style="font-size:0.4rem;font-weight:400;color:var(--text-muted);display:block;">' + cum + (rank ? ' / ' + rank + '\u00ba' : '') + '</span>' : '') +
                    diffStr +
                    '</td>';
            } else {
                html += '<td style="text-align:center;padding:0.1rem 0.1rem;color:var(--text-muted);font-size:0.55rem;">' +
                    (pick ? '<span style="font-size:0.45rem;display:block;">' + pick + '</span>' : '') +
                    '\u2014' +
                    (cum ? '<span style="font-size:0.4rem;display:block;">' + cum + (rank ? ' / ' + rank + '\u00ba' : '') + '</span>' : '') +
                    '</td>';
            }
        });
        html += '</tr>';
    });
    // Totals row
    html += '<tr style="border-top:2px solid var(--accent);font-weight:700;">';
    html += '<td style="padding:0.25rem 0.3rem;font-size:0.65rem;"></td><td style="padding:0.25rem 0.3rem;font-size:0.65rem;">Total</td>';
    activeArr.forEach(function(name, i) {
        const color = COLORS[i % COLORS.length];
        html += '<td style="text-align:center;padding:0.3rem 0.4rem;color:' + color + ';font-size:0.75rem;">' + P[name].total + '</td>';
    });
    html += '</tr></tbody></table></div>';
    // Add bonus row
    html += '<div style="display:flex;flex-wrap:wrap;gap:1rem;padding:0.5rem 0;font-size:0.75rem;color:var(--text-muted);">';
    activeArr.forEach(function(name, i) {
        const d = P[name];
        if (d.bonus_total > 0) {
            const color = COLORS[i % COLORS.length];
            html += '<div style="color:' + color + ';">\u25cf ' + name + ' b\u00f4nus times: +' + d.bonus + 'pts (' + d.bonus_correct + '/' + d.bonus_total + ')</div>';
        }
    });
    html += '</div>';
    html += '<div style="font-size:0.6rem;color:var(--text-muted);padding-top:0.15rem;">B\u00f4nus times: acertos em palpites de sele\u00e7\u00f5es que avan\u00e7aram de fase. Ex: 46/65 = 46 acertos em 65 palpites.</div>';
    container.innerHTML = html;
}
"""

    body = f"""
<div class="hero">
    <h1>\u2694\ufe0f Arena</h1>
    <div class="subtitle">Clique nos jogadores para ligar/desligar</div>
</div>

<div class="card">
    <div class="card-title">Jogadores</div>
    <div style="display:flex;flex-wrap:wrap;gap:0.4rem;">
        {toggle_btns}
    </div>
    <div style="display:flex;align-items:center;gap:0.5rem;padding-top:0.3rem;">
        <span style="font-size:0.7rem;color:var(--text-muted);">M\u00e1x 10 jogadores</span>
        <button onclick="resetSelection()" style="font-size:0.65rem;padding:0.15rem 0.5rem;border:1px solid var(--card-border);border-radius:4px;background:var(--card-bg);color:var(--text-muted);cursor:pointer;">Limpar</button>
    </div>
</div>

<div class="card">
    <div class="card-title">Estat\u00edsticas</div>
    <div id="arena-stats"><div class="subtitle" style="padding:0.5rem;">Selecione jogadores acima</div></div>
</div>

<div class="card">
    <div class="card-title">Evolu\u00e7\u00e3o no Ranking</div>
    <div id="arena-chart"></div>
</div>

<div class="card">
    <div class="card-title">Jogos</div>
    <div id="arena-table-wrap"><div class="subtitle" style="padding:0.5rem;">Selecione jogadores acima</div></div>
</div>

<style>
.toggle-btn {{
    padding: 0.35rem 0.7rem;
    border: 1px solid var(--card-border);
    border-radius: 6px;
    background: var(--card-bg);
    color: var(--text-muted);
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.2s;
}}
.toggle-btn.active {{
    background: var(--accent);
    color: var(--text-inverse);
    border-color: var(--accent);
}}
.team-flag {{
    width: 18px;
    height: 12px;
    vertical-align: middle;
}}
</style>

<script>
{js_code.replace('DATA_PLACEHOLDER', json_str)}
</script>
"""
    return _page_frame(config, f"Arena - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Boldômetro page
# ------------------------------------------------------------------


def _build_boldometer(config: ChampionshipConfig) -> str:
    """Simple tendency table: who predicts more/less goals than reality."""
    bold_path = _norm(os.path.join(config._au_first_round(), "boldness_index.csv"))
    if not os.path.exists(bold_path):
        return _page_frame(config, f"Bold\u00f4metro - {config.report_title}",
                           "<div class='hero'><h1>\U0001f4ca Bold\u00f4metro</h1><div class='subtitle'>Ainda n\u00e3o h\u00e1 dados.</div></div>")
    df_bold = pd.read_csv(bold_path, sep=",")
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    df_avg = df_valid.groupby("who")["pontos"].mean().reset_index()
    df_avg.columns = ["boleiro", "avg_pts_per_game"]
    df = df_bold.merge(df_avg, on="boleiro", how="left")

    # Real avg goals per game from results
    df_results = pd.read_csv(config.results_file, sep=",").dropna(subset=["home_goals"])
    real_avg = (df_results["home_goals"].astype(float) + df_results["away_goals"].astype(float)).mean()

    players = []
    for _, r in df.iterrows():
        players.append({
            "name": r["boleiro"],
            "avg_goals": float(r["avg_total_goals_bol"]),
            "avg_pts": float(r["avg_pts_per_game"]),
            "boldness": float(r["boldness_score"]),
            "games": int(r["games"]),
        })

    # Sort by boldness descending (most optimistic first)
    players.sort(key=lambda p: -p["boldness"])

    table_rows = ""
    for p in players:
        diff = p["avg_goals"] - real_avg
        if diff > 0.3:
            icon = "\U0001f446"
            label = "Otimista"
            color = "var(--warning)"
        elif diff < -0.3:
            icon = "\U0001f447"
            label = "Pessimista"
            color = "var(--bolao)"
        else:
            icon = "\u27a1\ufe0f"
            label = "Realista"
            color = "var(--text-muted)"
        bar_w = min(100, max(2, (p["avg_goals"] / (real_avg * 2) * 100)))
        table_rows += f"""<tr>
            <td style="padding:0.4rem 0.5rem;"><a href="boleiros/{p['name']}.html">{p['name']}</a></td>
            <td style="padding:0.4rem 0.5rem;text-align:center;"><span style="font-size:1.2rem;">{icon}</span></td>
            <td style="padding:0.4rem 0.5rem;font-weight:600;color:{color};">{label}</td>
            <td style="padding:0.4rem 0.5rem;">
                <div style="display:flex;align-items:center;gap:0.4rem;">
                    <span style="font-size:0.7rem;color:var(--text-muted);min-width:24px;">{real_avg:.1f}</span>
                    <div class="bar-track" style="flex:1;height:12px;">
                        <div class="bar-fill" style="width:{bar_w:.0f}%;height:12px;background:{color};border-radius:4px;"></div>
                    </div>
                    <span style="font-weight:700;font-size:0.85rem;min-width:30px;text-align:right;">{p['avg_goals']:.1f}</span>
                </div>
            </td>
            <td style="padding:0.4rem 0.5rem;text-align:right;color:var(--text-muted);font-size:0.8rem;">{p['games']}</td>
        </tr>"""

    body = f"""
<div class="hero">
    <h1>\U0001f4ca Bold\u00f4metro</h1>
    <div class="subtitle">Quem aposta mais gols? Quem aposta menos?</div>
</div>

<div class="card" style="margin:0.75rem;">
    <div style="font-size:0.85rem;margin-bottom:0.75rem;">
        <p style="margin-bottom:0.5rem;">
            A m\u00e9dia de <strong>gols reais</strong> por jogo \u00e9 <strong>{real_avg:.1f}</strong>.
            A barra mostra quantos gols cada jogador aposta em m\u00e9dia.
        </p>
        <p>
            <span style="color:var(--warning);font-weight:700;">\U0001f446 Otimista</span> = aposta mais gols que a m\u00e9dia real &middot;
            <span style="color:var(--bolao);font-weight:700;">\U0001f447 Pessimista</span> = aposta menos &middot;
            <span style="color:var(--text-muted);font-weight:700;">\u27a1\ufe0f Realista</span> = perto da m\u00e9dia
        </p>
    </div>
    <div style="overflow-x:auto;">
        <table class="rank-table">
            <thead><tr>
                <th>Jogador</th>
                <th style="text-align:center;">Tend\u00eancia</th>
                <th>Perfil</th>
                <th style="min-width:140px;">M\u00e9dia gols aposta vs real ({real_avg:.1f})</th>
                <th style="text-align:right;">Jogos</th>
            </tr></thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    <div style="margin-top:0.5rem;font-size:0.7rem;color:var(--text-muted);text-align:center;">
        Ordenado do mais otimista (aposta mais gols) ao mais pessimista (aposta menos)
    </div>
</div>
"""
    return _page_frame(config, f"Bold\u00f4metro - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Raio-X Radar page
# ------------------------------------------------------------------


def _build_bolao_xray(config: ChampionshipConfig) -> str:
    """Bolão X-ray: meta-analysis of the entire sweepstake — no per-player focus."""
    _parts: list[pd.DataFrame] = []
    gp = config.gold_all_path()
    if os.path.exists(gp):
        _parts.append(pd.read_csv(gp, sep=","))
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_all_path(pr.key)
        if os.path.exists(pp):
            _parts.append(pd.read_csv(pp, sep=","))
    if not _parts:
        return _page_frame(config, f"Raio-X do Bol\u00e3o - {config.report_title}", "<div class='hero'><h1>\U0001f50d Raio-X do Bol\u00e3o</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados. ainda</div></div>", active_nav="bolao_xray.html")
    df_all = pd.concat(_parts, ignore_index=True)
    df_valid = df_all[df_all["valido"] == 1].copy() if "valido" in df_all.columns else df_all.copy()
    df_results = pd.read_csv(config.results_file, sep=",").dropna(subset=["home_goals"])

    # Build resultado_real_placar from raw columns
    df_results["resultado_real_placar"] = df_results.apply(
        lambda r: f"{int(r['home_goals'])} x {int(r['away_goals'])}"
        if pd.notna(r.get("home_goals")) and pd.notna(r.get("away_goals"))
        else "",
        axis=1,
    )

    # Build a lookup: match -> real placar (from first prediction with result)
    match_real_result = df_valid.dropna(subset=["home_goals_real"]).groupby("match").agg(
        home_goals_real=("home_goals_real", "first"),
        away_goals_real=("away_goals_real", "first"),
    ).reset_index()
    match_real_result["real_placar"] = match_real_result.apply(
        lambda r: f"{int(r['home_goals_real'])} x {int(r['away_goals_real'])}", axis=1
    )

    # ----- Snapshot numbers -----
    n_players = df_valid["who"].nunique()
    n_matches = df_valid["match"].nunique()
    n_predictions = len(df_valid)
    total_pts = int(df_valid["pontos"].sum())
    avg_pts_player = round(total_pts / n_players, 1) if n_players else 0
    max_possible = _max_points_per_game(config) * n_matches * n_players
    overall_aproveitamento = round(total_pts / max_possible * 100, 1) if max_possible > 0 else 0

    # ----- Ranking table (moved from overview) -----
    score_names = config.scoring_rule_names()
    agg_cols = ["pontos"] + [c for c in score_names if c in df_valid.columns]
    df_rank = df_valid.groupby("who", as_index=False)[agg_cols].sum()
    df_rank.sort_values("pontos", ascending=False, inplace=True)
    df_rank.reset_index(drop=True, inplace=True)
    df_rank["#"] = range(1, len(df_rank) + 1)
    rank_rows = ""
    for _, row in df_rank.iterrows():
        rank_num = int(row["#"])
        medal = "\U0001f947" if rank_num == 1 else "\U0001f948" if rank_num == 2 else "\U0001f949" if rank_num == 3 else ""
        rank_class = f"rank-{rank_num}" if rank_num <= 3 else ""
        cells = f'<td>{medal} {rank_num}</td><td><a href="boleiros/{row["who"]}.html">{row["who"]}</a></td>'
        cells += f'<td style="font-weight:700;color:var(--accent)">{int(row["pontos"])}</td>'
        for sn in score_names:
            if sn in row.index:
                val = int(row[sn]) if pd.notna(row[sn]) else 0
                cells += f"<td>{val}</td>"
        rank_rows += f'<tr class="{rank_class}">{cells}</tr>\n'
    rank_header = ""
    for sn in score_names:
        emoji = config.scoring_emoji(sn)
        h = f"{emoji} " if emoji else ""
        h += sn.split("-")[0].strip()
        rank_header += f"<th>{h}</th>"

    # ----- Heatmap: player (row) x day (column), color = points -----
    df_heat = df_valid.groupby(["who", "date"], as_index=False)["pontos"].sum()
    # Sort players alphabetically
    player_order = sorted(df_heat["who"].unique())
    date_order = sorted(df_heat["date"].unique())

    # Theoretical max points per day = matches_that_day * max_points_per_game
    matches_per_day = df_valid.groupby("date")["match"].nunique()
    max_pts_per_game = _max_points_per_game(config)

    # Pivot: rows=players, cols=dates
    heat_pivot = df_heat.pivot(index="who", columns="date", values="pontos").fillna(0)
    heat_pivot = heat_pivot.reindex(player_order)
    heat_pivot = heat_pivot[date_order]

    # Color scale: red (0%) → green (100%) via simple RGB
    def _heat_color(pct: float) -> str:
        r = int(200 - pct * 160)
        g = int(55 + pct * 165)
        b = 55
        return f"rgb({r},{g},{b})"

    heat_html = ""
    for player in player_order:
        row = heat_pivot.loc[player]
        cells = ""
        for day in date_order:
            val = int(row[day])
            day_max = int(matches_per_day.get(day, 1) * max_pts_per_game)
            pct = val / day_max if day_max > 0 else 0
            display_val = f"{round(pct * 100)}%"
            bg = _heat_color(pct)
            cells += (
                f'<div class="heat-cell" style="background:{bg};" '
                f'title="{player}: {val} pts de {day_max} max possivel ({display_val})">{display_val}</div>'
            )
        heat_html += (
            f'<div class="heat-row">'
            f'<div class="heat-label">{player}</div>'
            f'<div class="heat-cells">{cells}</div>'
            f'<div class="heat-label-right">{player}</div>'
            f'</div>\n'
        )

    # Header row (wrap cells in .heat-cells too, to match data rows alignment)
    header_cells = ""
    for day in date_order:
        d = pd.to_datetime(day).strftime("%d/%m")
        header_cells += f'<div class="heat-cell-header">{d}</div>'
    heat_header = f'<div class="heat-row"><div class="heat-label">Jogador</div><div class="heat-cells">{header_cells}</div><div class="heat-label-right">Jogador</div></div>\n'

    # Average row: mean points per player per day
    avg_cells = ""
    for day in date_order:
        day_vals = heat_pivot[day].values
        avg = round(sum(day_vals) / len(day_vals), 1)
        avg_cells += f'<div class="heat-cell-header" style="font-weight:600;">{avg}</div>'
    heat_avg = f'<div class="heat-row"><div class="heat-total-label">Media pts/dia</div><div class="heat-cells">{avg_cells}</div><div class="heat-label-right" style="font-size:0.65rem;color:var(--text-muted);border-top:1px solid var(--card-border);">M\u00e9dia</div></div>\n'

    # Aproveitamento: average of INDIVIDUAL player pcts (each player's pts / theoretical max)
    pct_cells = ""
    for day in date_order:
        day_max = int(matches_per_day.get(day, 1) * max_pts_per_game)
        day_vals = heat_pivot[day].values
        # Each player's individual pct
        individual_pcts = [v / day_max for v in day_vals if day_max > 0]
        avg_pct = round(sum(individual_pcts) / len(individual_pcts) * 100) if individual_pcts else 0
        bg = _heat_color(avg_pct / 100)
        pct_cells += f'<div class="heat-cell" style="background:{bg};">{avg_pct}%</div>'
    heat_pct_row = f'<div class="heat-row"><div class="heat-total-label">Aproveitamento</div><div class="heat-cells">{pct_cells}</div><div class="heat-label-right" style="font-size:0.65rem;color:var(--text-muted);">Aprov.</div></div>\n'

    # Total row: max possivel per day
    total_cells = ""
    for day in date_order:
        day_max = int(matches_per_day.get(day, 1) * max_pts_per_game)
        total_cells += f'<div class="heat-cell-header" style="font-weight:700;">{day_max}</div>'
    heat_total = f'<div class="heat-row"><div class="heat-total-label">Max possivel</div><div class="heat-cells">{total_cells}</div><div class="heat-label-right" style="font-size:0.65rem;color:var(--text-muted);">M\u00e1x</div></div>\n'

    # ----- Hit type distribution (using actual scoring rules from config) -----
    rule_map = {r.name: r.points for r in config.scoring_rules}
    # Order the rules as they appear in config (priority = their index order)
    tipo_order = [r.name for r in config.scoring_rules]

    def _rule_color(rname: str) -> str:
        css_vars = config.scoring_css_var(rname)
        return css_vars[0] if css_vars and css_vars[0] else "var(--text-muted)"

    tipo_counts = df_valid["criterio"].value_counts()
    tipo_rows = ""
    largest_tipo_count = max((int(tipo_counts.get(t, 0)) for t in tipo_order), default=1)
    for t in tipo_order:
        cnt = int(tipo_counts.get(t, 0))
        pts_per = rule_map.get(t, 0)
        pct = round(cnt / n_predictions * 100, 1) if n_predictions else 0
        bar_w = max(cnt / largest_tipo_count * 100, 1)
        name_part = t.split("-", 1)[1] if "-" in t else t
        label = f"{name_part} (+{pts_per}p)" if pts_per > 0 else name_part
        color = _rule_color(t)
        tipo_rows += f"""
        <tr>
            <td style="padding:0.3rem 0.5rem;"><span style="color:{color};font-weight:700;">\u25a0</span> {label}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;font-weight:600;">{cnt}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;color:var(--text-muted);">{pct}%</td>
            <td style="padding:0.3rem 0.5rem;width:30%;"><div class="bar-track"><div class="bar-fill" style="width:{bar_w:.0f}%;background:{color};height:10px;"></div></div></td>
        </tr>"""

    # Exact-score rule name from config (e.g. "1-Placar exato")
    exact_rule_name = next((r.name for r in config.scoring_rules if r.rule == "exact_score"), "1-Placar exato")
    exact_points = next((r.points for r in config.scoring_rules if r.rule == "exact_score"), 12)

    # ----- Match predictability: percent who got EXACT SCORE (+{exact_points}) -----
    match_stats = df_valid.groupby("match").agg(
        total=("pontos", "count"),
        exact=("criterio", lambda x: (x == exact_rule_name).sum()),
    ).reset_index()
    match_stats["pct"] = (match_stats["exact"] / match_stats["total"] * 100).round(1)
    match_info = df_valid[["match", "home_team", "away_team"]].drop_duplicates("match")
    match_stats = match_stats.merge(match_info, on="match", how="left")
    match_stats = match_stats.merge(match_real_result[["match", "real_placar"]], on="match", how="left")
    match_stats["real_placar"] = match_stats["real_placar"].fillna("?")

    def _match_rows(subset):
        html = ""
        for _, r in subset.iterrows():
            html += f"<tr><td style='padding:0.3rem 0.5rem;font-size:0.75rem;'>{r['home_team']} vs {r['away_team']}</td><td style='padding:0.3rem 0.5rem;text-align:center;font-weight:600;'>{r['real_placar']}</td><td style='padding:0.3rem 0.5rem;text-align:right;font-weight:600;'>{r['pct']}%</td><td style='padding:0.3rem 0.5rem;text-align:right;color:var(--text-muted);'>{int(r['exact'])}/{int(r['total'])}</td></tr>"
        return html

    top_pred = match_stats.nlargest(10, "pct")
    top_pred_html = _match_rows(top_pred)
    worst_pred = match_stats.nsmallest(10, "pct")
    worst_pred_html = _match_rows(worst_pred)

    # ----- Points histogram: distribution of total points per match -----
    match_pts_total = df_valid.groupby("match")["pontos"].sum().reset_index()
    # Bucket by 20-point ranges
    max_pts_match = int(match_pts_total["pontos"].max())
    bucket_size = 20
    num_buckets = max(1, (max_pts_match // bucket_size) + 1)
    hist_buckets = {}
    for i in range(num_buckets):
        low = i * bucket_size
        high = (i + 1) * bucket_size
        label = f"{low}-{high}"
        count = int(((match_pts_total["pontos"] >= low) & (match_pts_total["pontos"] < high)).sum())
        if count > 0:
            hist_buckets[label] = count
    max_hist = max(hist_buckets.values()) if hist_buckets else 1
    hist_rows = ""
    for label, count in sorted(hist_buckets.items(), key=lambda x: int(x[0].split("-")[0])):
        bar_w = max(count / max_hist * 100, 1)
        hist_rows += f"""
        <tr>
            <td style="padding:0.3rem 0.5rem;font-weight:600;">{label}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;">{count}</td>
            <td style="padding:0.3rem 0.5rem;width:40%;"><div class="bar-track"><div class="bar-fill" style="width:{bar_w:.0f}%;background:var(--accent);height:12px;"></div></div></td>
        </tr>"""

    # ----- Most predicted scorelines -----
    score_counts = df_valid["resultado_bol_placar"].value_counts().head(10)
    score_rows = ""
    max_score_count = score_counts.iloc[0] if not score_counts.empty else 1
    for placar, cnt in score_counts.items():
        pct = round(cnt / n_predictions * 100, 1) if n_predictions else 0
        bar_w = max(cnt / max_score_count * 100, 1)
        score_rows += f"""
        <tr>
            <td style="padding:0.3rem 0.5rem;font-weight:600;font-size:0.9rem;">{placar}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;">{cnt}</td>
            <td style="padding:0.3rem 0.5rem;text-align:right;color:var(--text-muted);">{pct}%</td>
            <td style="padding:0.3rem 0.5rem;width:30%;"><div class="bar-track"><div class="bar-fill" style="width:{bar_w:.0f}%;background:var(--accent);height:10px;"></div></div></td>
        </tr>"""

    # ----- Actual score distribution -----
    actual_scores = df_results["resultado_real_placar"].value_counts().head(10)
    actual_rows = ""
    for placar, cnt in actual_scores.items():
        actual_rows += f"""
        <tr><td style="padding:0.3rem 0.5rem;font-weight:600;">{placar}</td><td style="padding:0.3rem 0.5rem;text-align:right;">{cnt}</td></tr>"""

    body = f"""
<div class="hero">
    <h1>\U0001f50d Raio-X do Bol\u00e3o</h1>
    <div class="subtitle">Como o bol\u00e3o inteiro est\u00e1 se comportando</div>
</div>

<!-- Snapshot -->
<div class="stat-row" style="grid-template-columns:repeat(3,1fr);margin:0.75rem;">
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--accent);">{n_players}</div>
        <div class="label">Participantes</div>
    </div>
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--accent);">{n_matches}</div>
        <div class="label">Partidas</div>
    </div>
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--accent);">{n_predictions}</div>
        <div class="label">Palpites</div>
    </div>
</div>
<div class="stat-row" style="grid-template-columns:repeat(3,1fr);margin:0 0.75rem 0.75rem;">
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--voce);">{total_pts}</div>
        <div class="label">Total Pontos</div>
    </div>
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--voce);">{avg_pts_player}</div>
        <div class="label">M\u00e9dia por jogador</div>
    </div>
    <div class="stat-card stat-card-sm">
        <div class="value" style="color:var(--voce);">{overall_aproveitamento}%</div>
        <div class="label">Aproveitamento geral</div>
    </div>
</div>

<!-- Heatmap: player x day -->
<div class="card">
    <div class="card-title">Heatmap: Pontos por dia</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Cada coluna \u00e9 um dia, cada linha \u00e9 um jogador (ordenado do melhor para o pior). A cor varia de <span style="color:rgb(200,55,55);font-weight:700;">\u25a0 vermelho (0%)</span> a <span style="color:rgb(55,220,55);font-weight:700;">\u25a0 verde (100%)</span> conforme o percentual de pontos que o jogador fez em rela\u00e7\u00e3o ao <strong>m\u00e1ximo te\u00f3rico</strong> daquele dia (n\u00ba de jogos \u00d7 {max_pts_per_game} pts). A \u00faltima linha mostra esse m\u00e1ximo te\u00f3rico.</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Role horizontalmente se a tabela n\u00e3o couber na tela.</div>
    <details style="font-size:0.7rem;color:var(--text-muted);margin-top:0.5rem;">
        <summary style="cursor:pointer;font-weight:600;">Como verificar se os n\u00fameros est\u00e3o certos?</summary>
        <ul style="padding-left:1rem;margin-top:0.3rem;">
            <li><strong>Max poss\u00edvel</strong> = n\u00famero de jogos do dia \u00d7 {max_pts_per_game} pts (placar exato). Ex: 3 jogos = {3 * max_pts_per_game} pts m\u00e1x.</li>
            <li><strong>M\u00e9dia pts/dia</strong> = soma dos pontos de todos os jogadores \u00f7 n\u00famero de participantes.</li>
            <li><strong>Aproveitamento</strong> = m\u00e9dia dos percentuais individuais. Para cada jogador: pts dele \u00f7 max te\u00f3rico, depois tira-se a m\u00e9dia entre todos.</li>
            <li>Para validar: pegue um dia, para cada jogador calcule % = pts dele \u00f7 max te\u00f3rico, depois tire a m\u00e9dia. O resultado deve bater com o "Aproveitamento".</li>
        </ul>
    </details>
    <div class="heat-container">
        {heat_header}
        {heat_html}
        {heat_avg}
        {heat_pct_row}
        {heat_total}
    </div>
</div>

<!-- Hit Type Distribution (now with real rule names and points from config) -->
<div class="card">
    <div class="card-title">Distribui\u00e7\u00e3o dos acertos</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Quantos palpites em cada categoria (conforme regras do campeonato)</div>
    <table data-sortable style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Tipo</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Qtde</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">%</th>
            <th style="padding:0.3rem 0.5rem;"></th>
        </tr>
        {tipo_rows}
    </table>
</div>

<!-- Points histogram: how many total points per match -->
<div class="card">
    <div class="card-title">Histograma: Pontos por partida</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Quantas partidas renderam X pontos totais (somando todos os jogadores)</div>
    <table data-sortable style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Faixa de pontos</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Partidas</th>
            <th style="padding:0.3rem 0.5rem;"></th>
        </tr>
        {hist_rows}
    </table>
</div>

<!-- Most predictable matches (with actual result) -->
<div class="card">
    <div class="card-title">Partidas mais previs\u00edveis</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">As 10 partidas com mais acertos de <strong>placar exato (+{exact_points}p)</strong> — a coluna "Acertaram" mostra quantos jogadores cravaram o placar certo.</div>
    <table data-sortable style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Partida</th>
            <th style="text-align:center;padding:0.3rem 0.5rem;">Resultado</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">% placar exato</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Acertaram (+{exact_points}p)</th>
        </tr>
        {top_pred_html}
    </table>
</div>

<!-- Least predictable matches (with actual result) -->
<div class="card">
    <div class="card-title">Partidas menos previs\u00edveis</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">As 10 partidas com menos acertos de <strong>placar exato (+{exact_points}p)</strong> — quase ningu\u00e9m cravou o placar certo.</div>
    <table data-sortable style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Partida</th>
            <th style="text-align:center;padding:0.3rem 0.5rem;">Resultado</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">% placar exato</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Acertaram (+{exact_points}p)</th>
        </tr>
        {worst_pred_html}
    </table>
</div>

<!-- Top-10 predicted scorelines -->
<div class="card">
    <div class="card-title">Placares mais apostados</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Os 10 placares que o bol\u00e3o mais apostou (previstos)</div>
    <table data-sortable style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Placar</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Apostas</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">%</th>
            <th style="padding:0.3rem 0.5rem;"></th>
        </tr>
        {score_rows}
    </table>
</div>

<!-- Actual score distribution -->
<div class="card">
    <div class="card-title">Placares reais mais comuns</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;">Os 10 placares que mais aconteceram de verdade</div>
    <table data-sortable style="width:100%;font-size:0.8rem;border-collapse:collapse;">
        <tr style="border-bottom:1px solid var(--card-border);color:var(--text-muted);font-size:0.7rem;">
            <th style="text-align:left;padding:0.3rem 0.5rem;">Placar</th>
            <th style="text-align:right;padding:0.3rem 0.5rem;">Ocorr\u00eancias</th>
        </tr>
        {actual_rows}
    </table>
</div>
"""
    return _page_frame(config, f"Raio-X do Bolão - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Round Winners page
# ------------------------------------------------------------------


def _build_day_winners(config: ChampionshipConfig) -> str:
    """Show day-by-day winners, zebras, and highlights with day selector."""
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    if df_valid.empty:
        return _page_frame(config, "Vencedores do Dia - sem dados", "<div class='hero'><h1>\U0001f3c6 Vencedores do Dia</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", back_link="index.html")
    df_all = pd.read_csv(config.gold_all_path(), sep=",")
    df_results = pd.read_csv(config.results_file, sep=",")
    upset_path = _norm(os.path.join(config._au_first_round(), "upset_tracker.csv"))
    if os.path.exists(upset_path):
        try:
            df_upset = pd.read_csv(upset_path, sep=",")
        except pd.errors.EmptyDataError:
            df_upset = pd.DataFrame()
    else:
        df_upset = pd.DataFrame()
    max_pts = _max_points_per_game(config)

    # Get unique days from games.csv (extract date part since it includes hour)
    df_results["date_only"] = df_results["date"].str.extract(r"(\d{4}-\d{2}-\d{2})", expand=False)
    days = sorted(df_results.dropna(subset=["home_goals"])["date_only"].unique())
    if len(days) == 0:
        days = sorted(df_valid["date"].unique())

    # Pre-build content per day
    day_content = {}
    for day in days:
        day_predictions = df_valid[df_valid["date"] == day]
        day_results = df_results[df_results["date_only"] == day].dropna(subset=["home_goals"])
        if day_predictions.empty:
            continue

        # Day winner: who scored most points this day
        day_pts = day_predictions.groupby("who")["pontos"].sum()
        winner = day_pts.idxmax()
        winner_pts = int(day_pts.max())
        runner_up = day_pts.nlargest(2).index[-1] if len(day_pts) >= 2 else ""
        runner_up_pts = int(day_pts.nlargest(2).iloc[-1]) if len(day_pts) >= 2 else 0

        # Average pts
        avg_pts = round(day_pts.mean(), 1)

        # Matches this day
        matches_this_day = day_predictions["match"].unique()

        # Upsets: matches where the favorite (most predicted winner) was wrong
        day_upsets = df_upset[df_upset["match"].isin(matches_this_day)]
        upsets = day_upsets[day_upsets["is_upset"] == 1]
        upset_list = []
        for _, u in upsets.iterrows():
            upset_list.append(f"{u['home_team']} vs {u['away_team']}: favorito {u['favorite']} n\u00e3o venceu")

        # Most original correct pick
        day_all = df_all[df_all["match"].isin(matches_this_day)]
        original_pick = ""
        if not day_all.empty:
            hits = day_all[day_all["pontos"] > 0]
            if not hits.empty:
                rarity = hits.groupby(["match", "resultado_bol_placar"]).size().reset_index(name="count")
                rarest = rarity.nsmallest(1, "count").iloc[0]
                match_info = hits[
                    (hits["match"] == rarest["match"])
                    & (hits["resultado_bol_placar"] == rarest["resultado_bol_placar"])
                ]
                if not match_info.empty:
                    row = match_info.iloc[0]
                    original_pick = (
                        f"{row['home_team']} {row['resultado_bol_placar']} {row['away_team']} "
                        f"por {row['who']} ({int(row['pontos'])} pts)"
                    )

        # Results summary
        result_lines = ""
        for _, r in day_results.iterrows():
            hg = int(r["home_goals"])
            ag = int(r["away_goals"])
            result_lines += f"<div style='font-size:0.85rem;padding:0.2rem 0;'>{r['home_team']} {hg}-{ag} {r['away_team']}</div>\n"

        day_content[day] = {
            "winner": winner,
            "winner_pts": winner_pts,
            "runner_up": runner_up,
            "runner_up_pts": runner_up_pts,
            "avg_pts": avg_pts,
            "upsets": upset_list,
            "original_pick": original_pick,
            "result_lines": result_lines,
        }

    if not day_content:
        return _page_frame(config, "Vencedores do Dia - sem dados", "<div class='hero'><h1>Vencedores do Dia</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", back_link="index.html")

    # Day selector options
    day_options = "".join(f'<option value="{d}">{pd.to_datetime(d).strftime("%d/%m (%a)")}</option>' for d in sorted(day_content.keys()))

    # Pre-render all cards (hidden via JS)
    card_html = {}
    for day, content in day_content.items():
        upset_html = ""
        if content["upsets"]:
            for u in content["upsets"]:
                upset_html += f'<div style="font-size:0.85rem;padding:0.2rem 0;color:var(--danger);">\U0001f4a5 {u}</div>\n'
        else:
            upset_html = '<div style="font-size:0.85rem;color:var(--text-muted);font-style:italic;">Nenhuma zebra neste dia</div>\n'

        original_html = ""
        if content["original_pick"]:
            original_html = f'<div style="font-size:0.85rem;margin-top:0.5rem;"><span style="color:var(--accent);font-weight:600;">\U0001f3af Palpite mais original:</span> {content["original_pick"]}</div>\n'
        else:
            original_html = '<div style="font-size:0.85rem;color:var(--text-muted);font-style:italic;">Nenhum palpite original neste dia</div>\n'

        date_display = pd.to_datetime(day).strftime("%d/%m/%Y")

        card_html[day] = f"""
<div class="card" id="day-card-{day}" style="display:none;">
    <div class="stat-row" style="grid-template-columns:repeat(3,1fr);">
        <div class="stat-card stat-card-sm">
            <div class="value" style="color:var(--voce);font-size:1.3rem;">{content["winner_pts"]}</div>
            <div class="label">Melhor do dia</div>
            <div style="font-size:0.8rem;"><a href="boleiros/{content['winner']}.html" style="color:var(--accent);">{content['winner']}</a></div>
        </div>
        <div class="stat-card stat-card-sm">
            <div class="value" style="font-size:1.1rem;">{content["avg_pts"]}</div>
            <div class="label">Media do dia</div>
        </div>
        <div class="stat-card stat-card-sm">
            <div class="value" style="font-size:1.1rem;">{len(content['upsets'])}</div>
            <div class="label">Zebras</div>
        </div>
    </div>
"""
        if content["runner_up"]:
            card_html[day] += f'<div style="font-size:0.85rem;margin-top:0.5rem;">\U0001f948 Vice: {content["runner_up"]} ({content["runner_up_pts"]} pts)</div>\n'

        card_html[day] += f"""
    <div style="margin-top:0.75rem;">
        <div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.25rem;">Resultados do dia</div>
        {content['result_lines']}
    </div>

    <div style="margin-top:0.75rem;">
        <div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.25rem;">\U0001f4a5 Zebras</div>
        <div style="font-size:0.8rem;color:var(--text-muted);margin-bottom:0.25rem;">
            Zebra = quando o favorito n\u00e3o venceu e \u226570% erraram o resultado.
        </div>
        {upset_html}
    </div>

    <div style="margin-top:0.75rem;">
        {original_html}
    </div>
</div>
"""

    # JS for day switching
    js_code = """
function showDay(day) {
    document.querySelectorAll('[id^="day-card-"]').forEach(function(el) {
        el.style.display = 'none';
    });
    const card = document.getElementById('day-card-' + day);
    if (card) card.style.display = 'block';
}
function onDayChange() {
    const sel = document.getElementById('day-select');
    showDay(sel.value);
}
"""

    body = f"""
<div class="hero">
    <h1>\U0001f3c6 Vencedores do Dia</h1>
    <div class="subtitle">Quem venceu cada dia, zebras e palpites originais</div>
</div>

<div class="card" style="margin:1rem 0.75rem;">
    <label class="arena-label" for="day-select">Selecione o dia</label>
    <select id="day-select" class="arena-select" onchange="onDayChange()">
        {day_options}
    </select>
</div>

<div id="day-cards-container">
    {''.join(card_html.values())}
</div>

<div class="card" style="margin:1rem 0.75rem 0.25rem;font-size:0.85rem;color:var(--text-muted);">
    <p><strong>Criterio de Zebra:</strong> Em cada partida, o sistema calcula o time mais votado como vencedor (o "favorito" do bolaao).
    Se o favorito perdeu ou empatou, a partida e marcada como ZEBRA. Quanto mais zebras, mais imprevisivel foi o dia.</p>
</div>
<div class="card" style="margin:0.25rem 0.75rem 1rem;font-size:0.85rem;color:var(--text-muted);">
    <p><strong>\U0001f3af Palpite mais original:</strong> Dentre todos os palpites <strong>corretos</strong> do dia, o sistema procura o placar que <strong>menos pessoas acertaram</strong>.
    Ou seja, a aposta certa que foi a mais incomum — quase ningu\u00e9m acreditou naquele placar, mas o jogador acertou.
    N\u00e3o \u00e9 necessariamente o maior pontuador do dia; \u00e9 o reconhecimento de uma "aposta ousada que deu certo".</p>
    <p style="margin-top:0.3rem;">Exemplo: Se todo mundo acertou Brasil 2 x 0 Argentina, mas s\u00f3 uma pessoa acertou Alemanha 3 x 2 Fran\u00e7a,
    essa pessoa leva o "palpite mais original" — mesmo que n\u00e3o seja a l\u00edder de pontos do dia.</p>
</div>

<script>
{js_code}
// Show first day on load
document.addEventListener('DOMContentLoaded', function() {{
    const sel = document.getElementById('day-select');
    if (sel && sel.value) showDay(sel.value);
}});
</script>
"""
    return _page_frame(config, f"Vencedores do Dia - {config.report_title}", body, back_link="index.html")


# ------------------------------------------------------------------
# Zebras & Favoritos
# ------------------------------------------------------------------

def _build_zebras(config: ChampionshipConfig) -> str:
    """Show all upset matches, ranking of zebra predictors, and impact analysis."""
    upset_path = _norm(os.path.join(config._au_first_round(), "upset_tracker.csv"))
    if not os.path.exists(upset_path):
        return _page_frame(config, "Zebras", "<div class='hero'><h1>\U0001f993 Zebras & Favoritos</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", active_nav="zebras.html")

    try:
        df_upset = pd.read_csv(upset_path, sep=",")
    except pd.errors.EmptyDataError:
        return _page_frame(config, "Zebras", "<div class='hero'><h1>\U0001f993 Zebras & Favoritos</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", active_nav="zebras.html")

    if "is_upset" not in df_upset.columns:
        df_upset["is_upset"] = 0

    # Only finished matches with a real result should be counted
    df_upset = df_upset[df_upset["real_winner"].notna() & (df_upset["real_winner"] != "")].copy()

    # Build match → phase lookup from games.csv
    match_phase_map: dict[str, str] = {}
    if os.path.exists(config.games_file):
        df_games_lu = pd.read_csv(config.games_file, sep=",")
        if "match" in df_games_lu.columns and "round" in df_games_lu.columns:
            for _, gr in df_games_lu.iterrows():
                ms = str(gr["match"]).strip()
                rv = str(gr["round"]).strip()
                # numeric round = group phase, else it's the phase name
                try:
                    int(rv)
                    phase_dir = config.group_phase_label
                except ValueError:
                    phase_dir = rv
                match_phase_map[ms] = phase_dir

    total_matches = len(df_upset)
    upset_matches = df_upset[df_upset["is_upset"] == 1]
    num_upsets = len(upset_matches)
    upset_pct = round(num_upsets / total_matches * 100, 1) if total_matches else 0

    # Parse players_correct column
    def _parse_correct(val: str) -> list[str]:
        if pd.isna(val) or not val:
            return []
        return [p.strip() for p in str(val).split("|")]

    # Build zebra cards
    zebra_cards = ""
    # Sort by most impactful first (more votes for favorite = bigger upset)
    upset_sorted = upset_matches.sort_values("favorite_votes", ascending=False) if not upset_matches.empty else upset_matches

    for _, row in upset_sorted.iterrows():
        match_slug = str(row.get("match", ""))
        home = str(row.get("home_team", ""))
        away = str(row.get("away_team", ""))
        favorite = str(row.get("favorite", "?"))
        real_winner = str(row.get("real_winner", "?"))
        fav_votes = int(row.get("favorite_votes", 0))
        total_votes = int(row.get("total_votes", 0))
        num_correct = int(row.get("num_correct", 0))
        match_date = str(row.get("date", ""))
        match_hour = str(row.get("hour", ""))
        players_correct = _parse_correct(row.get("players_correct", ""))

        fav_pct = round(fav_votes / total_votes * 100) if total_votes else 0
        winner_wrong_pct = 100 - round(num_correct / total_votes * 100) if total_votes else 0
        players_html = " ".join(f'<span class="tag">{p}</span>' for p in players_correct) if players_correct else '<span style="color:var(--text-muted);font-style:italic;">ningu\u00e9m acertou</span>'

        # Build match page link (read phase from games.csv lookup)
        _ph_dir = match_phase_map.get(match_slug, config.group_phase_label)
        match_href = f"jogos/{_ph_dir}/{match_date}_{match_hour}_{match_slug}.html" if match_date and match_hour else ""

        # Determine upset magnitude based on how many got the winner right
        matchup_display = f"<a href=\"{match_href}\">{home} vs {away}</a>" if match_href else f"{home} vs {away}"

        if num_correct <= 2:
            badge_html = f'<span class="zebra-badge upset">{ZEBRA_MONSTRA_LABEL}</span>'
        else:
            badge_html = f'<span class="zebra-badge upset">{ZEBRA_GRANDE_LABEL}</span>'

        zebra_cards += f"""
<div class="zebra-card upset">
    <div class="zebra-header">
        {badge_html}
        <span style="font-size:0.75rem;color:var(--text-muted);">{fav_votes}/{total_votes} ({fav_pct}%) acreditavam no {favorite} &mdash; {winner_wrong_pct}% erraram o resultado</span>
    </div>
    <div class="zebra-matchup">{matchup_display}</div>
    <div class="zebra-detail">
        Favorito: <strong>{favorite}</strong> | Resultado: <strong>{real_winner}</strong><br>
        Acertaram essa zebra: {num_correct} jogadores
    </div>
    <div class="zebra-players">{players_html}</div>
</div>
"""

    # No upsets message
    if not zebra_cards:
        zebra_cards = '<div class="card" style="text-align:center;color:var(--text-muted);font-style:italic;padding:2rem 1rem;">\U0001f614 Nenhuma zebra ate agora — o bolao esta muito previsivel!</div>'

    # Rank zebra predictors (who got the most upsets right)
    correct_counter: dict[str, int] = {}
    for _, row in upset_matches.iterrows():
        for p in _parse_correct(row.get("players_correct", "")):
            correct_counter[p] = correct_counter.get(p, 0) + 1

    zebra_king_rows = ""
    if correct_counter:
        sorted_kings = sorted(correct_counter.items(), key=lambda x: -x[1])
        for i, (name, count) in enumerate(sorted_kings):
            medal = "\U0001f947" if i == 0 else "\U0001f948" if i == 1 else "\U0001f949" if i == 2 else ""
            zebra_king_rows += f"<tr><td>{medal} {i+1}</td><td><a href='boleiros/{name}.html'>{name}</a></td><td style='font-weight:700;color:var(--accent);'>{count}</td></tr>\n"
    else:
        zebra_king_rows = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted);font-style:italic;">Nenhum dado</td></tr>'

    # Non-upset matches (favorites that won) — show a few
    non_upsets = df_upset[df_upset["is_upset"] == 0].head(6)
    fav_won_cards = ""
    for _, row in non_upsets.iterrows():
        home = str(row.get("home_team", ""))
        away = str(row.get("away_team", ""))
        favorite = str(row.get("favorite", "?"))
        fav_votes = int(row.get("favorite_votes", 0))
        total_votes = int(row.get("total_votes", 0))
        fav_pct = round(fav_votes / total_votes * 100) if total_votes else 0
        match_slug = str(row.get("match", ""))
        match_date = str(row.get("date", ""))
        match_hour = str(row.get("hour", ""))
        _ph_dir2 = match_phase_map.get(match_slug, config.group_phase_label)
        match_href = f"jogos/{_ph_dir2}/{match_date}_{match_hour}_{match_slug}.html" if match_date and match_hour else ""
        matchup_display = f"<a href=\"{match_href}\">{home} vs {away}</a>" if match_href else f"{home} vs {away}"
        fav_won_cards += f"""
<div class="zebra-card">
    <div class="zebra-header">
        <span class="zebra-badge favorite">Favorito Venceu</span>
        <span style="font-size:0.75rem;color:var(--text-muted);">{fav_pct}% no favorito</span>
    </div>
    <div class="zebra-matchup">{matchup_display}</div>
    <div class="zebra-detail">Favorito {favorite} confirmou</div>
</div>
"""

    # --- Partidas Mais Dificies (difficulty ranking) ---
    gold_all = config.gold_all_path()
    df_pred = pd.read_csv(gold_all, sep=",") if os.path.exists(gold_all) else pd.DataFrame()

    diff_matches = []
    for _, row in df_upset.iterrows():
        match = str(row.get("match", ""))
        home = str(row.get("home_team", ""))
        away = str(row.get("away_team", ""))
        favorite = str(row.get("favorite", "?"))
        real_winner = str(row.get("real_winner", "?"))
        fav_votes = int(row.get("favorite_votes", 0))
        total_votes = int(row.get("total_votes", 0))
        is_upset = int(row.get("is_upset", 0))
        num_correct = int(row.get("num_correct", 0))

        if total_votes == 0:
            continue

        exact_score_count = 0
        if not df_pred.empty:
            df_m = df_pred[df_pred["match"] == match]
            if not df_m.empty:
                exact_score_count = len(df_m[
                    (df_m["home_goals_bol"] == df_m["home_goals_real"]) &
                    (df_m["away_goals_bol"] == df_m["away_goals_real"])
                ])

        winner_wrong_pct = 100 - round(num_correct / total_votes * 100)
        exact_pct = round(exact_score_count / total_votes * 100)
        difficulty = winner_wrong_pct * 0.6 + exact_pct * 0.4
        if is_upset:
            difficulty = difficulty * 1.3 + 10

        diff_matches.append({
            "match": match, "home": home, "away": away,
            "favorite": favorite, "real_winner": real_winner,
            "num_correct": num_correct, "total_votes": total_votes,
            "is_upset": is_upset, "difficulty": round(difficulty, 1),
            "date": str(row.get("date", "")),
            "hour": str(row.get("hour", "")),
        })

    diff_cards = ""
    if diff_matches:
        diff_matches.sort(key=lambda x: -x["difficulty"])
        max_diff = diff_matches[0]["difficulty"]
        for i, m in enumerate(diff_matches[:10], 1):
            medal = "\U0001f947" if i == 1 else "\U0001f948" if i == 2 else "\U0001f949" if i == 3 else ""
            upset_tag = '<span style="display:inline-block;font-size:0.65rem;background:rgba(239,68,68,0.2);color:var(--danger);padding:0.15rem 0.5rem;border-radius:999px;margin-left:0.5rem;">\U0001f993 ZEBRA</span>' if m["is_upset"] else ""
            bar_pct = round(m["difficulty"] / max_diff * 100)
            bar_color = "var(--danger)" if m["is_upset"] else "var(--warning)"

            _ph_dir3 = match_phase_map.get(m["match"], config.group_phase_label)
            match_href = f"jogos/{_ph_dir3}/{m['date']}_{m['hour']}_{m['match']}.html" if m.get("date") and m.get("hour") else ""
            match_display = f"<a href=\"{match_href}\">{m['home']} vs {m['away']}</a>" if match_href else f"{m['home']} vs {m['away']}"
            diff_cards += f"""
<div style="margin-bottom:0.75rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <span style="font-weight:700;font-size:0.9rem;">{medal} {match_display}{upset_tag}</span>
        <span style="font-weight:700;color:var(--accent);font-size:0.85rem;">{m["difficulty"]}</span>
    </div>
    <div class="bar-track" style="height:5px;margin:0.25rem 0;">
        <div class="bar-fill" style="width:{bar_pct}%;height:5px;background:{bar_color};border-radius:3px;"></div>
    </div>
    <div style="display:flex;gap:0.5rem;font-size:0.7rem;color:var(--text-muted);flex-wrap:wrap;">
        <span>{m["num_correct"]}/{m["total_votes"]} acertaram</span>
        <span>Favorito: {m["favorite"]}</span>
        <span>Resultado: {m["real_winner"]}</span>
    </div>
</div>
"""
    if not diff_cards:
        diff_cards = '<div class="empty-state">Nenhum dado dispon\u00edvel</div>'

    body = f"""
<div class="hero">
    <h1>\U0001f993 Zebras & Favoritos</h1>
    <div class="subtitle">Partidas que derrubaram o bol\u00e3o — e quem acertou</div>
</div>

<div class="card" style="margin:1rem 0.75rem;">
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.75rem;">
        <div class="mini-stat">
            <div class="val">{total_matches}</div>
            <div class="lbl">Partidas</div>
        </div>
        <div class="mini-stat">
            <div class="val" style="color:var(--danger);">{num_upsets}</div>
            <div class="lbl">Zebras</div>
        </div>
        <div class="mini-stat">
            <div class="val">{upset_pct}%</div>
            <div class="lbl">% de Zebras</div>
        </div>
    </div>
</div>

<details>
    <summary>\U0001f4d6 Como funciona a regra da Zebra? (clique aqui)</summary>
    <div class="content">
        <p style="font-size:0.85rem;color:var(--text-muted);margin-bottom:0.75rem;">
            Uma partida \u00e9 considerada <strong>Zebra</strong> quando o resultado mais votado pelo bol\u00e3o <strong>N\u00c3O aconteceu</strong>
            e <strong>no m\u00e1ximo 5 participantes acertaram o vencedor</strong>.
        </p>
        <table class="rank-table" style="font-size:0.75rem;">
            <thead>
                <tr>
                    <th>Acertaram</th>
                    <th>Classifica\u00e7\u00e3o</th>
                    <th>O que significa</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>\u2264 2</td>
                    <td style="color:var(--danger);font-weight:700;">{ZEBRA_MONSTRA_LABEL}</td>
                    <td>Quase ningu\u00e9m acertou \u2014 o bol\u00e3o inteiro foi surpreendido</td>
                </tr>
                <tr>
                    <td>3 a 5</td>
                    <td style="color:var(--warning);font-weight:700;">{ZEBRA_GRANDE_LABEL}</td>
                    <td>Poucos acertaram \u2014 surpresa significativa</td>
                </tr>
                <tr>
                    <td>&gt; 5</td>
                    <td style="color:var(--text-muted);">\u274c N\u00e3o \u00e9 zebra</td>
                    <td>Muita gente acertou, n\u00e3o foi t\u00e3o surpreendente</td>
                </tr>
            </tbody>
        </table>
        <p style="font-size:0.85rem;color:var(--text-muted);margin-top:0.75rem;line-height:1.7;">
            <strong>Acertaram</strong> = quantidade de participantes que acertaram o <strong>vencedor</strong>
            (ou empate).<br>
            Ex: 1 pessoa acertou \u2192 \u2705 {ZEBRA_MONSTRA_LABEL}.<br>
            Ex: 4 pessoas acertaram \u2192 \u2705 {ZEBRA_GRANDE_LABEL}.<br>
            Ex: 8 pessoas acertaram \u2192 \u274c n\u00e3o \u00e9 zebra.
        </p>
    </div>
</details>

<div class="section">
    <div class="section-title">\U0001f4a5 Zebras do Torneio</div>
    {zebra_cards}
</div>

<div class="section">
    <div class="section-title">\U0001f451 Rei das Zebras</div>
    <div class="card" style="overflow-x:auto;">
        <table class="rank-table">
            <thead><tr><th>#</th><th>Boleiro</th><th>Zebras acertadas</th></tr></thead>
            <tbody>{zebra_king_rows}</tbody>
        </table>
    </div>
</div>

<div class="section">
    <div class="section-title">\U0001f480 Partidas Mais Dif\u00edceis</div>
    <div class="card" style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;padding:0.5rem 0.75rem;">
        <strong>\U0001f4a1 C\u00e1lculo:</strong> <strong>% que errou o vencedor</strong> (peso 60%) + <strong>raridade do placar exato</strong> (peso 40%). Se foi zebra, ganha b\u00f4nus de +30% + 10pts. Quanto maior, mais a partida derrubou o bol\u00e3o.
    </div>
    <div class="card">{diff_cards}</div>
</div>

<div class="section">
    <div class="section-title">\U00002705 Favoritos que Confirmaram</div>
    {fav_won_cards}
</div>
"""
    return _page_frame(config, f"Zebras - {config.report_title}", body, active_nav="zebras.html")


# ------------------------------------------------------------------
# Momentum & Sequencias
# ------------------------------------------------------------------

def _build_momentum(config: ChampionshipConfig) -> str:
    """Show current streaks, longest streaks, hot/cold players."""
    gold_dir = config._au_first_round()
    consistency_path = _norm(os.path.join(gold_dir, "consistency.csv"))
    ranking_path = _norm(os.path.join(gold_dir, "ranking_history.csv"))

    if not os.path.exists(consistency_path):
        return _page_frame(config, "Momento", "<div class='hero'><h1>\U0001f525 Momento</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", active_nav="momentum.html")

    df_cons = pd.read_csv(consistency_path, sep=",")

    # Current streak for each player
    df_cons_sorted = df_cons.sort_values(["boleiro", "date"])
    current_streaks: dict[str, dict] = {}
    longest_hot: dict[str, int] = {}
    longest_cold: dict[str, int] = {}

    for boleiro in df_cons["boleiro"].unique():
        df_b = df_cons_sorted[df_cons_sorted["boleiro"] == boleiro]
        # Current streak
        streak_type = ""
        streak_len = 0
        for _, r in reversed(list(df_b.iterrows())):
            st = r.get("streak_type", "")
            if st == "hit":
                if streak_type == "" or streak_type == "hit":
                    streak_type = "hit"
                    streak_len += 1
                else:
                    break
            elif st == "miss":
                if streak_type == "" or streak_type == "miss":
                    streak_type = "miss"
                    streak_len += 1
                else:
                    break
            else:
                break
        current_streaks[boleiro] = {"type": streak_type, "length": streak_len}

        # Longest streaks
        df_b = df_b.reset_index(drop=True)
        hot_max = 0
        cold_max = 0
        cur_hot = 0
        cur_cold = 0
        for _, r in df_b.iterrows():
            st = r.get("streak_type", "")
            if st == "hit":
                cur_hot += 1
                cur_cold = 0
                hot_max = max(hot_max, cur_hot)
            elif st == "miss":
                cur_cold += 1
                cur_hot = 0
                cold_max = max(cold_max, cur_cold)
            else:
                cur_hot = 0
                cur_cold = 0
        longest_hot[boleiro] = hot_max
        longest_cold[boleiro] = cold_max

    # Load avg points for ranking
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    df_avg = df_valid.groupby("who")["pontos"].mean().reset_index()
    df_avg.columns = ["boleiro", "avg_pts"]

    # Build streak bars for current
    players = sorted(current_streaks.keys())
    streak_rows = ""
    for p in players:
        info = current_streaks[p]
        is_hot = info["type"] == "hit"
        is_cold = info["type"] == "miss"
        if is_hot:
            pct = min(info["length"] / 10 * 100, 100)
            fill_class = "hot"
            icon = "\U0001f525"
            label = f"{info['length']} acertos"
        elif is_cold:
            pct = min(info["length"] / 10 * 100, 100)
            fill_class = "cold"
            icon = "\U0001f4a9"
            label = f"{info['length']} erros"
        else:
            pct = 0
            fill_class = ""
            icon = "\U0001f504"
            label = "sem streak"

        avg = df_avg.loc[df_avg["boleiro"] == p, "avg_pts"].values
        avg_str = f"{avg[0]:.1f}" if len(avg) else "-"

        streak_rows += f"""
<div class="streak-row">
    <span>{icon}</span>
    <span class="streak-name"><a href="boleiros/{p}.html">{p}</a></span>
    <span style="font-size:0.75rem;color:var(--text-muted);min-width:25px;">{avg_str}</span>
    <div class="streak-bar-mini"><div class="fill {fill_class}" style="width:{pct}%"></div></div>
    <span class="streak-val">{label}</span>
</div>
"""

    # Longest streaks table
    longest_rows = ""
    all_players_both = set(list(longest_hot.keys()) + list(longest_cold.keys()))
    for p in sorted(all_players_both):
        hot = longest_hot.get(p, 0)
        cold = longest_cold.get(p, 0)
        longest_rows += f"<tr><td><a href='boleiros/{p}.html'>{p}</a></td><td style='color:var(--success);font-weight:700;'>{hot}</td><td style='color:var(--danger);font-weight:700;'>{cold}</td></tr>\n"

    # Current hot streak champions
    hot_players = {p: v for p, v in current_streaks.items() if v["type"] == "hit"}
    top_hot = sorted(hot_players.items(), key=lambda x: -x[1]["length"])[:3]
    hot_championships = ""
    for i, (p, v) in enumerate(top_hot):
        medal = "\U0001f947" if i == 0 else "\U0001f948" if i == 1 else "\U0001f949"
        hot_championships += f"<tr><td>{medal}</td><td><a href='boleiros/{p}.html'>{p}</a></td><td style='font-weight:700;color:var(--success)'>{v['length']} acertos</td></tr>\n"

    if not hot_championships:
        hot_championships = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted);font-style:italic;">Ninguem em streak quente</td></tr>'

    # Cold streak champions
    cold_players = {p: v for p, v in current_streaks.items() if v["type"] == "miss"}
    top_cold = sorted(cold_players.items(), key=lambda x: -x[1]["length"])[:3]
    cold_championships = ""
    for i, (p, v) in enumerate(top_cold):
        medal = "\U0001f947" if i == 0 else "\U0001f948" if i == 1 else "\U0001f949"
        cold_championships += f"<tr><td>{medal}</td><td><a href='boleiros/{p}.html'>{p}</a></td><td style='font-weight:700;color:var(--danger)'>{v['length']} erros</td></tr>\n"

    if not cold_championships:
        cold_championships = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted);font-style:italic;">Ninguem em streak fria</td></tr>'

    body = f"""
<div class="hero">
    <h1>\U0001f525 Momento</h1>
    <div class="subtitle">Sequencias quentes e frias de cada jogador</div>
</div>

<div class="section">
    <div class="section-title">\U0001f4aa Momento Atual</div>
    <div class="card">
        <div style="display:flex;gap:0.75rem;padding:0 0 0.5rem;font-size:0.7rem;color:var(--text-muted);">
            <span style="flex:1;">Jogador</span>
            <span style="min-width:25px;">M\u00e9dia</span>
            <span style="flex:0 0 80px;">Sequ\u00eancia</span>
            <span style="min-width:50px;text-align:right;">Atual</span>
        </div>
        {streak_rows}
    </div>
</div>

<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:0.75rem;margin:0 0.75rem;">
    <div class="card" style="margin:0;">
        <div class="card-title">\U0001f525 Maiores Sequencias Quentes</div>
        <table class="rank-table">
            <thead><tr><th></th><th>Jogador</th><th>Streak</th></tr></thead>
            <tbody>{hot_championships}</tbody>
        </table>
    </div>
    <div class="card" style="margin:0;">
        <div class="card-title">\U0001f4a9 Maiores Sequencias Frias</div>
        <table class="rank-table">
            <thead><tr><th></th><th>Jogador</th><th>Streak</th></tr></thead>
            <tbody>{cold_championships}</tbody>
        </table>
    </div>
</div>

<div class="section">
    <div class="section-title">\U0001f4ca Maiores Sequencias (Geral)</div>
    <div class="card" style="overflow-x:auto;">
        <table class="rank-table">
            <thead><tr><th>Jogador</th><th>\U0001f525 Maior sequ\u00eancia de acertos</th><th>\U0001f4a9 Maior sequ\u00eancia de erros</th></tr></thead>
            <tbody>{longest_rows}</tbody>
        </table>
    </div>
</div>

<div class="card" style="margin:0.75rem;font-size:0.8rem;color:var(--text-muted);">
    <p><strong>\U0001f4a1 O que \u00e9 streak?</strong> Uma sequ\u00eancia de acertos (qualquer pontua\u00e7\u00e3o > 0) ou erros (0 pontos) consecutivos. O "momento atual" mostra a streak MAIS RECENTE de cada jogador.</p>
</div>
"""
    return _page_frame(config, f"Momento - {config.report_title}", body, active_nav="momentum.html")


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------

# --- Analytics HTML helpers (guarded by real results) ---


def _analytics_cleanup(config: ChampionshipConfig, html_base: str) -> None:
    """Delete stale analytics HTML files when no real results exist."""
    if os.path.exists(config.games_file):
        df_games = pd.read_csv(config.games_file, sep=",")
        has_results = not df_games.empty and "home_goals" in df_games.columns and df_games["home_goals"].notna().any()
    else:
        has_results = False
    if not has_results:
        stale = [
            "boldometer.html",
            "bolao_xray.html",
            "day_winners.html",
            "zebras.html",
            "momentum.html",
        ]
        for name in stale:
            path = _norm(os.path.join(html_base, name))
            if os.path.exists(path):
                os.remove(path)
                print_colored(f"\tremoved stale {name}", "yellow")


def _build_boldometer_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "boldometer.html"))
    print_colored("generating boldometer.html", "blue")
    _save(path, _build_boldometer(config))


def _build_bolao_xray_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "bolao_xray.html"))
    print_colored("generating bolao_xray.html", "blue")
    _save(path, _build_bolao_xray(config))


def _build_day_winners_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "day_winners.html"))
    print_colored("generating day_winners.html", "blue")
    _save(path, _build_day_winners(config))


def _build_zebras_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "zebras.html"))
    print_colored("generating zebras.html", "blue")
    _save(path, _build_zebras(config))


def _build_momentum_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "momentum.html"))
    print_colored("generating momentum.html", "blue")
    _save(path, _build_momentum(config))


def _has_any_valid(config: ChampionshipConfig) -> bool:
    """Check if gold_valid file has at least one row with valido=1."""
    path = config.gold_valid_path()
    if not os.path.exists(path):
        return False
    df = pd.read_csv(path, sep=",")
    if df.empty:
        return False
    if "valido" in df.columns:
        return df["valido"].eq(1).any()
    return False


def _compute_full_player_ranking(config: ChampionshipConfig) -> dict[str, int]:
    """Compute full ranking for all players: match + playoff match + bonus - penalty.

    Returns dict mapping player name → rank position (1-indexed), using the same
    methodology as _build_full_ranking() in dashboard.py.
    """
    gold_dir = config._au_first_round()
    valid_path = config.gold_valid_path()
    if not os.path.exists(valid_path):
        return {}
    df_val = pd.read_csv(valid_path, sep=",")
    if df_val.empty or "who" not in df_val.columns:
        return {}

    # Group match points
    score_names = config.scoring_rule_names()
    agg_cols = ["pontos"] + [c for c in score_names if c in df_val.columns]
    wh_mask = df_val["who"].notna() & (df_val["who"] != "")
    df_rank = df_val[wh_mask].groupby("who", as_index=False)[agg_cols].sum()

    # Playoff match points (per phase)
    playoff_pts: dict[str, int] = {}
    for pr in (config.playoff_rounds or []):
        phase_path = config.gold_playoff_valid_path(pr.key)
        if os.path.exists(phase_path):
            df_phase = pd.read_csv(phase_path, sep=",")
            if not df_phase.empty and "who" in df_phase.columns:
                for who, grp in df_phase.groupby("who"):
                    playoff_pts[str(who)] = playoff_pts.get(str(who), 0) + int(grp["pontos"].sum())
    df_rank["playoff_pts"] = df_rank["who"].map(playoff_pts).fillna(0).astype(int)

    # Bonus points (from playoffs_scored.csv)
    bonus_pts: dict[str, int] = {}
    bonus_path = _norm(os.path.join(gold_dir, "playoffs_scored.csv"))
    if os.path.exists(bonus_path):
        df_bonus = pd.read_csv(bonus_path, sep=",")
        if not df_bonus.empty:
            for _, row in df_bonus.iterrows():
                b = str(row["boleiro"])
                pts = int(row["points"])
                bonus_pts[b] = bonus_pts.get(b, 0) + pts
    df_rank["bonus_pts"] = df_rank["who"].map(bonus_pts).fillna(0).astype(int)

    # Penalty points
    df_rank["penalty_pts"] = df_rank["who"].map(
        lambda w: config.total_penalty(w)
    ).fillna(0).astype(int)

    # Total = match + playoff + bonus - penalty
    df_rank["total_pts"] = df_rank["pontos"] + df_rank["playoff_pts"] + df_rank["bonus_pts"] - df_rank["penalty_pts"]

    # Sort and assign ranks (same as dashboard.py)
    df_rank.sort_values(["total_pts", "who"], ascending=[False, True], inplace=True)
    df_rank.reset_index(drop=True, inplace=True)

    result: dict[str, int] = {}
    for i, (_, row) in enumerate(df_rank.iterrows()):
        result[str(row["who"])] = i + 1
    return result


def generate_html_reports(config: ChampionshipConfig) -> None:
    """Generate all HTML reports from gold-layer data."""
    html_base = _norm(os.path.join(config.reports_dir, "html"))

    # Create / recreate HTML directories (clean jogos to avoid stale files)
    dirs = [
        html_base,
        _norm(os.path.join(html_base, "boleiros")),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    # Copy sorttable.js to html output directory
    _js_src = _norm(os.path.join(os.path.dirname(__file__), "sorttable.js"))
    _js_dst = _norm(os.path.join(html_base, "sorttable.js"))
    try:
        with open(_js_src, "rb") as f_in:
            _js_content = f_in.read()
        with open(_js_dst, "wb") as f_out:
            f_out.write(_js_content)
    except Exception as e:
        print_colored(f"  [ERROR] Failed to copy sorttable.js: {e}", "red")

    # Clean jogos dirs to avoid stale HTML files from old runs
    jogos_base = _norm(os.path.join(html_base, "jogos"))
    if os.path.exists(jogos_base):
        shutil.rmtree(jogos_base)
    os.makedirs(_norm(os.path.join(jogos_base, config.group_phase_label)))
    for pr in (config.playoff_rounds or []):
        os.makedirs(_norm(os.path.join(jogos_base, pr.key)), exist_ok=True)

    # Load gold data
    gold_all = config.gold_all_path()
    if not os.path.exists(gold_all):
        print_colored(f"no gold data found at {gold_all}, skipping HTML reports", "yellow")
        return
    df_all = pd.read_csv(gold_all, sep=",")

    # --- Archetype classification (must run before per-player pages) ---
    try:
        classificar_jogadores(config)
    except Exception as e:
        print_colored(f"arquetipo classification failed: {e}", "yellow")

    # --- Per-player ---
    # Use valid if available and non-empty, otherwise fall back to all predictions
    # so boleiro pages are generated even before the tournament starts
    # (all predictions have valido=0 and gold_valid has 0 data rows).
    gold_all = config.gold_all_path()
    if not os.path.exists(gold_all):
        print_colored(f"no gold data found at {gold_all}, skipping HTML reports", "yellow")
        return
    df_all = pd.read_csv(gold_all, sep=",")
    gold_valid = config.gold_valid_path()
    if os.path.exists(gold_valid):
        df_valid = pd.read_csv(gold_valid, sep=",")
        if df_valid.empty:
            df_valid = df_all.copy()
    else:
        df_valid = df_all.copy()
    # Append playoff gold data so arena/boleiro pages include all phases
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_all_path(pr.key)
        if os.path.exists(pp):
            df_play = pd.read_csv(pp, sep=",")
            if not df_play.empty:
                df_valid = pd.concat([df_valid, df_play], ignore_index=True)
    # Compute full ranking once (match + playoff + bonus - penalty) so every
    # boleiro page shows the same rank as the index page.
    full_ranking = _compute_full_player_ranking(config)
    for boleiro in sorted(df_valid["who"].unique()):
        rank = full_ranking.get(boleiro, 0)
        print_colored(f"generating boleiro html: {boleiro}", "blue")
        html = _build_boleiro(config, boleiro, rank=rank)
        path = _norm(os.path.join(html_base, "boleiros", f"{boleiro}.html"))
        _save(path, html)

    # --- Arena (player comparison) ---
    print_colored("generating arena.html", "blue")
    arena_html = _build_arena(config, df_valid)
    _save(_norm(os.path.join(html_base, "arena.html")), arena_html)

    # --- Per-match (group phase) ---
    group_matches = df_all[df_all["match"].notna()].groupby("match")
    for match, df_match in group_matches:
        print_colored(f"generating match html: {match}", "blue")
        html = _build_match(config, match, config.group_phase_label, df_match)
        first = df_match.iloc[0]
        hour = first.get('hour', '')
        hour_str = str(int(hour)) if pd.notna(hour) and isinstance(hour, (int, float)) else str(hour)
        filename = f"{first['date']}_{hour_str}_{match}.html"
        path = _norm(os.path.join(html_base, "jogos", config.group_phase_label, filename))
        _save(path, html)

    # --- Per-match (playoff rounds) ---
    # Load games.csv once for fallback placeholder generation
    _df_games = None
    if os.path.exists(config.games_file):
        _df_games = pd.read_csv(config.games_file, sep=",")
    for pr in (config.playoff_rounds or []):
        phase = pr.key
        # Use all data (including pending/notstarted) so every match gets a
        # placeholder page even before the real result is known.  The
        # _build_match function handles valido=0 rows gracefully.
        playoff_path = config.gold_playoff_all_path(phase)
        has_gold = os.path.exists(playoff_path)
        if has_gold:
            df_phase = pd.read_csv(playoff_path, sep=",")
            if df_phase.empty:
                has_gold = False

        if has_gold:
            phase_matches = df_phase[df_phase["match"].notna()].groupby("match")
        elif _df_games is not None:
            # No predictions yet — generate placeholder pages from games.csv
            # so the dashboard shows upcoming fixtures even before player
            # picks are collected.
            phase_games = _df_games[_df_games["round"].astype(str).str.strip() == phase].copy()
            if phase_games.empty:
                continue
            # Build a synthetic gold-like DataFrame row per match so that
            # _build_match can render fixture info + "no predictions" state.
            rows = []
            for _, g_row in phase_games.iterrows():
                date_raw = str(g_row.get("date", ""))
                # games.csv date format: "2026-07-04 12h" — split into date + hour
                if " " in date_raw:
                    d, h = date_raw.split(" ", 1)
                else:
                    d, h = date_raw, ""
                home_goals_real = g_row.get("home_goals")
                away_goals_real = g_row.get("away_goals")
                # Build resultado_real_placar
                try:
                    hg_f = float(home_goals_real) if pd.notna(home_goals_real) else None
                    ag_f = float(away_goals_real) if pd.notna(away_goals_real) else None
                except (ValueError, TypeError):
                    hg_f = ag_f = None
                if hg_f is not None and ag_f is not None:
                    rrp = f"{int(hg_f)} x {int(ag_f)}"
                else:
                    rrp = ""
                rows.append({
                    "date": d,
                    "hour": h,
                    "match": str(g_row.get("match", "")),
                    "home_team": str(g_row.get("home_team", "")),
                    "away_team": str(g_row.get("away_team", "")),
                    "home_goals_bol": pd.NA,
                    "away_goals_bol": pd.NA,
                    "home_goals_real": hg_f,
                    "away_goals_real": ag_f,
                    "home_pen_bol": pd.NA,
                    "away_pen_bol": pd.NA,
                    "home_pen_real": g_row.get("home_pen", pd.NA),
                    "away_pen_real": g_row.get("away_pen", pd.NA),
                    "resultado_bol_placar": pd.NA,
                    "resultado_bol_time": pd.NA,
                    "resultado_real_placar": rrp,
                    "resultado_real_time": pd.NA,
                    "time_elapsed": str(g_row.get("time_elapsed", "")),
                    "who": "",
                    "pontos": 0,
                    "criterio": "",
                    "valido": 0,
                })
            df_phase = pd.DataFrame(rows)
            if df_phase.empty:
                continue
            phase_matches = df_phase.groupby("match")
        else:
            continue

        for match, df_match in phase_matches:
            print_colored(f"generating match html: {phase} {match}", "blue")
            html = _build_match(config, match, pr.key, df_match)
            first = df_match.iloc[0]
            hour = first.get('hour', '')
            hour_str = str(int(hour)) if pd.notna(hour) and isinstance(hour, (int, float)) else str(hour)
            filename = f"{first['date']}_{hour_str}_{match}.html"
            path = _norm(os.path.join(html_base, "jogos", phase, filename))
            _save(path, html)

    # --- Analytics-dependent pages ------------------------------------
    # If games.csv has no real results yet, delete any stale HTML files
    # so the user doesn't see outdated data. Pages are regenerated below
    # with placeholder "no data" messages when CSVs are missing.
    _analytics_cleanup(config, html_base)
    # Build pages (each builder handles missing data gracefully)
    _build_boldometer_page(config, html_base)
    _build_bolao_xray_page(config, html_base)
    _build_day_winners_page(config, html_base)
    _build_zebras_page(config, html_base)
    _build_momentum_page(config, html_base)

    # --- New views ---
    build_group_standings_page(config, html_base)
    build_similarity_matrix_page(config, html_base)
    build_round_predictions_page(config, html_base)
    build_round_matrix_page(config, html_base)
    build_all_team_pages(config, html_base)
    build_arquetipos_page(config, html_base)
