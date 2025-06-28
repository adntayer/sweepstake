# python -m src.services.transformers.load_excel
import pandas as pd


def parse_excel_1a_fase(path):
    who = path.split("-")[1].strip().replace(".xls", "")

    df = pd.read_excel(path, skiprows=2)

    df = df[df.columns[:9]]
    df.columns = [
        "date",
        "hour",
        "home_team",
        "home_pen",
        "home_goals",
        "x",
        "away_goals",
        "away_pen",
        "away_team",
    ]
    df.dropna(how="all", inplace=True)
    df["who"] = who
    df = df.loc[df["date"].notna()]
    df = df.loc[~df["date"].str.contains("GRUPO", na=False)]

    df_1a = df.head(48).copy()

    for col in ["home_goals", "home_pen", "away_goals", "away_pen"]:
        df_1a[col] = df_1a[col].astype(float)

    df_1a["date"] = pd.to_datetime(df_1a["date"]).dt.strftime("%Y-%m-%d")

    df_1a["match"] = (
        df_1a["home_team"].str.strip() + "-vs-" + df_1a["away_team"].str.strip()
    )
    df_1a["match"] = df_1a["match"].str.replace(" ", "_").str.lower()

    return df_1a


def parse_excel_palyoffs_full(path):
    who = path.split("-")[1].strip().replace(".xls", "")

    df = pd.read_excel(path, skiprows=2)

    df = df[df.columns[:9]]
    df.columns = [
        "date",
        "hour",
        "home_team",
        "home_pen",
        "home_goals",
        "x",
        "away_goals",
        "away_pen",
        "away_team",
    ]
    df.dropna(how="all", inplace=True)
    df["who"] = who
    df = df.loc[df["date"].notna()]
    df = df.loc[~df["date"].str.contains("GRUPO", na=False)]

    df_mm_oitavas = df.tail(19).head(8).copy()
    df_mm_oitavas["playoff"] = "oitavas"

    df_mm_quartas = df.tail(10).head(4).copy()
    df_mm_quartas["playoff"] = "quartas"

    df_mm_semi = df.tail(5).head(2).copy()
    df_mm_semi["playoff"] = "semi"

    df_mm_final = df.tail(2).head(1).copy()
    df_mm_final["playoff"] = "final"

    df_mm_striker = df.tail(1).copy()
    df_striker = df_mm_striker[["who", "home_team"]]
    df_striker.columns = ["boleiro", "striker"]

    df_playoff = pd.concat(
        [
            df_mm_oitavas,
            df_mm_quartas,
            df_mm_semi,
            df_mm_final,
        ],
        ignore_index=True,
    )
    for col in ["home_goals", "home_pen", "away_goals", "away_pen"]:
        df_playoff[col] = df_playoff[col].astype(float)

    df_playoff["date"] = pd.to_datetime(df_playoff["date"]).dt.strftime("%Y-%m-%d")

    return df_playoff, df_striker

def parse_excel_playoffs_oitavas(path):
    who = path.split("-")[1].strip().replace(".xls", "")

    df = pd.read_excel(path, skiprows=2)

    df = df[df.columns[:9]]
    df.columns = [
        "date",
        "hour",
        "home_team",
        "home_pen",
        "home_goals",
        "x",
        "away_goals",
        "away_pen",
        "away_team",
    ]
    df.dropna(how="all", inplace=True)
    df["who"] = who
    df = df.loc[df["date"].notna()]
    df['playoff'] = 'oitavas'
    df["match"] = (
        df["playoff"].str.strip() + "-" + df["home_team"].str.strip() + "-vs-" + df["away_team"].str.strip()
    )
    df["match"] = df["match"].str.replace(" ", "_").str.lower()

    return df


if __name__ == "__main__":
    import os

    parse_excel_palyoffs_full(
        os.path.join(
            "src",
            "a2025_club_world_cup",
            "data",
            "raw",
            "1afase",
            "Tabela Geral 2025 - André Tayer.xls",
        )
    )
