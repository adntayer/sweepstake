"""Generate Markdown reports from gold-layer data.

Produces:
  - overview.md (ranking, recent scores, last game)
  - Per-participant boleiros/<name>.md (X-ray analysis)
  - Per-match jogos/<phase>/<match>.md (prediction analysis)
"""

from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import pytz

from src.core.config import ChampionshipConfig
from src.services.printing import print_colored


def _norm(path: str) -> str:
    """Normalize a path to the current OS format."""
    return os.path.normpath(path)


def _ensure_dirs(config: ChampionshipConfig) -> None:
    """Create all report output directories."""
    base_md = _norm(os.path.join(config.reports_dir, "md"))
    dirs = [
        base_md,
        _norm(os.path.join(base_md, "boleiros")),
        _norm(os.path.join(base_md, "jogos", config.group_phase_label)),
    ]
    for pr in config.playoff_rounds:
        dirs.append(_norm(os.path.join(base_md, "jogos", pr.key)))
    for d in dirs:
        os.makedirs(d, exist_ok=True)


def _now_str(config: ChampionshipConfig) -> str:
    tz = pytz.timezone(config.timezone)
    return datetime.now(tz).strftime("%d/%m/%Y %H:%M:%S")


def _build_overview(config: ChampionshipConfig) -> None:
    """Generate overview.md."""
    df_results = pd.read_csv(config.results_file, sep=",")
    df_all = pd.read_csv(config.gold_all_path(), sep=",")
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")

    # Last game with result
    cols = ["date", "home_team", "home_goals", "x", "away_goals", "away_team"]
    df_games = df_results[cols].dropna(how="any").sort_values("date", ascending=False)

    # Ranking — only aggregate columns that actually exist in the gold CSV
    score_names = config.scoring_rule_names()
    agg_cols = ["pontos"] + [c for c in score_names if c in df_valid.columns]
    df_rank = df_valid.groupby("who", as_index=False)[agg_cols].sum()
    df_rank.sort_values("pontos", ascending=False, inplace=True)
    df_rank.reset_index(drop=True, inplace=True)
    df_rank.reset_index(inplace=True)
    df_rank.rename(columns={"index": "#", "who": "boleiro"}, inplace=True)
    df_rank["#"] += 1

    # Points by date (last 5 days)
    df_pts = df_valid.groupby(["who", "date"], as_index=False).agg({"pontos": "sum"})
    df_pts["date"] = pd.to_datetime(df_pts["date"])
    last_dts = sorted(df_pts["date"].unique())[-5:]
    df_last = df_pts[df_pts["date"].isin(last_dts)]
    df_pivot = (
        df_last.pivot(index="who", columns="date", values="pontos")
        .fillna(0)
        .astype(int)
    )
    df_pivot.columns = [c.strftime("%d/%m") for c in df_pivot.columns]
    df_pivot["total_ult_dias"] = df_pivot.sum(axis=1)

    row_mean = df_pivot.mean(axis=0).to_frame().T.round(1)
    row_mean.index = ["media"]
    row_std = df_pivot.std(axis=0).to_frame().T.round(1)
    row_std.index = ["desv. pdr"]

    df_pivot.sort_values("total_ult_dias", ascending=False, inplace=True)
    df_pivot = pd.concat([df_pivot, row_mean, row_std])
    df_pivot.reset_index(inplace=True)
    df_pivot.rename(columns={"index": "boleiro"}, inplace=True)

    now_str = _now_str(config)

    with open(config.overview_md_path(), "w", encoding="utf-8") as f:
        f.write(f"# Visao Geral dos Jogos - {config.group_phase_label}\n\n")
        f.write(f"_atualizado as {now_str}_\n\n")
        f.write("_ultimo jogo que tem resultado_\n\n")
        f.write(df_games.head(1).to_markdown(index=False))
        f.write("\n\n---\n")
        f.write("## Ranking\n")
        f.write(df_rank.to_markdown(index=False))
        f.write("\n\n## Ultimos dias de pontuacao\n")
        f.write(df_pivot.to_markdown(index=False))
        f.write("\n\n## ultimos 6 jogos\n")
        df_games.columns = ["date", "casa", "gols", "x", "gols", "visitante"]
        f.write(df_games.head(6).to_markdown(index=False))
        f.write("\n")


