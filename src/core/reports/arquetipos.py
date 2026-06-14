"""Arquetipos — player persona classification + gallery/legend page.

Classifies each player into 1 of 9 archetypes (including Indefinido)
with a tier (S/A/B/C/D) based on the intensity of that profile.
Saves ``arquetipos_classification.csv`` as the single source of truth,
reused by each per-player profile page.
"""

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


# ------------------------------------------------------------------
# Archetype definitions (single source of truth)
# ------------------------------------------------------------------

ARQUETIPOS: list[dict] = [
    {"emoji": "\U0001f9ea", "nome": "Cientista",
     "descricao": "Performance consistente, alta pontua\u00e7\u00e3o e regularidade.",
     "cor": "#6366f1"},
    {"emoji": "\U0001f993", "nome": "Zebreiro",
     "descricao": "Ca\u00e7a surpresas, opini\u00e3o contr\u00e1ria \u00e0 maioria.",
     "cor": "#ef4444"},
    {"emoji": "\U0001f6e1\ufe0f", "nome": "Conservador",
     "descricao": "Palpites seguros, perto da m\u00e9dia do bol\u00e3o.",
     "cor": "#3b82f6"},
    {"emoji": "\U0001f31f", "nome": "Otimista",
     "descricao": "Sempre espera muitos gols — superestima placares.",
     "cor": "#f59e0b"},
    {"emoji": "\u2601\ufe0f", "nome": "Pessimista",
     "descricao": "Sempre espera poucos gols — subestima placares.",
     "cor": "#6b7280"},
    {"emoji": "\U0001f3af", "nome": "Especialista",
     "descricao": "Muito preciso em time(s) espec\u00edfico(s).",
     "cor": "#10b981"},
    {"emoji": "\U0001f3a2", "nome": "Montanha-Russa",
     "descricao": "Altos e baixos — streaks que alternam, varia\u00e7\u00e3o alta.",
     "cor": "#ec4899"},
    {"emoji": "\u2705", "nome": "Placarzeiro",
     "descricao": "Especialista em acertar placar exato.",
     "cor": "#8b5cf6"},
    {"emoji": "\u2753", "nome": "Indefinido",
     "descricao": "Sem tra\u00e7os fortes o bastante para um perfil definido.",
     "cor": "#9ca3af"},
]

ARQ_MAP: dict[str, dict] = {a["nome"]: a for a in ARQUETIPOS}

TIERS: list[dict] = [
    {"label": "S", "nome": "Lend\u00e1rio", "min": 90, "emoji": "\U0001f48e", "cor": "var(--accent)"},
    {"label": "A", "nome": "Craque",     "min": 70, "emoji": "\U0001f947", "cor": "var(--success)"},
    {"label": "B", "nome": "Bom",        "min": 40, "emoji": "\U0001f948", "cor": "#3b82f6"},
    {"label": "C", "nome": "Mediano",    "min": 10, "emoji": "\U0001f949", "cor": "var(--warning)"},
    {"label": "D", "nome": "Incipiente", "min":  0, "emoji": "\U0001f331", "cor": "var(--text-muted)"},
]

# Minimum thresholds per archetype to be considered "active" (not Indefinido)
MIN_SCORE = 10  # below this → no archetype detected


# ------------------------------------------------------------------
# Classification engine
# ------------------------------------------------------------------

