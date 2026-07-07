"""Arquetipos — player persona classification + gallery/legend page.

Classifies each player into 1 of 9 archetypes (exclusive, no overlap)
organised into 3 categories. Also computes a GEO profile (which continent
the player predicts best).

Saves ``arquetipos_classification.csv`` as single source of truth,
reused by per-player profile pages.
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig
from src.core.printing import print_colored


def _norm(path: str) -> str:
    return os.path.normpath(path)


def _save(filepath: str, content: str) -> None:
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


# ------------------------------------------------------------------
# Categories & Archetype definitions
# ------------------------------------------------------------------

CATEGORIAS: list[dict] = [
    {
        "nome": "Performance",
        "emoji": "\U0001f3af",
        "descricao": "Como o jogador performa ao longo do campeonato",
        "arquetipos": ["Cientista", "Montanha-Russa"],
    },
    {
        "nome": "Estilo de Palpite",
        "emoji": "\U0001f3b2",
        "descricao": "Tend\u00eancia ao prever os placares",
        "arquetipos": ["Otimista", "Pessimista", "Conservador"],
    },
    {
        "nome": "Especializa\u00e7\u00e3o",
        "emoji": "\U0001f50d",
        "descricao": "O que o jogador faz de melhor",
        "arquetipos": ["Zebreiro", "Especialista", "Placarzeiro"],
    },
]

ARQUETIPOS: list[dict] = [
    {
        "emoji": "\U0001f9ea",
        "nome": "Cientista",
        "categoria": "Performance",
        "cor": "#6366f1",
        "descricao": "Performance consistente, alta pontua\u00e7\u00e3o e regularidade.",
        "racional": "Maior m\u00e9dia de pontos por jogo entre todos os participantes.",
    },
    {
        "emoji": "\U0001f3a2",
        "nome": "Montanha-Russa",
        "categoria": "Performance",
        "cor": "#ec4899",
        "descricao": "Altos e baixos — streaks que alternam, varia\u00e7\u00e3o alta.",
        "racional": "Maior coeficiente de varia\u00e7\u00e3o nos pontos por rodada + altern\u00e2ncia de streaks.",
    },
    {
        "emoji": "\U0001f31f",
        "nome": "Otimista",
        "categoria": "Estilo de Palpite",
        "cor": "#f59e0b",
        "descricao": "Sempre espera muitos gols — superestima placares.",
        "racional": "Goal bias positivo: em m\u00e9dia, prev\u00ea mais gols do que realmente acontecem.",
    },
    {
        "emoji": "\u2601\ufe0f",
        "nome": "Pessimista",
        "categoria": "Estilo de Palpite",
        "cor": "#6b7280",
        "descricao": "Sempre espera poucos gols — subestima placares.",
        "racional": "Goal bias negativo: em m\u00e9dia, prev\u00ea menos gols do que realmente acontecem.",
    },
    {
        "emoji": "\U0001f6e1\ufe0f",
        "nome": "Conservador",
        "categoria": "Estilo de Palpite",
        "cor": "#3b82f6",
        "descricao": "Palpites seguros, perto da m\u00e9dia do bol\u00e3o.",
        "racional": "Baixo \u00edndice de ousadia (boldness) — palpita perto da m\u00e9dia, sem arriscar.",
    },
    {
        "emoji": "\U0001f993",
        "nome": "Zebreiro",
        "categoria": "Especializa\u00e7\u00e3o",
        "cor": "#ef4444",
        "descricao": "Ca\u00e7a surpresas, opini\u00e3o contr\u00e1ria \u00e0 maioria.",
        "racional": "Mais zebras acertadas entre todos os participantes.",
    },
    {
        "emoji": "\U0001f3af",
        "nome": "Especialista",
        "categoria": "Especializa\u00e7\u00e3o",
        "cor": "#10b981",
        "descricao": "Muito preciso em time(s) espec\u00edfico(s).",
        "racional": "Alta varia\u00e7\u00e3o de acur\u00e1cia entre times — craque em alguns, fraco em outros.",
    },
    {
        "emoji": "\u2705",
        "nome": "Placarzeiro",
        "categoria": "Especializa\u00e7\u00e3o",
        "cor": "#8b5cf6",
        "descricao": "Especialista em acertar placar exato.",
        "racional": "Taxa de acerto de placar exato acima da m\u00e9dia do bol\u00e3o.",
    },
    {
        "emoji": "\u2753",
        "nome": "Indefinido",
        "categoria": "",
        "cor": "#9ca3af",
        "descricao": "Sem tra\u00e7os fortes o bastante para um perfil definido.",
        "racional": "Nenhum arqu\u00e9tipo atingiu o percentil m\u00ednimo de 50.",
    },
]

ARQ_MAP: dict[str, dict] = {a["nome"]: a for a in ARQUETIPOS}

TIERS: list[dict] = [
    {"label": "S", "nome": "Lend\u00e1rio", "min": 90, "emoji": "\U0001f48e", "cor": "#f59e0b"},
    {"label": "A", "nome": "Craque",     "min": 70, "emoji": "\U0001f947", "cor": "#10b981"},
    {"label": "B", "nome": "Bom",        "min": 40, "emoji": "\U0001f948", "cor": "#3b82f6"},
    {"label": "C", "nome": "Mediano",    "min": 10, "emoji": "\U0001f949", "cor": "#8b5cf6"},
    {"label": "D", "nome": "Incipiente", "min":  0, "emoji": "\U0001f331", "cor": "#6b7280"},
]

# Mapa de continentes com emoji
GEO_EMOJI: dict[str, str] = {
    "europeu": "\U0001f30d",
    "latino": "\U0001f30e",
    "asiatico": "\U0001f30f",
    "africano": "\U0001f30c",
    "anfitriao": "\U0001f3c6",
    "oceanico": "\U0001f30a",
}
GEO_NOME: dict[str, str] = {
    "europeu": "europeu",
    "latino": "latino",
    "asiatico": "asiatico",
    "africano": "africano",
    "anfitriao": "anfitriao",
    "oceanico": "oceanico",
}

GEO_ORDER: list[str] = ["europeu", "latino", "asiatico", "africano", "anfitriao", "oceanico"]

MIN_SCORE = 50  # minimum percentile to assign a non-Indefinido archetype


# ------------------------------------------------------------------
# Percentile helper
# ------------------------------------------------------------------

def _percentile_rank(values: list[float]) -> list[float]:
    """Convert a list of values to percentile ranks (0-100).

    Uses the 'average' method: percentile = (number_of_values_below / total) * 100
    Returns 0 for constant/empty inputs.
    """
    n = len(values)
    if n == 0:
        return []
    sorted_vals = sorted(values)
    ranks: list[float] = []
    for v in values:
        below = sum(1 for sv in sorted_vals if sv < v)
        tied = sum(1 for sv in sorted_vals if sv == v)
        # Use (below + 0.5*tied) / n * 100 to handle ties gracefully
        rank = ((below + 0.5 * tied) / n) * 100.0
        ranks.append(rank)
    return ranks


# ------------------------------------------------------------------
# Load gold data
# ------------------------------------------------------------------

def _load_gold(config: ChampionshipConfig) -> dict:
    """Load all gold OBT parquets needed for classification."""
    out: dict = {}

    def _try_load_obt(name: str) -> pd.DataFrame:
        """Load OBT parquet; return empty DataFrame on missing/error."""
        return config.load_gold_dataframe(name)

    out["valid"] = _try_load_obt("obt_palpites")
    if not out["valid"].empty and "valido" in out["valid"].columns:
        out["valid"] = out["valid"][out["valid"]["valido"] == 1].copy()

    for name in ("obt_boldness", "obt_upsets", "obt_consistency",
                 "obt_team_accuracy", "obt_goal_error", "obt_round_by_round"):
        out[name.replace("obt_", "")] = _try_load_obt(name)

    return out


def _get_players(data: dict) -> list[str]:
    """Get sorted unique player names from all available data."""
    players: set[str] = set()
    for key, df in data.items():
        if df.empty:
            continue
        for col in ("boleiro", "who"):
            if col in df.columns:
                players.update(df[col].unique())
    return sorted(players)


def _player_val(df: pd.DataFrame, player: str, col: str, default=0.0):
    """Get a scalar value from a player-specific DataFrame row."""
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


# ------------------------------------------------------------------
# Core classification
# ------------------------------------------------------------------

def classificar_jogadores(config: ChampionshipConfig) -> pd.DataFrame:
    """Classify every player into archetype + geo, save CSV, return DataFrame."""
    data = _load_gold(config)
    players = _get_players(data)
    if not players:
        return pd.DataFrame()

    # --- Pre-compute bolão-wide stats ---
    df_v = data["valid"]

    bolao_exata_rate = 0.0
    if not df_v.empty and "1-Placar exato" in df_v.columns:
        bolao_exata_rate = df_v["1-Placar exato"].mean()

    # Pre-load shared DataFrames
    df_upset = data.get("upset_tracker", pd.DataFrame())
    df_bold = data.get("boldness_index", pd.DataFrame())
    df_geo_err = data.get("goal_error_by_team", pd.DataFrame())
    df_ta = data.get("team_accuracy", pd.DataFrame())
    df_rr = data.get("round_by_round", pd.DataFrame())
    df_cons = data.get("consistency", pd.DataFrame())

    # --- Step 1: compute raw scores per player per dimension ---
    raw_rows: list[dict] = []
    for p in players:
        row: dict = {"boleiro": p}

        # Player's valid predictions
        if "who" in df_v.columns:
            df_pp = df_v[df_v["who"] == p]
        elif "boleiro" in df_v.columns:
            df_pp = df_v[df_v["boleiro"] == p]
        else:
            df_pp = pd.DataFrame()

        # -- Cientista: avg points per game --
        avg_pts = 0.0
        if not df_pp.empty and "pontos" in df_pp.columns:
            avg_pts = df_pp["pontos"].mean()
        row["raw_cientista"] = avg_pts

        # -- Zebreiro: count of upsets correctly predicted --
        zebra_count = 0
        if not df_upset.empty:
            upset_matches = df_upset[df_upset.get("is_upset", 0) == 1]
            for _, r in upset_matches.iterrows():
                pc = str(r.get("players_correct", ""))
                if p in [x.strip() for x in pc.split("|")]:
                    zebra_count += 1
        row["raw_zebreiro"] = float(zebra_count)

        # -- Conservador: inverse of boldness (0-100) --
        boldness_score = 0.0
        if not df_bold.empty:
            boldness_score = _player_val(df_bold, p, "boldness_score", 0.0)
        boldness_norm = max(0, min(100, 50 + boldness_score * 25))
        row["raw_conservador"] = max(0, 100 - boldness_norm)

        # -- Otimista / Pessimista: goal_bias from goal_error_by_team --
        mean_bias = 0.0
        if not df_geo_err.empty and "boleiro" in df_geo_err.columns:
            df_bias = df_geo_err[df_geo_err["boleiro"] == p]
            if not df_bias.empty and "goal_bias" in df_bias.columns:
                mean_bias = df_bias["goal_bias"].mean()
        row["raw_otimista"] = max(0, mean_bias)
        row["raw_pessimista"] = max(0, -mean_bias)

        # -- Especialista: std of accuracy across teams (aggregated) --
        spec_score = 0.0
        if not df_ta.empty and "boleiro" in df_ta.columns:
            df_ta_p = df_ta[df_ta["boleiro"] == p].copy()
            if not df_ta_p.empty and "accuracy_pct" in df_ta_p.columns and "total_bets" in df_ta_p.columns and "team" in df_ta_p.columns:
                # Aggregate home+away per team when role exists
                team_aggr = df_ta_p.groupby("team").agg(
                    total_bets=("total_bets", "sum"),
                    correct_winner=("correct_winner", "sum"),
                ).reset_index()
                # Recompute accuracy per team
                team_aggr["accuracy"] = team_aggr["correct_winner"] / team_aggr["total_bets"]
                # Use all teams with >= 1 bet; need at least 2 teams for meaningful std
                if len(team_aggr) >= 2:
                    acc = team_aggr["accuracy"].values
                    mean_a = acc.mean()
                    if mean_a > 0:
                        std_a = acc.std(ddof=0)
                        # Coefficient of variation
                        spec_score = min(100, std_a / mean_a * 100)
        row["raw_especialista"] = spec_score

        # -- Montanha-Russa: CV of round points --
        cv_score = 0.0
        if not df_rr.empty and "boleiro" in df_rr.columns:
            df_rr_p = df_rr[df_rr["boleiro"] == p]
            if not df_rr_p.empty and "points" in df_rr_p.columns:
                pts_s = df_rr_p["points"]
                if pts_s.std() > 0 and pts_s.mean() > 0:
                    cv_score = pts_s.std() / pts_s.mean() * 50  # scale so CV=1 → 50
                    cv_score = min(100, cv_score)
        # Boost from streak alternations
        if not df_cons.empty and "boleiro" in df_cons.columns:
            df_c2 = df_cons[df_cons["boleiro"] == p].sort_values("date")
            if len(df_c2) >= 4:
                streak_types = df_c2["streak_type"].tolist()
                alternations = sum(
                    1 for i in range(1, len(streak_types))
                    if streak_types[i] != streak_types[i - 1]
                    and streak_types[i] in ("hit", "miss")
                    and streak_types[i - 1] in ("hit", "miss")
                )
                if alternations >= 3:
                    cv_score = max(cv_score, min(80, alternations * 15))
        row["raw_montanha"] = cv_score

        # -- Placarzeiro: exact-score rate vs bolão avg --
        pl_score = 0.0
        if not df_pp.empty and "1-Placar exato" in df_pp.columns:
            player_exata = df_pp["1-Placar exato"].mean()
            if bolao_exata_rate > 0 and player_exata > 0:
                ratio = player_exata / bolao_exata_rate
                pl_score = max(0, min(100, (ratio - 1) * 50))
        row["raw_placarzeiro"] = pl_score

        # -- Key display stats --
        row["avg_pts"] = round(avg_pts, 1)
        row["num_games"] = len(df_pp) if not df_pp.empty else 0
        row["zebra_count"] = zebra_count

        raw_rows.append(row)

    df_raw = pd.DataFrame(raw_rows)

    # --- Step 2: convert raw scores to percentiles ---
    score_cols = [
        "raw_cientista", "raw_zebreiro", "raw_conservador",
        "raw_otimista", "raw_pessimista", "raw_especialista",
        "raw_montanha", "raw_placarzeiro",
    ]
    arq_names = [
        "Cientista", "Zebreiro", "Conservador",
        "Otimista", "Pessimista", "Especialista",
        "Montanha-Russa", "Placarzeiro",
    ]

    pct_data: dict[str, list[float]] = {}
    for col in score_cols:
        vals = df_raw[col].fillna(0).tolist()
        pct_data[col] = _percentile_rank(vals)

    # --- Step 3: determine exclusive primary archetype ---
    df_result = df_raw.copy()
    for i, col in enumerate(score_cols):
        df_result[col + "_pct"] = pct_data[col]

    # Tiebreaker: z-score of each raw value (how extreme relative to peers)
    tb_z: dict[str, list[float]] = {}
    for col in score_cols:
        vals = df_raw[col].fillna(0).tolist()
        m = sum(vals) / len(vals)
        s = (sum((v - m)**2 for v in vals) / len(vals))**0.5
        tb_z[col] = [0.0] * len(vals) if s == 0 else [(v - m) / s for v in vals]

    primary_arqs: list[str] = []
    primary_scores: list[int] = []
    runner_up_arqs: list[str] = []
    runner_up_scores: list[int] = []
    is_indefinido_list: list[bool] = []

    for pi in range(len(df_raw)):
        scored: list[tuple[float, str, float]] = [
            (pct_data[col][pi], arq_names[j], tb_z[col][pi])
            for j, col in enumerate(score_cols)
        ]
        scored.sort(key=lambda x: (-x[0], -x[2]))
        best_pct, best_name, _ = scored[0]
        runner_pct, runner_name, _ = scored[1] if len(scored) > 1 else (0.0, "", 0.0)

        if best_pct < config.archetype_min_percentile:
            best_name = "Indefinido"
            best_pct = 0.0

        primary_arqs.append(best_name)
        primary_scores.append(round(best_pct))
        runner_up_arqs.append(runner_name if runner_name != best_name else "")
        runner_up_scores.append(round(runner_pct) if runner_name != best_name else 0)
        is_indefinido_list.append(best_name == "Indefinido")

    df_result["arquetipo"] = primary_arqs
    df_result["score"] = primary_scores
    df_result["runner_up_arq"] = runner_up_arqs
    df_result["runner_up_score"] = runner_up_scores
    df_result["is_indefinido"] = is_indefinido_list
    df_result["arquetipo_emoji"] = df_result["arquetipo"].map(
        lambda n: ARQ_MAP.get(n, {}).get("emoji", "?")
    )
    df_result["arquetipo_cor"] = df_result["arquetipo"].map(
        lambda n: ARQ_MAP.get(n, {}).get("cor", "#999")
    )

    # --- Step 4: Tiers ---
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

    # --- Step 5: GEO (Perfil Global) classification ---
    # Use the VALID predictions (gold data) with actual pontos per match
    geo_mapping = config.team_geo  # {pt_name: geo_key}
    if geo_mapping and not df_v.empty and "who" in df_v.columns and "resultado_bol_time" in df_v.columns:
        # Filter to rows where player predicted a specific team (not empate)
        df_team_preds = df_v[
            df_v["resultado_bol_time"].isin(geo_mapping.keys())
        ].copy()
        if not df_team_preds.empty:
            df_team_preds["continent"] = df_team_preds["resultado_bol_time"].map(geo_mapping)
            # Aggregate per (who, continent): sum pontos, count distinct teams
            geo_agg = df_team_preds.groupby(["who", "continent"]).agg(
                total_points=("pontos", "sum"),
                nteams=("resultado_bol_time", "nunique"),
            ).reset_index()
            geo_agg.rename(columns={"who": "boleiro"}, inplace=True)
            # Filter minimum 3 teams
            geo_agg = geo_agg[geo_agg["nteams"] >= 2].copy()
            if not geo_agg.empty:
                # Compute z-score per continent: how many stds above/below the
                # bolão average the player performs on that continent
                geo_agg["pts_per_team"] = geo_agg["total_points"] / geo_agg["nteams"]
                cont_stats = geo_agg.groupby("continent")["pts_per_team"].agg(
                    ["mean", "std"]
                ).reset_index()
                geo_agg = geo_agg.merge(cont_stats, on="continent", how="left")
                geo_agg["z_score"] = (
                    (geo_agg["pts_per_team"] - geo_agg["mean"])
                    / geo_agg["std"].replace(0, 1)
                )
                # Pick continent with highest z-score per player
                best_idx = geo_agg.groupby("boleiro")["z_score"].idxmax()
                df_geo = geo_agg.loc[best_idx, [
                    "boleiro", "continent", "z_score", "total_points", "nteams"
                ]].copy()
                df_geo.rename(columns={
                    "continent": "perfil_global",
                    "z_score": "global_score",
                    "total_points": "global_correct",
                    "nteams": "global_teams",
                }, inplace=True)
                df_geo["global_bets"] = df_geo["global_teams"]
                # Convert z-score to display-friendly 0-100 scale
                # z-score typically ranges -3 to +3; shift & scale
                df_geo["global_score"] = (
                    (df_geo["global_score"].clip(-3, 3) + 3) / 6 * 100
                ).round(0).astype(int)
            else:
                df_geo = pd.DataFrame(columns=["boleiro", "perfil_global", "global_score", "global_teams", "global_correct", "global_bets"])
        else:
            df_geo = pd.DataFrame(columns=["boleiro", "perfil_global", "global_score", "global_teams", "global_correct", "global_bets"])
    else:
        df_geo = pd.DataFrame(columns=["boleiro", "perfil_global", "global_score", "global_teams", "global_correct", "global_bets"])

    # Merge geo into result
    geo_cols = ["boleiro", "perfil_global", "global_score", "global_teams", "global_correct", "global_bets"]
    if not df_geo.empty:
        df_result = df_result.merge(df_geo[geo_cols], on="boleiro", how="left")
    else:
        for c in geo_cols[1:]:
            df_result[c] = 0
        df_result["perfil_global"] = ""

    df_result["perfil_global"] = df_result["perfil_global"].fillna("")
    df_result["global_score"] = df_result["global_score"].fillna(0).astype(int)
    df_result["global_teams"] = df_result["global_teams"].fillna(0).astype(int)
    df_result["global_correct"] = df_result["global_correct"].fillna(0).astype(int)
    df_result["global_bets"] = df_result["global_bets"].fillna(0).astype(int)

    # --- Save ---
    out_path = _norm(os.path.join(config._au_first_round(), "arquetipos_classification.csv"))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df_result.to_csv(out_path, sep=",", index=False)
    print_colored(f"salvos {len(df_result)} arquetipos em {out_path}", "green")

    return df_result


# ------------------------------------------------------------------
# HTML page builder
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
.hero-stats {
    display: flex; justify-content: center; gap: 1.5rem;
    margin-top: 0.75rem; flex-wrap: wrap;
}
.hero-stat { text-align: center; }
.hero-stat .hero-stat-num {
    display: block; font-size: 1.3rem; font-weight: 800;
    color: var(--accent);
}
.hero-stat { font-size: 0.7rem; color: var(--text-muted); }

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

/* Legend table */
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
    padding: 0.4rem 0.5rem;
    border-bottom: 1px solid var(--card-border);
    vertical-align: middle;
}
.legend-table tr:last-child td { border-bottom: none; }
.legend-table .arq-emoji { font-size: 1.2rem; text-align: center; width: 2rem; }
.legend-table .arq-name { font-weight: 600; white-space: nowrap; }
.legend-table .arq-desc { font-size: 0.74rem; color: var(--text-muted); }
.legend-table .arq-racional { font-size: 0.7rem; color: var(--text-muted); opacity: 0.8; max-width: 180px; }
.legend-table .cat-header td {
    font-size: 0.85rem;
    font-weight: 700;
    padding: 0.6rem 0.5rem 0.2rem;
    border-bottom: none;
    letter-spacing: 0.3px;
}
.tier-tag {
    display: inline-block;
    font-size: 0.6rem;
    font-weight: 700;
    padding: 0.1rem 0.35rem;
    border-radius: 4px;
    margin: 0.05rem;
    white-space: nowrap;
}

/* Distribution */
.dist-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.3rem;
    font-size: 0.8rem;
}
.dist-bar .dist-label { min-width: 130px; display: flex; align-items: center; gap: 0.3rem; }
.dist-bar .dist-track { flex: 1; height: 16px; background: var(--card-border); border-radius: 8px; overflow: hidden; }
.dist-bar .dist-fill { height: 100%; border-radius: 8px; }
.dist-bar .dist-count { min-width: 30px; text-align: right; color: var(--text-muted); }

/* Archetype cards in gallery */
.arq-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 0.6rem;
    margin-bottom: 0.6rem;
    border-left: 4px solid var(--arq-color, var(--card-border));
}
.arq-card-header {
    display: flex; align-items: center; gap: 0.5rem;
    margin-bottom: 0.4rem;
    flex-wrap: wrap;
}
.arq-card-header .arq-emoji { font-size: 1.4rem; }
.arq-card-header .arq-title { font-weight: 700; font-size: 0.95rem; }
.arq-card-header .arq-count {
    font-size: 0.7rem; color: var(--text-muted);
    margin-left: auto;
}
.arq-card-body {
    display: flex; flex-direction: column; gap: 0.2rem;
}
.player-row {
    display: flex; align-items: center; gap: 0.4rem;
    padding: 0.25rem 0.3rem;
    border-radius: 6px;
    font-size: 0.8rem;
    flex-wrap: wrap;
}
.player-row:hover { background: var(--hover-overlay); }
.player-row .tier-badge {
    display: inline-block;
    font-size: 0.6rem;
    font-weight: 700;
    padding: 0.1rem 0.4rem;
    border-radius: 999px;
    min-width: 2.2rem;
    text-align: center;
}
.player-row .player-name { font-weight: 600; flex: 1; }
.player-row .player-name a { color: var(--text); }
.player-row .player-score { font-size: 0.7rem; color: var(--text-muted); }
.player-row .runner-up { font-size: 0.6rem; color: var(--text-muted); opacity: 0.7; white-space: nowrap; }
.player-row .geo-badge {
    display: inline-block;
    font-size: 0.6rem;
    padding: 0.1rem 0.35rem;
    border-radius: 4px;
    background: var(--card-border);
    color: var(--text-muted);
}

/* GEO section */
.geo-card {
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 0.6rem;
    margin-bottom: 0.5rem;
}
.geo-card .geo-title {
    font-size: 0.85rem; font-weight: 700; margin-bottom: 0.3rem;
    display: flex; align-items: center; gap: 0.4rem;
}
.geo-card .geo-title .geo-count {
    font-size: 0.6rem; font-weight: 600;
    margin-left: auto;
    background: var(--card-border);
    padding: 0.05rem 0.35rem;
    border-radius: 999px;
    color: var(--text-muted);
    white-space: nowrap;
}
.geo-card .geo-players {
    font-size: 0.78rem; display: flex; flex-direction: column; gap: 0.2rem;
}
.geo-card .geo-player {
    display: flex; align-items: center; gap: 0.4rem;
}
.geo-card .geo-player .geo-player-name {
    min-width: 130px; flex-shrink: 0;
}
.geo-card .geo-player a { color: var(--text); }
.geo-card .geo-player .geo-score {
    font-size: 0.65rem; color: var(--text-muted); white-space: nowrap;
}

.empty-state { color: var(--text-muted); font-size: 0.85rem; padding: 1rem; text-align: center; }

/* Accordion (details/summary) */
.accordion-section {
    margin: 0.75rem;
    background: var(--card-bg);
    border: 1px solid var(--card-border);
    border-radius: 12px;
    padding: 0;
    overflow: hidden;
}
.accordion-summary {
    padding: 0.6rem 0.75rem;
    font-weight: 700;
    font-size: 0.95rem;
    cursor: pointer;
    user-select: none;
    -webkit-user-select: none;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.accordion-summary::-webkit-details-marker { display: none; }
.accordion-summary::marker { display: none; content: ""; }
.accordion-summary .accordion-hint {
    font-weight: 400;
    font-size: 0.7rem;
    color: var(--text-muted);
}
.accordion-summary::after {
    content: "\u25c0";
    font-size: 0.6rem;
    margin-left: auto;
    transition: transform 0.2s;
    color: var(--text-muted);
}
.accordion-section[open] .accordion-summary::after {
    transform: rotate(-90deg);
}
.accordion-section[open] .accordion-summary {
    border-bottom: 1px solid var(--card-border);
}
.accordion-section .section { margin: 0; }
.accordion-section .card { border-radius: 0; border-left: none; border-right: none; border-bottom: none; }

/* GEO bar — mini horizontal bar for relative performance */
.geo-bar-wrap {
    display: inline-flex; align-items: center; gap: 0.3rem;
    flex: 1; min-width: 4rem; max-width: 6rem;
}
.geo-bar-track {
    flex: 1; height: 4px; background: var(--card-border);
    border-radius: 2px; position: relative; overflow: hidden;
}
.geo-bar-fill {
    height: 100%; border-radius: 2px;
    transition: width 0.3s;
}
.geo-bar-mid {
    position: absolute; left: 50%; top: 0; bottom: 0;
    width: 1px; background: var(--text-muted); opacity: 0.5;
}
"""


