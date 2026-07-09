"""New static views: group standings, team pages, similarity matrix, simulator, round matrix."""

from __future__ import annotations

import json
import os
import unicodedata
from datetime import datetime

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig
from src.core.printing import print_colored
from src.core.logo_fetcher import _team_logo_tag


def _norm(path: str) -> str:
    return os.path.normpath(path)


def _save(filepath: str, content: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _page_frame(config: ChampionshipConfig, title: str, body: str, back_link: str = "", active_nav: str = "", temperature: str = "") -> str:
    from src.core.reports.html import _CSS_BASE, _bottom_nav_html
    tz = pytz.timezone(config.timezone)
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    back_html = ""
    nav_prefix = ""
    if back_link:
        back_html = f'<div class="back-nav"><span style="color:var(--text-muted);">\u2192</span> <a href="{back_link}">Voltar</a></div>'
        idx = back_link.rfind("index.html")
        if idx >= 0:
            nav_prefix = back_link[:idx]
    script_src = nav_prefix + "sorttable.js" if back_link else "sorttable.js"
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
<div style="text-align:center;padding:2rem 1rem 5rem;color:var(--text-muted);font-family:var(--font-mono);font-size:0.65rem;letter-spacing:0.02em;">
    atualizado \u00e0s {now_str}
</div>
{_bottom_nav_html(active_nav, nav_prefix, config.nav_items)}
<script src="{script_src}"></script>
</body>
</html>"""


# ------------------------------------------------------------------
# 1. TABELA REAL DOS GRUPOS (Real Group Standings)
# ------------------------------------------------------------------

def _build_group_standings(config: ChampionshipConfig) -> str:
    """Real tournament group standings from games.csv results."""
    if not config.groups:
        return "<div class='hero'><h1>\U0001f3c6 Tabela Real</h1><div class='subtitle'>Nenhum grupo configurado</div></div>"

    df_games = pd.read_csv(config.games_file, sep=",")
    if df_games.empty:
        return _page_frame(config, "Tabela Real", "<div class='hero'><h1>\U0001f3c6 Tabela Real</h1><div class='subtitle'>Nenhum jogo encontrado</div></div>")

    # Filter group stage matches (rounds 1, 2, 3)
    group_rounds = ["1", "2", "3"]
    df_group = df_games[df_games["round"].astype(str).str.strip().isin(group_rounds)].copy()

    html = '<div class="hero"><h1>\U0001f3c6 Tabela Real dos Grupos</h1><div class="subtitle">Classifica\u00e7\u00e3o do campeonato real</div></div>'

    for grp in config.groups:
        group_name = grp.get("name", "?")
        teams = grp.get("teams", [])
        standings = _compute_group_standings(teams, df_group)

        if not standings:
            html += f'<div class="section"><div class="section-title">\U0001f3c6 Grupo {group_name}</div><div class="card"><div class="empty-state">Nenhum jogo encontrado para este grupo</div></div></div>'
            continue

        # Build table
        # Sort: points desc, GD desc, GF desc
        standings.sort(key=lambda r: (-r["pts"], -(r["gf"] - r["ga"]), -r["gf"]))

        table_rows = ""
        for i, row in enumerate(standings):
            rank_class = f' class="rank-{i+1}"' if i < 3 else ""
            gd = row["gf"] - row["ga"]
            gd_str = f"+{gd}" if gd > 0 else str(gd)
            table_rows += f"""<tr{rank_class}>
                <td>{i+1}</td>
                <td><strong>{row["team"]}</strong></td>
                <td>{row["p"]}</td>
                <td>{row["w"]}</td>
                <td>{row["d"]}</td>
                <td>{row["l"]}</td>
                <td>{row["gf"]}</td>
                <td>{row["ga"]}</td>
                <td><strong>{gd_str}</strong></td>
                <td><strong>{row["pts"]}</strong></td>
            </tr>
"""

        table_rows += "</tbody>"

        # Which teams advanced (top N from each group in this format)
        adv_count = config.teams_advance_per_group
        advancing = [r["team"] for i, r in enumerate(standings) if i < adv_count]
        advance_badge = ""
        if len(advancing) >= adv_count:
            classified = ", ".join(advancing[:adv_count])
            advance_badge = f'<div style="margin-top:0.5rem;font-size:0.75rem;color:var(--success);">\u2705 Classificados: {classified}</div>'

        html += f"""<div class="section">
    <div class="section-title">\U0001f3c6 Grupo {group_name}</div>
    <div class="card">
        <div style="overflow-x:auto;">
            <table class="rank-table">
                <thead><tr>
                    <th>#</th><th>Time</th><th>PJ</th><th>V</th><th>E</th><th>D</th><th>GP</th><th>GC</th><th>SG</th><th>Pts</th>
                </tr></thead>
                <tbody>
                {table_rows}
            </table>
        </div>
        {advance_badge}
    </div>
</div>"""

    # Add bracket visualization for knockout stage
    html += _build_knockout_bracket(config, df_games)

    return _page_frame(config, "Tabela Real dos Grupos", html, back_link="index.html", active_nav="index.html")


def _compute_group_standings(teams: list[str], df_group: pd.DataFrame) -> list[dict]:
    """Compute standings for a group of teams from group-stage matches."""
    standings = {t: {"team": t, "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0} for t in teams}

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

    return list(standings.values())


def _build_knockout_bracket(config: ChampionshipConfig, df_games: pd.DataFrame) -> str:
    """Build a simple text-based knockout bracket visualization."""
    if not config.playoff_rounds:
        return ""

    # Determine advancing teams from group stage
    advancing = []
    if config.groups:
        df_group = df_games[df_games["round"].astype(str).str.strip().isin(config.group_round_labels)]
        for grp in config.groups:
            teams = grp.get("teams", [])
            standings = _compute_group_standings(teams, df_group)
            standings.sort(key=lambda r: (-r["pts"], -(r["gf"] - r["ga"]), -r["gf"]))
            for i, r in enumerate(standings):
                if i < config.teams_advance_per_group:
                    advancing.append(r["team"])

    html = '<div class="section"><div class="section-title">\U0001f3c6 Chaveamento Mata-Mata</div><div class="card">'

    for pr in config.playoff_rounds:
        phase = pr.key
        phase_matches = df_games[df_games["round"].astype(str).str.strip() == phase]
        if phase_matches.empty:
            continue

        matches_html = ""
        for _, row in phase_matches.iterrows():
            home = str(row.get("home_team", ""))
            away = str(row.get("away_team", ""))
            try:
                hg = int(row["home_goals"]) if pd.notna(row.get("home_goals")) else None
                ag = int(row["away_goals"]) if pd.notna(row.get("away_goals")) else None
            except (ValueError, TypeError):
                hg = ag = None

            if hg is not None and ag is not None:
                score = f"{hg} x {ag}"
            else:
                score = "? x ?"

            matches_html += f'<div style="padding:0.3rem 0;font-size:0.85rem;border-bottom:1px solid var(--card-border);">{home} <strong>{score}</strong> {away}</div>'

        if matches_html:
            emoji = "\U0001f3c6" if phase == "final" else "\U0001f525"
            html += f'<details {"open" if phase == "oitavas" else ""}><summary>{emoji} {pr.name}</summary><div class="content">{matches_html}</div></details>'

    html += "</div></div>"
    return html


# ------------------------------------------------------------------
# 2. PÁGINA DE TIME (Team Page)
# ------------------------------------------------------------------

def _all_teams(config: ChampionshipConfig) -> list[str]:
    """Get all team names from config team_name_mapping values, sorted alphabetically."""
    teams = sorted(config.team_name_mapping.values())
    return teams


def _build_team_page(config: ChampionshipConfig, team: str) -> str:
    """Per-team analytics page."""
    from src.core.reports.html import ZEBRA_MONSTRA_EMOJI, ZEBRA_GRANDE_EMOJI

    df_games = pd.read_csv(config.games_file, sep=",")

    # Load upset data for zebra indicators
    upset_lookup: dict[str, tuple[int, int, str]] = {}
    upset_path = os.path.join(config._au_first_round(), "upset_tracker.csv")
    if os.path.exists(upset_path):
        try:
            df_upset = pd.read_csv(upset_path, sep=",")
        except pd.errors.EmptyDataError:
            df_upset = pd.DataFrame()
        for _, r in df_upset.iterrows():
            if int(r.get("is_upset", 0)) == 1:
                upset_lookup[str(r["match"])] = (
                    int(r.get("winner_wrong_pct", 0)),
                    int(r.get("num_correct", 0)),
                    str(r.get("favorite", "")),
                )

    # Find which group this team belongs to
    group_name = ""
    for grp in config.groups:
        if team in grp.get("teams", []):
            group_name = grp.get("name", "")
            break

    # Team's matches
    team_matches = df_games[(df_games["home_team"] == team) | (df_games["away_team"] == team)]

    # Build match → (date, hour) lookup from gold prediction data so game links
    # use the correct hour (from the Excel/prediction data), not the games.csv hour
    # which may differ for some matches (e.g., Holanda vs Marrocos: 22h vs 19h).
    _match_info_lookup: dict[str, tuple[str, str]] = {}
    gold_all = config.gold_all_path()
    if os.path.exists(gold_all):
        df_gold = pd.read_csv(gold_all, sep=",")
        if not df_gold.empty and "match" in df_gold.columns:
            for _, g_row in df_gold.drop_duplicates("match").iterrows():
                m = str(g_row.get("match", ""))
                d = str(g_row.get("date", ""))
                h = str(g_row.get("hour", ""))
                if m and d:
                    _match_info_lookup[m] = (d, h)
    # Also check playoff gold all files
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_all_path(pr.key)
        if os.path.exists(pp):
            df_pp = pd.read_csv(pp, sep=",")
            if not df_pp.empty and "match" in df_pp.columns:
                for _, g_row in df_pp.drop_duplicates("match").iterrows():
                    m = str(g_row.get("match", ""))
                    d = str(g_row.get("date", ""))
                    h = str(g_row.get("hour", ""))
                    if m and d and m not in _match_info_lookup:
                        _match_info_lookup[m] = (d, h)

    total_played = 0
    wins = draws = losses = 0
    gf = ga = 0
    for _, row in team_matches.iterrows():
        try:
            hg = int(row["home_goals"]) if pd.notna(row.get("home_goals")) else None
            ag = int(row["away_goals"]) if pd.notna(row.get("away_goals")) else None
        except (ValueError, TypeError):
            continue
        if hg is None or ag is None:
            continue
        total_played += 1
        if str(row["home_team"]) == team:
            gf += hg
            ga += ag
            if hg > ag:
                wins += 1
            elif ag > hg:
                losses += 1
            else:
                draws += 1
        else:
            gf += ag
            ga += hg
            if ag > hg:
                wins += 1
            elif hg > ag:
                losses += 1
            else:
                draws += 1

    bp = "../boleiros"

    # ── Extra stats ──
    clean_sheets = 0
    biggest_win_goals = 0
    biggest_loss_goals = 0
    biggest_win_str = ""
    biggest_loss_str = ""
    form_list: list[str] = []
    for _, row in team_matches.iterrows():
        try:
            hg = int(row["home_goals"]) if pd.notna(row.get("home_goals")) else None
            ag = int(row["away_goals"]) if pd.notna(row.get("away_goals")) else None
        except (ValueError, TypeError):
            continue
        if hg is None or ag is None:
            continue
        is_home = str(row["home_team"]) == team
        scored = hg if is_home else ag
        conceded = ag if is_home else hg
        if scored > conceded:
            form_list.append("V")
            diff = scored - conceded
            if diff > biggest_win_goals:
                biggest_win_goals = diff
                biggest_win_str = f"{hg}-{ag}" if is_home else f"{ag}-{hg}"
        elif conceded > scored:
            form_list.append("D")
            diff = conceded - scored
            if diff > biggest_loss_goals:
                biggest_loss_goals = diff
                biggest_loss_str = f"{hg}-{ag}" if is_home else f"{ag}-{hg}"
        else:
            form_list.append("E")
        if conceded == 0:
            clean_sheets += 1
    # Take last 5 for form string
    form_str = " ".join(form_list[-5:]) if form_list else "-"

    # Per-player accuracy for this team
    team_acc_path = _norm(os.path.join(config._au_first_round(), "team_accuracy.csv"))
    player_rows = ""
    if os.path.exists(team_acc_path):
        df_acc = pd.read_csv(team_acc_path, sep=",")
        df_acc["team"] = df_acc["team"].str.strip()
        df_acc_team = df_acc[df_acc["team"] == team]
        if not df_acc_team.empty:
            # Aggregate home + away per player
            agg = df_acc_team.groupby("boleiro").agg(
                total_bets=("total_bets", "sum"),
                correct_winner=("correct_winner", "sum"),
                exact_score=("exact_score", "sum"),
            ).reset_index()
            agg["accuracy_pct"] = (agg["correct_winner"] / agg["total_bets"] * 100).round(1)
            agg.sort_values("accuracy_pct", ascending=False, inplace=True)
            for _, r in agg.iterrows():
                player_rows += f"""<tr>
                    <td><a href="{bp}/{r['boleiro']}.html">{r['boleiro']}</a></td>
                    <td>{int(r['correct_winner'])}</td>
                    <td>{int(r['exact_score'])}</td>
                    <td style="font-weight:700;color:var(--accent);">{r['accuracy_pct']}%</td>
                </tr>
"""

    # Goal error per player for this team with visual bars
    error_legend = """<div class="card" style="margin-bottom:0.75rem;font-size:0.75rem;color:var(--text-muted);line-height:1.6;padding:0.75rem 1rem;">
    <strong>\u2139\ufe0f Entendendo o MAE:</strong> O <strong>MAE</strong> (Erro Absoluto M\u00e9dio) \u00e9 a m\u00e9dia da diferen\u00e7a entre gols previstos e reais.
    <span style="color:var(--success);">\u25cf Menor \u2192 mais preciso</span> &nbsp;|&nbsp;
    <span style="color:var(--danger);">\u25cf Maior \u2192 menos preciso</span> &nbsp;|&nbsp;
    A nota (A\u2013F) ajuda a comparar rapidamente.
    <span style="display:inline-block;margin-left:0.5rem;font-size:0.65rem;color:var(--text-muted);">Ex: MAE 0.50 = erra por meio gol em m\u00e9dia</span>
</div>
"""
    error_path = _norm(os.path.join(config._au_first_round(), "goal_error_by_team.csv"))
    error_html = ""
    if os.path.exists(error_path):
        df_err = pd.read_csv(error_path, sep=",")
        df_err["team"] = df_err["team"].str.strip()
        df_err_team = df_err[(df_err["team"] == team) & (df_err["role"] == "total")].copy()
        if not df_err_team.empty:
            error_html = error_legend
            df_err_team.sort_values("mae", ascending=True, inplace=True)
            max_mae = df_err_team["mae"].max()

            best = df_err_team.iloc[0]
            worst = df_err_team.iloc[-1]
            avg_mae = df_err_team['mae'].mean()

            # Grade thresholds based on data distribution
            def _grade(v: float) -> tuple[str, str]:
                if v <= max_mae * 0.2:  return "A+", "var(--success)"
                if v <= max_mae * 0.4:  return "A",  "var(--success)"
                if v <= max_mae * 0.6:  return "B",  "var(--accent)"
                if v <= max_mae * 0.8:  return "C",  "var(--warning)"
                if v <= max_mae * 0.95: return "D",  "var(--danger)"
                return "F", "var(--danger)"

            error_summary = f"""
<div class="stat-row" style="margin-bottom:0.75rem;">
    <div class="stat-card">
        <div class="value" style="color:var(--success);">{best['mae']}</div>
        <div class="label">Menor MAE<br><span style="font-size:0.65rem;color:var(--text-muted);">{best['boleiro']}</span></div>
    </div>
    <div class="stat-card">
        <div class="value" style="color:var(--accent);">{avg_mae:.2f}</div>
        <div class="label">M\u00e9dia do Bol\u00e3o</div>
    </div>
    <div class="stat-card">
        <div class="value" style="color:var(--danger);">{worst['mae']}</div>
        <div class="label">Maior MAE<br><span style="font-size:0.65rem;color:var(--text-muted);">{worst['boleiro']}</span></div>
    </div>
</div>
"""
            err_rows = ""
            for _, r in df_err_team.iterrows():
                mae = r["mae"]
                pct = round(mae / max_mae * 100) if max_mae > 0 else 0
                grade, g_color = _grade(mae)

                # Bias: simpler icon
                bias_val = r["goal_bias"]
                if bias_val > 0.3:
                    bias_tag = f'<span style="color:var(--warning);font-size:0.7rem;" title="Superestima (prev\u00ea +{bias_val:.2f} gols/jogo)">\U0001f446</span>'
                elif bias_val < -0.3:
                    bias_tag = f'<span style="color:var(--bolao);font-size:0.7rem;" title="Subestima (prev\u00ea {bias_val:.2f} gols/jogo)">\U0001f447</span>'
                else:
                    bias_tag = f'<span style="color:var(--text-muted);font-size:0.7rem;" title="Vi\u00e9s neutro">\u27a1\ufe0f</span>'

                # Bar: accent color, fill from left
                bar_color = f"rgba(245,197,24,0.7)"  # solid accent

                # Compare vs average
                vs_avg = f'<span style="font-size:0.6rem;color:{"var(--success)" if mae < avg_mae else "var(--danger)"};">{"\u25bc" if mae < avg_mae else "\u25b2"} {abs(mae - avg_mae):.2f}</span>' if len(df_err_team) > 1 else ""

                err_rows += f"""<tr>
                    <td><a href="{bp}/{r['boleiro']}.html" style="font-weight:600;">{r['boleiro']}</a></td>
                    <td style="text-align:center;">{int(r['games'])}</td>
                    <td style="min-width:150px;">
                        <div style="display:flex;align-items:center;gap:0.4rem;">
                            <div class="bar-track" style="flex:1;height:10px;">
                                <div class="bar-fill" style="width:{pct}%;height:10px;background:{bar_color};border-radius:4px;"></div>
                            </div>
                            <span style="font-weight:700;font-size:0.85rem;color:var(--text);min-width:32px;text-align:right;">{mae}</span>
                            <span style="font-weight:700;font-size:0.65rem;color:{g_color};min-width:22px;text-align:center;">{grade}</span>
                        </div>
                        <div style="display:flex;gap:0.75rem;margin-top:0.15rem;font-size:0.6rem;color:var(--text-muted);padding-left:0;">
                            <span>Prev: {r['avg_predicted']}</span>
                            <span>Real: {r['avg_real']}</span>
                            <span>{bias_tag}</span>
                            {vs_avg}
                        </div>
                    </td>
                </tr>
"""

            error_html += f"""{error_summary}
<div style="overflow-x:auto;">
    <table class="rank-table">
        <thead><tr><th>Jogador</th><th>Jogos</th><th style="min-width:170px;">MAE (erro m\u00e9dio) &nbsp;<span style="font-weight:400;font-size:0.6rem;color:var(--text-muted);">barra \u2192 nota</span></th></tr></thead>
        <tbody>
        {err_rows}
        </tbody>
    </table>
</div>
"""

    # Match history
    match_rows = ""
    for _, row in team_matches.iterrows():
        try:
            hg = int(row["home_goals"]) if pd.notna(row.get("home_goals")) else None
            ag = int(row["away_goals"]) if pd.notna(row.get("away_goals")) else None
        except (ValueError, TypeError):
            hg = ag = None
        home = str(row.get("home_team", ""))
        away = str(row.get("away_team", ""))
        if hg is not None and ag is not None:
            score = f"{hg} x {ag}"
        else:
            score = "? x ?"
        
        # Game link — use hour from gold prediction data (not games.csv) so the
        # href matches the actual filename on disk (which uses the Excel hour).
        match_slug = str(row.get("match", ""))
        gold_info = _match_info_lookup.get(match_slug)
        if gold_info:
            game_date, game_hour = gold_info
            date_hour = f"{game_date}_{game_hour}" if game_hour else game_date
        else:
            # Fallback: use games.csv date (may embed hour, e.g. "2026-06-29 19h")
            date_hour = str(row.get("date", "")).replace(' ', '_')
        
        round_raw = row.get("round", "")
        if pd.notna(round_raw) and isinstance(round_raw, (int, float)):
            round_val = str(int(round_raw))
        else:
            round_val = str(round_raw).strip()
            
        phase_v = round_val if round_val not in ["1", "2", "3"] else config.group_phase_label
        game_href = f"../jogos/{phase_v}/{date_hour}_{match_slug}.html"

        # Zebra indicator
        zebra_tag = ""
        if match_slug in upset_lookup:
            _, nc, _ = upset_lookup[match_slug]
            if nc <= 2:
                zebra_tag = f' <span style="display:inline-block;font-size:0.6rem;background:rgba(239,68,68,0.2);color:var(--danger);padding:0.1rem 0.4rem;border-radius:999px;font-weight:700;">{ZEBRA_MONSTRA_EMOJI}</span>'
            else:
                zebra_tag = f' <span style="display:inline-block;font-size:0.6rem;background:rgba(239,68,68,0.15);color:var(--warning);padding:0.1rem 0.4rem;border-radius:999px;font-weight:700;">{ZEBRA_GRANDE_EMOJI}</span>'

        match_rows += f"""<tr>
            <td style="padding:0.25rem 0.5rem;font-size:0.7rem;color:var(--text-muted);">{row.get("round", "")}</td>
            <td style="padding:0.25rem 0.5rem;font-size:0.8rem;{'font-weight:700;' if home == team else ''}">{home}</td>
            <td style="padding:0.25rem 0.5rem;font-size:0.85rem;font-weight:700;text-align:center;white-space:nowrap;">{score}</td>
            <td style="padding:0.25rem 0.5rem;font-size:0.8rem;{'font-weight:700;' if away == team else ''}">{away}</td>
            <td style="padding:0.25rem 0.5rem;text-align:center;">{zebra_tag}</td>
            <td style="padding:0.25rem 0.5rem;text-align:right;"><a href="{game_href}" style="color:var(--accent);font-size:0.65rem;">ver</a></td>
        </tr>
"""

    rev_map = {v: k for k, v in config.team_name_mapping.items()}
    group_label = f" - Grupo {group_name}" if group_name else ""
    en = rev_map.get(team, team)
    logo_tag = _team_logo_tag(en, config, cls="team-logo", start=config.reports_dir + "/html/times")

    # ── Stats summary card ──
    avg_gf = round(gf / total_played, 2) if total_played > 0 else 0
    avg_ga = round(ga / total_played, 2) if total_played > 0 else 0
    gd = gf - ga
    stats_cells = f"""
    <div class="stat-row" style="margin-bottom:0.5rem;">
        <div class="stat-card"><div class="value" style="color:var(--accent);">{total_played}</div><div class="label">Jogos</div></div>
        <div class="stat-card"><div class="value" style="color:var(--success);">{wins}</div><div class="label">Vit\u00f3rias</div></div>
        <div class="stat-card"><div class="value" style="color:var(--text);">{draws}</div><div class="label">Empates</div></div>
        <div class="stat-card"><div class="value" style="color:var(--danger);">{losses}</div><div class="label">Derrotas</div></div>
    </div>
    <div class="stat-row">
        <div class="stat-card"><div class="value" style="color:var(--accent);">{gf}</div><div class="label">Gols Pr\u00f3</div></div>
        <div class="stat-card"><div class="value" style="color:var(--danger);">{ga}</div><div class="label">Gols Contra</div></div>
        <div class="stat-card"><div class="value" style="color:var(--{'success' if gd >= 0 else 'danger'});">{'+' if gd > 0 else ''}{gd}</div><div class="label">Saldo</div></div>
        <div class="stat-card"><div class="value" style="color:var(--text-muted);">{clean_sheets}</div><div class="label">Clean Sheets</div></div>
    </div>
    <div class="stat-row">
        <div class="stat-card"><div class="value" style="font-size:0.8rem;color:var(--text-muted);">{avg_gf:.2f}</div><div class="label">M\u00e9dia GPJ</div></div>
        <div class="stat-card"><div class="value" style="font-size:0.8rem;color:var(--text-muted);">{avg_ga:.2f}</div><div class="label">M\u00e9dia GCJ</div></div>
        <div class="stat-card"><div class="value" style="font-size:0.7rem;">{form_str}</div><div class="label">\u00daltimos 5</div></div>
        <div class="stat-card" style="grid-column:span 1;"><div class="value" style="font-size:0.7rem;color:var(--text-muted);">{biggest_win_str if biggest_win_str else '-'} / {biggest_loss_str if biggest_loss_str else '-'}</div><div class="label">Maior V / D</div></div>
    </div>
"""

    body = f"""<div class="hero">
    <h1>{logo_tag} {team}</h1>
    <div class="subtitle">Guia do Time{group_label} • {total_played} jogos • {wins}V {draws}E {losses}D ({gf}-{ga})</div>
</div>

<div class="section">
    <div class="card">
        {stats_cells}
    </div>
</div>

<div class="section">
    <div class="section-title">\U0001f4ca Aproveitamento por Jogador</div>
    <div class="card">
        <div style="overflow-x:auto;">
            <table class="rank-table">
                <thead><tr><th>Jogador</th><th>Acertos</th><th>Placar Exato</th><th>Precis\u00e3o</th></tr></thead>
                <tbody>
                {player_rows if player_rows else '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);font-style:italic;">Nenhum dado de precis\u00e3o dispon\u00edvel</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
</div>

<div class="section">
    <div class="section-title">\U0001f4c8 Erro por Jogador (MAE)</div>
    <div class="card">
        {error_html if error_html else '<div style="text-align:center;padding:1.5rem 1rem;color:var(--text-muted);font-style:italic;">Nenhum dado de erro dispon\u00edvel</div>'}
    </div>
</div>

<div class="section">
    <div class="section-title">\U0001f4c5 Jogos do {team}</div>
    <div class="card" style="padding:0;">
        <div style="overflow-x:auto;">
            <table class="rank-table">
                <thead><tr><th>Fase</th><th>Mandante</th><th style="text-align:center;">Placar</th><th>Visitante</th><th style="text-align:center;">Zebra</th><th style="text-align:right;"></th></tr></thead>
                <tbody>
                {match_rows if match_rows else '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:1rem;">Nenhum jogo encontrado</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
</div>
"""
    return _page_frame(config, f"Guia do Time: {team}", body, back_link="../index.html", active_nav="index.html")


def _build_times_index(config: ChampionshipConfig, html_base: str) -> str:
    """Build an index page listing all teams with elimination status and group stats."""
    teams = _all_teams(config)
    if not teams:
        body = '<div class="hero"><h1>\U0001f3c6 Guia de Times</h1><div class="subtitle">Nenhum time encontrado</div></div>'
        return _page_frame(config, "Guia de Times", body, back_link="index.html", active_nav="times.html")

    # Build a group lookup
    group_of_team = {}
    for grp in config.groups:
        for t in grp.get("teams", []):
            group_of_team[t] = grp.get("name", "?")

    # ── Phase ordering for knockout progression ──
    _PHASE_ORDER = list(config.group_round_labels)
    _PHASE_LABEL: dict[str, str] = {}
    for i, rl in enumerate(config.group_round_labels):
        _PHASE_LABEL[rl] = f"{i+1}\u00aa Fase"
    for pr in config.playoff_rounds:
        _PHASE_ORDER.append(pr.key)
        _PHASE_LABEL[pr.key] = pr.name
    _PHASE_LABEL["group"] = _PHASE_LABEL.get(config.group_round_labels[0], "1\u00aa Fase") if config.group_round_labels else "1\u00aa Fase"

    # ── Compute league-style table + elimination status from games.csv ──
    team_stats: dict[str, dict] = {}
    for t in teams:
        team_stats[t] = {"pts": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "gd": 0, "gp": 0}

    team_status: dict[str, tuple[str, str]] = {}  # team -> ("alive"|"eliminated", phase_key)

    if os.path.exists(config.games_file):
        df_games = pd.read_csv(config.games_file, sep=",")

        # ── Points table ──
        for _, r in df_games.iterrows():
            try:
                hg = int(r["home_goals"]) if pd.notna(r.get("home_goals")) else None
                ag = int(r["away_goals"]) if pd.notna(r.get("away_goals")) else None
            except (ValueError, TypeError):
                continue
            if hg is None or ag is None:
                continue
            ht = str(r["home_team"])
            at = str(r["away_team"])
            if ht not in team_stats or at not in team_stats:
                continue
            team_stats[ht]["gp"] += 1
            team_stats[at]["gp"] += 1
            team_stats[ht]["gf"] += hg
            team_stats[ht]["ga"] += ag
            team_stats[at]["gf"] += ag
            team_stats[at]["ga"] += hg
            if hg > ag:
                team_stats[ht]["pts"] += 3
                team_stats[ht]["w"] += 1
                team_stats[at]["l"] += 1
            elif ag > hg:
                team_stats[at]["pts"] += 3
                team_stats[at]["w"] += 1
                team_stats[ht]["l"] += 1
            else:
                team_stats[ht]["pts"] += 1
                team_stats[ht]["d"] += 1
                team_stats[at]["pts"] += 1
                team_stats[at]["d"] += 1

        # ── Elimination status (win/loss in last match) ──
        for team in teams:
            tm = df_games[(df_games["home_team"] == team) | (df_games["away_team"] == team)].copy()
            if tm.empty:
                team_status[team] = ("alive", "")
                continue

            # Sort by phase order descending to get the most recent phase
            tm["_phase_ord"] = tm["round"].astype(str).str.strip().map(
                lambda r: _PHASE_ORDER.index(r) if r in _PHASE_ORDER else -1
            )
            tm = tm.sort_values("_phase_ord")
            last = tm.iloc[-1]
            last_phase = str(last["round"]).strip()

            # Check if team appears in any playoff phase
            playoff_phases = [p for p in _PHASE_ORDER if p not in ("1", "2", "3")]
            appears_in_playoff = tm["round"].astype(str).str.strip().isin(playoff_phases).any()

            if not appears_in_playoff:
                team_status[team] = ("eliminated", "group")
                continue

            # Has playoff — check result of last match
            try:
                hg = int(last["home_goals"]) if pd.notna(last.get("home_goals")) else None
                ag = int(last["away_goals"]) if pd.notna(last.get("away_goals")) else None
            except (ValueError, TypeError):
                hg = ag = None

            if hg is None or ag is None:
                team_status[team] = ("alive", last_phase)
                continue

            is_home = last["home_team"] == team
            team_goals = hg if is_home else ag
            opp_goals = ag if is_home else hg

            if team_goals > opp_goals:
                # Won — check if they appear in the next phase
                last_idx = _PHASE_ORDER.index(last_phase) if last_phase in _PHASE_ORDER else -1
                if last_idx >= 0 and last_idx + 1 < len(_PHASE_ORDER):
                    next_ph = _PHASE_ORDER[last_idx + 1]
                    next_appear = tm[tm["round"].astype(str).str.strip() == next_ph]
                    if not next_appear.empty:
                        team_status[team] = ("alive", next_ph)
                    else:
                        df_next = df_games[df_games["round"].astype(str).str.strip() == next_ph]
                        has_teams = (
                            df_next["home_team"].notna().any()
                            and (df_next["home_team"].astype(str).str.strip() != "").any()
                        )
                        if has_teams:
                            # Next phase exists but this team isn't there
                            # This shouldn't happen for a win, but could on walkover
                            team_status[team] = ("alive", last_phase)
                        else:
                            # Next phase not set up yet — still alive
                            team_status[team] = ("alive", last_phase)
                else:
                    team_status[team] = ("alive", last_phase)
            elif team_goals < opp_goals:
                team_status[team] = ("eliminated", last_phase)
            else:
                # Draw in knockout — check penalties, then next phase
                try:
                    hp = int(last["home_pen"]) if (pd.notna(last.get("home_pen")) and str(last.get("home_pen", "")).strip()) else None
                    ap = int(last["away_pen"]) if (pd.notna(last.get("away_pen")) and str(last.get("away_pen", "")).strip()) else None
                except (ValueError, TypeError):
                    hp = ap = None

                if hp is not None and ap is not None:
                    if (is_home and hp > ap) or (not is_home and ap > hp):
                        team_status[team] = ("alive", last_phase)
                    else:
                        team_status[team] = ("eliminated", last_phase)
                else:
                    # No penalty data — check next phase
                    last_idx = _PHASE_ORDER.index(last_phase) if last_phase in _PHASE_ORDER else -1
                    if last_idx >= 0 and last_idx + 1 < len(_PHASE_ORDER):
                        next_ph = _PHASE_ORDER[last_idx + 1]
                        next_appear = tm[tm["round"].astype(str).str.strip() == next_ph]
                        if not next_appear.empty:
                            team_status[team] = ("alive", next_ph)
                        else:
                            df_next = df_games[df_games["round"].astype(str).str.strip() == next_ph]
                            has_teams = (
                                df_next["home_team"].notna().any()
                                and (df_next["home_team"].astype(str).str.strip() != "").any()
                            )
                            if has_teams:
                                team_status[team] = ("eliminated", last_phase)
                            else:
                                team_status[team] = ("alive", last_phase)
                    else:
                        team_status[team] = ("alive", last_phase)

    else:
        # No games.csv — everything alive
        for t in teams:
            team_status[t] = ("alive", "")

    for t in teams:
        team_stats[t]["gd"] = team_stats[t]["gf"] - team_stats[t]["ga"]

    # Sort teams: alive first, then by pts, GD, GF, name
    def _sort_key(t: str) -> tuple:
        status, phase = team_status.get(t, ("alive", ""))
        s = team_stats[t]
        return (0 if status == "alive" else 1, -s["pts"], -s["gd"], -s["gf"], t)

    teams_sorted = sorted(teams, key=_sort_key)

    rows = ""
    for i, team in enumerate(teams_sorted, 1):
        en = {v: k for k, v in config.team_name_mapping.items()}.get(team, team)
        logo_html = _team_logo_tag(en, config, cls="team-logo-sm", start=html_base)
        if not logo_html:
            initials = "".join(p[0] for p in team.split()[:2]).upper()
            logo_html = f'<div class="player-avatar" style="width:32px;height:32px;font-size:0.7rem;">{initials}</div>'

        # Status badge with phase info
        status, phase_key = team_status.get(team, ("alive", ""))
        if status == "alive":
            phase_display = _PHASE_LABEL.get(phase_key, phase_key)
            status_badge = f'<span style="font-size:0.6rem;background:rgba(34,197,94,0.15);color:var(--success);padding:0.15rem 0.4rem;border-radius:999px;font-weight:600;">\u25cf Vivo</span>'
            if phase_display:
                status_badge += f' <span style="font-size:0.55rem;color:var(--text-muted);">({phase_display})</span>'
        else:
            phase_display = _PHASE_LABEL.get(phase_key, phase_key) if phase_key else ""
            status_badge = f'<span style="font-size:0.6rem;background:rgba(239,68,68,0.15);color:var(--danger);padding:0.15rem 0.4rem;border-radius:999px;font-weight:600;">\u2620 Eliminado</span>'
            if phase_display:
                status_badge += f' <span style="font-size:0.55rem;color:var(--text-muted);">{phase_display}</span>'

        s = team_stats[team]
        rows += f"""<tr>
            <td style="width:30px;">{i}</td>
            <td style="width:36px;">{logo_html}</td>
            <td><a href="times/{team}.html" style="font-weight:600;font-size:0.9rem;">{team}</a></td>
            <td style="text-align:center;font-weight:700;color:var(--accent);">{s["pts"]}</td>
            <td style="text-align:center;">{s["gp"]}</td>
            <td style="text-align:center;color:var(--success);">{s["w"]}</td>
            <td style="text-align:center;">{s["d"]}</td>
            <td style="text-align:center;color:var(--danger);">{s["l"]}</td>
            <td style="text-align:center;font-weight:600;">{s["gf"]}</td>
            <td style="text-align:center;">{s["ga"]}</td>
            <td style="text-align:center;font-weight:600;color:var(--{'success' if s['gd'] > 0 else 'danger' if s['gd'] < 0 else 'text'});">{'+' if s['gd'] > 0 else ''}{s['gd']}</td>
            <td>{status_badge}</td>
        </tr>
"""

    body = f"""<div class="hero">
    <h1>\U0001f3c6 Guia de Times</h1>
    <div class="subtitle">Classifica\u00e7\u00e3o por pontos (3V\u20221E\u20220D) \u2022 {len(teams)} times</div>
</div>
<div class="section">
    <div class="card" style="padding:0;">
        <div style="overflow-x:auto;">
            <table class="rank-table" style="min-width:520px;">
                <thead><tr><th>#</th><th></th><th>Time</th><th style="text-align:center;">P</th><th style="text-align:center;">J</th><th style="text-align:center;color:var(--success);">V</th><th style="text-align:center;">E</th><th style="text-align:center;color:var(--danger);">D</th><th style="text-align:center;">GP</th><th style="text-align:center;">GC</th><th style="text-align:center;">SG</th><th>Status</th></tr></thead>
                <tbody>
                {rows}
                </tbody>
            </table>
        </div>
    </div>
</div>"""
    return _page_frame(config, "Guia de Times", body, back_link="index.html", active_nav="index.html")


def _build_all_team_pages(config: ChampionshipConfig, html_base: str) -> None:
    """Generate team pages for all teams."""
    times_dir = _norm(os.path.join(html_base, "times"))
    os.makedirs(times_dir, exist_ok=True)

    teams = _all_teams(config)
    for team in teams:
        print_colored(f"generating team page: {team}", "blue")
        html = _build_team_page(config, team)
        path = _norm(os.path.join(times_dir, f"{team}.html"))
        _save(path, html)

    # Generate index page
    index_html = _build_times_index(config, html_base)
    _save(_norm(os.path.join(html_base, "times.html")), index_html)


# ------------------------------------------------------------------
# 3. MATRIZ DE SIMILARIDADE (Similarity Matrix)
# ------------------------------------------------------------------

def _build_similarity_matrix(config: ChampionshipConfig) -> str:
    """Show a matrix of how similar each pair of players' predictions are."""
    gold_all = config.gold_all_path()
    if not os.path.exists(gold_all):
        return _page_frame(config, "Matriz de Similaridade",
                          "<div class='hero'><h1>\U0001f9ee Similaridade</h1><div class='subtitle'>Ainda n\u00e3o h\u00e1 dados de palpites</div></div>")

    df = pd.read_csv(gold_all, sep=",")
    if df.empty or "who" not in df.columns:
        return _page_frame(config, "Matriz de Similaridade",
                          "<div class='hero'><h1>\U0001f9ee Similaridade</h1><div class='subtitle'>Nenhum palpite encontrado</div></div>")

    boleiros = sorted(df["who"].unique())
    n = len(boleiros)
    if n < 2:
        return _page_frame(config, "Matriz de Similaridade",
                          "<div class='hero'><h1>\U0001f9ee Similaridade</h1><div class='subtitle'>Precisa de pelo menos 2 jogadores</div></div>")

    # For each pair, compute similarity
    similarity_data = []
    for i in range(n):
        for j in range(i + 1, n):
            b1, b2 = boleiros[i], boleiros[j]
            df1 = df[df["who"] == b1].set_index("match")
            df2 = df[df["who"] == b2].set_index("match")

            common = df1.index.intersection(df2.index)
            if len(common) == 0:
                continue

            same_winner = 0
            same_score = 0
            for match in common:
                w1 = df1.loc[match, "resultado_bol_time"]
                w2 = df2.loc[match, "resultado_bol_time"]
                if w1 == w2:
                    same_winner += 1
                s1 = f"{int(df1.loc[match, 'home_goals_bol'])}x{int(df1.loc[match, 'away_goals_bol'])}"
                s2 = f"{int(df2.loc[match, 'home_goals_bol'])}x{int(df2.loc[match, 'away_goals_bol'])}"
                if s1 == s2:
                    same_score += 1

            total = len(common)
            similarity_data.append({
                "b1": b1, "b2": b2,
                "common": total,
                "same_winner": same_winner,
                "same_score": same_score,
                "winner_pct": round(same_winner / total * 100, 1) if total else 0,
                "score_pct": round(same_score / total * 100, 1) if total else 0,
            })

    if not similarity_data:
        return _page_frame(config, "Matriz de Similaridade",
                          "<div class='hero'><h1>\U0001f9ee Similaridade</h1><div class='subtitle'>Nenhum jogo em comum entre os jogadores</div></div>")

    df_sim = pd.DataFrame(similarity_data)

    # Build table sorted by highest winner similarity
    df_sim.sort_values("winner_pct", ascending=False, inplace=True)

    table_rows = ""
    rank = 0
    prev_pct = None
    for _, row in df_sim.iterrows():
        if row["winner_pct"] != prev_pct:
            rank += 1
            prev_pct = row["winner_pct"]
        medal = "\U0001f947" if rank == 1 else "\U0001f948" if rank == 2 else "\U0001f949" if rank == 3 else ""
        table_rows += f"""<tr>
            <td>{medal if rank <= 3 else rank}</td>
            <td><a href="boleiros/{row['b1']}.html">{row['b1']}</a></td>
            <td><a href="boleiros/{row['b2']}.html">{row['b2']}</a></td>
            <td>{int(row['common'])}</td>
            <td>{int(row['same_winner'])}</td>
            <td style="font-weight:700;color:var(--accent);">{row['winner_pct']}%</td>
            <td>{int(row['same_score'])}</td>
            <td>{row['score_pct']}%</td>
        </tr>
"""

    # Full matrix heatmap (table)
    matrix_header = "<tr><th></th>" + "".join(f'<th style="writing-mode:vertical-lr;font-size:0.6rem;padding:0.25rem;">{b[:8]}</th>' for b in boleiros) + "</tr>"
    matrix_rows = ""
    for b1 in boleiros:
        row_cells = f'<td style="font-weight:600;font-size:0.7rem;padding:0.15rem 0.25rem;">{b1[:12]}</td>'
        for b2 in boleiros:
            if b1 == b2:
                row_cells += '<td style="background:var(--accent);width:24px;height:24px;border-radius:3px;"></td>'
            else:
                match_row = df_sim[((df_sim["b1"] == b1) & (df_sim["b2"] == b2)) | ((df_sim["b1"] == b2) & (df_sim["b2"] == b1))]
                if not match_row.empty:
                    pct = match_row.iloc[0]["winner_pct"]
                    intensity = min(pct / 100, 1)
                    r = int(255 * (1 - intensity))
                    g = int(180 + 75 * intensity)
                    b = int(50 * (1 - intensity))
                    row_cells += f'<td style="background:rgba({r},{g},{b},0.3);width:24px;height:24px;text-align:center;font-size:0.55rem;font-weight:600;border-radius:3px;">{int(pct)}%</td>'
                else:
                    row_cells += '<td style="width:24px;height:24px;"></td>'
        matrix_rows += f"<tr>{row_cells}</tr>\n"

    body = f"""<div class="hero">
    <h1>\U0001f9ee Matriz de Similaridade</h1>
    <div class="subtitle">Quem pensa igual? Compara\u00e7\u00e3o de palpites entre jogadores</div>
</div>

<div class="section">
    <div class="section-title">\U0001f4ca Mapa de Calor</div>
    <div class="card">
        <div style="overflow-x:auto;">
            <table style="border-collapse:collapse;font-size:0.75rem;">
                {matrix_header}
                {matrix_rows}
            </table>
        </div>
        <div style="margin-top:0.5rem;font-size:0.7rem;color:var(--text-muted);">C\u00e9lulas mostram % de mesmo vencedor. Diagonal = o pr\u00f3prio jogador.</div>
    </div>
</div>

<div class="section">
    <div class="section-title">\U0001f3af Pares Mais Parecidos (Mesmo Vencedor)</div>
    <div class="card">
        <div style="overflow-x:auto;">
            <table class="rank-table">
                <thead><tr><th>#</th><th>Jogador 1</th><th>Jogador 2</th><th>Jogos Comuns</th><th>Mesmo Vencedor</th><th>% Vencedor</th><th>Mesmo Placar</th><th>% Placar</th></tr></thead>
                <tbody>
                {table_rows if table_rows else '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);font-style:italic;">Nenhum dado dispon\u00edvel</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
</div>
"""
    return _page_frame(config, "Matriz de Similaridade", body, back_link="index.html", active_nav="index.html")


# ------------------------------------------------------------------
# 4. PALPITES DA RODADA (Per-round prediction grid)
# ------------------------------------------------------------------

def _build_round_predictions(config: ChampionshipConfig) -> str:
    """Show predictions grid with multi-game selector.

    Default view: last 10 completed games + next upcoming game.
    Users can select multiple games via round filter buttons or individual
    checkboxes.  A "Filtrar" button applies the selection to the table.
    Columns are ordered chronologically (oldest -> newest -> future).
    Completed games show real score, predicted score and points.
    """
    _parts: list[pd.DataFrame] = []
    gold_all = config.gold_all_path()
    if os.path.exists(gold_all):
        _parts.append(pd.read_csv(gold_all, sep=","))
    for pr in (config.playoff_rounds or []):
        pp = config.gold_playoff_all_path(pr.key)
        if os.path.exists(pp):
            _parts.append(pd.read_csv(pp, sep=","))
    if not _parts:
        return _page_frame(config, "Palpites",
                          "<div class='hero'><h1>\U0001f4cb Palpites</h1><div class='subtitle'>Ainda n\u00e3o h\u00e1 dados de palpites</div></div>")

    df_pred = pd.concat(_parts, ignore_index=True)
    if df_pred.empty or "who" not in df_pred.columns:
        return _page_frame(config, "Palpites",
                          "<div class='hero'><h1>\U0001f4cb Palpites</h1><div class='subtitle'>Nenhum palpite encontrado</div></div>")

    df_pred["match"] = df_pred["match"].astype(str)

    # ── Load games.csv and normalize match keys for join ──
    def _strip_acc(text: str) -> str:
        return "".join(
            c for c in unicodedata.normalize("NFD", text)
            if not unicodedata.combining(c)
        )

    df_games = pd.read_csv(config.games_file, sep=",")
    df_games["match"] = df_games["match"].astype(str)
    df_games["match_raw"] = df_games["match"].copy()
    df_games["round"] = df_games["round"].astype(str).str.strip()

    # Accent-normalise both sides for reliable merge
    df_pred["match_key"] = df_pred["match"].apply(_strip_acc)
    df_games["match_key"] = df_games["match"].apply(_strip_acc)

    # ── Build ordered match list from games.csv (ALL phases) ──
    match_order = df_games[["match_key", "date", "home_team", "away_team", "round"]].copy()

    # Disambiguate duplicate match_keys (e.g. multiple "-vs-" for unknown playoff teams)
    dup_mask = match_order["match_key"].duplicated(keep=False)
    match_order.loc[dup_mask, "match_key"] = (
        match_order.loc[dup_mask, "match_key"] + "|" +
        match_order.loc[dup_mask, "round"].astype(str) + "." +
        match_order.loc[dup_mask].groupby(["match_key", "round"]).cumcount().astype(str)
    )

    match_order = match_order.drop_duplicates("match_key")
    match_order = match_order.sort_values("date", ascending=True)
    all_matches = match_order["match_key"].tolist()

    # Round-slug per match (from games.csv — source of truth)
    match_round_map = dict(zip(match_order["match_key"], match_order["round"]))

    # Round labels for display
    round_labels: dict[str, str] = {}
    for i, rl in enumerate(config.group_round_labels):
        round_labels[rl] = f"{i+1}\u00aa Rodada"
    for pr in config.playoff_rounds:
        round_labels[pr.key] = pr.name
    group_phase_label = getattr(config, "group_phase_label", "1\u00aa Fase")

    # Build accent-insensitive Portuguese-name → slug lookup from config
    _pt_to_slug: dict[str, str] = {}
    for en, pt in config.team_name_mapping.items():
        key = _strip_acc(pt.lower())
        slug = config.team_slugs.get(en, "")
        if slug:
            _pt_to_slug[key] = slug

    match_info: dict[str, tuple] = {}
    for _, r in match_order.iterrows():
        mk = r["match_key"]
        ht = str(r["home_team"]).strip()
        at = str(r["away_team"]).strip()
        rs = r["round"]
        rl = round_labels.get(rs, rs.capitalize() if rs else group_phase_label)
        ha = _pt_to_slug.get(_strip_acc(ht.lower()), ht[:3].upper() if ht and ht not in ("nan", "") else "???")
        aa = _pt_to_slug.get(_strip_acc(at.lower()), at[:3].upper() if at and at not in ("nan", "") else "???")
        match_info[mk] = (ha, aa, ht, at, rl, rs)

    # ── Merge predictions with round info ──
    game_round_map = df_games[["match_key", "round"]].copy()
    df = df_pred.merge(game_round_map, on="match_key", how="left")
    df["round_label"] = df["round"].map(round_labels).fillna(group_phase_label)

    df_valid = df[df["valido"] == 1].copy()
    df_upcoming = df[df["valido"] == 0].copy()

    if df_valid.empty and df_upcoming.empty:
        return _page_frame(config, "Palpites",
                          "<div class='hero'><h1>\U0001f4cb Palpites</h1><div class='subtitle'>Nenhum jogo encontrado</div></div>")

    boleiros = sorted(df["who"].unique())

    # ── Build country slug → match mapping for country filter ──
    # config.team_slugs: {english_name: slug}  e.g. {"Brazil": "BRA"}
    # Invert to get slug → list of english names
    slug_to_en: dict[str, list[str]] = {}
    for en, slug in config.team_slugs.items():
        slug_to_en.setdefault(slug, []).append(en)
    # Build match_key → {home_slug, away_slug}
    match_slugs: dict[str, tuple[str, str]] = {}
    for mk, (ha, aa, ht, at, rl, rs) in match_info.items():
        # ha and aa are already slugs from _pt_to_slug or uppercase fallback
        match_slugs[mk] = (ha, aa)

    # Default view: last 4 completed + next upcoming
    completed_matches = [m for m in all_matches if m in set(df_valid["match_key"].unique())]
    upcoming_matches = [m for m in all_matches if m not in set(completed_matches)]
    last_4 = completed_matches[-4:] if len(completed_matches) >= 4 else completed_matches
    next_upcoming = upcoming_matches[0] if upcoming_matches else None
    default_matches = list(last_4)
    if next_upcoming:
        default_matches.append(next_upcoming)

    # ── Master table ──
    header_cells = (
        '<th style="position:sticky;top:0;left:0;z-index:4;background:var(--card-bg);'
        'white-space:nowrap;">Jogador</th>\n'
    )
    for m in all_matches:
        if m not in match_info:
            continue
        ha, aa, _, _, rl, rs = match_info[m]
        is_default = m in default_matches
        cls = "game-col" + (" game-default" if is_default else "")
        # data-teams for country filter
        team_slugs_attr = f"{ha},{aa}"
        header_cells += (
            f'<th class="{cls}" data-match="{m}" data-round="{rs}" '
            f'data-teams="{team_slugs_attr}" '
            f'title="rodada {rs}" '
            'style="position:sticky;top:0;z-index:3;background:var(--card-bg);'
            'font-size:0.55rem;text-align:center;padding:0.2rem 0.1rem;'
            f'min-width:34px;line-height:1.1;">{ha}<br>x<br>{aa}</th>\n'
        )
    header_cells += (
        '<th style="position:sticky;top:0;z-index:3;background:var(--card-bg);'
        'color:var(--accent);white-space:nowrap;">Total</th>\n'
    )

    table_rows = ""
    for b in boleiros:
        df_b = df[df["who"] == b]
        cells = (
            '<td style="position:sticky;left:0;z-index:2;background:var(--card-bg);'
            'border-bottom:1px solid var(--card-border);font-weight:600;font-size:0.7rem;">'
            f'<a href="boleiros/{b}.html">{b}</a></td>\n'
        )
        row_total = 0
        for m in all_matches:
            if m not in match_info:
                continue
            row = df_b[df_b["match_key"] == m]
            _, _, _, _, _, rs = match_info[m]
            is_default = m in default_matches
            cls = "game-col" + (" game-default" if is_default else "")
            if not row.empty:
                rw = row.iloc[0]
                if rw["valido"] == 1:
                    pts = int(rw["pontos"])
                    row_total += pts
                    crit_color = config.scoring_color(rw["criterio"])
                    hgr = int(rw["home_goals_real"]) if pd.notna(rw["home_goals_real"]) else "?"
                    agr = int(rw["away_goals_real"]) if pd.notna(rw["away_goals_real"]) else "?"
                    cells += (
                        f'<td class="{cls}" data-match="{m}" data-round="{rs}" data-pts="{pts}" '
                        'style="text-align:center;font-size:0.6rem;padding:0.15rem 0.1rem;'
                        'white-space:nowrap;border-bottom:1px solid var(--card-border);">'
                        f'<span style="font-size:0.5rem;color:var(--text-muted);">{hgr}-{agr}</span><br>'
                        f'<span style="font-weight:600;font-size:0.65rem;">'
                        f'{int(rw["home_goals_bol"]) if pd.notna(rw["home_goals_bol"]) else "?"}-{int(rw["away_goals_bol"]) if pd.notna(rw["away_goals_bol"]) else "?"}</span> '
                        f'<span style="font-size:0.5rem;color:{crit_color};">+{pts}</span></td>\n'
                    )
                else:
                    hb = int(rw["home_goals_bol"]) if pd.notna(rw["home_goals_bol"]) else "?"
                    ab = int(rw["away_goals_bol"]) if pd.notna(rw["away_goals_bol"]) else "?"
                    cells += (
                        f'<td class="{cls}" data-match="{m}" data-round="{rs}" data-pts="0" '
                        'style="text-align:center;font-size:0.65rem;padding:0.22rem 0.1rem;'
                        'white-space:nowrap;border-bottom:1px solid var(--card-border);'
                        'color:var(--text-muted);">'
                        f'<span style="font-weight:600;">{hb}-{ab}</span></td>\n'
                    )
            else:
                cells += (
                    f'<td class="{cls}" data-match="{m}" data-round="{rs}" data-pts="0" '
                    'style="text-align:center;color:var(--text-muted);font-size:0.55rem;'
                    'border-bottom:1px solid var(--card-border);">\u2014</td>\n'
                )
        cells += (
            '<td data-total-cell style="font-weight:700;color:var(--accent);text-align:center;'
            f'font-size:0.8rem;border-bottom:1px solid var(--card-border);">{row_total}</td>'
        )
        table_rows += f"<tr>{cells}</tr>\n"

    # ── Dynamic phase filters: one dropdown per distinct round ──
    mata_slugs = {pr.key for pr in (config.playoff_rounds or []) if pr.key != "segunda_fase"}
    group_keys = [r for r in config.group_round_labels if any(match_round_map.get(m) == r for m in all_matches)]
    knockout_present = [r for r in sorted(set(match_round_map.values())) if r in mata_slugs]
    r32_key = config.playoff_rounds[0].key if config.playoff_rounds else "segunda_fase"
    r32_present = r32_key in set(match_round_map.values())

    phase_defs: list[tuple[str, str, list[str]]] = []
    for k in group_keys:
        phase_defs.append((k, k, [k]))
    if r32_present:
        phase_defs.append(("segunda_fase", "segunda_fase", ["segunda_fase"]))
    if knockout_present:
        phase_defs.append(("mata", "mata", knockout_present))

    dd_btn_style = (
        "padding:0.3rem 0.5rem;background:var(--card-bg);color:var(--text);"
        "border:1px solid var(--card-border);border-radius:6px;font-size:0.65rem;"
        "font-weight:600;cursor:pointer;white-space:nowrap;display:inline-flex;"
        "align-items:center;gap:0.3rem;"
    )
    dd_panel_style = (
        "display:none;position:absolute;top:100%;left:0;z-index:100;"
        "background:var(--card-bg);border:1px solid var(--card-border);"
        "border-radius:8px;padding:0.4rem;min-width:180px;max-width:260px;"
        "box-shadow:0 4px 12px rgba(0,0,0,0.2);margin-top:2px;"
    )
    phase_dropdowns_html = ""
    _html_base_logo = _norm(config.reports_dir + "/html")
    for key, label, slugs in phase_defs:
        matches_in_round = [m for m in all_matches if match_round_map.get(m) in slugs]
        if not matches_in_round:
            continue
        default_count = sum(1 for m in matches_in_round if m in default_matches)
        checkboxes_html = ""
        for m in matches_in_round:
            ha, aa, ht, at, _, _ = match_info.get(m, ("?", "?", "", "", "", ""))
            checked = "checked" if m in default_matches else ""
            home_logo = _team_logo_tag(ht, config, cls="team-logo-sm", start=_html_base_logo) if ht and ht not in ("nan", "") else ""
            away_logo = _team_logo_tag(at, config, cls="team-logo-sm", start=_html_base_logo) if at and at not in ("nan", "") else ""
            checkboxes_html += (
                f'<label style="display:flex;align-items:center;gap:0.2rem;'
                f'font-size:0.55rem;padding:0.15rem 0;cursor:pointer;white-space:nowrap;">'
                f'<input type="checkbox" value="{m}" {checked} '
                f'onchange="onCheckChange(this)" style="width:0.75rem;height:0.75rem;"> '
                f'{home_logo}{ha} x {aa}{away_logo}</label>\n'
            )
        phase_dropdowns_html += (
            f'<div class="dd-wrap" style="position:relative;display:inline-block;">'
            f'<button id="dd-btn-{key}" onclick="toggleDD(\'{key}\')" style="{dd_btn_style}">'
            f'{label} <span id="dd-badge-{key}" style="font-size:0.55rem;'
            f'color:var(--accent);">({default_count})</span> \u25be</button>'
            f'<div id="dd-panel-{key}" style="{dd_panel_style}">'
            f'<div style="font-size:0.6rem;font-weight:600;color:var(--text-muted);'
            f'margin-bottom:0.2rem;">{label}</div>'
            f'<div style="max-height:160px;overflow-y:auto;">{checkboxes_html}</div>'
            f'<div style="display:flex;gap:0.3rem;margin-top:0.3rem;padding-top:0.2rem;'
            f'border-top:1px solid var(--card-border);">'
            f'<button onclick="ddSelectAll(\'{key}\')" '
            f'style="font-size:0.5rem;padding:0.15rem 0.4rem;">\u2713 Todos</button>'
            f'<button onclick="ddSelectNone(\'{key}\')" '
            f'style="font-size:0.5rem;padding:0.15rem 0.4rem;">\u2717 Nenhum</button>'
            f'</div></div></div>\n'
        )

    # ── Country dropdown filter ──
    unique_slugs = sorted(set(
        slug for mk in all_matches if mk in match_info
        for slug in match_slugs.get(mk, ())
    ))
    country_dropdown_html = ""
    if unique_slugs:
        country_checkboxes = ""
        for slug in unique_slugs:
            en_names = slug_to_en.get(slug, [slug])
            display = en_names[0]  # First English name as label
            country_checkboxes += (
                f'<label style="display:flex;align-items:center;gap:0.2rem;'
                f'font-size:0.55rem;padding:0.15rem 0;cursor:pointer;white-space:nowrap;">'
                f'<input type="checkbox" value="{slug}" '
                f'onchange="onCountryChange(this)" style="width:0.75rem;height:0.75rem;"> '
                f'{display}</label>\n'
            )
        country_dropdown_html = (
            f'<div class="dd-wrap" style="position:relative;display:inline-block;">'
            f'<button id="btn-pais" onclick="toggleCountryDD()" style="{dd_btn_style}">'
            f'\U0001f30d País \u25be</button>'
            f'<div id="panel-pais" class="country-panel" style="{dd_panel_style}">'
            f'<div style="font-size:0.6rem;font-weight:600;color:var(--text-muted);'
            f'margin-bottom:0.2rem;">País</div>'
            f'<div style="max-height:160px;overflow-y:auto;">{country_checkboxes}</div>'
            f'</div></div>\n'
        )

    # ── JavaScript for dropdown + multi-select filtering ──
    js = r"""
<script>
var selectedGames = new Set();

function toggleDD(key) {
    var panel = document.getElementById('dd-panel-' + key);
    if (!panel) return;
    var isOpen = panel.style.display !== 'none';
    // Close all panels
    document.querySelectorAll('[id^="dd-panel-"]').forEach(function(el) {
        el.style.display = 'none';
    });
    if (!isOpen) panel.style.display = 'block';
}

function toggleCountryDD() {
    var panel = document.getElementById('panel-pais');
    if (!panel) return;
    var isOpen = panel.style.display !== 'none';
    closeAllDDs();
    if (!isOpen) panel.style.display = 'block';
}

function closeAllDDs() {
    document.querySelectorAll('[id^="dd-panel-"]').forEach(function(el) {
        el.style.display = 'none';
    });
    var countryPanel = document.getElementById('panel-pais');
    if (countryPanel) countryPanel.style.display = 'none';
}

function refreshBadge(key) {
    var panel = document.getElementById('dd-panel-' + key);
    if (!panel) return;
    var checked = panel.querySelectorAll('input[type="checkbox"]:checked').length;
    var badge = document.getElementById('dd-badge-' + key);
    if (badge) badge.textContent = '(' + checked + ')';
}

function ddSelectAll(key) {
    var panel = document.getElementById('dd-panel-' + key);
    if (!panel) return;
    panel.querySelectorAll('input[type="checkbox"]').forEach(function(cb) { cb.checked = true; });
    refreshBadge(key);
    applyFilter();
}

function ddSelectNone(key) {
    var panel = document.getElementById('dd-panel-' + key);
    if (!panel) return;
    panel.querySelectorAll('input[type="checkbox"]').forEach(function(cb) { cb.checked = false; });
    refreshBadge(key);
    applyFilter();
}

function onCheckChange(el) {
    var panel = el.closest('[id^="dd-panel-"]');
    if (!panel) return;
    var key = panel.id.replace('dd-panel-', '');
    refreshBadge(key);
    applyFilter();
}

function onCountryChange(el) {
    var slug = el.value;
    var isChecked = el.checked;
    // Get all selected country slugs
    var selectedSlugs = [];
    document.querySelectorAll('#panel-pais input[type="checkbox"]:checked').forEach(function(cb) {
        selectedSlugs.push(cb.value);
    });
    if (selectedSlugs.length === 0) {
        // No countries selected — go back to default
        setDefault();
        return;
    }
    // Uncheck ALL phase checkboxes first
    document.querySelectorAll('[id^="dd-panel-"] input[type="checkbox"]').forEach(function(cb) {
        cb.checked = false;
    });
    // Then check only matches belonging to ANY selected country
    document.querySelectorAll('[id^="dd-panel-"] input[type="checkbox"]').forEach(function(cb) {
        var match = cb.value;
        var th = document.querySelector('.game-col[data-match="' + match + '"]');
        if (th) {
            var teams = th.getAttribute('data-teams') || '';
            var matchToShow = false;
            selectedSlugs.forEach(function(s) {
                if (teams.split(',').indexOf(s) !== -1) {
                    matchToShow = true;
                }
            });
            if (matchToShow) {
                cb.checked = true;
            }
        }
    });
    applyFilter();
}

function setDefault() {
    // Uncheck all checkboxes in all panels
    document.querySelectorAll('[id^="dd-panel-"] input[type="checkbox"]').forEach(function(cb) {
        cb.checked = false;
    });
    // Also uncheck country checkboxes
    document.querySelectorAll('#panel-pais input[type="checkbox"]').forEach(function(cb) {
        cb.checked = false;
    });
    // Check .game-default matches
    document.querySelectorAll('.game-default').forEach(function(el) {
        var match = el.getAttribute('data-match');
        if (match) {
            document.querySelectorAll('[id^="dd-panel-"] input[type="checkbox"][value="' + match + '"]').forEach(function(cb) {
                cb.checked = true;
            });
        }
    });
    // Refresh all badges (keys injected by Python)
    var allKeys = __PHASE_KEYS__;
    allKeys.forEach(function(k) { refreshBadge(k); });
    applyFilter();
}

function applyFilter() {
    selectedGames.clear();
    document.querySelectorAll('[id^="dd-panel-"] input[type="checkbox"]:checked').forEach(function(cb) {
        selectedGames.add(cb.value);
    });
    document.querySelectorAll('.game-col').forEach(function(el) {
        var match = el.getAttribute('data-match');
        el.style.display = selectedGames.has(match) ? 'table-cell' : 'none';
    });
    // Recalculate totals for visible columns
    document.querySelectorAll('tbody tr').forEach(function(row) {
        var total = 0;
        row.querySelectorAll('.game-col').forEach(function(cell) {
            if (selectedGames.has(cell.getAttribute('data-match'))) {
                total += parseInt(cell.getAttribute('data-pts')) || 0;
            }
        });
        var totalCell = row.querySelector('[data-total-cell]');
        if (totalCell) totalCell.textContent = total;
    });
}

// ── Sort controls ──
function sortByName() {
    var tbody = document.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort(function(a, b) {
        var aName = a.querySelector('td a').textContent.trim();
        var bName = b.querySelector('td a').textContent.trim();
        return aName.localeCompare(bName);
    });
    rows.forEach(function(row) { tbody.appendChild(row); });
    // Update button styles
    document.getElementById('sort-name-btn').style.background = '#1a3a5c';
    document.getElementById('sort-name-btn').style.color = 'white';
    document.getElementById('sort-name-btn').style.border = 'none';
    document.getElementById('sort-total-btn').style.background = 'var(--card-bg)';
    document.getElementById('sort-total-btn').style.color = 'var(--text)';
    document.getElementById('sort-total-btn').style.border = '1px solid var(--card-border)';
}

function sortByTotal() {
    var tbody = document.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr'));
    rows.sort(function(a, b) {
        var aTotal = parseInt(a.querySelector('[data-total-cell]').textContent) || 0;
        var bTotal = parseInt(b.querySelector('[data-total-cell]').textContent) || 0;
        return bTotal - aTotal; // descending
    });
    rows.forEach(function(row) { tbody.appendChild(row); });
    // Update button styles
    document.getElementById('sort-total-btn').style.background = '#1a3a5c';
    document.getElementById('sort-total-btn').style.color = 'white';
    document.getElementById('sort-total-btn').style.border = 'none';
    document.getElementById('sort-name-btn').style.background = 'var(--card-bg)';
    document.getElementById('sort-name-btn').style.color = 'var(--text)';
    document.getElementById('sort-name-btn').style.border = '1px solid var(--card-border)';
}

// Close dropdowns when clicking outside
document.addEventListener('click', function(e) {
    if (!e.target.closest('.dd-wrap')) {
        closeAllDDs();
    }
});

document.addEventListener('DOMContentLoaded', function() { setDefault(); });
</script>
"""

    # ── Game selector UI ──
    buttons_html = (
        '<div style="display:flex;gap:0.5rem;align-items:center;flex-wrap:wrap;margin-bottom:0.5rem;">'
        '<button onclick="setDefault()" style="padding:0.4rem 0.8rem;background:#1a3a5c;'
        'color:white;border:none;border-radius:6px;font-size:0.75rem;font-weight:600;cursor:pointer;">'
        'padr\u00e3o: \u00faltimos 4 jogos + pr\u00f3ximo</button>'
        '<span style="font-size:0.65rem;color:var(--text-muted);">Ordenar:</span>'
        '<button id="sort-name-btn" onclick="sortByName()" '
        'style="padding:0.25rem 0.5rem;background:#1a3a5c;color:white;border:none;'
        'border-radius:4px;font-size:0.65rem;font-weight:600;cursor:pointer;">Nome</button>'
        '<button id="sort-total-btn" onclick="sortByTotal()" '
        'style="padding:0.25rem 0.5rem;background:var(--card-bg);color:var(--text);'
        'border:1px solid var(--card-border);border-radius:4px;font-size:0.65rem;'
        'font-weight:600;cursor:pointer;">Total</button>'
        '</div>'

        '<div style="display:flex;gap:0.3rem;flex-wrap:wrap;align-items:flex-start;">'
        f'{phase_dropdowns_html}{country_dropdown_html}'
        '</div>'
    )

    js_table_scroll = r"""
<script>
function fixScrollerHeight() {
    var hero = document.querySelector('.hero');
    var card = document.querySelector('.card');
    var scroller = document.querySelector('.table-scroller');
    if (!hero || !card || !scroller) return;
    var heroBot = Math.max(0, hero.getBoundingClientRect().bottom);
    var cardH = card.offsetHeight || 0;
    var used = heroBot + cardH + 16;
    var avail = window.innerHeight - used;
    scroller.style.maxHeight = Math.max(200, avail) + 'px';
}
window.addEventListener('load', fixScrollerHeight);
window.addEventListener('resize', fixScrollerHeight);
window.addEventListener('scroll', fixScrollerHeight);
</script>
"""

    # Inject phase key list into JS for setDefault badge refresh
    phase_keys_json = json.dumps([k for k, _, _ in phase_defs])
    js = js.replace("__PHASE_KEYS__", phase_keys_json)

    body = f"""<div class="hero">
    <h1>\U0001f4cb Palpites</h1>
    <div class="subtitle">Aposta de cada jogador partida a partida</div>
</div>

<div class="section" style="overflow:clip;display:flex;flex-direction:column;">
    <div class="card" style="text-align:center;position:sticky;top:0;z-index:20;flex-shrink:0;">
        {buttons_html}
    </div>

    <div class="table-scroller" style="overflow:auto;margin-top:0.5rem;">
        <table data-sortable style="border-collapse:separate;border-spacing:0;width:100%;font-size:0.7rem;">
            <thead><tr>{header_cells}</tr></thead>
            <tbody>{table_rows}</tbody>
        </table>
    </div>
</div>
{js_table_scroll}
{js}
"""
    return _page_frame(config, "Palpites", body, back_link="index.html", active_nav="index.html")


# ------------------------------------------------------------------
# 5. TABELA DE RODADAS (Round Matrix)
# ------------------------------------------------------------------

def _build_round_matrix(config: ChampionshipConfig) -> str:
    """Round-by-round comparison matrix."""
    rr_path = _norm(os.path.join(config._au_first_round(), "round_by_round.csv"))
    if not os.path.exists(rr_path):
        return _page_frame(config, "Tabela de Rodadas",
                          "<div class='hero'><h1>\U0001f4ca Rodadas</h1><div class='subtitle'>Ainda n\u00e3o h\u00e1 dados de rodadas</div></div>")

    df = pd.read_csv(rr_path, sep=",")
    if df.empty:
        return _page_frame(config, "Tabela de Rodadas",
                          "<div class='hero'><h1>\U0001f4ca Rodadas</h1><div class='subtitle'>Nenhum dado de rodada dispon\u00edvel</div></div>")

    boleiros = sorted(df["boleiro"].unique())
    rounds = sorted(df["round_number"].unique())
    round_labels = {}
    for rn in rounds:
        sub = df[df["round_number"] == rn]
        round_labels[rn] = sub.iloc[0].get("round_label", str(rn))

    # Build matrix: rows = players, cols = rounds, cells = points (with rank)
    # Also compute total
    matrix = {}
    totals = {}
    for b in boleiros:
        matrix[b] = {}
        totals[b] = 0
        sub = df[df["boleiro"] == b]
        for _, row in sub.iterrows():
            rn = int(row["round_number"])
            pts = int(row["points"])
            matrix[b][rn] = int(row["points"])
            totals[b] += pts

    # Sort players by total points desc
    boleiros_sorted = sorted(boleiros, key=lambda b: -totals[b])

    # Compute rank per round
    rank_per_round = {}
    for rn in rounds:
        r_pts = {}
        for b in boleiros:
            r_pts[b] = matrix.get(b, {}).get(rn, 0)
        sorted_round = sorted(r_pts.items(), key=lambda x: -x[1])
        rank_per_round[rn] = {b: i+1 for i, (b, _) in enumerate(sorted_round)}

    # Find max pts per round for highlight
    max_per_round = {}
    for rn in rounds:
        max_per_round[rn] = max(matrix.get(b, {}).get(rn, 0) for b in boleiros)

    table_rows = ""
    for rank, b in enumerate(boleiros_sorted, 1):
        medal = "\U0001f947" if rank == 1 else "\U0001f948" if rank == 2 else "\U0001f949" if rank == 3 else ""
        rank_class = f' class="rank-{rank}"' if rank <= 3 else ""
        cells = f"<td><strong>{b}</strong></td>"
        for rn in rounds:
            pts = matrix.get(b, {}).get(rn, 0)
            rnk = rank_per_round.get(rn, {}).get(b, "-")
            is_max = pts == max_per_round.get(rn, 0) and pts > 0
            highlight = ' style="font-weight:700;color:var(--accent);"' if is_max else ""
            cells += f'<td{highlight}>{pts}<br><span style="font-size:0.6rem;color:var(--text-muted);">#{rnk}</span></td>'
        cells += f'<td style="font-weight:700;color:var(--accent);font-size:1rem;">{totals[b]}</td>'
        table_rows += f"<tr{rank_class}><td>{medal} {rank}</td>{cells}</tr>\n"

    # Header
    header = "<th>#</th><th>Jogador</th>"
    for rn in rounds:
        label = round_labels.get(rn, str(rn))
        header += f'<th style="writing-mode:vertical-lr;font-size:0.6rem;padding:0.25rem 0.3rem;">R{label}</th>'
    header += '<th style="color:var(--accent);">Total</th>'

    body = f"""<div class="hero">
    <h1>\U0001f4ca Tabela de Rodadas</h1>
    <div class="subtitle">Compara\u00e7\u00e3o rodada a rodada \u2022 Pontos por rodada e rank</div>
</div>

<div class="section">
    <div class="section-title">\U0001f4c8 Matriz de Rodadas</div>
    <div class="card">
        <div style="overflow-x:auto;">
            <table class="rank-table" style="font-size:0.75rem;">
                <thead><tr>{header}</tr></thead>
                <tbody>
                {table_rows if table_rows else '<tr><td colspan="' + str(3 + len(rounds)) + '" style="text-align:center;color:var(--text-muted);font-style:italic;">Nenhum dado</td></tr>'}
                </tbody>
            </table>
        </div>
        <div style="margin-top:0.5rem;font-size:0.7rem;color:var(--text-muted);">
            C\u00e9lulas: <strong>pontos</strong> na rodada / rank na rodada. <span style="color:var(--accent);font-weight:600;">Destaque</span> = melhor pontua\u00e7\u00e3o da rodada.
        </div>
    </div>
</div>

<div class="section">
    <div class="section-title">\U0001f525 Maiores Pontuadores por Rodada</div>
    <div class="card">
"""
    for rn in rounds:
        label = round_labels.get(rn, str(rn))
        top_players = [(b, matrix.get(b, {}).get(rn, 0)) for b in boleiros]
        top_players.sort(key=lambda x: -x[1])
        top_html = ""
        for i, (b, pts) in enumerate(top_players[:3]):
            medal = "\U0001f947" if i == 0 else "\U0001f948" if i == 1 else "\U0001f949"
            top_html += f'<div style="display:flex;justify-content:space-between;padding:0.2rem 0;font-size:0.85rem;"><span>{medal} <a href="boleiros/{b}.html">{b}</a></span><span style="font-weight:700;">{pts} pts</span></div>'
        body += f"""<details>
    <summary>\U0001f3af Rodada {label}</summary>
    <div class="content">
        {top_html if top_html else '<div class="empty-state">Nenhum dado</div>'}
    </div>
</details>
"""

    body += """
    </div>
</div>
"""
    return _page_frame(config, "Tabela de Rodadas", body, back_link="index.html", active_nav="index.html")


# ------------------------------------------------------------------
# Page builder wrappers (called from html.py)
# ------------------------------------------------------------------

def build_group_standings_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "tabela_real.html"))
    print_colored("generating tabela_real.html", "blue")
    _save(path, _build_group_standings(config))


def build_similarity_matrix_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "similaridade.html"))
    print_colored("generating similaridade.html", "blue")
    _save(path, _build_similarity_matrix(config))


def build_round_predictions_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "palpites.html"))
    print_colored("generating palpites.html", "blue")
    _save(path, _build_round_predictions(config))


def build_round_matrix_page(config: ChampionshipConfig, html_base: str) -> None:
    path = _norm(os.path.join(html_base, "rodadas.html"))
    print_colored("generating rodadas.html", "blue")
    _save(path, _build_round_matrix(config))


def build_all_team_pages(config: ChampionshipConfig, html_base: str) -> None:
    _build_all_team_pages(config, html_base)