def _load_gold(config: ChampionshipConfig) -> dict:
    """Load all gold CSVs needed for classification. Returns a dict of DataFrames."""
    gd = config._au_first_round()
    out = {}

    # 1afase_valido_all
    valid_path = config.gold_valid_path()
    if os.path.exists(valid_path):
        out["valid"] = pd.read_csv(valid_path, sep=",")
    else:
        out["valid"] = pd.DataFrame()

    # boldness_index
    bp = _norm(os.path.join(gd, "boldness_index.csv"))
    if os.path.exists(bp):
        out["boldness"] = pd.read_csv(bp, sep=",")
    else:
        out["boldness"] = pd.DataFrame()

    # upset_tracker
    up = _norm(os.path.join(gd, "upset_tracker.csv"))
    if os.path.exists(up):
        out["upset"] = pd.read_csv(up, sep=",")
    else:
        out["upset"] = pd.DataFrame()

    # consistency
    cp = _norm(os.path.join(gd, "consistency.csv"))
    if os.path.exists(cp):
        out["consistency"] = pd.read_csv(cp, sep=",")
    else:
        out["consistency"] = pd.DataFrame()

    # team_accuracy
    tap = _norm(os.path.join(gd, "team_accuracy.csv"))
    if os.path.exists(tap):
        out["team_accuracy"] = pd.read_csv(tap, sep=",")
    else:
        out["team_accuracy"] = pd.DataFrame()

    # goal_error_by_team
    gep = _norm(os.path.join(gd, "goal_error_by_team.csv"))
    if os.path.exists(gep):
        out["goal_error"] = pd.read_csv(gep, sep=",")
    else:
        out["goal_error"] = pd.DataFrame()

    # round_by_round
    rrp = _norm(os.path.join(gd, "round_by_round.csv"))
    if os.path.exists(rrp):
        out["round_by_round"] = pd.read_csv(rrp, sep=",")
    else:
        out["round_by_round"] = pd.DataFrame()

    return out


def _get_players(data: dict) -> list[str]:
    """Get sorted list of all player names from available data."""
    players: set[str] = set()
    for key in ("valid", "boldness", "upset", "consistency", "team_accuracy",
                "goal_error", "round_by_round"):
        df = data.get(key, pd.DataFrame())
        if "boleiro" in df.columns:
            players.update(df["boleiro"].unique())
        elif "who" in df.columns:
            players.update(df["who"].unique())
    return sorted(players)


def _player_val(data: dict, key: str, col: str, player: str, default=0):
    """Get a single value from a gold dataframe for a given player."""
    df = data.get(key, pd.DataFrame())
    if df.empty:
        return default
    col_name = "boleiro" if "boleiro" in df.columns else ("who" if "who" in df.columns else None)
    if col_name is None:
        return default
    row = df[df[col_name] == player]
    if row.empty or col not in row.columns:
        return default
    val = row.iloc[0][col]
    try:
        return float(val) if pd.notna(val) else default
    except (ValueError, TypeError):
        return default


