# python -m src.a2025_club_world_cup.processing.raw_to_bronze
import os
import shutil
from glob import glob

import pandas as pd

from src.a2025_club_world_cup.processing.load_excel import (
    parse_excel_1a_fase,
    parse_excel_palyoffs_full,
)
from src.services.printing import print_colored


def main():
    core_path = os.path.join("src", "a2025_club_world_cup", "data", "bronze")
    if os.path.exists(core_path):
        shutil.rmtree(core_path)
        print_colored(
            f"Folder '{core_path}' and its contents deleted successfully.", "green"
        )
    else:
        print_colored(f"Folder '{core_path}' does not exist.", "gray")

    list_folder_paths = [
        core_path,
        os.path.join("src", "a2025_club_world_cup", "data", "bronze", "1afase"),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "bronze", "playoffs", "full", "games"
        ),
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "bronze",
            "playoffs",
            "full",
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "bronze", "playoffs", "oitavas"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "bronze", "playoffs", "quartas"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "bronze", "playoffs", "semi"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "bronze", "playoffs", "final"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "bronze", "playoffs", "striker"
        ),
    ]
    for path in list_folder_paths:
        os.makedirs(path, exist_ok=True)

    print_colored("raw to bronze", "sand")
    root_dir = os.path.join("src", "a2025_club_world_cup", "data", "raw", "1afase", "*")
    list_excel_paths = glob(root_dir, recursive=True)

    df_strikers = pd.DataFrame()
    for e, path_excel in enumerate(list_excel_paths, 1):
        print_colored(
            f"\t[{e:2}/{len(list_excel_paths)}] parsing excel {path_excel}", "ice"
        )
        df = parse_excel_1a_fase(path_excel)
        df_playoffs, df_striker = parse_excel_palyoffs_full(path_excel)
        who = df["who"].unique()[0]
        path_bronze_1afase = os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "bronze",
            "1afase",
            f"1afase_{who}.csv",
        )
        df.sort_values(by=["date", "hour"], inplace=True)
        df.to_csv(path_bronze_1afase, sep=",", decimal=".", index=False)

        path_bronze_playoffs_games = os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "bronze",
            "playoffs",
            "full",
            "games",
            f"playoffs_games_{who}.csv",
        )
        df_playoffs.sort_values(by=["date", "hour"], inplace=True)
        df_playoffs.to_csv(
            path_bronze_playoffs_games, sep=",", decimal=".", index=False
        )

        df_strikers = pd.concat([df_strikers, df_striker], ignore_index=True)
    path_bronze_playoffs_striker = os.path.join(
        "src",
        "a2025_club_world_cup",
        "data",
        "bronze",
        "playoffs",
        "full",
        "playoffs_strikers.csv",
    )
    df_strikers.sort_values(by=["boleiro"], inplace=True)
    df_strikers.to_csv(path_bronze_playoffs_striker, sep=",", decimal=".", index=False)
    print_colored("raw to bronze completed", "green")


if __name__ == "__main__":
    main()
