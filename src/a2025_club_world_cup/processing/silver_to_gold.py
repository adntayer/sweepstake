# python -m src.a2025_club_world_cup.processing.silver_to_gold
import os
from glob import glob

import pandas as pd

from src.services.printing import print_colored


def main():
    print_colored("silver to gold", "sand")
    list_folder_paths = [
        os.path.join("src", "a2025_club_world_cup", "data", "gold"),
        os.path.join("src", "a2025_club_world_cup", "data", "gold", "1afase"),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "gold", "playoffs", "full", "games"
        ),
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "gold",
            "playoffs",
            "full",
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "gold", "playoffs", "oitavas"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "gold", "playoffs", "quartas"
        ),
        os.path.join("src", "a2025_club_world_cup", "data", "gold", "playoffs", "semi"),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "gold", "playoffs", "final"
        ),
        os.path.join(
            "src", "a2025_club_world_cup", "data", "gold", "playoffs", "striker"
        ),
    ]
    for path in list_folder_paths:
        os.makedirs(path, exist_ok=True)

    list_csvs = glob(
        os.path.join("src", "a2025_club_world_cup", "data", "silver", "1afase", "*"),
        recursive=True,
    )
    df_all = pd.DataFrame()
    for path_csv in list_csvs:
        df = pd.read_csv(path_csv, sep=",")
        df_all = pd.concat([df_all, df], ignore_index=True)
        who = df["who"].iloc[0]
        os.makedirs(
            os.path.join(
                "src", "a2025_club_world_cup", "data", "gold", "1afase", "boleiros"
            ),
            exist_ok=True,
        )
        output_path_all = os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "gold",
            "1afase",
            "boleiros",
            f"1afase_all_{who}.csv",
        )
        output_path_valido = os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "gold",
            "1afase",
            "boleiros",
            f"1afase_valido_{who}.csv",
        )
        df_criterios_onehot = pd.get_dummies(df["criterio"])
        df = pd.concat([df, df_criterios_onehot], axis=1)
        df.to_csv(output_path_all, sep=",", decimal=".", index=False)
        df.query("valido==1").to_csv(
            output_path_valido, sep=",", decimal=".", index=False
        )

    who = "all"
    output_path_all = os.path.join(
        "src",
        "a2025_club_world_cup",
        "data",
        "gold",
        "1afase",
        f"1afase_{who}.csv",
    )
    output_path_valido = os.path.join(
        "src",
        "a2025_club_world_cup",
        "data",
        "gold",
        "1afase",
        f"1afase_valido_{who}.csv",
    )
    df_criterios_onehot = pd.get_dummies(df_all["criterio"])
    df_all = pd.concat([df_all, df_criterios_onehot], axis=1)
    df_all.to_csv(output_path_all, sep=",", decimal=".", index=False)
    df_all.query("valido==1").to_csv(
        output_path_valido, sep=",", decimal=".", index=False
    )

    df_playoffs = pd.read_csv(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "silver",
            "playoffs",
            "full",
            "games",
            "playoff_full_games.csv",
        ),
        sep=",",
    )
    df_playoffs.to_csv(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "gold",
            "playoffs",
            "full",
            "games",
            "playoff_full_games.csv",
        ),
        sep=",",
    )

    df_strikers = pd.read_csv(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "silver",
            "playoffs",
            "full",
            "playoffs_strikers.csv",
        ),
        sep=",",
    )
    df_strikers.to_csv(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "gold",
            "playoffs",
            "full",
            "playoffs_strikers.csv",
        ),
        sep=",",
    )
    print_colored("silver to gold completed", "green")


if __name__ == "__main__":
    main()
