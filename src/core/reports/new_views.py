"""New static views: group standings, team pages, similarity matrix, simulator, round matrix."""

from __future__ import annotations

import json
import os
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


def _page_frame(config: ChampionshipConfig, title: str, body: str, back_link: str = "", active_nav: str = "") -> str:
    from src.core.reports.html import _CSS_BASE, _bottom_nav_html
    tz = pytz.timezone(config.timezone)
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")
    back_html = ""
    nav_prefix = ""
    if back_link:
        back_html = f'<div class="back-nav"><a href="{back_link}">\u2190 Voltar</a></div>'
        idx = back_link.rfind("index.html")
        if idx >= 0:
            nav_prefix = back_link[:idx]
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
    {config.theme.to_css_vars()}
    {_CSS_BASE}
    </style>
</head>
<body>
{back_html}
{body}
<div style="text-align:center;padding:2rem 1rem 5rem;color:var(--text-muted);font-size:0.75rem;">
    atualizado \u00e0s {now_str}
</div>
{_bottom_nav_html(active_nav, nav_prefix)}
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

        # Which teams advanced (top 2 from each group in this format)
        advancing = [r["team"] for i, r in enumerate(standings) if i < 2]
        advance_badge = ""
        if len(advancing) >= 2:
            advance_badge = f'<div style="margin-top:0.5rem;font-size:0.75rem;color:var(--success);">\u2705 Classificados: {advancing[0]}, {advancing[1]}</div>'

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
        group_rounds = ["1", "2", "3"]
        df_group = df_games[df_games["round"].astype(str).str.strip().isin(group_rounds)]
        for grp in config.groups:
            teams = grp.get("teams", [])
            standings = _compute_group_standings(teams, df_group)
            standings.sort(key=lambda r: (-r["pts"], -(r["gf"] - r["ga"]), -r["gf"]))
            for i, r in enumerate(standings):
                if i < 2:
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
    df_games = pd.read_csv(config.games_file, sep=",")

    # Find which group this team belongs to
    group_name = ""
    for grp in config.groups:
        if team in grp.get("teams", []):
            group_name = grp.get("name", "")
            break

    # Team's matches
    team_matches = df_games[(df_games["home_team"] == team) | (df_games["away_team"] == team)]
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
    <strong>\u2139\ufe0f Como ler:</strong> A barra mostra o <strong>MAE</strong> (Erro Absoluto M\u00e9dio) de cada jogador para esse time.
    Quanto menor o MAE, mais preciso o jogador. A cor da barra varia de <span style="color:var(--success);">verde (baixo erro)</span> a <span style="color:var(--danger);">vermelho (alto erro)</span>.
    O \u00edcone de <strong>Vi\u00e9s</strong> indica se o jogador tende a <span style="color:var(--warning);">\U0001f446 superestimar</span> (prev\u00ea mais gols que o real)
    ou <span style="color:var(--bolao);">\U0001f447 subestimar</span> (prev\u00ea menos). \u27a1\ufe0f = vi\u00e9s neutro.
    <strong>Previsto</strong> e <strong>Real</strong> s\u00e3o as m\u00e9dias de gols previstos vs reais por jogo.
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

            error_summary = f"""
<div class="stat-row" style="margin-bottom:0.75rem;">
    <div class="stat-card">
        <div class="value" style="color:var(--success);">{best['mae']}</div>
        <div class="label">Menor MAE<br><span style="font-size:0.65rem;color:var(--text-muted);">{best['boleiro']}</span></div>
    </div>
    <div class="stat-card">
        <div class="value" style="color:var(--accent);">{df_err_team['mae'].mean():.2f}</div>
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
                bias_val = r["goal_bias"]
                if bias_val > 0.3:
                    bias_icon = "\U0001f446"
                    bias_color = "var(--warning)"
                elif bias_val < -0.3:
                    bias_icon = "\U0001f447"
                    bias_color = "var(--bolao)"
                else:
                    bias_icon = "\u27a1\ufe0f"
                    bias_color = "var(--text-muted)"
                bias_str = f"+{bias_val:.2f}" if bias_val > 0 else f"{bias_val:.2f}"

                mae_ratio = mae / max_mae if max_mae > 0 else 0
                r_bar = int(255 * mae_ratio)
                g_bar = int(200 * (1 - mae_ratio) + 55)
                bar_color = f"rgba({r_bar},{g_bar},50,0.7)"

                err_rows += f"""<tr>
                    <td><a href="{bp}/{r['boleiro']}.html">{r['boleiro']}</a></td>
                    <td style="text-align:center;">{int(r['games'])}</td>
                    <td style="min-width:140px;">
                        <div style="display:flex;align-items:center;gap:0.5rem;">
                            <div class="bar-track" style="flex:1;height:14px;">
                                <div class="bar-fill" style="width:{pct}%;height:14px;background:{bar_color};border-radius:4px;"></div>
                            </div>
                            <span style="font-weight:700;font-size:0.85rem;color:var(--text);min-width:35px;">{mae}</span>
                        </div>
                    </td>
                    <td style="text-align:center;"><span style="font-size:0.85rem;">{bias_icon}</span> <span style="color:{bias_color};font-weight:600;">{bias_str}</span></td>
                    <td style="text-align:center;">{r['avg_predicted']}</td>
                    <td style="text-align:center;">{r['avg_real']}</td>
                </tr>
