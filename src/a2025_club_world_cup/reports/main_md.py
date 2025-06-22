# python -m src.a2025_club_world_cup.reports.main_md
import os
from datetime import datetime

import pandas as pd
import pytz

from src.services.printing import print_colored

list_html_folder_paths = [
    os.path.join("src", "a2025_club_world_cup", "docs", "md"),
    os.path.join("src", "a2025_club_world_cup", "docs", "md", "boleiros"),
    os.path.join("src", "a2025_club_world_cup", "docs", "md", "jogos", "1afase"),
    os.path.join("src", "a2025_club_world_cup", "docs", "md", "jogos", "oitavas"),
    os.path.join("src", "a2025_club_world_cup", "docs", "md", "jogos", "quartas"),
    os.path.join("src", "a2025_club_world_cup", "docs", "md", "jogos", "semi"),
    os.path.join("src", "a2025_club_world_cup", "docs", "md", "jogos", "final"),
]
for path in list_html_folder_paths:
    os.makedirs(path, exist_ok=True)

PATH_CSV_GAMES = os.path.join("src", "a2025_club_world_cup", "data", "jogos_1afase.csv")
PATH_CSV_VALIDO_ALL = os.path.join(
    "src", "a2025_club_world_cup", "data", "gold", "1afase", "1afase_valido_all.csv"
)
PATH_CSV_ALL = os.path.join(
    "src", "a2025_club_world_cup", "data", "gold", "1afase", "1afase_all.csv"
)
PATH_CSV_STRIKER = os.path.join(
    "src",
    "a2025_club_world_cup",
    "data",
    "gold",
    "playoffs",
    "full",
    "playoffs_strikers.csv",
)
PATH_OVERVIEW = os.path.join("src", "a2025_club_world_cup", "docs", "md", "overview.md")