def classificar_jogadores(config: ChampionshipConfig) -> pd.DataFrame:
    """Classify every player and save the result CSV. Returns the DataFrame."""
    data = _load_gold(config)
    players = _get_players(data)

    # Compute bolão-wide averages
    bolao_avg_goals = 0.0
    bolao_exata_rate = 0.0
    if not data["valid"].empty and "who" in data["valid"].columns:
        if "home_goals_bol" in data["valid"].columns and "away_goals_bol" in data["valid"].columns:
            total_games = len(data["valid"])
            total_goals = (data["valid"]["home_goals_bol"].fillna(0) +
                           data["valid"]["away_goals_bol"].fillna(0)).sum()
            bolao_avg_goals = round(total_goals / total_games, 2) if total_games else 0.0
        if "1-Placar exato" in data["valid"].columns:
            bolao_exata_rate = data["valid"]["1-Placar exato"].mean()

    # Max points per game
    max_pts = config.scoring_dict()
    max_pts_val = max(max_pts.values()) if max_pts else 10

    rows = []
    for p in players:
        row: dict[str, object] = {"boleiro": p}

        # --- 1. Cientista: pts_pct + prec_pct + reg_pct ---
        # Filter player's valid predictions
        df_p = data["valid"]
        if "who" in df_p.columns:
            df_pp = df_p[df_p["who"] == p]
        elif "boleiro" in df_p.columns:
            df_pp = df_p[df_p["boleiro"] == p]
        else:
            df_pp = pd.DataFrame()

        if not df_pp.empty and "pontos" in df_pp.columns:
            total_pts = int(df_pp["pontos"].sum())
            num_games = len(df_pp)
            avg_pts = total_pts / num_games if num_games else 0
            max_possible = num_games * max_pts_val
            pts_pct = min(100, round(total_pts / max_possible * 100)) if max_possible else 0
            prec_pct = min(100, round(avg_pts / max_pts_val * 100)) if max_pts_val else 0
        else:
            pts_pct = 0
            prec_pct = 0

        # Regularity from consistency.csv (running_avg_5)
        reg_pct = 50
        if not data["consistency"].empty:
            df_c = data["consistency"][data["consistency"]["boleiro"] == p]
            if not df_c.empty and "running_avg_5" in df_c.columns:
                avg_run = df_c["running_avg_5"].mean()
                reg_pct = min(100, round(avg_run / max_pts_val * 100)) if max_pts_val else 50

        score_cientista = round((pts_pct + prec_pct + reg_pct) / 3)
        row["score_cientista"] = score_cientista

        # --- 2. Zebreiro: zebra_pct × (1 + boldness/50) ---
        # Boldness
        boldness_score = _player_val(data, "boldness", "boldness_score", p, 0.0)
        boldness_norm = max(0, min(100, round(50 + boldness_score * 25)))

        # Zebra count
        zebra_pct = 0
        player_upsets = 0
        total_upsets = 0
        if not data["upset"].empty:
            upset_matches = data["upset"][data["upset"].get("is_upset", 0) == 1]
            total_upsets = len(upset_matches)
            for _, r in upset_matches.iterrows():
                pc = str(r.get("players_correct", ""))
                if p in [x.strip() for x in pc.split("|")]:
                    player_upsets += 1
            zebra_pct = round(player_upsets / total_upsets * 100) if total_upsets else 0

        score_zebreiro = min(100, round(zebra_pct * (1 + boldness_score)))
        if score_zebreiro < 0:
            score_zebreiro = 0
        row["score_zebreiro"] = score_zebreiro

        # --- 3. Conservador: inverse of boldness ---
        score_conservador = max(0, min(100, round(100 - boldness_norm)))
        row["score_conservador"] = score_conservador

        # --- 4. Otimista: avg goals above bolão avg ---
        avg_goals = _player_val(data, "boldness", "avg_total_goals_bol", p, 0.0)
        desvio_acima = max(0, avg_goals - bolao_avg_goals)
        score_otimista = min(100, round(desvio_acima * 50))
        row["score_otimista"] = score_otimista

        # --- 5. Pessimista: avg goals below bolão avg ---
        desvio_abaixo = max(0, bolao_avg_goals - avg_goals)
        score_pessimista = min(100, round(desvio_abaixo * 50))
        row["score_pessimista"] = score_pessimista

        # --- 6. Especialista: std dev of team accuracy (normalized) ---
        # High std = player is very good at some teams, bad at others.
        score_especialista = 0
        if not data["team_accuracy"].empty:
            df_ta = data["team_accuracy"][data["team_accuracy"]["boleiro"] == p].copy()
            if not df_ta.empty and "accuracy_pct" in df_ta.columns:
                acc_norm = df_ta["accuracy_pct"] / 100.0
                acc_std = acc_norm.std(ddof=0)
                # std in [0, ~0.5] → multiply by 100 to get 0-50 range
                score_especialista = min(100, round(acc_std * 100))
        row["score_especialista"] = score_especialista

        # --- 7. Montanha-Russa: CV of points per round ---
        score_montanha = 0
        if not data["round_by_round"].empty:
            df_rr = data["round_by_round"][data["round_by_round"]["boleiro"] == p]
            if not df_rr.empty and "points" in df_rr.columns:
                pts_series = df_rr["points"]
                if pts_series.std() > 0 and pts_series.mean() > 0:
                    cv = pts_series.std() / pts_series.mean()
                    # Use cv * 50 so cv=1 → 50, cv=2 → 100 (balanced with other scores)
                    score_montanha = min(100, round(cv * 50))
        # Also check consistency for alternating streaks (modest boost)
        if not data["consistency"].empty:
            df_c2 = data["consistency"][data["consistency"]["boleiro"] == p].sort_values("date")
            if len(df_c2) >= 4:
                streak_types = df_c2["streak_type"].tolist()
                alternations = sum(1 for i in range(1, len(streak_types))
                                   if streak_types[i] != streak_types[i-1]
                                   and streak_types[i] in ("hit", "miss")
                                   and streak_types[i-1] in ("hit", "miss"))
                # Only boost if there are clear alternations AND CV is already notable
                if alternations >= 4 and score_montanha < 40:
                    score_montanha = max(score_montanha, min(60, alternations * 15))
        row["score_montanha"] = score_montanha

        # --- 8. Placarzeiro: exact-score rate (0-100, capped) ---
        score_placarzeiro = 0
        if not df_pp.empty and "1-Placar exato" in df_pp.columns:
            player_exata = df_pp["1-Placar exato"].mean()
            if bolao_exata_rate > 0:
                ratio = player_exata / bolao_exata_rate
                # ratio 0 → 0, ratio 1 (avg) → 0, ratio 2 (2x avg) → 50, ratio 3 → 100
                score_placarzeiro = max(0, min(100, round((ratio - 1) * 50)))
        row["score_placarzeiro"] = score_placarzeiro

        # --- Key stats for display ---
        row["avg_pts"] = round(avg_pts, 1) if not df_pp.empty and "pontos" in df_pp.columns else 0
        row["num_games"] = num_games if not df_pp.empty else 0
        row["zebra_count"] = player_upsets

        rows.append(row)

    # --- Second pass: z-score normalization across all players ---
    df_raw = pd.DataFrame(rows)
    score_cols = [
        "score_cientista", "score_zebreiro", "score_conservador",
        "score_otimista", "score_pessimista", "score_especialista",
        "score_montanha", "score_placarzeiro",
    ]
    arq_names = [
        "Cientista", "Zebreiro", "Conservador",
        "Otimista", "Pessimista", "Especialista",
        "Montanha-Russa", "Placarzeiro",
    ]

    # Compute z-scores: (value - mean) / std, clipped to [-3, 3], scaled to 0-100
    zscore_data: dict[str, list[float]] = {}
    for col in score_cols:
        vals = df_raw[col].fillna(0).values.astype(float)
        mean_v = vals.mean()
        std_v = vals.std()
        if std_v > 0:
            zs_raw = (vals - mean_v) / std_v
        else:
            zs_raw = vals * 0.0
        # Clip to [-3, 3] and scale to 0-100
        zs_list = []
        for z in zs_raw:
            zc = max(-3.0, min(3.0, z))
            scaled = round(((zc + 3.0) / 6.0) * 100.0)
            zs_list.append(scaled)
        zscore_data[col] = zs_list

    # Add z-scores and determine primary archetype + tier
    df_result = df_raw.copy()
    for i, col in enumerate(score_cols):
        df_result[col + "_z"] = zscore_data[col]

    # Determine primary archetype by highest z-score
    primary_arqs: list[str] = []
    primary_scores: list[int] = []
    secondary_json: list[str] = []

    for pi in range(len(df_raw)):
        best_name = "Indefinido"
        best_z = -999
        sec_list: list[dict] = []

        for j, col in enumerate(score_cols):
            zs = zscore_data[col][pi]  # z-score for this player
            nm = arq_names[j]

            if zs > best_z:
                # Previous best becomes secondary (if >= 50, i.e., above average)
                if best_z >= 50 and best_name != "Indefinido":
                    prev_emoji = ARQ_MAP.get(best_name, {}).get("emoji", "?")
                    prev_cor = ARQ_MAP.get(best_name, {}).get("cor", "#999")
                    sec_list.append({"nome": best_name, "score": int(best_z),
                                     "emoji": prev_emoji, "cor": prev_cor})
                best_z = zs
                best_name = nm
            elif zs >= 50:
                # Other secondary traits (above average)
                emoji = ARQ_MAP.get(nm, {}).get("emoji", "?")
                cor = ARQ_MAP.get(nm, {}).get("cor", "#999")
                sec_list.append({"nome": nm, "score": int(zs), "emoji": emoji, "cor": cor})

        # If best_z is below 40 (below average in ALL dimensions), mark as Indefinido
        if best_z < 40:
            best_name = "Indefinido"
            best_z = 0

        primary_arqs.append(best_name)
        primary_scores.append(int(best_z))
        secondary_json.append(json.dumps(sec_list, ensure_ascii=False))

    df_result["arquetipo"] = primary_arqs
    df_result["score"] = primary_scores
    df_result["secondary"] = secondary_json
    df_result["arquetipo_emoji"] = df_result["arquetipo"].map(
        lambda n: ARQ_MAP.get(n, {}).get("emoji", "?")
    )
    df_result["arquetipo_cor"] = df_result["arquetipo"].map(
        lambda n: ARQ_MAP.get(n, {}).get("cor", "#999")
    )

    # Determine tier for each player
    tier_labels: list[str] = []
    tier_nomes: list[str] = []
    tier_emojis: list[str] = []
    tier_cores: list[str] = []
    for _, row in df_result.iterrows():
        sc = int(row["score"])
        found = False
        for t in TIERS:
            if sc >= t["min"]:
                tier_labels.append(t["label"])
                tier_nomes.append(t["nome"])
                tier_emojis.append(t["emoji"])
                tier_cores.append(t["cor"])
                found = True
                break
        if not found:
            tier_labels.append("D")
            tier_nomes.append("Incipiente")
            tier_emojis.append("\U0001f331")
            tier_cores.append("var(--text-muted)")
    df_result["tier_label"] = tier_labels
    df_result["tier_nome"] = tier_nomes
    df_result["tier_emoji"] = tier_emojis
    df_result["tier_cor"] = tier_cores

    # Save CSV
    out_path = _norm(os.path.join(config._au_first_round(), "arquetipos_classification.csv"))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df_result.to_csv(out_path, sep=",", index=False)
    print_colored(f"salvos {len(df_result)} arquetipos em {out_path}", "green")

    return df_result