"""

            error_html += f"""{error_summary}
<div style="overflow-x:auto;">
    <table class="rank-table">
        <thead><tr><th>Jogador</th><th>Jogos</th><th style="min-width:160px;">MAE (Erro m\u00e9dio)</th><th>Vi\u00e9s</th><th>Previsto</th><th>Real</th></tr></thead>
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
        match_rows += f'<div style="padding:0.3rem 0;font-size:0.85rem;border-bottom:1px solid var(--card-border);">{home} <strong>{score}</strong> {away} <span style="color:var(--text-muted);font-size:0.7rem;">({row.get("round", "")})</span></div>'

    rev_map = {v: k for k, v in config.team_name_mapping.items()}
    group_label = f" - Grupo {group_name}" if group_name else ""
    en = rev_map.get(team, team)
    logo_tag = _team_logo_tag(config, en, cls="team-logo", start=config.reports_dir + "/html/times")

    body = f"""<div class="hero">
    <h1>{logo_tag} {team}</h1>
    <div class="subtitle">Guia do Time{group_label} • {total_played} jogos • {wins}V {draws}E {losses}D ({gf}-{ga})</div>
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
    <div class="card">
        {match_rows if match_rows else '<div class="empty-state">Nenhum jogo encontrado</div>'}
    </div>
</div>
"""
    return _page_frame(config, f"Guia do Time: {team}", body, back_link="../index.html", active_nav="index.html")


