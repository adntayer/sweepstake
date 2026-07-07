# Sweepstake — Data Vault 2.0 Architecture

## Overview

Three-layer Medallion architecture with **Data Vault 2.0** at Silver and **One Big Tables (OBTs)** at Gold.  
Zero on-the-fly calculation in the backend — everything is pre-computed at pipeline time.

```
Bronze (CSV imutável) ──→ Silver (Data Vault Parquet) ──→ Gold (OBT Parquet)
     raw Excel                  hubs / links / sats           one big tables
```

---

## Layer Architecture

### Bronze (`bronze/`) — Raw Immutable Data

| Path | Content |
|------|---------|
| `bronze/first_round/group_phase_{boleiro}.csv` | Player predictions (group stage) |
| `bronze/first_round/bonus_teams_{boleiro}.csv` | Player's knockout team picks |
| `bronze/first_round/striker_{boleiro}.csv` | Player's top scorer pick |
| `bronze/playoffs/group_phase_{phase}_{boleiro}.csv` | Per-round playoff predictions |
| `{base_dir}/games.csv` | Official match results (single source of truth) |

**Source**: Raw Excel files parsed by `run_raw_to_bronze()` in `src/core/pipeline.py`.  
**Storage**: CSV (immutable, never overwritten after creation).

### Silver (`silver/`) — Data Vault 2.0 Parquet

Three sub-layers with classic Data Vault columns:

#### Hubs (`silver/hubs/*.parquet`)

Business keys only — the "who" of the data.

| Hub | Business Key | Description |
|-----|-------------|-------------|
| `hub_jogador` | `boleiro_name` | Every player in the pool |
| `hub_partida` | `match_slug` | Every unique match |
| `hub_time` | `team_name` | Every team (Portuguese name) |
| `hub_fase` | `phase_key` | Every tournament phase (grupo, oitavas, etc.) |
| `hub_campeonato` | `championship_id` | The championship itself |

**Columns**: `{hub}_hk` (MD5 hash, PK), `{business_key}`, `load_date`, `record_source`.

#### Links (`silver/links/*.parquet`)

Associations between hubs — the "what happened".

| Link | Hub FKs | Description |
|------|---------|-------------|
| `link_palpite` | `jogador_hk` → `partida_hk` | A player bet on a match |
| `link_partida_times` | `partida_hk` → `time_hk` (×2: home + away) | Teams involved in a match |
| `link_bonus_time` | `jogador_hk` → `time_hk` → `fase_hk` → `campeonato_hk` | Player's bonus team pick for a phase |
| `link_artilheiro` | `jogador_hk` → `time_hk` → `campeonato_hk` | Player's top scorer pick |

**Columns**: `{link}_hk` (MD5 hash, PK), hub FKs, `load_date`, `record_source`.

#### Satellites (`silver/satellites/*.parquet`)

Descriptive attributes — the "how, when, what score".

| Satellite | Parent FK | Key Attributes |
|-----------|-----------|----------------|
| `sat_partida` | `partida_hk` | `date_pred`, `hour_pred`, `home_team`, `away_team` |
| `sat_palpite` | `link_palpite_hk` | Goals predicted, real goals, scoring, penalty info |
| `sat_jogador` | `jogador_hk` | Display name, penalties |
| `sat_time` | `time_hk` | Team name variants |
| `sat_fase` | `fase_hk` | Phase name, emoji, round labels |

**Columns**: `{parent}_hk` (FK), `load_date` (PK component), `hash_diff`, `record_source`, attributes.

#### DV Column Conventions

| Column | Description |
|--------|-------------|
| `{hub}_hk` | MD5 hash (32 hex chars) — primary key |
| `load_date` | UTC ISO timestamp of when the row was loaded |
| `record_source` | Source system identifier (e.g. `BRONZE_CSV`, `GAMES_CSV`) |
| `hash_diff` | MD5 of all descriptive columns — change detection |

### Gold (`gold/`) — One Big Tables Parquet

All data pre-joined, pre-scored, analytics pre-computed.  
Reports read these directly — no calculation, no CSV.

#### OBTs (`gold/obt/*.parquet`)

| OBT | Content | Source |
|-----|---------|--------|
| `obt_palpites.parquet` | All predictions × results × scoring | Silver DV (sat_palpite + hubs) |
| `obt_bonus.parquet` | Knockout bonus team scoring | link_bonus_time + sat_fase |
| `obt_artilheiros.parquet` | Top scorer scoring | link_artilheiro + config |
| `obt_ranking_history.parquet` | Daily rank per player | Derived from obt_palpites |
| `obt_consistency.parquet` | Streaks + running averages | Derived from obt_palpites |
| `obt_boldness.parquet` | Goal prediction boldness index | Derived from obt_palpites |
| `obt_team_accuracy.parquet` | Winner/exact-score accuracy per team | Derived from obt_palpites |
| `obt_round_by_round.parquet` | Points per round + cumulative | Derived from obt_palpites |
| `obt_upsets.parquet` | Zebra match detection + predictors | Derived from obt_palpites |
| `obt_goal_error.parquet` | MAE per team per player | Derived from obt_palpites |
| `obt_group_standings.parquet` | Real tournament table | games.csv |
| `obt_prediction_timing.parquet` | Lead days from Excel mtime | filesystem |

#### OBT Column Conventions