# ------------------------------------------------------------------
# HTML page builder – Legend + Gallery
# ------------------------------------------------------------------

_CSS_ARQUETIPOS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif;
    background: var(--bg);
    color: var(--text);
    font-size: 16px;
    line-height: 1.5;
    -webkit-text-size-adjust: 100%;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

.hero {
    background: var(--bg);
    padding: 1.5rem 1rem;
    text-align: center;
    border-bottom: 1px solid var(--card-border);
}
.hero h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
.hero .subtitle { font-size: 0.9rem; opacity: 0.85; }

.section { margin: 0.75rem; }
.section-title {
    font-size: 1rem; font-weight: 700;
    margin-bottom: 0.5rem; padding: 0 0.25rem;
    display: flex; align-items: center; gap: 0.4rem;
}
.card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 0.75rem;
    margin-bottom: 0.75rem;
}
.card-title { font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-muted); }

/* Grid da galeria */
.gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.75rem;
}
.player-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 0.75rem;
    text-align: center;
    transition: border-color 0.15s;
    display: flex;
    flex-direction: column;
    align-items: center;
}
.player-card:hover { border-color: var(--accent); }
.player-card .rank-emoji { font-size: 1.8rem; line-height: 1.2; }
.player-card .tier-badge {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 999px;
    margin: 0.2rem 0;
}
.player-card .name { font-size: 0.8rem; font-weight: 600; margin: 0.2rem 0; }
.player-card .arq-name { font-size: 0.75rem; opacity: 0.8; }
.player-card .stats { font-size: 0.65rem; color: var(--text-muted); margin: 0.25rem 0; }
.player-card .secondary-badges {
    display: flex; flex-wrap: wrap; gap: 0.2rem; justify-content: center;
    margin-top: 0.25rem;
}
.player-card .sec-badge {
    font-size: 0.65rem;
    padding: 0.1rem 0.35rem;
    border-radius: 4px;
    background: var(--card-border);
    color: var(--text-muted);
}
.player-card .sec-badge.active { opacity: 1; }