def _build_times_index(config: ChampionshipConfig, html_base: str) -> str:
    """Build an index page listing all teams in a grouped table."""
    teams = _all_teams(config)
    if not teams:
        body = '<div class="hero"><h1>\U0001f3c6 Guia de Times</h1><div class="subtitle">Nenhum time encontrado</div></div>'
        return _page_frame(config, "Guia de Times", body, back_link="index.html", active_nav="index.html")

    # Build a group lookup
    group_of_team = {}
    for grp in config.groups:
        for t in grp.get("teams", []):
            group_of_team[t] = grp.get("name", "?")

    # Sort teams: by group then alphabetically
    def _sort_key(t: str) -> tuple:
        g = group_of_team.get(t, "ZZ")
        return (g, t)

    teams_sorted = sorted(teams, key=_sort_key)

    rows = ""
    for i, team in enumerate(teams_sorted, 1):
        grp = group_of_team.get(team, "-")
        en = {v: k for k, v in config.team_name_mapping.items()}.get(team, team)
        logo_html = _team_logo_tag(config, en, cls="team-logo-sm")
        if not logo_html:
            initials = "".join(p[0] for p in team.split()[:2]).upper()
            logo_html = f'<div class="player-avatar" style="width:32px;height:32px;font-size:0.7rem;">{initials}</div>'
        rows += f"""<tr>
            <td style="width:30px;">{i}</td>
            <td style="width:36px;">{logo_html}</td>
            <td><a href="times/{team}.html" style="font-weight:600;font-size:0.9rem;">{team}</a></td>
            <td style="color:var(--text-muted);font-size:0.8rem;">{grp}</td>
        </tr>
"""

    body = f"""<div class="hero">
    <h1>\U0001f3c6 Guia de Times</h1>
    <div class="subtitle">An\u00e1lise de palpites por time \u2022 {len(teams)} times</div>
</div>
<div class="section">
    <div class="card" style="padding:0;">
        <div style="overflow-x:auto;">
            <table class="rank-table">
                <thead><tr><th>#</th><th></th><th>Time</th><th>Grupo</th></tr></thead>
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
    """Show each player's predictions grouped by round, with round selector."""
    gold_all = config.gold_all_path()
    if not os.path.exists(gold_all):
        return _page_frame(config, "Palpites da Rodada",
                          "<div class='hero'><h1>\U0001f4cb Palpites da Rodada</h1><div class='subtitle'>Ainda n\u00e3o h\u00e1 dados de palpites</div></div>")

    df_pred = pd.read_csv(gold_all, sep=",")
    if df_pred.empty or "who" not in df_pred.columns:
        return _page_frame(config, "Palpites da Rodada",
                          "<div class='hero'><h1>\U0001f4cb Palpites da Rodada</h1><div class='subtitle'>Nenhum palpite encontrado</div></div>")

    df_games = pd.read_csv(config.games_file, sep=",")
    game_map = df_games[["match", "round", "home_team", "away_team", "home_goals", "away_goals"]].copy()
    game_map["round"] = game_map["round"].astype(str).str.strip()

    df = df_pred.merge(game_map, on="match", how="left", suffixes=("_pred", "_real"))
    df = df[df["round"].notna() & (df["valido"] == 1)].copy()

    boleiros = sorted(df["who"].unique())
    rounds = sorted(df["round"].unique())

    round_labels = {
        "1": "1\u00aa Rodada", "2": "2\u00aa Rodada", "3": "3\u00aa Rodada",
        "oitavas": "Oitavas de Final", "quartas": "Quartas de Final",
        "semi": "Semifinal", "final": "Final",
    }

    round_bodies = ""
    select_options = ""
    for idx_r, r in enumerate(rounds):
        label = round_labels.get(r, f"Rodada {r}")
        select_options += f'<option value="round-{r}">{label}</option>\n'

        df_r = df[df["round"] == r]
        matches_r = sorted(df_r["match"].unique())

        match_abbrevs = []
        for m in matches_r:
            dm = df_r[df_r["match"] == m].iloc[0]
            match_abbrevs.append((m, dm["home_team_real"][:3].upper(), dm["away_team_real"][:3].upper()))

        header_cells = '<th style="position:sticky;top:0;left:0;z-index:4;background:var(--card-bg);white-space:nowrap;">Jogador</th>'
        for _, ha, aa in match_abbrevs:
            header_cells += f'<th style="position:sticky;top:0;z-index:3;background:var(--card-bg);font-size:0.55rem;text-align:center;padding:0.2rem 0.1rem;min-width:34px;line-height:1.1;">{ha}<br>x<br>{aa}</th>'
        header_cells += '<th style="position:sticky;top:0;z-index:3;background:var(--card-bg);color:var(--accent);white-space:nowrap;">Total</th>'

        table_rows = ""
        for b in boleiros:
            df_b = df_r[df_r["who"] == b]
            cells = f'<td style="position:sticky;left:0;z-index:2;background:var(--card-bg);border-bottom:1px solid var(--card-border);font-weight:600;font-size:0.7rem;"><a href="boleiros/{b}.html">{b}</a></td>'
            row_total = 0
            for m, _, _ in match_abbrevs:
                row = df_b[df_b["match"] == m]
                if not row.empty:
                    rw = row.iloc[0]
                    pts = int(rw["pontos"])
                    row_total += pts
                    crit_color = config.scoring_color(rw["criterio"])
                    cells += f'<td style="text-align:center;font-size:0.65rem;padding:0.22rem 0.1rem;white-space:nowrap;border-bottom:1px solid var(--card-border);"><span style="font-weight:600;">{int(rw["home_goals_bol"])}-{int(rw["away_goals_bol"])}</span> <span style="font-size:0.5rem;color:{crit_color};">+{pts}</span></td>'
                else:
                    cells += '<td style="text-align:center;color:var(--text-muted);font-size:0.55rem;border-bottom:1px solid var(--card-border);">\u2014</td>'
            cells += f'<td style="font-weight:700;color:var(--accent);text-align:center;font-size:0.8rem;border-bottom:1px solid var(--card-border);">{row_total}</td>'
            table_rows += f'<tr>{cells}</tr>\n'

        display = "block" if idx_r == 0 else "none"
        round_bodies += f'<div id="round-{r}" class="round-table" style="display:{display};overflow:auto;max-height:75vh;"><table style="border-collapse:separate;border-spacing:0;width:100%;font-size:0.7rem;"><thead><tr>{header_cells}</tr></thead><tbody>{table_rows}</tbody></table></div>\n'

    js = """
<script>
function showRound(id) {
    var els = document.querySelectorAll('.round-table');
    for (var i = 0; i < els.length; i++) { els[i].style.display = 'none'; }
    var el = document.getElementById(id);
    if (el) el.style.display = 'block';
}
document.addEventListener('DOMContentLoaded', function(){
    var sel = document.getElementById('round-selector');
    if (sel) showRound(sel.value);
});
</script>
"""

    body = f"""<div class="hero">
    <h1>\U0001f4cb Palpites da Rodada</h1>
    <div class="subtitle">Aposta de cada jogador partida a partida</div>
</div>

<div class="section">
    <div class="card" style="text-align:center;">
        <label for="round-selector" style="font-weight:600;margin-right:0.5rem;">Rodada:</label>
        <select id="round-selector" onchange="showRound(this.value)" style="padding:0.5rem 1rem;background:var(--card-bg);color:var(--text);border:1px solid var(--card-border);border-radius:8px;font-size:1rem;">
        {select_options}
        </select>
    </div>
</div>

<div class="section">
    {round_bodies}
</div>
{js}
"""
    return _page_frame(config, "Palpites da Rodada", body, back_link="index.html", active_nav="index.html")


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