def main():
    os.makedirs(os.path.dirname(PATH_OVERVIEW), exist_ok=True)
    df = pd.read_csv(PATH_CSV_GAMES, sep=",")
    df_all = pd.read_csv(PATH_CSV_ALL, sep=",")
    df_all_valido = pd.read_csv(PATH_CSV_VALIDO_ALL, sep=",")

    list_desired_cols = [
        "date",
        "home_team",
        "home_goals",
        "x",
        "away_goals",
        "away_team",
    ]
    df = df[list_desired_cols]
    df.dropna(how="any", inplace=True)
    df.sort_values("date", ascending=False, inplace=True)

    df_rank = df_all.groupby("who", as_index=False)[
        [
            "pontos",
            "1-Placar exato",
            "2-Vencedor + gols de um time",
            "3-Vencedor correto",
            "4-Gols de um time",
            "5-Nenhum acerto",
        ]
    ].sum()
    df_rank.sort_values("pontos", ascending=False, inplace=True)
    df_rank.reset_index(inplace=True, drop=True)
    df_rank.reset_index(inplace=True)
    df_rank.rename(
        columns={"index": "#", "who": "boleiro", "pontos": "pontos"}, inplace=True
    )
    df_rank["#"] += 1

    df_points_by_dt = df_all_valido.groupby(["who", "date"], as_index=False).agg(
        {"pontos": "sum"}
    )
    df_points_by_dt["date"] = pd.to_datetime(df_points_by_dt["date"])
    last_dts = sorted(df_points_by_dt["date"].unique())[-5:]
    df_last = df_points_by_dt[df_points_by_dt["date"].isin(last_dts)]
    df_pivot = (
        df_last.pivot(index="who", columns="date", values="pontos")
        .fillna(0)
        .astype(int)
    )
    df_pivot.columns = [col.strftime("%d/%m") for col in df_pivot.columns]
    df_pivot["total_ult_dias"] = df_pivot.sum(axis=1)

    row_mean = df_pivot.mean(axis=0).to_frame().T.round(1)
    row_mean.index = ["média"]

    row_std = df_pivot.std(axis=0).to_frame().T.round(1)
    row_std.index = ["desv. pdr"]

    df_pivot.sort_values("total_ult_dias", ascending=False, inplace=True)
    df_pivot = pd.concat([df_pivot, row_mean, row_std])
    df_pivot.reset_index(inplace=True)
    df_pivot.rename(columns={"index": "boleiro"}, inplace=True)

    tz_sp = pytz.timezone("America/Sao_Paulo")
    now_sp = datetime.now(tz_sp).strftime("%d/%m/%Y %H:%M:%S")

    with open(PATH_OVERVIEW, "w", encoding="utf-8") as f:
        f.write("# Visão Geral dos Jogos - 1ª Fase\n\n")
        f.write(f"_atualizado às {now_sp}_\n\n")
        f.write("_último jogo que tem resultado_\n\n")
        f.write(df.head(1).to_markdown(index=False))
        f.write("\n\n")
        f.write("\n")
        f.write("\n---\n")
        f.write("## Ranking\n")
        f.write(df_rank.to_markdown(index=False))
        f.write("\n\n")
        f.write("## Últimos dias de pontuacao\n")
        f.write(df_pivot.to_markdown(index=False))
        f.write("\n\n")
        f.write("## últimos 6 jogos\n")
        df.columns = ["date", "casa", "gols", "x", "gols", "visitante"]
        f.write(df.head(6).to_markdown(index=False))
        f.write("\n")

    list_boleiros = list(df_all_valido["who"].unique())

    df_striker = pd.read_csv(PATH_CSV_STRIKER, sep=",")
    for boleiro in list_boleiros:
        print_colored(f"building boleiros md: {boleiro}", "blue")
        df_bol = df_all_valido.loc[df_all_valido["who"] == boleiro]
        df_striker_bol = df_striker.loc[df_striker["boleiro"] == boleiro]

        list_desired_cols = [
            "date",
            "hour",
            "home_team",
            "away_team",
            "resultado_bol_placar",
            "resultado_bol_time",
            "resultado_real_placar",
            "resultado_real_time",
            "pontos",
            "criterio",
            "match",
        ]
        df_bol = df_bol[list_desired_cols].sort_values(["date", "hour"], ascending=True)
        df_bol["pontos_acumulados"] = df_bol["pontos"].cumsum()
        df_bol.reset_index(inplace=True, drop=True)
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

        df_bol_stats = (
            df_bol.groupby("date")
            .agg({"match": "count", "pontos": ["sum", "mean", "std"]})
            .reset_index()
        )
        df_bol_stats.columns = ["date", "jogos", "pontos", "media", "desvio padrao"]
        df_bol_stats["pontos_acumulados"] = df_bol_stats["pontos"].cumsum()
        df_bol_stats = df_bol_stats.round(1)
        df_pivot = df_bol.pivot_table(
            index="date",
            columns="criterio",
            values="dummy",
            aggfunc="sum",
            fill_value=0,
        ).reset_index()
        df_bol_stats = df_bol_stats.merge(df_pivot, on="date")
        df_bol_stats.fillna(0, inplace=True)
        df_bol_stats = df_bol_stats.sort_values(["date"], ascending=False)
        df_bol.drop(columns=["dummy", "match"], inplace=True)
        path_bol_xray = os.path.join(
            "src", "a2025_club_world_cup", "docs", "md", "boleiros", f"{boleiro}.md"
        )

        df_bol["date"] = pd.to_datetime(df_bol["date"]).dt.strftime("%d.%b.%Y")
        df_bol_stats["date"] = pd.to_datetime(df_bol_stats["date"]).dt.strftime(
            "%d.%b.%Y"
        )
        with open(path_bol_xray, "w", encoding="utf-8") as f:
            f.write("# Visão Geral dos Jogos - 1ª Fase\n\n")
            f.write(f"# {boleiro}\n\n")
            f.write(f"_atualizado às {now_sp}_\n\n")
            f.write("## resumo\n\n")
            f.write(df_bol_stats.to_markdown(index=False))
            f.write("\n\n")
            f.write("## raio x\n\n")
            f.write(f"Artilheiro: **{df_striker_bol.iloc[0]['striker']}**\n\n")
            f.write(df_bol.to_markdown(index=False))
            f.write("\n")

    list_matches = list(df_all["match"].unique())

    for match in list_matches:
        print_colored(f"building jogos md: {match}", "blue")
        df_m = df_all.loc[df_all["match"] == match]

        list_desired_cols = [
            "date",
            "hour",
            "who",
            "home_team",
            "away_team",
            "pontos",
            "criterio",
            "resultado_bol_placar",
            "resultado_bol_time",
            "resultado_real_placar",
            "resultado_real_time",
        ]
        df_m = df_m[list_desired_cols].sort_values(["pontos", "who"], ascending=False)
        df_m.rename(columns={"who": "boleiro"}, inplace=True)

        df_pre_result_placar = (
            df_m[["resultado_bol_time", "resultado_bol_placar"]]
            .value_counts()
            .reset_index()
        )
        df_pre_result_placar.sort_values("resultado_bol_placar", inplace=True)
        df_pre_result_placar.columns = ["vencedor", "placar", "#"]
        df_pre_result_placar["pct"] = (
            round(df_pre_result_placar["#"] / df_pre_result_placar["#"].sum(), 2) * 100
        ).astype(int).astype(str) + " %"
        df_pre_result_placar["g"] = (
            (
                round(df_pre_result_placar["#"] / df_pre_result_placar["#"].sum(), 2)
                * 100
            )
            .astype(int)
            .apply(lambda x: ("█" * (x // 5)).ljust(20))
        )  # 1 barra por 5%

        df_pre_result_time = df_m["resultado_bol_time"].value_counts().reset_index()
        df_pre_result_time.columns = ["vencedor", "#"]
        df_pre_result_time["pct"] = (
            round(df_pre_result_time["#"] / df_pre_result_time["#"].sum(), 2) * 100
        ).astype(int).astype(str) + " %"
        df_pre_result_time["g"] = (
            (round(df_pre_result_time["#"] / df_pre_result_time["#"].sum(), 2) * 100)
            .astype(int)
            .apply(lambda x: ("█" * (x // 5)).ljust(20))
        )  # 1 barra por 5%

        df_pos = df_m["criterio"].value_counts().reset_index()
        df_pos.columns = ["criterio", "#"]
        df_pos.sort_values("criterio", inplace=True)
        df_pos["g"] = (
            (round(df_pos["#"] / df_pos["#"].sum(), 2) * 100)
            .astype(int)
            .apply(lambda x: ("█" * (x // 5)).ljust(20))
        )

        filename = f"{df_m.iloc[0]['date']}_{df_m.iloc[0]['hour']}_{match}.md"
        path_game_xray = os.path.join(
            "src", "a2025_club_world_cup", "docs", "md", "jogos", "1afase", filename
        )

        df_m["date"] = pd.to_datetime(df_m["date"]).dt.strftime("%d.%b.%Y")
        df_m.columns = [
            "date",
            "h",
            "boleiro",
            "casa",
            "visitante",
            "pontos",
            "criteiro",
            "bol_placar",
            "bol_time",
            "real_placar",
            "real_time",
        ]
        with open(path_game_xray, "w", encoding="utf-8") as f:
            f.write("# Visão Geral dos Jogos - 1ª Fase\n\n")
            f.write(f"# {match}\n\n")
            f.write(f"_atualizado às {now_sp}_\n\n")
            f.write("## pré jogo\n\n")
            f.write("### time\n\n")
            f.write(df_pre_result_time.to_markdown(index=False))
            f.write("\n\n")
            f.write("### placar\n\n")
            f.write(df_pre_result_placar.to_markdown(index=False))
            f.write("\n\n")
            f.write("## pós jogo\n\n")
            f.write(df_pos.to_markdown(index=False))
            f.write("\n\n")
            f.write("## raio x\n\n")
            f.write(df_m.to_markdown(index=False))


if __name__ == "__main__":
    main()