def _build_boleiro_reports(config: ChampionshipConfig) -> None:
    """Generate per-participant Markdown reports."""
    df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
    df_striker = pd.read_csv(config.playoff_strikers_path(), sep=",")
    now_str = _now_str(config)

    for boleiro in sorted(df_valid["who"].unique()):
        print_colored(f"building boleiros md: {boleiro}", "blue")
        df_bol = df_valid.loc[df_valid["who"] == boleiro].copy()
        df_striker_bol = df_striker.loc[df_striker["boleiro"] == boleiro]

        cols = [
            "date", "hour", "home_team", "away_team",
            "resultado_bol_placar", "resultado_bol_time",
            "resultado_real_placar", "resultado_real_time",
            "pontos", "criterio", "match",
        ]
        df_bol = df_bol[cols].sort_values(["date", "hour"], ascending=True)
        df_bol["pontos_acumulados"] = df_bol["pontos"].cumsum()
        df_bol.reset_index(drop=True, inplace=True)
        df_bol.reset_index(inplace=True)
        df_bol.rename(
            columns={
                "index": "#",
                "home_team": "casa",
                "away_team": "visitante",
                "resultado_bol_placar": "bolao_placar",
                "resultado_bol_time": "bolao_time",
                "resultado_real_placar": "real_placar",
                "resultado_real_time": "real_time",
            },
            inplace=True,
        )
        df_bol["#"] += 1
        df_bol = df_bol.sort_values(["date", "hour"], ascending=False)
        df_bol["dummy"] = 1

        # Stats per date
        df_stats = (
            df_bol.groupby("date")
            .agg({"match": "count", "pontos": ["sum", "mean", "std"]})
            .reset_index()
        )
        df_stats.columns = ["date", "jogos", "pontos", "media", "desvio padrao"]
        df_stats["pontos_acumulados"] = df_stats["pontos"].cumsum()
        df_stats = df_stats.round(1)

        # Pivot criteria per date
        df_pivot = df_bol.pivot_table(
            index="date", columns="criterio", values="dummy",
            aggfunc="sum", fill_value=0,
        ).reset_index()
        df_stats = df_stats.merge(df_pivot, on="date")
        df_stats.fillna(0, inplace=True)
        df_stats = df_stats.sort_values(["date"], ascending=False)

        df_bol.drop(columns=["dummy", "match"], inplace=True)
        df_bol["date"] = pd.to_datetime(df_bol["date"]).dt.strftime("%d.%b.%Y")
        df_stats["date"] = pd.to_datetime(df_stats["date"]).dt.strftime("%d.%b.%Y")

        path = _norm(os.path.join(
            config.reports_dir, "md", "boleiros", f"{boleiro}.md"
        ))
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Visao Geral dos Jogos - {config.group_phase_label}\n\n")
            f.write(f"# {boleiro}\n\n")
            f.write(f"_atualizado as {now_str}_\n\n")
            f.write("## resumo\n\n")
            f.write(df_stats.to_markdown(index=False))
            f.write("\n\n## raio x\n\n")
            striker_name = df_striker_bol.iloc[0]["striker"]
            f.write(f"Artilheiro: **{striker_name}**\n\n")
            f.write(df_bol.to_markdown(index=False))
            f.write("\n")


def _build_match_reports(config: ChampionshipConfig) -> None:
    """Generate per-match Markdown reports."""
    df_all = pd.read_csv(config.gold_all_path(), sep=",")
    now_str = _now_str(config)

    for match in sorted(df_all["match"].unique()):
        print_colored(f"building jogos md: {match}", "blue")
        df_m = df_all.loc[df_all["match"] == match].copy()

        cols = [
            "date", "hour", "who", "home_team", "away_team",
            "pontos", "criterio",
            "resultado_bol_placar", "resultado_bol_time",
            "resultado_real_placar", "resultado_real_time",
        ]
        df_m = df_m[cols].sort_values(["pontos", "who"], ascending=False)
        df_m.rename(columns={"who": "boleiro"}, inplace=True)

        # Pre-game: score distribution
        df_pre_placar = (
            df_m[["resultado_bol_time", "resultado_bol_placar"]]
            .value_counts()
            .reset_index()
        )
        df_pre_placar.sort_values("resultado_bol_placar", inplace=True)
        df_pre_placar.columns = ["vencedor", "placar", "#"]
        total = df_pre_placar["#"].sum()
        df_pre_placar["pct"] = (
            (round(df_pre_placar["#"] / total, 2) * 100)
            .astype(int).astype(str) + " %"
        )
        df_pre_placar["g"] = (
            (round(df_pre_placar["#"] / total, 2) * 100)
            .astype(int)
            .apply(lambda x: ("\u2588" * (x // 5)).ljust(20))
        )

        # Pre-game: team vote distribution
        df_pre_time = df_m["resultado_bol_time"].value_counts().reset_index()
        df_pre_time.columns = ["vencedor", "#"]
        total_t = df_pre_time["#"].sum()
        df_pre_time["pct"] = (
            (round(df_pre_time["#"] / total_t, 2) * 100)
            .astype(int).astype(str) + " %"
        )
        df_pre_time["g"] = (
            (round(df_pre_time["#"] / total_t, 2) * 100)
            .astype(int)
            .apply(lambda x: ("\u2588" * (x // 5)).ljust(20))
        )

        # Post-game: criteria distribution
        df_post = df_m["criterio"].value_counts().reset_index()
        df_post.columns = ["criterio", "#"]
        df_post.sort_values("criterio", inplace=True)
        total_c = df_post["#"].sum()
        df_post["g"] = (
            (round(df_post["#"] / total_c, 2) * 100)
            .astype(int)
            .apply(lambda x: ("\u2588" * (x // 5)).ljust(20))
        )

        filename = f"{df_m.iloc[0]['date']}_{df_m.iloc[0]['hour']}_{match}.md"
        path = _norm(os.path.join(
            config.reports_dir, "md", "jogos", config.group_phase_label, filename
        ))

        df_m["date"] = pd.to_datetime(df_m["date"]).dt.strftime("%d.%b.%Y")
        df_m.columns = [
            "date", "h", "boleiro", "casa", "visitante",
            "pontos", "criteiro", "bol_placar", "bol_time",
            "real_placar", "real_time",
        ]

        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Visao Geral dos Jogos - {config.group_phase_label}\n\n")
            f.write(f"# {match}\n\n")
            f.write("## pre jogo\n\n")
            f.write("### time\n\n")
            f.write(df_pre_time.to_markdown(index=False))
            f.write("\n\n### placar\n\n")
            f.write(df_pre_placar.to_markdown(index=False))
            f.write("\n\n## pos jogo\n\n")
            f.write(df_post.to_markdown(index=False))
            f.write("\n\n## raio x\n\n")
            f.write(df_m.to_markdown(index=False))


def generate_markdown_reports(config: ChampionshipConfig) -> None:
    """Generate all Markdown reports."""
    _ensure_dirs(config)
    _build_overview(config)
    _build_boleiro_reports(config)
    _build_match_reports(config)
