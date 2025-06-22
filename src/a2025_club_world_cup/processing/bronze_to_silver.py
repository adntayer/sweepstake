# python -m src.a2025_club_world_cup.processing.bronze_to_silver
import os
from glob import glob

import pandas as pd

from src.services.printing import print_colored


def main():
    print_colored("bronze to silver", "sand")
    list_folder_paths = [
        os.path.join("src", "a2025_club_world_cup", "data", "silver"),
        os.path.join("src", "a2025_club_world_cup", "data", "silver", "1afase"),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "silver", "playoffs", "full", "games"
        ),
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "silver",
            "playoffs",
            "full",
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "silver", "playoffs", "oitavas"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "silver", "playoffs", "quartas"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "silver", "playoffs", "semi"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "silver", "playoffs", "final"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "silver", "playoffs", "striker"
        ),
    ]
    for path in list_folder_paths:
        os.makedirs(path, exist_ok=True)

    list_csvs = glob(
        os.path.join("src", "a2025_club_world_cup", "data", "bronze", "1afase", "*"),
        recursive=True,
    )
    df_games = pd.read_csv(
        os.path.join("src", "a2025_club_world_cup", "data", "jogos_1afase.csv"), sep=","
    )

    for path_csv in list_csvs:
        df_boleiro = pd.read_csv(path_csv, sep=",")
        df_merge = df_boleiro.merge(df_games, on="match", suffixes=("_bol", "_real"))
        df_merge[["pontos", "criterio", "valido"]] = df_merge.apply(
            lambda row: handle_results(row), axis=1
        )
        df_merge.rename(
            columns={
                "date_bol": "date",
                "match_bol": "match",
                "home_team_bol": "home_team",
                "away_team_bol": "away_team",
            },
            inplace=True,
        )
        df_merge["resultado_bol_placar"] = (
            df_merge["home_goals_bol"].astype("Int64").astype(str)
            + " x "
            + df_merge["away_goals_bol"].astype("Int64").astype(str)
        )
        df_merge["resultado_bol_time"] = df_merge.apply(
            lambda row: row["home_team"]
            if row["home_goals_bol"] > row["away_goals_bol"]
            else row["away_team"]
            if row["away_goals_bol"] > row["home_goals_bol"]
            else "empate",
            axis=1,
        )

        df_merge["resultado_real_placar"] = (
            df_merge["home_goals_real"].astype("Int64").astype(str)
            + " x "
            + df_merge["away_goals_real"].astype("Int64").astype(str)
        )
        df_merge["resultado_real_time"] = df_merge.apply(
            lambda row: row["home_team"]
            if row["home_goals_real"] > row["away_goals_real"]
            else row["away_team"]
            if row["away_goals_real"] > row["home_goals_real"]
            else "empate",
            axis=1,
        )
        df_merge = df_merge.reindex(
            columns=[
                "date",
                "hour",
                "match",
                "home_team",
                "away_team",
                "resultado_bol_placar",
                "resultado_bol_time",
                "resultado_real_placar",
                "resultado_real_time",
                "criterio",
                "pontos",
                "valido",
                "who",
            ]
        )
        df_merge.sort_values(by=["date", "hour"], inplace=True)
        os.makedirs(
            os.path.join("src", "a2025_club_world_cup", "data", "silver", "1afase"),
            exist_ok=True,
        )
        who = df_merge["who"].iloc[0]
        output_path = os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "silver",
            "1afase",
            f"1afase_{who}.csv",
        )
        df_merge.to_csv(output_path, sep=",", decimal=".", index=False)

    df_playoff_pre_full = pd.DataFrame()
    list_csvs_playoffs = glob(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "bronze",
            "playoffs",
            "full",
            "games",
            "*",
        ),
        recursive=True,
    )
    for path_playoffs in list_csvs_playoffs:
        df_playoff_pre = pd.read_csv(path_playoffs, sep=",")
        df_playoff_loop = pd.concat(
            [
                df_playoff_pre[["home_team", "who", "playoff"]].rename(
                    columns={"home_team": "team"}
                ),
                df_playoff_pre[["away_team", "who", "playoff"]].rename(
                    columns={"away_team": "team"}
                ),
            ],
            ignore_index=True,
        )
        df_playoff_pre_full = pd.concat(
            [df_playoff_pre_full, df_playoff_loop], ignore_index=True
        )
    df_playoff_pre_full.sort_values(["who", "playoff", "team"], inplace=True)
    output_path = os.path.join(
        "src",
        "a2025_club_world_cup",
        "data",
        "silver",
        "playoffs",
        "full",
        "games",
        "playoff_full_games.csv",
    )
    df_playoff_pre_full.to_csv(output_path, sep=",", decimal=".", index=False)

    df_striker = pd.read_csv(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "bronze",
            "playoffs",
            "full",
            "playoffs_strikers.csv",
        ),
        sep=",",
    )
    output_path = os.path.join(
        "src",
        "a2025_club_world_cup",
        "data",
        "silver",
        "playoffs",
        "full",
        "playoffs_strikers.csv",
    )
    df_striker.to_csv(output_path, sep=",", decimal=".", index=False)
    print_colored("bronze to silver completed", "green")


def handle_results(row):
    # Palpite
    home_pred = row["home_goals_bol"]
    away_pred = row["away_goals_bol"]

    # Resultado real
    home_real = row["home_goals_real"]
    away_real = row["away_goals_real"]

    # Checagem de dados ausentes
    if (
        pd.isna(home_pred)
        or pd.isna(away_pred)
        or pd.isna(home_real)
        or pd.isna(away_real)
    ):
        return pd.Series([0, "9-Sem jogo", 0])

    # 1. Placar exato
    if home_pred == home_real and away_pred == away_real:
        return pd.Series([12, "1-Placar exato", 1])

    # Determina vencedores
    def get_winner(home, away):
        if home > away:
            return "home"
        if away > home:
            return "away"
        return "draw"

    pred_winner = get_winner(home_pred, away_pred)
    real_winner = get_winner(home_real, away_real)

    # 2. Vencedor + gols de um time
    if pred_winner == real_winner and (
        home_pred == home_real or away_pred == away_real
    ):
        return pd.Series([7, "2-Vencedor + gols de um time", 1])

    # 3. Vencedor correto
    if pred_winner == real_winner:
        return pd.Series([5, "3-Vencedor correto", 1])

    # 4. Gols de um time
    if home_pred == home_real or away_pred == away_real:
        return pd.Series([1, "4-Gols de um time", 1])

    # 5. Nenhum acerto
    return pd.Series([0, "5-Nenhum acerto", 1])


if __name__ == "__main__":
    main()