def _build_arquetipos(config: ChampionshipConfig) -> str:
    """Build arquetipos.html page."""
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

    # Sort by score descending (non-indefinido first)
    df["score_int"] = df["score"].astype(int)
    df = df.sort_values(["is_indefinido", "score_int"], ascending=[True, False])

    tz = pytz.timezone(config.timezone)
    now_str = datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")

    body = ""

    # --- Hero with stats ---
    n_players = len(df)
    n_arqs = df["arquetipo"].nunique()
    n_geos = df["perfil_global"].nunique() if "perfil_global" in df.columns else 0
    body += f"""
<div class="hero">
    <h1>\U0001f3ad Arqu\u00e9tipos do Bol\u00e3o</h1>
    <div class="subtitle">Cada jogador tem <strong>1 \u00fanico arqu\u00e9tipo</strong> baseado no seu estilo de palpitar</div>
    <div class="hero-stats">
        <div class="hero-stat"><span class="hero-stat-num">{n_players}</span> jogadores</div>
        <div class="hero-stat"><span class="hero-stat-num">{n_arqs}</span> arqu\u00e9tipos</div>
        <div class="hero-stat"><span class="hero-stat-num">{n_geos}</span> perfis globais</div>
    </div>
</div>
<div style="text-align:center;font-size:0.75rem;color:var(--text-muted);padding:0 0.75rem 0.5rem;">
    atualizado \u00e0s {now_str}
</div>
"""

    # --- Legend + How to Read (accordion, closed by default, simplified) ---
    legend_intro = (
        "Cada jogador recebe <strong>1 \u00fanico arqu\u00e9tipo</strong>. "
        "A classifica\u00e7\u00e3o compara 8 m\u00e9tricas, converte cada uma em percentil (0\u2013100) "
        "e atribui o arqu\u00e9tipo com maior percentil. Se nenhum passar de 50%, o jogador "
        "\u00e9 classificado como <em>Indefinido</em>."
    )
    legend_rows = ""
    for cat in CATEGORIAS:
        cat_name = cat["nome"]
        cat_emoji = cat["emoji"]
        cat_desc = cat["descricao"]
        legend_rows += f'<tr class="cat-header"><td colspan="3" style="color:var(--text);">\n    {cat_emoji} <strong>{cat_name}</strong> <span style="font-weight:400;font-size:0.75rem;color:var(--text-muted);">— {cat_desc}</span>\n</td></tr>\n'
        for a in ARQUETIPOS:
            if a.get("categoria") != cat_name:
                continue
            emoji = a["emoji"]
            nome = a["nome"]
            desc = a["descricao"]
            cor = a["cor"]
            legend_rows += f"""<tr>
    <td class="arq-emoji">{emoji}</td>
    <td class="arq-name" style="color:{cor};">{nome}</td>
    <td class="arq-desc">{desc}</td>
</tr>"""
    body += f"""
<details class="accordion-section">
    <summary class="accordion-summary">\U0001f4d6 Legenda dos Arqu\u00e9tipos <span class="accordion-hint">(clique para expandir)</span></summary>
    <div class="section" style="margin-top:0.5rem;">
        <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;padding:0 0.25rem;">
        {legend_intro}
        </div>
        <div class="card" style="overflow-x:auto;">
            <table class="legend-table">
                <thead><tr>
                    <th></th>
                    <th>Arqu\u00e9tipo</th>
                    <th>Descri\u00e7\u00e3o</th>
                </tr></thead>
                <tbody>
                {legend_rows}
                </tbody>
            </table>
        </div>
    </div>
</details>
"""

    # --- Gallery: one card per archetype ---
    body += _build_gallery(df)

    # --- Distribution ---
    dist_counts = df["arquetipo"].value_counts()
    dist_rows = ""
    max_cnt_val = int(dist_counts.max()) if not dist_counts.empty else 1
    for a in ARQUETIPOS:
        nome = a["nome"]
        cnt = int(dist_counts.get(nome, 0))
        if cnt == 0 and nome != "Indefinido":
            continue
        emoji = a["emoji"]
        cor = a["cor"]
        if cnt == 0 and nome == "Indefinido":
            continue
        pct = (cnt / max_cnt_val * 100) if max_cnt_val else 0
        pct = pct if pct >= 1 else 1
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

    return _page_frame(config, f"Arqu\u00e9tipos - {config.report_title}", body, active_nav="arquetipos.html")