/* Barra de score */
.score-bar {
    width: 100%;
    height: 6px;
    background: var(--card-border);
    border-radius: 3px;
    margin: 0.3rem 0;
    overflow: hidden;
}
.score-bar .fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s;
}

/* Tabela da legenda */
.legend-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.78rem;
}
.legend-table th {
    text-align: left;
    padding: 0.4rem 0.5rem;
    color: var(--text-muted);
    border-bottom: 1px solid var(--card-border);
    font-weight: 600;
}
.legend-table td {
    padding: 0.5rem;
    border-bottom: 1px solid var(--card-border);
    vertical-align: middle;
}
.legend-table tr:last-child td { border-bottom: none; }
.legend-table .arq-emoji { font-size: 1.3rem; text-align: center; }
.legend-table .arq-name { font-weight: 600; white-space: nowrap; }
.legend-table .tier-tag {
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    margin: 0.05rem;
    white-space: nowrap;
}

/* Distribuição */
.dist-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.3rem;
    font-size: 0.8rem;
}
.dist-bar .dist-label { min-width: 100px; display: flex; align-items: center; gap: 0.3rem; }
.dist-bar .dist-track { flex: 1; height: 16px; background: var(--card-border); border-radius: 8px; overflow: hidden; }
.dist-bar .dist-fill { height: 100%; border-radius: 8px; }
.dist-bar .dist-count { min-width: 30px; text-align: right; color: var(--text-muted); }