- **Flat**: Denormalized, no hash keys, no DV columns.
- **Scored**: `pontos`, `criterio`, one-hot columns per scoring rule.
- **Named**: `boleiro_name`, `match_slug`, `team_name`, `phase_key`.

---

## Pipeline Flow

### Entry Point

```
run_pipeline(config, dv=True)     # src/core/pipeline.py
  ├── fetch_all_logos()           # Team logo cache
  ├── build_world_cup_csv()       # games.csv from source
  ├── run_raw_to_bronze()         # Excel → bronze CSVs
  ├── run_bronze_to_silver_dv()   # Bronze → Silver DV Parquet
  └── run_silver_to_gold_dv()     # Silver DV → Gold OBTs Parquet
```

### Silver Build (`run_bronze_to_silver_dv`)

```
1. build_all_hubs()               # Scan bronze CSVs + config for business keys
2. build_all_links(hubs)          # Read bronze CSVs, resolve hub FKs, build links
3. build_all_satellites(hubs, links)  # Attach attributes to links
```

All outputs saved as Parquet (zstd compression) to `silver/{hubs,links,satellites}/`.

### Gold Build (`run_silver_to_gold_dv`)

```
1. build_obt_palpites()           # Join links + satellites, score every prediction
2. build_obt_bonus()              # Score knockout bonus picks
3. build_obt_artilheiros()        # Score top scorer picks
4. build_obt_ranking_history()    # Daily cumulative ranks
5. build_obt_consistency()        # Streaks + running avg
6. build_obt_boldness()           # Goal bias vs bolão average
7. build_obt_team_accuracy()      # Per-team accuracy
8. build_obt_round_by_round()     # Round-level aggregation
9. build_obt_upsets()             # Zebra detection
10. build_obt_goal_error()        # MAE per team
11. build_obt_group_standings()   # Real tournament table
12. build_obt_prediction_timing() # Lead days
```

All OBTs saved as Parquet (zstd) to `gold/obt/`.

---

## Reports Layer

Reports read OBT parquets directly via `config.load_gold_dataframe("obt_*")`.

| Report File | Function | Key OBTs Used |
|-------------|----------|---------------|
| `index.html` | - | obt_palpites, obt_bonus |
| `bolao_xray.html` | `build_bolao_xray_page()` | obt_palpites |
| `times.html` | `build_all_team_pages()` | obt_palpites |
| `zebras.html` | `build_zebra_page()` | obt_upsets |
| `palpites.html` | `build_match_pages()` | obt_palpites |
| `boleiros/` | `_build_boleiro()` | obt_palpites, obt_bonus |
| `jogos/` | `build_match_pages()` | obt_palpites |
| `arquetipos.html` | `build_arquetipos_page()` | obt_palpites, obt_boldness, obt_upsets |
| `grupos.html` | `build_group_standings_page()` | obt_group_standings |

Utility loading via `src/core/reports/utils.py`:
- `load_obt(config, "obt_*")` — direct parquet load
- `load_obt_palpites(config)` — pre-filtered valid predictions

---

## Configuration-Driven

Every championship is defined by a YAML config (`config/*.yaml`).  
Same pipeline code works for any tournament.

```yaml
# Example: config/copa_2026.yaml
id: copa_2026
name: Copa do Mundo 2026
timezone: America/Sao_Paulo
group_phase_label: 1afase
scoring_rules:
  - name: "1-Placar exato"
    points: 12
emoji: "\U0001f3c6"
teams: [...]
groups: [...]
playoff_rounds: [...]
boleiros: {...}
```

Config paths (`ChampionshipConfig`): `src/core/config.py`.

---

## Key Design Principles

1. **Immutability**: Bronze is never modified after creation.
2. **Determinism**: All DV hash keys are deterministic MD5 — same input always produces same hash.
3. **Separation**: Hubs (who), Links (what), Satellites (how) are physically separated.
4. **Pre-computation**: Gold OBTs contain everything needed for display. No scoring or aggregation at query time.
5. **Column lineage**: Every DV row tracks its `load_date` and `record_source`.
6. **Change tracking**: Satellite `hash_diff` enables natural type-2 historization.
7. **No CSV in reports**: Reports read only Parquet OBTs. Bronze CSVs are never read by reports.

---

## File Map

```
src/
├── core/
│   ├── config.py              # ChampionshipConfig → all paths, helpers
│   ├── datavault.py            # Hubs/Links/Sats builders, OBT builders, orchestrators
│   ├── pipeline.py             # run_pipeline entry point + legacy CSV pipeline
│   ├── loader.py               # Raw Excel parser
│   ├── scoring.py              # Prediction scoring engine
│   └── reports/
│       ├── html.py             # Per-player + match HTML pages (4656 lines)
│       ├── new_views.py        # All collective report pages
│       ├── arquetipos.py       # Player archetype classification
│       ├── dashboard.py        # Streamlit dashboard
│       └── utils.py            # OBT load helpers
data/
├── {championship_id}/
│   ├── raw/                    # Original Excel files
│   ├── bronze/                 # Parsed CSV (immutable)
│   ├── silver/                 # Data Vault parquet
│   │   ├── hubs/               # hub_*.parquet
│   │   ├── links/              # link_*.parquet
│   │   └── satellites/         # sat_*.parquet
│   └── gold/
│       └── obt/                # obt_*.parquet
config/
└── *.yaml                      # Championship config files
```