def _build_geo_section(df: pd.DataFrame) -> str:
    """Build Perfil Global section — one card per continent with player list."""
    if "perfil_global" not in df.columns:
        return ""
    df_geo = df[df["perfil_global"].notna() & (df["perfil_global"] != "")].copy()
    if df_geo.empty:
        return ""

    html = '<div class="section">\n'
    html += '    <div class="section-title">\U0001f30d Perfil Global</div>\n'
    html += '    <div style="font-size:0.75rem;color:var(--text-muted);margin-bottom:0.5rem;padding:0 0.25rem;">\n'
    html += '    <strong>Em qual continente cada jogador mais se destaca?</strong> '
    html += 'Comparamos os pontos de cada jogador \u00e0 m\u00e9dia do bol\u00e3o '
    html += 'naquele continente. O Perfil Global \u00e9 o continente onde o jogador tem o <strong>melhor desempenho relativo</strong> '
    html += '(maior z-score), mesmo que esse desempenho esteja abaixo da m\u00e9dia geral '
    html += '\u2014 s\u00e3o os jogadores que aparecem com a barrinha <span style="color:#f59e0b;">\u25a0 laranja</span>. '
    html += 'Usamos os pontos reais de cada partida (placar exato, vencedor, etc.). '
    html += 'S\u00f3 consideramos continentes com <strong>m\u00ednimo 2 sele\u00e7\u00f5es</strong> diferentes por jogador.\n'
    html += '    <br><br>\n'
    html += '    <strong>Exemplo:</strong> se um jogador faz <strong>50 pts em 6 sele\u00e7\u00f5es europeias</strong> '
    html += '(m\u00e9dia 8,3) e a m\u00e9dia geral do bol\u00e3o na Europa \u00e9 5,0 pts/sel, '
    html += 'ele est\u00e1 acima da m\u00e9dia (barrinha <span style="color:#10b981;">\u25a0 verde</span>). '
    html += 'Se em todos os continentes ele estiver abaixo da m\u00e9dia, o Perfil Global \u00e9 o continente '
    html += 'onde ele fica <strong>menos abaixo</strong> da m\u00e9dia (barrinha <span style="color:#f59e0b;">\u25a0 laranja</span>).\n'
    html += '    </div>\n'

    for geo_key in GEO_ORDER:
        emoji = GEO_EMOJI.get(geo_key, "\U0001f30d")
        nome = GEO_NOME.get(geo_key, geo_key)
        df_cont = df_geo[df_geo["perfil_global"] == geo_key].sort_values("global_score", ascending=False)
        if df_cont.empty:
            continue
        count = len(df_cont)
        players_html = ""
        for _, r in df_cont.iterrows():
            nome_jog = str(r["boleiro"])
            pts = int(r.get("global_correct", 0))
            nteams = int(r.get("global_teams", 0))
            avg = pts / nteams if nteams else 0
            score_str = f"{pts} pts em {nteams} sel. (m\u00e9dia {avg:.1f})" if nteams else f"{pts} pts"
            score_str = score_str.replace(".", ",")
            gscore = int(r.get("global_score", 50))
            bar_w = max(2, min(100, gscore))
            bar_color = "#f59e0b" if gscore < 50 else "#10b981"
            bar_html = (
                f'<div class="geo-bar-wrap" title="z-score: {gscore-50}{" (acima da m\u00e9dia)" if gscore>=50 else " (abaixo da m\u00e9dia)"}">'
                f'<div class="geo-bar-track">'
                f'<div class="geo-bar-mid"></div>'
                f'<div class="geo-bar-fill" style="width:{bar_w}%;background:{bar_color};"></div>'
                f'</div>'
                f'</div>'
            )
            players_html += (
                f'<div class="geo-player">'
                f'<span class="geo-player-name"><a href="boleiros/{nome_jog}.html">{nome_jog}</a></span>'
                f'{bar_html}'
                f'<span class="geo-score">{score_str}</span>'
                f'</div>\n'
            )
        count_label = f"{count} jogador" + ("es" if count != 1 else "")
        html += f"""
<div class="geo-card">
    <div class="geo-title">{emoji} {nome} <span class="geo-count">{count_label}</span></div>
    <div class="geo-players">{players_html}</div>
</div>
"""
    html += '</div>\n'
    return html