.empty-state { color: var(--text-muted); font-size: 0.85rem; padding: 1rem; text-align: center; }
"""


def _build_arquetipos(config: ChampionshipConfig) -> str:
    """Build the full arquetipos.html page (legend + gallery)."""
    # Load classification CSV (must exist)
    csv_path = _norm(os.path.join(config._au_first_round(), "arquetipos_classification.csv"))
    if not os.path.exists(csv_path):
        return _page_frame(config, "Arqu\u00e9tipos",
                           '<div class="hero"><h1>\U0001f3ad Arquetipos</h1><div class="subtitle">Classifique os jogadores executando o pipeline primeiro.</div></div>',
                           active_nav="arquetipos.html")
    df = pd.read_csv(csv_path, sep=",")
    if df.empty:
        return _page_frame(config, "Arqu\u00e9tipos",
                           '<div class="hero"><h1>\U0001f3ad Arquetipos</h1><div class="subtitle">Nenhum jogador classificado.</div></div>',
                           active_nav="arquetipos.html")

    tz = pytz.timezone(config.timezone)
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")

    # Sort by score descending
    df["score_int"] = df["score"].astype(int)
    df = df.sort_values("score_int", ascending=False)

    body = ""

    # --- Hero ---
    body += f"""
<div class="hero">
    <h1>\U0001f3ad Arqu\u00e9tipos do Bol\u00e3o</h1>
    <div class="subtitle">O estilo de cada jogador, revelado pelos dados</div>
</div>
<div style="text-align:center;font-size:0.75rem;color:var(--text-muted);padding:0 0.75rem 0.5rem;">
    atualizado \u00e0s {now_str}
</div>
"""

    # --- Legend ---
    legend_rows = ""
    for a in ARQUETIPOS:
        emoji = a["emoji"]
        nome = a["nome"]
        desc = a["descricao"]
        cor = a["cor"]
        # Build tier tags
        tier_tags = ""
        for t in TIERS:
            tt_color = t["cor"]
            tier_tags += f'<span class="tier-tag" style="background:{tt_color}22;color:{tt_color};border:1px solid {tt_color};">{t["emoji"]} {t["label"]} (\u2265{t["min"]}%)</span> '
        legend_rows += f"""<tr>
    <td class="arq-emoji">{emoji}</td>
    <td class="arq-name" style="color:{cor};">{nome}</td>
    <td style="color:var(--text-muted);">{desc}</td>
    <td>{tier_tags}</td>
</tr>"""

    body += f"""
<div class="section">
    <div class="section-title">\U0001f4d6 Legenda Completa</div>
    <div class="card" style="overflow-x:auto;">
        <table class="legend-table">
            <thead><tr>
                <th></th>
                <th>Arqu\u00e9tipo</th>
                <th>Descri\u00e7\u00e3o</th>
                <th>Tiers</th>
            </tr></thead>
            <tbody>{legend_rows}</tbody>
        </table>
        <div style="font-size:0.7rem;color:var(--text-muted);margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--card-border);">
            <strong>Badges comuns</strong>: \U0001f525 Embrazado (streak \u2265 3 acertos) \u00b7 \U0001f993 Ca\u00e7ador de Zebras (top 3 zebras) \u00b7 \U0001f4a5 Ousado (boldness > 0.3) \u00b7 \U0001F9CA Conservador (boldness &lt; -0.3) \u00b7 \U0001f40d L\u00edder (1\u00ba geral) \u00b7 \U0001f3af Especialista em X (maior acur\u00e1cia num time)
        </div>
    </div>
</div>
"""

    # --- Distribution ---
    dist_counts = df["arquetipo"].value_counts()
    dist_rows = ""
    for a in ARQUETIPOS:
        nome = a["nome"]
        cnt = int(dist_counts.get(nome, 0))
        if cnt == 0:
            continue
        emoji = a["emoji"]
        cor = a["cor"]
        max_cnt = dist_counts.max()
        pct = max(cnt / max_cnt * 100, 1) if max_cnt else 0
        dist_rows += f"""