def _build_gallery(df: pd.DataFrame) -> str:
    """Build gallery: one card per archetype, listing players inside."""
    # Group players by archetype
    gal_groups: dict[str, list[dict]] = {}
    for _, r in df.iterrows():
        arq = str(r["arquetipo"])
        if arq not in gal_groups:
            gal_groups[arq] = []
        gal_groups[arq].append(r.to_dict())

    html = '<div class="section">\n'
    html += '    <div class="section-title">\U0001f465 Galeria por Arqu\u00e9tipo</div>\n'

    # Order: Categorias order, then Indefinido last
    seen_arqs: set[str] = set()
    for cat in CATEGORIAS:
        for a_def in ARQUETIPOS:
            nome = a_def["nome"]
            if nome not in gal_groups or nome in seen_arqs:
                continue
            if a_def.get("categoria") != cat["nome"]:
                continue
            seen_arqs.add(nome)
            html += _build_archetype_card(nome, gal_groups[nome], a_def)

    # Indefinido (if any)
    if "Indefinido" in gal_groups and "Indefinido" not in seen_arqs:
        a_def = ARQ_MAP.get("Indefinido", {})
        html += _build_archetype_card("Indefinido", gal_groups["Indefinido"], a_def)

    html += '</div>\n'
    return html


def _build_archetype_card(arq_name: str, players: list[dict], a_def: dict) -> str:
    """Build one archetype card with player rows sorted by score descending."""
    arq_emoji = a_def.get("emoji", "?")
    arq_cor = a_def.get("cor", "var(--text-muted)")
    arq_desc = a_def.get("descricao", "")
    count = len(players)

    # Sort players by score desc
    players_sorted = sorted(
        players,
        key=lambda r: -int(r.get("score_int", 0))
    )

    rows_html = ""
    for r in players_sorted:
        nome = str(r["boleiro"])
        score = int(r.get("score_int", 0))
        ru_arq = str(r.get("runner_up_arq", ""))
        ru_score = int(r.get("runner_up_score", 0))
        ru_html = f'<span class="runner-up">2\u00ba: {ru_arq} {ru_score}%</span>' if ru_arq else ""

        rows_html += f"""
<div class="player-row">
    <span class="player-name"><a href="boleiros/{nome}.html">{nome}</a></span>
    <span class="player-score">{score}%</span>
    {ru_html}
</div>"""

    return f"""
<div class="arq-card" style="--arq-color:{arq_cor};">
    <div class="arq-card-header">
        <span class="arq-emoji">{arq_emoji}</span>
        <span class="arq-title" style="color:{arq_cor};">{arq_name}</span>
        <span class="arq-count">{count} jogador{'es' if count != 1 else ''}</span>
    </div>
    <div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:0.3rem;">{arq_desc}</div>
    <div class="arq-card-body">{rows_html}</div>
</div>"""


# ------------------------------------------------------------------
# Page frame
# ------------------------------------------------------------------

def _page_frame(config: ChampionshipConfig, title: str, body: str, back_link: str = "", active_nav: str = "") -> str:
    """Replica of _page_frame to avoid circular imports."""
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
    script_src = nav_prefix + "sorttable.js" if back_link else "sorttable.js"
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
{_bottom_nav_html(active_nav, nav_prefix, config.nav_items)}
<script src="{script_src}"></script>
</body>
</html>"""


def build_arquetipos_page(config: ChampionshipConfig, html_base: str) -> None:
    """Generate arquetipos.html and save it."""
    path = _norm(os.path.join(html_base, "arquetipos.html"))
    print_colored("generating arquetipos.html", "blue")
    _save(path, _build_arquetipos(config))