<div class="dist-bar">
    <span class="dist-label">{emoji} {nome}</span>
    <div class="dist-track"><div class="dist-fill" style="width:{pct}%;background:{cor};"></div></div>
    <span class="dist-count">{cnt}</span>
</div>"""
    if dist_rows:
        body += f"""
<div class="section">
    <div class="section-title">\U0001f4ca Distribui\u00e7\u00e3o</div>
    <div class="card">{dist_rows}</div>
</div>
"""

    # --- Gallery (players sorted by score) ---
    cards_html = ""
    indefinidos_html = ""
    for _, r in df.iterrows():
        nome = str(r["boleiro"])
        arq = str(r["arquetipo"])
        arq_emoji = str(r["arquetipo_emoji"])
        arq_cor = str(r["arquetipo_cor"])
        score = int(r.get("score_int", 0))
        tier_emoji = str(r.get("tier_emoji", ""))
        tier_label = str(r.get("tier_label", ""))
        tier_cor = str(r.get("tier_cor", "var(--text-muted)"))
        avg_pts = str(r.get("avg_pts", "-"))
        zebras = str(r.get("zebra_count", "0"))

        # Secondary traits
        sec_raw = str(r.get("secondary", "[]"))
        try:
            sec_list = json.loads(sec_raw)
        except (json.JSONDecodeError, TypeError):
            sec_list = []
        sec_badges = ""
        for s in sec_list:
            s_emoji = s.get("emoji", "?")
            s_nome = s.get("nome", "")
            s_cor = s.get("cor", "#999")
            sec_badges += f'<span class="sec-badge" style="background:{s_cor}22;color:{s_cor};">{s_emoji} {s_nome}</span>\n'

        # Tier badge color
        score_pct = min(score, 100)

        card = f"""
<div class="player-card">
    <div class="rank-emoji">{arq_emoji}</div>
    <div class="tier-badge" style="background:{tier_cor}22;color:{tier_cor};border:1px solid {tier_cor};">{tier_emoji} {tier_label}</div>
    <div class="score-bar"><div class="fill" style="width:{score_pct}%;background:{arq_cor};"></div></div>
    <div class="arq-name" style="color:{arq_cor};">{arq}</div>
    <div class="name"><a href="boleiros/{nome}.html" style="color:var(--text);">{nome}</a></div>
    <div class="stats">{avg_pts}m\u00e9d \u00b7 {zebras} zebras</div>
    {f'<div class="secondary-badges">{sec_badges}</div>' if sec_badges else ''}
</div>"""

        if arq == "Indefinido":
            indefinidos_html += card
        else:
            cards_html += card

    gallery_html = ""
    if cards_html:
        gallery_html += f"""
<div class="section">
    <div class="section-title">\U0001f465 Galeria de Jogadores</div>
    <div class="gallery-grid">{cards_html}</div>
</div>"""
    if indefinidos_html:
        gallery_html += f"""
<div class="section">
    <div class="section-title">\u2753 Indefinidos</div>
    <div class="gallery-grid">{indefinidos_html}</div>
    <div style="font-size:0.75rem;color:var(--text-muted);margin-top:0.3rem;">Jogadores sem tra\u00e7os fortes o bastante para um perfil definido.</div>
</div>"""

    body += gallery_html

    return _page_frame(config, f"Arqu\u00e9tipos - {config.report_title}", body, active_nav="arquetipos.html")


# ------------------------------------------------------------------
# Page builder wrapper
# ------------------------------------------------------------------

def _page_frame(config: ChampionshipConfig, title: str, body: str, back_link: str = "", active_nav: str = "") -> str:
    """Replica of _page_frame from new_views.py to avoid circular imports."""
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
    {_CSS_ARQUETIPOS}
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


def build_arquetipos_page(config: ChampionshipConfig, html_base: str) -> None:
    """Generate arquetipos.html and save it."""
    path = _norm(os.path.join(html_base, "arquetipos.html"))
    print_colored("generating arquetipos.html", "blue")
    _save(path, _build_arquetipos(config))
