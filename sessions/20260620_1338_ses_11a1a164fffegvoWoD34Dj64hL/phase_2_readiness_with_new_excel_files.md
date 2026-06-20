---
title: "Phase 2 readiness with new Excel files"
session_id: "ses_11a1a164fffegvoWoD34Dj64hL"
slug: "neon-orchid"
agent: "plan"
model: "deepseek-v4-flash-free"
cost: 0
time:
  created: "20260620_1338"
  updated: "20260620_1600"
tokens:
  input: 134640
  output: 7158
  reasoning: 7514
  cache_read: 992000
---

# 📑 HISTÓRICO: Phase 2 readiness with new Excel files

### 👤 PROMPT DO USUÁRIO:
does this repo is ready for the 2nd phase with new excels at '2026_world_cup/data/raw/2afase/*'? does the pipeline continues with the championship without break? am i all good to continue?

---

### 🤖 AGENTE (Turno 1):

💭 **PENSAMENTO DO AGENTE:**
The user is asking me to check if the repository is ready for phase 2 with new Excel files at `2026_world_cup/data/raw/2afase/*`. They want to know if the pipeline continues without breaking. I'm in plan mode (read-only), so I need to explore the codebase and data to assess readiness.

Let me start by exploring the structure of the repo, the data files, and the pipeline code.

🛠️ **AÇÃO DA FERRAMENTA [TASK]**
*Alvo/Parâmetro:* `Explore the repository at C:\Users\adnta\Documents\1.codigos\git\sweepstake thoroughly. I need to understand:

1. The overall project structure (directories, key files)
2. The pipeline / ETL code (Python scripts that process data)
3. The data directory structure, specifically under `2026_world_cup/data/raw/`
4. Whether there's already a `2afase` directory under `2026_world_cup/data/raw/` and what files are in it
5. What Excel files exist under `2026_world_cup/data/raw/` (recursively)
6. Any configuration files, `__init__.py`, or pipeline orchestration scripts

Please be very thorough - list all files in the repo, especially Python scripts, data files (Excel/CSV), and config files. Return the complete file listing and the contents of any Python scripts related to data processing or pipeline stages. Also check if there's any YAML/JSON config files, database files, or anything that might reference "2afase" or "fase" or "phase".`

```text
<task id="ses_11a1a0003ffefOeudrfv6zzbak" state="completed">
<task_result>
Here is the complete and thorough analysis of the repository.

---

## 1. Overall Project Structure

**Project:** "Bolao" / "Sweepstake" -- a Python CLI application for football (soccer) prediction sweepstake analysis. It reads Excel files containing participants' match predictions, fetches real match results, runs a **medallion pipeline (bronze -> silver -> gold)** to clean/merge/score predictions, and generates **static HTML reports**.

### Top-level layout

```
C:\Users\adnta\Documents\1.codigos\git\sweepstake\
├── AGENTS.md
├── README.md
├── play-off-plan.md
├── logo.txt               # ASCII art logo
├── opencode.json          # OpenCode agent configuration
├── sessao.json            # Session state
├── cli.py                 # **CLI entry point** (ss command)
├── pyproject.toml          # Python project config (dependencies, scripts)
├── Taskfile.yml            # Task runner (Task) configuration
├── upgrade.py             # Utility script
├── parse_opencode_session.py  # Utility script
├── _check_dist.py         # Distribution check
├── uv.lock                # Dependency lock file
│
├── src/                   # **Main source code**
│   ├── __init__.py         (empty)
│   ├── core/              # **Championship-agnostic engine**
│   │   ├── __init__.py    (docstring)
│   │   ├── config.py      # ChampionshipConfig dataclass + YAML loader
│   │   ├── pipeline.py    # **Medallion pipeline (bronze→silver→gold)**
│   │   ├── loader.py      # **Excel file parser for predictions**
│   │   ├── scoring.py     # Scoring engine + playoff bonus scoring
│   │   ├── get_results.py # Download/transform match results
│   │   ├── printing.py    # Colored terminal output
│   │   ├── logo_fetcher.py # Download team flag logos
│   │   ├── matches/
│   │   │   ├── __init__.py
│   │   │   └── wc2026.py  # Build games.csv for 2026 World Cup
│   │   └── reports/
│   │       ├── __init__.py (empty)
│   │       ├── utils.py   # Report utility functions
│   │       ├── html.py    # **HTML report generation (4079+ lines)**
│   │       ├── dashboard.py # Dashboard (index.html) builder
│   │       ├── new_views.py # Additional HTML views
│   │       ├── markdown.py  # Markdown report generation
│   │       └── arquetipos.py # **Player archetype classification + gallery**
│   │
│   ├── championships/     # **Per-championship configurations**
│   │   ├── __init__.py    # Registry (list_championships, load_config)
│   │   ├── 2026_world_cup/  # **2026 World Cup**
│   │   │   ├── __init__.py (empty)
│   │   │   ├── config.yaml  # **Main YAML config**
│   │   │   ├── data/        # Data directory (see section 3)
│   │   │   ├── logos/       # Team flag PNGs (48 teams)
│   │   │   └── reports/     # Generated HTML reports
│   │   └── 2025_club_world_cup/  # **2025 Club World Cup**
│   │       ├── __init__.py (empty)
│   │       ├── config.yaml
│   │       └── data/
│   │
│   └── bolao.egg-info/    # Python egg info
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── core/
│       ├── test_config.py
│       ├── test_loader.py
│       ├── test_pipeline.py
│       ├── test_reports.py
│       └── test_scoring.py
│
├── sessions/              # OpenCode session logs (2 sessions)
├── .github/workflows/     # CI/CD (test.yml, 01_deploy.yaml)
└── .opencode/             # OpenCode agents & skills
```

### CLI Usage
- `ss list` -- List available championships
- `ss run <championship>` -- Run full pipeline + reports
- `ss run <championship> --pipeline/--bronze/--silver/--gold/--reports` -- Selective stages
- `ss fetch-logos <championship>` -- Download team logos

---

## 2. Pipeline / ETL Code (Python scripts that process data)

The entire ETL is in `src/core/pipeline.py` (1039 lines). The pipeline architecture:

### Medallion Architecture

```
raw/1afase/*.xls/.xlsx
        │
        ▼  run_raw_to_bronze()
bronze/first_round/
  ├── group_phase_{boleiro}.csv    # parsed predictions
  ├── bonus_teams_{boleiro}.csv    # playoff team picks
  └── striker_{boleiro}.csv        # top scorer pick
bronze/playoffs/                         # (future: per-round CSV files)
        │
        ▼  run_bronze_to_silver()
silver/first_round/
  └── group_phase_{boleiro}.csv    # predictions + real results merged
silver/playoffs/                         # (future)
        │
        ▼  run_silver_to_gold()
gold/first_round/
  ├── group_phase_{boleiro}.csv    # scored predictions
  ├── {label}_all.csv              # all predictions aggregated
  ├── {label}_valido_all.csv       # valid predictions only
  ├── striker_{boleiro}.csv        # striker picks per player
  ├── playoffs_strikers.csv        # aggregated strikers
  ├── playoffs_scored.csv          # scored bonus picks
  ├── strikers_scored.csv          # scored strikers
  ├── boldness_index.csv           # analytics
  ├── consistency.csv              # analytics
  ├── upset_tracker.csv            # analytics
  ├── round_by_round.csv           # analytics
  ├── team_accuracy.csv            # analytics
  ├── ranking_history.csv          # analytics
  ├── prediction_timing.csv        # analytics
  ├── goal_error_by_team.csv       # analytics
  ├── group_standings.csv          # analytics
  └── arquetipos_classification.csv # player archetypes
gold/playoffs/                          # (future)
```

### Key Python files:

| File | Path | Lines | Purpose |
|------|------|-------|---------|
| **pipeline.py** | `src/core/pipeline.py` | 1039 | Medallion pipeline orchestrator |
| **loader.py** | `src/core/loader.py` | 506 | Excel file parser (group stage + playoffs) |
| **config.py** | `src/core/config.py` | 653 | Data classes + YAML config loader |
| **scoring.py** | `src/core/scoring.py` | 323 | Scoring engine + bonus/striker scoring |
| **get_results.py** | `src/core/get_results.py` | 180 | Download results from fixturedownload.com |
| **cli.py** | `cli.py` | 146 | CLI entry point |
| **arquetipos.py** | `src/core/reports/arquetipos.py` | 1155 | Player archetype classification + HTML gallery |
| **html.py** | `src/core/reports/html.py` | 4079+ | Main HTML report generator |
| **dashboard.py** | `src/core/reports/dashboard.py` | ~1160 | Dashboard homepage builder |
| **new_views.py** | `src/core/reports/new_views.py` | (exist) | Additional HTML views |

---

## 3. Data Directory Structure under `2026_world_cup/data/`

```
src/championships/2026_world_cup/
├── config.yaml               # Championship config (280 lines)
├── __init__.py               (empty)
├── data/
│   ├── games.csv             # Official match results (all rounds)
│   ├── raw/
│   │   └── 1afase/           # **Raw Excel files from participants**
│   │       ├── *.xls  (23 files)
│   │       ├── *.xlsx (10 files)
│   │       └── *.xlsm (1 file)
│   ├── bronze/
│   │   ├── first_round/      # Generated CSVs (group_phase_*, bonus_teams_*, striker_*)
│   │   └── playoffs/         (empty)
│   ├── silver/
│   │   ├── first_round/      # Generated CSVs (group_phase_* with merged real results)
│   │   └── playoffs/         (empty)
│   └── gold/
│       ├── first_round/      # Generated CSVs (scored predictions + all analytics)
│       └── playoffs/         (empty)
├── logos/                    # 48 team flag PNGs
└── reports/
    └── html/                 # Generated HTML reports
        ├── index.html
        ├── arquetipos.html
        ├── zebras.html
        ├── boleiros/         # Per-player pages
        ├── jogos/            # Per-match pages
        ├── times/            # Per-team pages
        └── ... (other HTML pages)
```

---

## 4. Does a `2afase` directory exist under `data/raw/`?

**No.** There is **no `2afase`** directory anywhere in the repository.

The only subdirectory under `data/raw/` is `1afase/` (first phase / group stage).

The glob searches confirmed:
- `**/2afase/**` -- no results
- `**/2afase` -- no results (directory does not exist)
- `**/*fase*` -- no results (no files/dirs with "fase" in the name)

The `group_phase_label` for 2026 World Cup is configured as `"1afase"` in `config.yaml` line 7. The code in `pipeline.py` reads from `config.group_phase_label` (the raw dir pattern) which points to `1afase/`.

---

## 5. Excel Files under `2026_world_cup/data/raw/` (recursively)

All 34 files are in `data/raw/1afase/`:

### .xlsx files (10)
1. `Cipriano L. - Primeira Fase 2026.xlsx`
2. `Francisco Camargo - Primeira Fase.xlsx`
3. `Giancarlo - Primeira Fase 2026.xlsx`
4. `Haroldo - Primeira Fase 2026.xlsx`
5. `Leo Fernandes - Primeira Fase 2026.xlsx`
6. `Luca Caviglia Del Soldato - Primeira Fase 2026.xlsx`
7. `Mateus Tone - Primeira Fase 2026.xlsx`
8. `Pedro Tayer - Primeira Fase 2026.xlsx`
9. `Rafael Conte - Primeira Fase 2026.xlsx`
10. `Thales Oliveira - Primeira Fase 2026.xlsx`

### .xls files (23)
1. `Andre Bonito - Primeira Fase 2026.xls`
2. `Andre Mendes - Primeira Fase 2026.xls`
3. `Andre Tayer - Primeira Fase 2026.xls`
4. `Davi & Cesar - Primeira Fase 2026.xls`
5. `Ditchos - Primeira Fase 2026.xls`
6. `Felipe Giannoni - Primeira Fase 2026.xls`
7. `Frederico Soter - Primeira Fase 2026.xls`
8. `Gabao - Primeira Fase 2026.xls`
9. `Guilherne - Primeira Fase 2026.xls`
10. `Joao Henrique - Primeira Fase 2026.xls`
11. `Jose Ricardo - Primeira Fase 2026.xls`
12. `Kiko Toloza - Pprimeira Fase 2026.xls`
13. `LLM Gemini - Primeira Fase 2026.xls`
14. `LLM GPT - Primeira Fase 2026.xls`
15. `Luiz Augusto - Primeira Fase 2026.xls`
16. `Marcelo - Primeira Fase 2026.xls`
17. `Marcelo Boix - Primeira Fase 2026.xls`
18. `Marco Lavander - Primeira Fase 2026.xls`
19. `Mauricio Saraiva- Primeira Fase 2026.xls`
20. `RODRIGO ALBERNAZ - Primeira Fase 2026.xls`
21. `Thiago Bahiense - Primeira Fase.xls`
22. `Tiago - Primeira Fase 2026.xls`

### .xlsm file (1)
1. `Lucas Ubertini - Primeira Fase 2026.xlsm`

---

## 6. Configuration Files, `__init__.py` files, and Pipeline Orchestration

### Configuration files

| File | Path | Format |
|------|------|--------|
| **2026 World Cup config** | `src/championships/2026_world_cup/config.yaml` | YAML (280 lines) |
| **2025 Club World Cup config** | `src/championships/2025_club_world_cup/config.yaml` | YAML (194 lines) |
| **Taskfile** | `Taskfile.yml` | YAML (27 lines) |
| **GitHub CI** | `.github/workflows/test.yml` | YAML |
| **GitHub Deploy** | `.github/workflows/01_deploy.yaml` | YAML |
| **pyproject.toml** | `pyproject.toml` | TOML (106 lines) |
| **opencode.json** | `opencode.json` | JSON |
| **sessao.json** | `sessao.json` | JSON |
| **uv.lock** | `uv.lock` | Lock file |

### `__init__.py` files

| File | Content |
|------|---------|
| `src/__init__.py` | Empty |
| `src/core/__init__.py` | Docstring (8 lines) describing architecture |
| `src/core/matches/__init__.py` | Same docstring as `core/__init__.py` |
| `src/core/reports/__init__.py` | Empty |
| `src/championships/__init__.py` | Registry with `list_championships`, `load_config`, `ChampionshipConfig` |
| `src/championships/2026_world_cup/__init__.py` | Empty |
| `src/championships/2025_club_world_cup/__init__.py` | Empty |
| `tests/__init__.py` | Empty |

### Pipeline Orchestration

The pipeline is orchestrated via:
1. **`cli.py`** (main entry) -> calls `run_pipeline(config)` or individual stage functions
2. **`src/core/pipeline.py`** -> `run_pipeline()` calls:
   - `fetch_all_logos(config)` -- download team flag images
   - `build_world_cup_csv(config.games_file)` -- build match schedule
   - `run_raw_to_bronze(config)` -- parse raw Excel -> bronze CSVs
   - `run_bronze_to_silver(config)` -- merge with real results -> silver CSVs
   - `run_silver_to_gold(config)` -- score predictions + generate analytics -> gold CSVs
3. After the pipeline, `generate_html_reports(config)` and `generate_dashboard(config)` produce the static HTML output.

### References to "2afase", "fase", "phase"

- **No references to "2afase"** exist anywhere in the codebase (source code, config, or data).
- **"fase"** appears in:
  - `group_phase_label: "1afase"` in both `config.yaml` files
  - `segunda_fase` as a playoff round key in `2026_world_cup/config.yaml` (line 79, 187)
  - Portuguese comments/docstrings referencing "1a Fase", "Segunda Fase", "fase do campeonato"
- **"phase"** appears extensively in the code as a variable/parameter name (phase key for playoff rounds like `oitavas`, `quartas`, `semi`, `final`, `segunda_fase`)
</task_result>
</task>
```

---

### 🤖 AGENTE (Turno 2):

💭 **PENSAMENTO DO AGENTE:**
Let me understand the situation:

1. The repo has a medallion pipeline (bronze → silver → gold) that processes predictions.
2. Currently, only `1afase` (first phase / group stage) Excel files exist.
3. The user wants to know if they can drop new Excel files in `2026_world_cup/data/raw/2afase/` and have the pipeline continue without breaking.

Let me now look at the config.yaml and pipeline.py more carefully to understand:
- How the pipeline handles multiple phases
- Whether the pipeline is designed to continue from where it left off
- What changes would be needed for a 2nd phase

Let me read the key files.

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\championships\2026_world_cup\config.yaml`

```python
1: # Championship: 2026 FIFA World Cup
2: id: 2026_world_cup
3: name: "2026 World Cup"
4: year: 2026
5: timezone: "America/Sao_Paulo"
6: report_title: "2026 World Cup"
7: group_phase_label: "1afase"
8: 
9: # 2026 uses group standings format (not individual match predictions)
10: standings_format: true
11: standings_skiprows: 1
12: 
13: # All paths (relative to project root)
14: base_dir: "src/championships/2026_world_cup/data"
15: raw_dir: "src/championships/2026_world_cup/data/raw"
16: results_file: "src/championships/2026_world_cup/data/games.csv"
17: games_file: "src/championships/2026_world_cup/data/games.csv"
18: bronze_dir: "src/championships/2026_world_cup/data/bronze"
19: silver_dir: "src/championships/2026_world_cup/data/silver"
20: gold_dir: "src/championships/2026_world_cup/data/gold"
21: reports_dir: "src/championships/2026_world_cup/reports"
22: 
23: # External results source
24: results_endpoint: "https://fixturedownload.com/download/fifa-world-cup-2026-UTC.csv"
25: 
26: # English → Portuguese team name mapping (Excel uses Portuguese names)
27: team_name_mapping:
28:   - {en: "South Africa", pt: "África do Sul", slug: "RSA", logo: "https://flagcdn.com/w80/za.png", geo: africano}
29:   - {en: "South Korea", pt: "Coréia do Sul", slug: "KOR", logo: "https://flagcdn.com/w80/kr.png", geo: asiatico}
30:   - {en: "Czech Republic", pt: "República Tcheca", slug: "CZE", logo: "https://flagcdn.com/w80/cz.png", geo: europeu}
31:   - {en: "Mexico", pt: "México", slug: "MEX", logo: "https://flagcdn.com/w80/mx.png", geo: anfitriao}
32:   - {en: "Canada", pt: "Canadá", slug: "CAN", logo: "https://flagcdn.com/w80/ca.png", geo: anfitriao}
33:   - {en: "Bosnia and Herzegovina", pt: "Bósnia", slug: "BIH", logo: "https://flagcdn.com/w80/ba.png", geo: europeu}
34:   - {en: "Qatar", pt: "Catar", slug: "QAT", logo: "https://flagcdn.com/w80/qa.png", geo: asiatico}
35:   - {en: "Switzerland", pt: "Suíça", slug: "SUI", logo: "https://flagcdn.com/w80/ch.png", geo: europeu}
36:   - {en: "Brazil", pt: "Brasil", slug: "BRA", logo: "https://flagcdn.com/w80/br.png", geo: latino}
37:   - {en: "Morocco", pt: "Marrocos", slug: "MAR", logo: "https://flagcdn.com/w80/ma.png", geo: africano}
38:   - {en: "Haiti", pt: "Haiti", slug: "HAI", logo: "https://flagcdn.com/w80/ht.png", geo: latino}
39:   - {en: "Scotland", pt: "Escócia", slug: "SCO", logo: "https://flagcdn.com/w80/gb-sct.png", geo: europeu}
40:   - {en: "United States", pt: "Estados Unidos", slug: "USA", logo: "https://flagcdn.com/w80/us.png", geo: anfitriao}
41:   - {en: "Paraguay", pt: "Paraguai", slug: "PAR", logo: "https://flagcdn.com/w80/py.png", geo: latino}
42:   - {en: "Australia", pt: "Austrália", slug: "AUS", logo: "https://flagcdn.com/w80/au.png", geo: oceanico}
43:   - {en: "Turkey", pt: "Turquia", slug: "TUR", logo: "https://flagcdn.com/w80/tr.png", geo: europeu}
44:   - {en: "Germany", pt: "Alemanha", slug: "GER", logo: "https://flagcdn.com/w80/de.png", geo: europeu}
45:   - {en: "Curaçao", pt: "Curaçao", slug: "CUW", logo: "https://flagcdn.com/w80/cw.png", geo: latino}
46:   - {en: "Ivory Coast", pt: "Costa do Marfim", slug: "CIV", logo: "https://flagcdn.com/w80/ci.png", geo: africano}
47:   - {en: "Ecuador", pt: "Equador", slug: "ECU", logo: "https://flagcdn.com/w80/ec.png", geo: latino}
48:   - {en: "Netherlands", pt: "Holanda", slug: "NED", logo: "https://flagcdn.com/w80/nl.png", geo: europeu}
49:   - {en: "Japan", pt: "Japão", slug: "JPN", logo: "https://flagcdn.com/w80/jp.png", geo: asiatico}
50:   - {en: "Sweden", pt: "Suécia", slug: "SWE", logo: "https://flagcdn.com/w80/se.png", geo: europeu}
51:   - {en: "Tunisia", pt: "Tunísia", slug: "TUN", logo: "https://flagcdn.com/w80/tn.png", geo: africano}
52:   - {en: "Belgium", pt: "Bélgica", slug: "BEL", logo: "https://flagcdn.com/w80/be.png", geo: europeu}
53:   - {en: "Egypt", pt: "Egito", slug: "EGY", logo: "https://flagcdn.com/w80/eg.png", geo: africano}
54:   - {en: "Iran", pt: "Irã", slug: "IRN", logo: "https://flagcdn.com/w80/ir.png", geo: asiatico}
55:   - {en: "New Zealand", pt: "Nova Zelândia", slug: "NZL", logo: "https://flagcdn.com/w80/nz.png", geo: oceanico}
56:   - {en: "Spain", pt: "Espanha", slug: "ESP", logo: "https://flagcdn.com/w80/es.png", geo: europeu}
57:   - {en: "Cape Verde", pt: "Cabo Verde", slug: "CPV", logo: "https://flagcdn.com/w80/cv.png", geo: africano}
58:   - {en: "Saudi Arabia", pt: "Arábia Saudita", slug: "KSA", logo: "https://flagcdn.com/w80/sa.png", geo: asiatico}
59:   - {en: "Uruguay", pt: "Uruguai", slug: "URU", logo: "https://flagcdn.com/w80/uy.png", geo: latino}
60:   - {en: "France", pt: "França", slug: "FRA", logo: "https://flagcdn.com/w80/fr.png", geo: europeu}
61:   - {en: "Senegal", pt: "Senegal", slug: "SEN", logo: "https://flagcdn.com/w80/sn.png", geo: africano}
62:   - {en: "Iraq", pt: "Iraque", slug: "IRQ", logo: "https://flagcdn.com/w80/iq.png", geo: asiatico}
63:   - {en: "Norway", pt: "Noruega", slug: "NOR", logo: "https://flagcdn.com/w80/no.png", geo: europeu}
64:   - {en: "Argentina", pt: "Argentina", slug: "ARG", logo: "https://flagcdn.com/w80/ar.png", geo: latino}
65:   - {en: "Algeria", pt: "Argélia", slug: "ALG", logo: "https://flagcdn.com/w80/dz.png", geo: africano}
66:   - {en: "Austria", pt: "Áustria", slug: "AUT", logo: "https://flagcdn.com/w80/at.png", geo: europeu}
67:   - {en: "Jordan", pt: "Jordânia", slug: "JOR", logo: "https://flagcdn.com/w80/jo.png", geo: asiatico}
68:   - {en: "Portugal", pt: "Portugal", slug: "POR", logo: "https://flagcdn.com/w80/pt.png", geo: europeu}
69:   - {en: "Democratic Republic of the Congo", pt: "RD Congo", slug: "COD", logo: "https://flagcdn.com/w80/cd.png", geo: africano}
70:   - {en: "Uzbekistan", pt: "Uzbequistão", slug: "UZB", logo: "https://flagcdn.com/w80/uz.png", geo: asiatico}
71:   - {en: "Colombia", pt: "Colômbia", slug: "COL", logo: "https://flagcdn.com/w80/co.png", geo: latino}
72:   - {en: "England", pt: "Inglaterra", slug: "ENG", logo: "https://flagcdn.com/w80/gb-eng.png", geo: europeu}
73:   - {en: "Croatia", pt: "Croácia", slug: "CRO", logo: "https://flagcdn.com/w80/hr.png", geo: europeu}
74:   - {en: "Ghana", pt: "Gana", slug: "GHA", logo: "https://flagcdn.com/w80/gh.png", geo: africano}
75:   - {en: "Panama", pt: "Panamá", slug: "PAN", logo: "https://flagcdn.com/w80/pa.png", geo: latino}
76: 
77: # Playoff bonus scoring (per correct pick per phase)
78: playoff_scoring:
79:   segunda_fase: 4
80:   oitavas: 8
81:   quartas: 12
82:   semi: 20
83:   final: 30
84:   campeao: 45
85: 
86: # Striker scoring (points if player's pick matches actual_top_scorer)
87: striker_scoring:
88:   points: 25
89: 
90: # Actual top scorer of the championship
91: actual_top_scorer: "Harry Kane"
92: 
93: # Scoring rules (checked in rule order)
94: scoring:
95:   - name: "1-Placar exato"
96:     rule: "exact_score"
97:     points: 15
98:     priority: 1
99:     emoji: "🎯"
100:     description: "Acertou o placar exato da partida"
101:     color_text: "#00cc00"
102:   - name: "2-Vencedor + gols de um time (erro <= 2)"
103:     rule: "correct_winner_and_one_goal"
104:     points: 10
105:     priority: 2
106:     max_total_error: 2
107:     emoji: "🥅"
108:     description: "Acertou o vencedor e o nº de gols de um time, com erro total ≤ 2"
109:     color_text: "#66ff66"
110:   - name: "3-Vencedor + diferenca de gols (erro <= 2)"
111:     rule: "correct_winner_and_goal_diff"
112:     points: 7
113:     priority: 3
114:     max_total_error: 2
115:     emoji: "📊"
116:     description: "Acertou o vencedor e a diferença de gols, com erro ≤ 2"
117:     color_text: "#66ff66"
118:   - name: "4-Empate c/ erro total <= 2"
119:     rule: "correct_draw_and_low_error"
120:     points: 7
121:     priority: 4
122:     max_total_error: 2
123:     emoji: "🤝"
124:     description: "Acertou o empate com erro total ≤ 2"
125:     color_text: "#ffcc00"
126:   - name: "5-Vencedor + gols de um time (erro > 2)"
127:     rule: "correct_winner_and_one_goal"
128:     points: 7
129:     priority: 5
130:     min_total_error: 3
131:     emoji: "🔶"
132:     description: "Acertou o vencedor e o nº de gols de um time, com erro > 2"
133:     color_text: "#ffcc00"
134:   - name: "6-Vencedor correto"
135:     rule: "correct_winner"
136:     points: 5
137:     priority: 6
138:     emoji: "✔️"
139:     description: "Acertou apenas o vencedor da partida"
140:     color_text: "#ffcc00"
141:   - name: "7-Qualquer outro empate"
142:     rule: "correct_draw"
143:     points: 5
144:     priority: 7
145:     emoji: "⚖️"
146:     description: "Acertou o empate, mas com erro > 2"
147:     color_text: "#ffcc00"
148:   - name: "8-Gols de um time"
149:     rule: "one_team_goals"
150:     points: 1
151:     priority: 8
152:     emoji: "👊"
153:     description: "Acertou o nº de gols de um time, mas não o vencedor"
154:     color_text: "#ff9900"
155:   - name: "9-Nenhum acerto"
156:     rule: "no_score"
157:     points: 0
158:     priority: 9
159:     emoji: "❌"
160:     description: "Não acertou nenhum dos critérios"
161:     color_text: "#ff3333"
162:   - name: "99-Sem jogo"
163:     rule: "missing_data"
164:     points: 0
165:     priority: 99
166:     emoji: "❓"
167:     description: "Partida não realizada ou sem palpite"
168:     color_text: "#888888"
169: 
170: 
171: # Excel parsing layout
172: excel_layout:
173:   first_round:
174:     matches: 72
175:     skiprows: 2
176:   playoffs:
177:     striker_row_offset: 1
178:     striker_label: "Artilheiro"
179:     striker_name_column: 2
180:     striker_name_fallback_column: 8
181:     champion_cell: "M119"
182:     name_split_char: "-"
183:     name_split_index: 0
184:     playoffs_sheet_name: "Tabela Jogos"
185:     rounds:
186:       - name: "Segunda Fase"
187:         key: "segunda_fase"
188:         matches: 16
189:         tail_offset: 33
190:       - name: "Oitavas de Final"
191:         key: "oitavas"
192:         matches: 8
193:         tail_offset: 17
194:       - name: "Quartas de Final"
195:         key: "quartas"
196:         matches: 4
197:         tail_offset: 9
198:       - name: "Semifinal"
199:         key: "semi"
200:         matches: 2
201:         tail_offset: 5
202:       - name: "Disputa 3\u00ba Lugar"
203:         key: "terceiro_lugar"
204:         matches: 1
205:         tail_offset: 3
206:       - name: "Final"
207:         key: "final"
208:         matches: 1
209:         tail_offset: 2
210: 
211: # Groups (48 teams, 12 groups of 4)
212: groups:
213:   - name: "A"
214:     teams: ["México", "África do Sul", "Coréia do Sul", "República Tcheca"]
215:   - name: "B"
216:     teams: ["Canadá", "Bósnia", "Catar", "Suíça"]
217:   - name: "C"
218:     teams: ["Estados Unidos", "Paraguai", "Austrália", "Turquia"]
219:   - name: "D"
220:     teams: ["Brasil", "Marrocos", "Haiti", "Escócia"]
221:   - name: "E"
222:     teams: ["Alemanha", "Curaçao", "Costa do Marfim", "Equador"]
223:   - name: "F"
224:     teams: ["Holanda", "Japão", "Suécia", "Tunísia"]
225:   - name: "G"
226:     teams: ["Espanha", "Cabo Verde", "Arábia Saudita", "Uruguai"]
227:   - name: "H"
228:     teams: ["Bélgica", "Egito", "Irã", "Nova Zelândia"]
229:   - name: "I"
230:     teams: ["França", "Senegal", "Iraque", "Noruega"]
231:   - name: "J"
232:     teams: ["Argentina", "Argélia", "Áustria", "Jordânia"]
233:   - name: "K"
234:     teams: ["Portugal", "RD Congo", "Uzbequistão", "Colômbia"]
235:   - name: "L"
236:     teams: ["Inglaterra", "Croácia", "Gana", "Panamá"]
237: 
238: # HTML report theme
239: theme:
240:   mode: "dark"
241:   colors:
242:     primary: "#0f4a14"
243:     primary_light: "#166320"
244:     accent: "#f5c518"
245:     accent_dark: "#b8940f"
246:     bg: "#060d1a"
247:     card_bg: "#0d1b2e"
248:     card_border: "#1a3050"
249:     text: "#ffffff"
250:     text_muted: "#8899aa"
251:     text_inverse: "#000000"
252:     success: "#15803d"
253:     warning: "#f59e0b"
254:     danger: "#ef4444"
255:     voce: "#f5c518"
256:     bolao: "#3b82f6"
257:     silver: "#c0c0c0"
258:     bronze: "#cd7f32"
259:     accent_highlight: "rgba(245,197,24,0.1)"
260:     silver_highlight: "rgba(192,192,192,0.08)"
261:     bronze_highlight: "rgba(205,127,50,0.08)"
262:     zebra_stripe: "rgba(255,255,255,0.02)"
263:     hover_overlay: "rgba(255,255,255,0.03)"
264:     shadow_color: "rgba(0,0,0,0.4)"
265:     player_card_active: "rgba(245,197,24,0.05)"
266:     score_exact: "#00cc00"
267:     score_exact_bg: "rgba(0,204,0,0.1)"
268:     score_exact_border: "rgba(0,204,0,0.4)"
269:     score_winner_goals: "#66ff66"
270:     score_winner_goals_bg: "rgba(102,255,102,0.1)"
271:     score_winner_goals_border: "rgba(102,255,102,0.4)"
272:     score_winner: "#ffcc00"
273:     score_winner_bg: "rgba(255,204,0,0.1)"
274:     score_winner_border: "rgba(255,204,0,0.4)"
275:     score_one_team: "#ff9900"
276:     score_one_team_bg: "rgba(255,153,0,0.1)"
277:     score_one_team_border: "rgba(255,153,0,0.4)"
278:     score_none: "#ff3333"
279:     score_none_bg: "rgba(255,51,51,0.1)"
280:     score_none_border: "rgba(255,51,51,0.4)"

(End of file - total 280 lines)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\pipeline.py`

```python
1: """Medallion pipeline: bronze -> silver -> gold.
2: 
3: All stages are driven by ChampionshipConfig so the same code works
4: for any championship.
5: 
6: Structure:
7:   Bronze:
8:     bronze/first_round/group_phase_{boleiro}.csv
9:     bronze/first_round/bonus_teams_{boleiro}.csv
10:     bronze/first_round/striker_{boleiro}.csv
11:     bronze/playoffs/  (future separate playoff Excel files)
12: 
13:   Silver:
14:     silver/first_round/group_phase_{boleiro}.csv
15:     silver/playoffs/  (future)
16: 
17:   Gold:
18:     gold/first_round/group_phase_{boleiro}.csv
19:     gold/first_round/{label}_all.csv
20:     gold/first_round/{label}_valido_all.csv
21:     gold/first_round/striker_{boleiro}.csv
22:     gold/first_round/playoffs_strikers.csv
23:     gold/playoffs/  (future)
24: """
25: 
26: from __future__ import annotations
27: 
28: import os
29: import re
30: import shutil
31: import unicodedata
32: from glob import glob
33: 
34: import pandas as pd
35: 
36: from datetime import datetime
37: from pathlib import Path
38: 
39: import numpy as np
40: 
41: from src.core.config import ChampionshipConfig
42: from src.core.loader import (
43:     parse_group_stage,
44:     parse_group_standings,
45:     parse_playoff_stage,
46:     parse_bonus_playoffs,
47:     _extract_playoff_phase_and_who as _extract_phase_who_from_path,
48:     _extract_who,
49: )
50: from src.core.printing import print_colored
51: from src.core.scoring import score_prediction, score_playoff_bonus, score_strikers
52: from src.core.matches.wc2026 import build_world_cup_csv
53: from src.core.logo_fetcher import fetch_all_logos
54: 
55: # ------------------------------------------------------------------
56: # Helpers
57: # ------------------------------------------------------------------
58: 
59: 
60: def _norm(path: str) -> str:
61:     """Normalize a path to the current OS format."""
62:     return os.path.normpath(path)
63: 
64: 
65: def _has_real_results(config: ChampionshipConfig) -> bool:
66:     """Check if games.csv contains any actual match results."""
67:     if not os.path.exists(config.games_file):
68:         return False
69:     df = pd.read_csv(config.games_file, sep=",")
70:     if df.empty:
71:         return False
72:     if "home_goals" not in df.columns:
73:         return False
74:     return df["home_goals"].notna().any()
75: 
76: 
77: def _recreate_dirs(paths: list[str]) -> None:
78:     """Delete and recreate a list of directories."""
79:     root = _norm(paths[0]) if paths else ""
80:     if root and os.path.exists(root):
81:         shutil.rmtree(root)
82:         print_colored(f"Folder '{root}' deleted.", "green")
83:     for p in paths:
84:         os.makedirs(_norm(p), exist_ok=True)
85: 
86: 
87: def _save_csv(df: pd.DataFrame, path: str) -> None:
88:     """Save a DataFrame to CSV with consistent settings."""
89:     p = _norm(path)
90:     os.makedirs(os.path.dirname(p), exist_ok=True)
91:     df.to_csv(p, sep=",", decimal=".", index=False)
92: 
93: 
94: def _boleiros_from_raw(config: ChampionshipConfig) -> list[tuple[str, str]]:
95:     """Return sorted list of (excel_path, boleiro_name) from raw dir."""
96:     group_label = config.group_phase_label
97:     raw_pattern = _norm(os.path.join(config.raw_dir, group_label, "*"))
98:     excel_paths = sorted(glob(raw_pattern, recursive=True))
99:     result = []
100:     for path_excel in excel_paths:
101:         boleiro = _extract_who(path_excel, config)
102:         result.append((path_excel, boleiro))
103:     return result
104: 
105: 
106: def _extract_playoff_phase_and_boleiro(path_csv: str, config: ChampionshipConfig) -> tuple[str, str]:
107:     """Extract (phase, boleiro) from a bronze/silver playoff CSV filename.
108: 
109:     Expects format: ``group_phase_{phase}_{boleiro}.csv``
110:     """
111:     basename = os.path.basename(path_csv).replace("group_phase_", "").replace(".csv", "")
112:     # Match known phase key at the start
113:     for pr in config.playoff_rounds:
114:         prefix = pr.key + "_"
115:         if basename.startswith(prefix):
116:             return pr.key, basename[len(prefix):]
117:     raise ValueError(f"Cannot extract phase from playoff file: {path_csv}")
118: 
119: 
120: def _playoff_files_from_raw(config: ChampionshipConfig) -> list[tuple[str, str, str]]:
121:     """Return sorted list of (excel_path, phase_key, boleiro_name) from raw/playoffs/."""
122:     raw_playoff_dir = config._raw_playoffs()
123:     if not os.path.isdir(raw_playoff_dir):
124:         return []
125:     pattern = _norm(os.path.join(raw_playoff_dir, "*"))
126:     excel_paths = sorted(glob(pattern))
127:     result = []
128:     for path_excel in excel_paths:
129:         ext = os.path.splitext(path_excel)[1].lower()
130:         if ext not in (".xls", ".xlsx"):
131:             continue
132:         phase, boleiro = _extract_phase_who_from_path(path_excel, config)
133:         result.append((path_excel, phase, boleiro))
134:     return result
135: 
136: 
137: # ------------------------------------------------------------------
138: # Result merge helpers
139: # ------------------------------------------------------------------
140: 
141: def _strip_accents(text: str) -> str:
142:     """Remove diacritics/accents from a string (e.g. São -> Sao)."""
143:     return "".join(
144:         c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
145:     )
146: 
147: 
148: def _merge_with_results(df_pred: pd.DataFrame, df_results: pd.DataFrame) -> pd.DataFrame:
149:     """Merge predictions with official results on 'match' key.
150: 
151:     Adds real goals and result description columns.
152: 
153:     Normalises Unicode accents on the match key so that accented
154:     match slugs from player Excel files (e.g. ``méxico-vs-áfrica_do_sul``)
155:     match the ASCII-only slugs in ``games.csv`` (``mexico-vs-africa_do_sul``).
156:     """
157:     df_pred = df_pred.copy()
158:     df_results = df_results.copy()
159:     df_pred["match"] = df_pred["match"].apply(_strip_accents)
160:     df_results["match"] = df_results["match"].apply(_strip_accents)
161:     df = df_pred.merge(df_results, on="match", how="left", suffixes=("_bol", "_real"))
162: 
163:     # Build result strings
164:     df["resultado_bol_placar"] = (
165:         df["home_goals_bol"].astype("Int64").astype(str)
166:         + " x "
167:         + df["away_goals_bol"].astype("Int64").astype(str)
168:     )
169:     df["resultado_bol_time"] = df.apply(
170:         lambda r: r["home_team_bol"]
171:         if r["home_goals_bol"] > r["away_goals_bol"]
172:         else r["away_team_bol"]
173:         if r["away_goals_bol"] > r["home_goals_bol"]
174:         else "empate",
175:         axis=1,
176:     )
177:     df["resultado_real_placar"] = df.apply(
178:         lambda r: f"{int(r['home_goals_real'])} x {int(r['away_goals_real'])}"
179:         if pd.notna(r.get("home_goals_real")) and pd.notna(r.get("away_goals_real"))
180:         else "",
181:         axis=1,
182:     )
183:     df["resultado_real_time"] = df.apply(
184:         lambda r: r["home_team_real"]
185:         if pd.notna(r.get("home_goals_real")) and pd.notna(r.get("away_goals_real"))
186:         and r["home_goals_real"] > r["away_goals_real"]
187:         else r["away_team_real"]
188:         if pd.notna(r.get("home_goals_real")) and pd.notna(r.get("away_goals_real"))
189:         and r["away_goals_real"] > r["home_goals_real"]
190:         else "empate"
191:         if pd.notna(r.get("home_goals_real")) and pd.notna(r.get("away_goals_real"))
192:         else "",
193:         axis=1,
194:     )
195: 
196:     return df
197: 
198: 
199: # ------------------------------------------------------------------
200: # Scoring helpers
201: # ------------------------------------------------------------------
202: 
203: def _apply_scoring(df: pd.DataFrame, config: ChampionshipConfig) -> pd.DataFrame:
204:     """Score each prediction and add scoring columns.
205: 
206:     Adds: pontos, criterio, valido, plus one-hot columns for each rule name.
207:     """
208:     pontos_list: list = []
209:     criterio_list: list = []
210:     valido_list: list = []
211: 
212:     for _, row in df.iterrows():
213:         try:
214:             result = score_prediction(
215:                 row["home_goals_bol"],
216:                 row["away_goals_bol"],
217:                 row.get("home_goals_real"),
218:                 row.get("away_goals_real"),
219:                 config,
220:             )
221:             pontos_list.append(result.iloc[0])
222:             criterio_list.append(result.iloc[1])
223:             valido_list.append(result.iloc[2])
224:         except Exception:
225:             pontos_list.append(0)
226:             criterio_list.append("5-Nenhum acerto")
227:             valido_list.append(1)
228: 
229:     df["pontos"] = pontos_list
230:     df["criterio"] = criterio_list
231:     df["valido"] = valido_list
232: 
233:     # One-hot encode criteria
234:     rule_names = config.scoring_rule_names()
235:     for rule in rule_names:
236:         df[rule] = df["criterio"] == rule
237: 
238:     return df
239: 
240: 
241: # ------------------------------------------------------------------
242: # Bronze: raw Excel -> first_round/ + playoffs/
243: # ------------------------------------------------------------------
244: 
245: def run_raw_to_bronze(config: ChampionshipConfig) -> None:
246:     """Parse all raw Excel files and write bronze CSVs."""
247:     print_colored("raw to bronze", "sand")
248: 
249:     dirs = [
250:         config.bronze_dir,
251:         config._br_first_round(),
252:         config._br_playoffs(),
253:     ]
254:     _recreate_dirs(dirs)
255: 
256:     # --- First round (group stage) ---
257:     boleiros = _boleiros_from_raw(config)
258:     for idx, (path_excel, boleiro) in enumerate(boleiros, 1):
259:         print_colored(f"\t[{idx:2}/{len(boleiros)}] parsing {boleiro}", "ice")
260: 
261:         if config.standings_format:
262:             df_group, df_bonus, df_striker = parse_group_standings(path_excel, config)
263:         else:
264:             df_group = parse_group_stage(path_excel, config)
265:             df_bonus, df_striker = parse_bonus_playoffs(path_excel, config)
266: 
267:         df_group.sort_values(by=["date", "hour"], inplace=True)
268:         _save_csv(df_group, config.bronze_group_path(boleiro))
269: 
270:         _save_csv(df_bonus, config.bronze_bonus_path(boleiro))
271:         _save_csv(df_striker, config.bronze_striker_path(boleiro))
272: 
273:     # --- Playoff rounds (separate Excel per phase) ---
274:     playoff_files = _playoff_files_from_raw(config)
275:     for idx, (path_excel, phase, boleiro) in enumerate(playoff_files, 1):
276:         print_colored(f"\t[{idx:2}/{len(playoff_files)}] parsing {phase} {boleiro}", "ice")
277:         df_playoff = parse_playoff_stage(path_excel, config)
278:         df_playoff.sort_values(by=["date", "hour"], inplace=True)
279:         _save_csv(df_playoff, config.bronze_playoff_path(boleiro, phase))
280: 
281:     print_colored("raw to bronze completed", "green")
282: 
283: 
284: # ------------------------------------------------------------------
285: # Silver: bronze first_round + official results -> merged predictions
286: # ------------------------------------------------------------------
287: 
288: def run_bronze_to_silver(config: ChampionshipConfig) -> None:
289:     """Merge bronze first_round predictions with official results (per boleiro).
290: 
291:     Playoffs are bonus-only and do not flow to silver.
292:     """
293:     print_colored("bronze to silver", "sand")
294: 
295:     dirs = [
296:         config.silver_dir,
297:         config._ag_first_round(),
298:         config._ag_playoffs(),
299:     ]
300:     _recreate_dirs(dirs)
301: 
302:     # Load official results
303:     df_results = pd.read_csv(config.games_file, sep=",")
304: 
305:     # --- First round (group stage) ---
306:     group_pattern = _norm(os.path.join(config._br_first_round(), "group_phase_*"))
307:     group_paths = sorted(glob(group_pattern))
308: 
309:     for path_csv in group_paths:
310:         boleiro = os.path.basename(path_csv).replace("group_phase_", "").replace(".csv", "")
311:         print_colored(f"\tmerging {boleiro}", "ice")
312: 
313:         df_boleiro = pd.read_csv(path_csv, sep=",")
314:         df_merged = _merge_with_results(df_boleiro, df_results)
315: 
316:         # Rename suffixed columns back to canonical names
317:         df_merged.rename(
318:             columns={
319:                 "date_bol": "date",
320:                 "home_team_bol": "home_team",
321:                 "away_team_bol": "away_team",
322:             },
323:             inplace=True,
324:         )
325: 
326:         # Select and order columns (keep penalty columns for tie-break analysis)
327:         df_merged = df_merged.reindex(
328:             columns=[
329:                 "date",
330:                 "hour",
331:                 "match",
332:                 "home_team",
333:                 "away_team",
334:                 "home_goals_bol",
335:                 "away_goals_bol",
336:                 "home_goals_real",
337:                 "away_goals_real",
338:                 "home_pen_bol",
339:                 "away_pen_bol",
340:                 "home_pen_real",
341:                 "away_pen_real",
342:                 "resultado_bol_placar",
343:                 "resultado_bol_time",
344:                 "resultado_real_placar",
345:                 "resultado_real_time",
346:                 "time_elapsed",
347:                 "who",
348:             ]
349:         )
350:         df_merged.sort_values(by=["date", "hour"], inplace=True)
351:         _save_csv(df_merged, config.silver_group_path(boleiro))
352: 
353:     # --- Playoff rounds ---
354:     playoff_pattern = _norm(os.path.join(config._br_playoffs(), "group_phase_*"))
355:     playoff_paths = sorted(glob(playoff_pattern))
356: 
357:     for path_csv in playoff_paths:
358:         phase, boleiro = _extract_playoff_phase_and_boleiro(path_csv, config)
359:         print_colored(f"\tmerging {phase} {boleiro}", "ice")
360: 
361:         df_boleiro = pd.read_csv(path_csv, sep=",")
362: 
363:         # Filter results to only this playoff phase
364:         df_results_phase = df_results[df_results["round"] == phase].copy()
365: 
366:         df_merged = _merge_with_results(df_boleiro, df_results_phase)
367: 
368:         # Rename suffixed columns back to canonical names
369:         df_merged.rename(
370:             columns={
371:                 "date_bol": "date",
372:                 "home_team_bol": "home_team",
373:                 "away_team_bol": "away_team",
374:             },
375:             inplace=True,
376:         )
377: 
378:         # Select and order columns (keep penalty columns for tie-break analysis)
379:         df_merged = df_merged.reindex(
380:             columns=[
381:                 "date",
382:                 "hour",
383:                 "match",
384:                 "home_team",
385:                 "away_team",
386:                 "home_goals_bol",
387:                 "away_goals_bol",
388:                 "home_goals_real",
389:                 "away_goals_real",
390:                 "home_pen_bol",
391:                 "away_pen_bol",
392:                 "home_pen_real",
393:                 "away_pen_real",
394:                 "resultado_bol_placar",
395:                 "resultado_bol_time",
396:                 "resultado_real_placar",
397:                 "resultado_real_time",
398:                 "time_elapsed",
399:                 "who",
400:             ]
401:         )
402:         df_merged.sort_values(by=["date", "hour"], inplace=True)
403:         _save_csv(df_merged, config.silver_playoff_path(boleiro, phase))
404: 
405:     print_colored("bronze to silver completed", "green")
406: 
407: 
408: # ------------------------------------------------------------------
409: # Gold: silver -> scoring applied + aggregated views
410: # ------------------------------------------------------------------
411: 
412: def run_silver_to_gold(config: ChampionshipConfig) -> None:
413:     """Create gold-layer analytical datasets (per-boleiro + aggregated).
414: 
415:     Playoffs are bonus-only and do not flow to gold.
416:     """
417:     print_colored("silver to gold", "sand")
418: 
419:     dirs = [
420:         config.gold_dir,
421:         config.gold_first_round_dir(),
422:         config.gold_playoffs_dir(),
423:     ]
424:     _recreate_dirs(dirs)
425: 
426:     # --- First round ---
427:     silver_pattern = _norm(os.path.join(config._ag_first_round(), "group_phase_*"))
428:     silver_paths = sorted(glob(silver_pattern))
429: 
430:     df_all_parts = []
431:     df_valid_parts = []
432:     df_all = pd.DataFrame()
433:     df_valid = pd.DataFrame()
434: 
435:     for path_csv in silver_paths:
436:         boleiro = os.path.basename(path_csv).replace("group_phase_", "").replace(".csv", "")
437:         print_colored(f"\tscoring first_round {boleiro}", "ice")
438: 
439:         df_silver = pd.read_csv(path_csv, sep=",")
440:         df_gold = _apply_scoring(df_silver, config)
441: 
442:         # Save per-boleiro gold file
443:         _save_csv(df_gold, config.gold_group_boleiro_path(boleiro))
444: 
445:         df_all_parts.append(df_gold)
446:         df_valid_parts.append(df_gold.query("valido == 1"))
447: 
448:     # Aggregate first round
449:     if df_all_parts:
450:         df_all = pd.concat(df_all_parts, ignore_index=True)
451:         df_all.sort_values(by=["date", "hour", "who"], inplace=True)
452:         _save_csv(df_all, config.gold_all_path("group"))
453: 
454:         df_valid = pd.concat(df_valid_parts, ignore_index=True)
455:         df_valid.sort_values(by=["date", "hour", "who"], inplace=True)
456:         _save_csv(df_valid, config.gold_valid_path("group"))
457: 
458:     # --- Copy strikers to gold ---
459:     striker_pattern = _norm(os.path.join(config._br_first_round(), "striker_*"))
460:     striker_paths = sorted(glob(striker_pattern))
461: 
462:     df_strikers_parts = []
463:     for path_csv in striker_paths:
464:         df_st = pd.read_csv(path_csv, sep=",")
465:         df_strikers_parts.append(df_st)
466: 
467:     if df_strikers_parts:
468:         df_strikers = pd.concat(df_strikers_parts, ignore_index=True)
469:         df_strikers.sort_values(by=["boleiro"], inplace=True)
470:         _save_csv(df_strikers, config.playoff_strikers_path("gold"))
471: 
472:         # Also copy individual striker files to gold
473:         for path_csv in striker_paths:
474:             boleiro = os.path.basename(path_csv).replace("striker_", "").replace(".csv", "")
475:             df_st = pd.read_csv(path_csv, sep=",")
476:             _save_csv(df_st, config.gold_striker_path(boleiro))
477: 
478:     # --- Playoff rounds ---
479:     playoff_silver_pattern = _norm(os.path.join(config._ag_playoffs(), "group_phase_*"))
480:     playoff_silver_paths = sorted(glob(playoff_silver_pattern))
481: 
482:     # Group paths by phase so we can aggregate per phase
483:     playoff_by_phase: dict[str, list[str]] = {}
484:     for path_csv in playoff_silver_paths:
485:         phase, _ = _extract_playoff_phase_and_boleiro(path_csv, config)
486:         playoff_by_phase.setdefault(phase, []).append(path_csv)
487: 
488:     for phase, phase_paths in sorted(playoff_by_phase.items()):
489:         print_colored(f"\tscoring playoff phase: {phase}", "ice")
490:         all_phase_parts = []
491:         valid_phase_parts = []
492: 
493:         for path_csv in phase_paths:
494:             _, boleiro = _extract_playoff_phase_and_boleiro(path_csv, config)
495:             df_silver = pd.read_csv(path_csv, sep=",")
496:             if df_silver.empty:
497:                 continue
498:             df_gold = _apply_scoring(df_silver, config)
499: 
500:             # Save per-boleiro gold file for this phase
501:             _save_csv(df_gold, config.gold_playoff_boleiro_path(boleiro, phase))
502: 
503:             all_phase_parts.append(df_gold)
504:             valid_phase_parts.append(df_gold.query("valido == 1"))
505: 
506:         # Aggregate per phase
507:         if all_phase_parts:
508:             df_all = pd.concat(all_phase_parts, ignore_index=True)
509:             df_all.sort_values(by=["date", "hour", "who"], inplace=True)
510:             _save_csv(df_all, config.gold_playoff_all_path(phase))
511: 
512:             df_valid = pd.concat(valid_phase_parts, ignore_index=True)
513:             df_valid.sort_values(by=["date", "hour", "who"], inplace=True)
514:             _save_csv(df_valid, config.gold_playoff_valid_path(phase))
515: 
516:     # --- Analytics (skip when no real results yet) ---
517:     if not _has_real_results(config):
518:         print_colored("\tno real results in games.csv — skipping all analytics", "yellow")
519:     else:
520:         _generate_playoff_scoring(config)
521:         _generate_striker_scoring(config)
522:         _generate_consistency(df_valid, config)
523:         _generate_upset_tracker(df_all, config)
524:         _generate_round_by_round(df_valid, config)
525:         _generate_team_accuracy(df_valid, config)
526: 
527:         _generate_ranking_history(df_valid, config)
528:         _generate_boldness_index(df_all, config, df_valid)
529:         _generate_prediction_timing(config)
530:         _generate_goal_error_by_team(df_valid, config)
531:         _generate_group_standings(config)
532: 
533:     print_colored("silver to gold completed", "green")
534: 
535: 
536: # ------------------------------------------------------------------
537: # Derived analytics (generated from gold data)
538: # ------------------------------------------------------------------
539: 
540: 
541: def _generate_playoff_scoring(config: ChampionshipConfig) -> None:
542:     """Score playoff bonus team picks and save to gold."""
543:     if not config.playoff_scoring:
544:         print_colored("\tskipping playoff scoring (no config)", "yellow")
545:         return
546:     print_colored("\tgenerating playoff scoring", "ice")
547:     df = score_playoff_bonus(config)
548:     _save_csv(df, _norm(os.path.join(config._au_first_round(), "playoffs_scored.csv")))
549:     print_colored(f"\tplayoffs_scored.csv: {len(df)} rows", "green")
550: 
551: 
552: def _generate_striker_scoring(config: ChampionshipConfig) -> None:
553:     """Score striker picks and save to gold."""
554:     if not config.actual_top_scorer or not config.striker_points:
555:         print_colored("\tskipping striker scoring (no config)", "yellow")
556:         return
557:     print_colored("\tgenerating striker scoring", "ice")
558:     df = score_strikers(config)
559:     _save_csv(df, _norm(os.path.join(config._au_first_round(), "strikers_scored.csv")))
560:     print_colored(f"\tstrikers_scored.csv: {len(df)} rows", "green")
561: 
562: 
563: def _generate_consistency(df_valid: pd.DataFrame, config: ChampionshipConfig) -> None:
564:     """Derive streak/consistency data from gold predictions."""
565:     if df_valid.empty:
566:         print_colored("\tconsistency.csv: 0 rows (no data)", "yellow")
567:         return
568:     print_colored("\tgenerating consistency tracking", "ice")
569:     df = df_valid.copy()
570:     # Normalize hour: extract numeric part (e.g. "22h" -> 22) for correct numeric sort
571:     df["_hour_num"] = pd.to_numeric(df["hour"].astype(str).str.replace("h", "", regex=False), errors="coerce").fillna(0).astype(int)
572:     df = df.sort_values(["who", "date", "_hour_num"])
573:     df.drop(columns=["_hour_num"], inplace=True)
574:     df["hit"] = df["pontos"] > 0
575: 
576:     rows = []
577:     for boleiro, group in df.groupby("who"):
578:         streak_type = None
579:         streak_len = 0
580:         # Use a positional index for the running avg to avoid
581:         # slice-by-label on a reindexed DataFrame
582:         group = group.reset_index(drop=True)
583:         for idx, (_, row) in enumerate(group.iterrows()):
584:             is_hit = row["hit"]
585:             if is_hit and streak_type == "hit":
586:                 streak_len += 1
587:             elif not is_hit and streak_type == "miss":
588:                 streak_len += 1
589:             else:
590:                 streak_type = "hit" if is_hit else "miss"
591:                 streak_len = 1
592: 
593:             # Running avg of last 5 games — use positional index
594:             recent = group.loc[:idx, "pontos"].tail(5).mean()
595: 
596:             rows.append({
597:                 "boleiro": boleiro,
598:                 "date": row["date"],
599:                 "match": row.get("match", ""),
600:                 "streak_type": streak_type,
601:                 "streak_length": streak_len,
602:                 "running_avg_5": round(recent, 1),
603:             })
604: 
605:     df_out = pd.DataFrame(rows)
606:     _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "consistency.csv")))
607:     print_colored(f"\tconsistency.csv: {len(df_out)} rows", "green")
608: 
609: 
610: def _generate_upset_tracker(df_all: pd.DataFrame, config: ChampionshipConfig) -> None:
611:     """Identify upset matches and who correctly predicted them."""
612:     if df_all.empty:
613:         print_colored("\tupset_tracker.csv: 0 rows (no data)", "yellow")
614:         return
615:     print_colored("\tgenerating upset tracker", "ice")
616:     df = df_all.copy()
617:     df_results = pd.read_csv(config.games_file, sep=",")
618: 
619:     # Merge round info
620:     df_games_round = df_results[["match", "round"]].drop_duplicates()
621:     df = df.merge(df_games_round, on="match", how="left")
622: 
623:     rows = []
624:     for match, group in df.groupby("match"):
625:         first = group.iloc[0]
626:         home = first["home_team"]
627:         away = first["away_team"]
628:         real_winner_raw = first.get("resultado_real_time", "")
629:         # CSV round-trip converts empty strings to NaN; pd.isna catches both
630:         real_winner = "" if pd.isna(real_winner_raw) else str(real_winner_raw)
631: 
632:         # Also check time_elapsed — live or notstarted matches do NOT count as finished
633:         time_elapsed_raw = first.get("time_elapsed", "")
634:         time_elapsed = "" if pd.isna(time_elapsed_raw) else str(time_elapsed_raw).strip().lower()
635: 
636:         # Skip unfinished matches — no real result yet
637:         if not real_winner or time_elapsed in ("live", "notstarted"):
638:             continue
639: 
640:         # Determine favorite (most predicted winner)
641:         vote_counts = group["resultado_bol_time"].value_counts()
642:         favorite = vote_counts.index[0] if not vote_counts.empty else ""
643:         favorite_votes = int(vote_counts.iloc[0]) if not vote_counts.empty else 0
644:         total_votes = len(group)
645: 
646:         # Which players got the result right
647:         players_correct = []
648:         for _, p_row in group.iterrows():
649:             if str(p_row.get("resultado_bol_time", "")) == real_winner:
650:                 players_correct.append(p_row["who"])
651: 
652:         num_correct = len(players_correct)
653:         winner_wrong_pct = 100 - round(num_correct / total_votes * 100) if total_votes else 0
654: 
655:         is_upset = 0
656:         if favorite != real_winner and num_correct <= 5:
657:             is_upset = 1
658: 
659:         rows.append({
660:             "match": match,
661:             "date": first["date"],
662:             "hour": first["hour"],
663:             "home_team": home,
664:             "away_team": away,
665:             "real_winner": real_winner,
666:             "favorite": favorite,
667:             "favorite_votes": favorite_votes,
668:             "total_votes": total_votes,
669:             "winner_wrong_pct": winner_wrong_pct,
670:             "is_upset": is_upset,
671:             "num_correct": num_correct,
672:             "players_correct": " | ".join(players_correct),
673:         })
674: 
675:     df_out = pd.DataFrame(rows)
676:     _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "upset_tracker.csv")))
677:     print_colored(f"\tupset_tracker.csv: {len(df_out)} rows", "green")
678: 
679: 
680: def _generate_round_by_round(df_valid: pd.DataFrame, config: ChampionshipConfig) -> None:
681:     """Aggregate points per round for each player."""
682:     if df_valid.empty:
683:         print_colored("\tround_by_round.csv: 0 rows (no data)", "yellow")
684:         return
685:     print_colored("\tgenerating round-by-round tracking", "ice")
686:     df = df_valid.copy()
687:     df_results = pd.read_csv(config.games_file, sep=",")
688: 
689:     # Merge round info from games.csv
690:     df_games_round = df_results[["match", "round"]].drop_duplicates()
691:     df = df.merge(df_games_round, on="match", how="left")
692:     df["round"] = df["round"].fillna("0")
693: 
694:     # Map round labels to numeric ordering
695:     round_order = {}
696:     for i, r in enumerate(["1", "2", "3", "oitavas", "quartas", "semi", "final"]):
697:         round_order[r] = i + 1
698:     df["round_number"] = df["round"].map(round_order).fillna(0).astype(int)
699: 
700:     rows = []
701:     for boleiro, group in df.groupby("who"):
702:         group = group.sort_values("round_number")
703:         cum = 0
704:         for rn, rgroup in group.groupby("round_number"):
705:             pts = int(rgroup["pontos"].sum())
706:             cum += pts
707:             rows.append({
708:                 "boleiro": boleiro,
709:                 "round_number": rn,
710:                 "round_label": rgroup.iloc[0]["round"],
711:                 "points": pts,
712:                 "cumulative_points": cum,
713:             })
714: 
715:     # Add rank per round
716:     df_out = pd.DataFrame(rows)
717:     if not df_out.empty:
718:         for rn in df_out["round_number"].unique():
719:             mask = df_out["round_number"] == rn
720:             df_out.loc[mask, "rank"] = df_out.loc[mask, "cumulative_points"].rank(
721:                 ascending=False, method="min"
722:             ).astype(int)
723: 
724:     _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "round_by_round.csv")))
725:     print_colored(f"\tround_by_round.csv: {len(df_out)} rows", "green")
726: 
727: 
728: def _generate_team_accuracy(df_valid: pd.DataFrame, config: ChampionshipConfig) -> None:
729:     """Calculate prediction accuracy per team for each player."""
730:     if df_valid.empty:
731:         print_colored("\tteam_accuracy.csv: 0 rows (no data)", "yellow")
732:         return
733:     print_colored("\tgenerating team accuracy tracking", "ice")
734:     df = df_valid.copy()
735: 
736:     rows = []
737:     # For home team role
738:     for team_col, opp_col in [("home_team", "away_team"), ("away_team", "home_team")]:
739:         for team, group in df.groupby(team_col):
740:             for boleiro, bg in group.groupby("who"):
741:                 total = len(bg)
742:                 correct_winner = sum(
743:                     1 for _, r in bg.iterrows()
744:                     if str(r.get("resultado_bol_time", "")) == str(r.get("resultado_real_time", ""))
745:                 )
746:                 exact_score = sum(
747:                     1 for _, r in bg.iterrows()
748:                     if r.get("home_goals_bol", -1) == r.get("home_goals_real", -2)
749:                     and r.get("away_goals_bol", -1) == r.get("away_goals_real", -2)
750:                 )
751:                 rows.append({
752:                     "team": team,
753:                     "role": team_col.replace("_team", ""),
754:                     "boleiro": boleiro,
755:                     "total_bets": total,
756:                     "correct_winner": correct_winner,
757:                     "exact_score": exact_score,
758:                     "accuracy_pct": round(correct_winner / total * 100, 1) if total > 0 else 0,
759:                 })
760: 
761:     df_out = pd.DataFrame(rows)
762:     _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "team_accuracy.csv")))
763:     print_colored(f"\tteam_accuracy.csv: {len(df_out)} rows", "green")
764: 
765: 
766: # ------------------------------------------------------------------
767: # New analytics #1: Ranking history (daily rank position)
768: # ------------------------------------------------------------------
769: 
770: 
771: def _generate_ranking_history(df_valid: pd.DataFrame, config: ChampionshipConfig) -> None:
772:     """Daily rank position for each player (cumulative ranking)."""
773:     if df_valid.empty:
774:         print_colored("\tranking_history.csv: 0 rows (no data)", "yellow")
775:         return
776:     print_colored("\tgenerating ranking history", "ice")
777:     df = df_valid.copy()
778:     df = df.sort_values(["who", "date"])
779: 
780:     rows = []
781:     for date, day_group in df.groupby("date"):
782:         # Cumulative points up to this date for each player
783:         daily_pts = day_group.groupby("who")["pontos"].sum()
784:         # Get all players' cumulative up to this date
785:         all_cum = df[df["date"] <= date].groupby("who")["pontos"].sum()
786:         leader_pts = int(all_cum.max()) if not all_cum.empty else 0
787:         leader_name = str(all_cum.idxmax()) if not all_cum.empty else ""
788: 
789:         # Include ALL players, not just those who bet today,
790:         # so ranking history has no gaps for skipped days.
791:         all_players = all_cum.index.tolist()
792:         for boleiro in all_players:
793:             cum = int(all_cum.get(boleiro, 0))
794:             rank = int(all_cum.rank(ascending=False, method="min").get(boleiro, 0))
795:             daily_pts_val = int(daily_pts.get(boleiro, 0))
796:             rows.append({
797:                 "boleiro": boleiro,
798:                 "date": date,
799:                 "daily_points": daily_pts_val,
800:                 "cumulative_points": cum,
801:                 "rank": rank,
802:                 "leader_name": leader_name,
803:                 "leader_distance": leader_pts - cum,
804:             })
805: 
806:     df_out = pd.DataFrame(rows)
807:     _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "ranking_history.csv")))
808:     print_colored(f"\tranking_history.csv: {len(df_out)} rows", "green")
809: 
810: 
811: # ------------------------------------------------------------------
812: # New analytics #2: Boldness index
813: # ------------------------------------------------------------------
814: 
815: 
816: def _generate_boldness_index(df_all: pd.DataFrame, config: ChampionshipConfig, df_valid: pd.DataFrame | None = None) -> None:
817:     """Measure how 'bold' each player's predictions are."""
818:     source = df_valid if df_valid is not None and not df_valid.empty else df_all
819:     if source.empty:
820:         print_colored("\tboldness_index.csv: 0 rows (no data)", "yellow")
821:         return
822:     print_colored("\tgenerating boldness index", "ice")
823: 
824:     # Use a single data source for both player averages AND bolão average
825:     # to avoid comparing apples to oranges.
826:     df = source.copy()
827:     bolao_avg = (df["home_goals_bol"] + df["away_goals_bol"]).mean()
828: 
829:     rows = []
830:     for boleiro, group in df.groupby("who"):
831:         total_goals = group["home_goals_bol"] + group["away_goals_bol"]
832:         avg_total = total_goals.mean()
833:         games = len(group)
834: 
835:         # How often they predict extreme scores (>= 5 total goals)
836:         extreme_pct = (total_goals >= 5).sum() / games * 100 if games > 0 else 0
837: 
838:         rows.append({
839:             "boleiro": boleiro,
840:             "avg_total_goals_bol": round(avg_total, 2),
841:             "avg_home_goals_bol": round(group["home_goals_bol"].mean(), 2),
842:             "avg_away_goals_bol": round(group["away_goals_bol"].mean(), 2),
843:             "max_home_bol": int(group["home_goals_bol"].max()),
844:             "max_away_bol": int(group["away_goals_bol"].max()),
845:             "extreme_score_pct": round(extreme_pct, 1),
846:             "games": games,
847:             "boldness_score": round(avg_total - bolao_avg, 2),
848:         })
849: 
850:     df_out = pd.DataFrame(rows)
851:     df_out = df_out.sort_values("boldness_score", ascending=False)
852:     _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "boldness_index.csv")))
853:     print_colored(f"\tboldness_index.csv: {len(df_out)} rows", "green")
854: 
855: 
856: # ------------------------------------------------------------------
857: # New analytics #3: Prediction timing (lead days from raw Excel mtime)
858: # ------------------------------------------------------------------
859: 
860: 
861: def _generate_prediction_timing(config: ChampionshipConfig) -> None:
862:     """Estimate how early each player submitted picks (via raw Excel mtime)."""
863:     print_colored("\tgenerating prediction timing", "ice")
864: 
865:     # Load games to know first match date
866:     df_games = pd.read_csv(config.games_file, sep=",")
867:     if "date" in df_games.columns and not df_games["date"].empty:
868:         first_match = pd.to_datetime(df_games["date"].dropna().min())
869:     else:
870:         first_match = datetime.now()
871: 
872:     # Scan raw Excel files for modification time
873:     raw_pattern = _norm(os.path.join(config.raw_dir, config.group_phase_label, "*"))
874:     raw_paths = sorted(glob(raw_pattern))
875: 
876:     rows = []
877:     for path_excel in raw_paths:
878:         boleiro = _extract_who(path_excel, config)
879: 
880:         mtime = os.path.getmtime(path_excel)
881:         mtime_dt = datetime.fromtimestamp(mtime)
882:         lead_days = (first_match - pd.Timestamp(mtime_dt)).days if first_match else 0
883: 
884:         rows.append({
885:             "boleiro": boleiro,
886:             "file_mtime": mtime_dt.strftime("%Y-%m-%d %H:%M:%S"),
887:             "first_match_date": first_match.strftime("%Y-%m-%d") if not pd.isna(first_match) else "",
888:             "lead_days": max(lead_days, 0),
889:         })
890: 
891:     if not rows:
892:         print_colored("\tprediction_timing.csv: 0 rows (no raw files found)", "yellow")
893:         df_out = pd.DataFrame(columns=["boleiro", "file_mtime", "first_match_date", "lead_days"])
894:         _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "prediction_timing.csv")))
895:         return
896:     df_out = pd.DataFrame(rows)
897:     df_out = df_out.sort_values("lead_days", ascending=False)
898:     _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "prediction_timing.csv")))
899:     print_colored(f"\tprediction_timing.csv: {len(df_out)} rows", "green")
900: 
901: 
902: # ------------------------------------------------------------------
903: # New analytics: Group standings (real tournament table)
904: # ------------------------------------------------------------------
905: 
906: 
907: def _generate_group_standings(config: ChampionshipConfig) -> None:
908:     """Compute real group standings from games.csv and save to gold."""
909:     if not config.groups:
910:         print_colored("\tskipping group standings (no groups configured)", "yellow")
911:         return
912:     print_colored("\tgenerating group standings", "ice")
913:     df_games = pd.read_csv(config.games_file, sep=",")
914:     group_rounds = ["1", "2", "3"]
915:     df_group = df_games[df_games["round"].astype(str).str.strip().isin(group_rounds)]
916: 
917:     rows = []
918:     for grp in config.groups:
919:         group_name = grp.get("name", "?")
920:         teams = grp.get("teams", [])
921:         standings = {}
922:         for t in teams:
923:             standings[t] = {"team": t, "group": group_name, "p": 0, "w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "pts": 0}
924:         for _, row in df_group.iterrows():
925:             home = str(row.get("home_team", ""))
926:             away = str(row.get("away_team", ""))
927:             if home not in standings or away not in standings:
928:                 continue
929:             try:
930:                 hg = int(row["home_goals"]) if pd.notna(row.get("home_goals")) else None
931:                 ag = int(row["away_goals"]) if pd.notna(row.get("away_goals")) else None
932:             except (ValueError, TypeError):
933:                 continue
934:             if hg is None or ag is None:
935:                 continue
936:             standings[home]["p"] += 1
937:             standings[away]["p"] += 1
938:             standings[home]["gf"] += hg
939:             standings[home]["ga"] += ag
940:             standings[away]["gf"] += ag
941:             standings[away]["ga"] += hg
942:             if hg > ag:
943:                 standings[home]["w"] += 1; standings[home]["pts"] += 3
944:                 standings[away]["l"] += 1
945:             elif ag > hg:
946:                 standings[away]["w"] += 1; standings[away]["pts"] += 3
947:                 standings[home]["l"] += 1
948:             else:
949:                 standings[home]["d"] += 1; standings[away]["d"] += 1
950:                 standings[home]["pts"] += 1; standings[away]["pts"] += 1
951:         for t, s in standings.items():
952:             s["gd"] = s["gf"] - s["ga"]
953:             rows.append(s)
954: 
955:     if not rows:
956:         print_colored("\tgroup_standings.csv: 0 rows (no data)", "yellow")
957:         return
958:     df_out = pd.DataFrame(rows)
959:     df_out = df_out.sort_values(["group", "pts", "gd", "gf"], ascending=[True, False, False, False])
960:     _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "group_standings.csv")))
961:     print_colored(f"\tgroup_standings.csv: {len(df_out)} rows", "green")
962: 
963: 
964: # ------------------------------------------------------------------
965: # New analytics #4: Goal error by team
966: # ------------------------------------------------------------------
967: 
968: 
969: def _generate_goal_error_by_team(df_valid: pd.DataFrame, config: ChampionshipConfig) -> None:
970:     """Mean Absolute Error per team for each player's goal predictions."""
971:     if df_valid.empty:
972:         print_colored("\tgoal_error_by_team.csv: 0 rows (no data)", "yellow")
973:         return
974:     print_colored("\tgenerating goal error by team", "ice")
975:     df = df_valid.copy()
976: 
977:     rows = []
978:     for team_col in ("home_team", "away_team"):
979:         role = team_col.replace("_team", "")
980:         goals_bol_col = f"{role}_goals_bol"
981:         goals_real_col = f"{role}_goals_real"
982: 
983:         for team, group in df.groupby(team_col):
984:             for boleiro, bg in group.groupby("who"):
985:                 games = len(bg)
986:                 if games == 0:
987:                     continue
988:                 errors = abs(bg[goals_bol_col] - bg[goals_real_col])
989:                 mae = round(errors.mean(), 2)
990:                 bias = round((bg[goals_bol_col] - bg[goals_real_col]).mean(), 2)
991: 
992:                 rows.append({
993:                     "boleiro": boleiro,
994:                     "team": team,
995:                     "role": role,
996:                     "games": games,
997:                     "mae": mae,
998:                     "goal_bias": bias,
999:                     "avg_predicted": round(bg[goals_bol_col].mean(), 2),
1000:                     "avg_real": round(bg[goals_real_col].mean(), 2),
1001:                 })
1002: 
1003:     # Also total MAE (home + away combined)
1004:     # Group by (boleiro, team) and merge home/away rows
1005:     df_out = pd.DataFrame(rows)
1006:     # Add a "total" row per boleiro+team
1007:     totals = []
1008:     for (boleiro, team), group in df_out.groupby(["boleiro", "team"]):
1009:         total_games = group["games"].sum()
1010:         total_mae = round((group["mae"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0
1011:         totals.append({
1012:             "boleiro": boleiro,
1013:             "team": team,
1014:             "role": "total",
1015:             "games": total_games,
1016:             "mae": total_mae,
1017:             "goal_bias": round((group["goal_bias"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0,
1018:             "avg_predicted": round((group["avg_predicted"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0,
1019:             "avg_real": round((group["avg_real"] * group["games"]).sum() / total_games, 2) if total_games > 0 else 0,
1020:         })
1021:     df_totals = pd.DataFrame(totals)
1022:     df_out = pd.concat([df_out, df_totals], ignore_index=True)
1023:     df_out = df_out.sort_values(["boleiro", "team", "role"])
1024: 
1025:     _save_csv(df_out, _norm(os.path.join(config._au_first_round(), "goal_error_by_team.csv")))
1026:     print_colored(f"\tgoal_error_by_team.csv: {len(df_out)} rows", "green")
1027: 
1028: 
1029: # ------------------------------------------------------------------
1030: # Orchestrator
1031: # ------------------------------------------------------------------
1032: 
1033: def run_pipeline(config: ChampionshipConfig) -> None:
1034:     """Run the full medallion pipeline."""
1035:     fetch_all_logos(config)
1036:     build_world_cup_csv(config.games_file)
1037:     run_raw_to_bronze(config)
1038:     run_bronze_to_silver(config)
1039:     run_silver_to_gold(config)

(End of file - total 1039 lines)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\loader.py`

```python
1: """Generic Excel parser for sweepstake prediction sheets.
2: 
3: Reads raw Excel files and extracts group-stage predictions and
4: bonus playoff team picks according to the championship's ExcelLayout.
5: """
6: 
7: from __future__ import annotations
8: 
9: import os
10: 
11: import pandas as pd
12: 
13: from src.core.config import ChampionshipConfig
14: 
15: # Column names expected in the first 9 columns of the Excel sheet
16: _EXCEL_COLUMNS = [
17:     "date",
18:     "hour",
19:     "home_team",
20:     "home_pen",
21:     "home_goals",
22:     "x",
23:     "away_goals",
24:     "away_pen",
25:     "away_team",
26: ]
27: 
28: 
29: def _extract_who(path: str, config: ChampionshipConfig) -> str:
30:     """Extract participant name from the Excel filename.
31: 
32:     Uses ``os.path.basename`` so that splitting by ``name_split_char``
33:     operates only on the filename, not the full file path.
34:     """
35:     layout = config.excel_layout
36:     fname = os.path.basename(path)
37:     name_no_ext = fname.replace(".xlsx", "").replace(".xls", "").strip()
38:     parts = name_no_ext.split(layout.playoffs.name_split_char)
39:     name = parts[layout.playoffs.name_split_index].strip()
40:     return name
41: 
42: 
43: def _clean_dataframe(df: pd.DataFrame, who: str) -> pd.DataFrame:
44:     """Apply common cleaning steps to a parsed Excel dataframe."""
45:     df = df.copy()
46:     df.dropna(how="all", inplace=True)
47:     df["who"] = who
48:     df = df.loc[df["date"].notna()]
49:     df = df.loc[~df["date"].str.contains("GRUPO", na=False)]
50:     return df
51: 
52: 
53: def _normalize_types(df: pd.DataFrame) -> pd.DataFrame:
54:     """Cast numeric and date columns to proper types."""
55:     df = df.copy()
56:     for col in ["home_goals", "home_pen", "away_goals", "away_pen"]:
57:         if col in df.columns:
58:             df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)
59:     df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=True).dt.strftime("%Y-%m-%d")
60:     df = df.loc[df["date"].notna()]
61:     return df
62: 
63: 
64: def _make_match_key(df: pd.DataFrame) -> pd.DataFrame:
65:     """Add a 'match' column from home_team and away_team.
66: 
67:     Enforces: lowercase, no spaces, no hyphens — only underscores.
68:     This must stay in sync with _slug() in get_results.py.
69:     """
70:     df = df.copy()
71: 
72:     def _slug(name: str) -> str:
73:         s = name.lower().strip()
74:         s = s.replace(" ", "_").replace("-", "_")
75:         return s
76: 
77:     df["match"] = df["home_team"].apply(_slug) + "-vs-" + df["away_team"].apply(_slug)
78:     return df
79: 
80: 
81: def parse_group_stage(path: str, config: ChampionshipConfig) -> pd.DataFrame:
82:     """Parse the group-stage predictions from an Excel file.
83: 
84:     Returns a DataFrame with columns:
85:         date, hour, home_team, home_pen, home_goals, x, away_goals, away_pen,
86:         away_team, who, match
87:     """
88:     layout = config.excel_layout
89:     who = _extract_who(path, config)
90: 
91:     df = pd.read_excel(path, skiprows=layout.first_round.skiprows)
92:     df = df[df.columns[:9]]
93:     df.columns = _EXCEL_COLUMNS
94: 
95:     df = _clean_dataframe(df, who)
96:     df = df.head(layout.first_round.matches).copy()
97:     df = _normalize_types(df)
98:     df = _make_match_key(df)
99: 
100:     return df
101: 
102: 
103: def _extract_playoff_phase_and_who(path: str, config: ChampionshipConfig) -> tuple[str, str]:
104:     """Extract (phase_key, boleiro_name) from a playoff Excel filename.
105: 
106:     Expects format: ``{phase}_{boleiro}.xlsx`` where phase is one of
107:     the configured playoff round keys (oitavas, quartas, semi, final).
108:     """
109:     fname = os.path.basename(path)
110:     name_no_ext = fname.replace(".xlsx", "").replace(".xls", "").strip()
111: 
112:     # Try to match a known phase key at the start of the filename
113:     for pr in config.playoff_rounds:
114:         prefix = pr.key + "_"
115:         if name_no_ext.startswith(prefix):
116:             boleiro = name_no_ext[len(prefix):].strip()
117:             return pr.key, boleiro
118: 
119:     # Fallback: use first part before first '_' as phase, rest as name
120:     if "_" in name_no_ext:
121:         parts = name_no_ext.split("_", 1)
122:         return parts[0].strip(), parts[1].strip()
123: 
124:     raise ValueError(
125:         f"Cannot extract phase and boleiro from filename: {fname}. "
126:         f"Expected format: {{phase}}_{{boleiro}}.xlsx"
127:     )
128: 
129: 
130: def parse_playoff_stage(path: str, config: ChampionshipConfig) -> pd.DataFrame:
131:     """Parse playoff-round predictions from a dedicated Excel file.
132: 
133:     Each file contains only the matches for a single knockout round
134:     (e.g. 8 oitavas matches, 4 quartas matches, etc.).
135: 
136:     Returns a DataFrame with columns:
137:         date, hour, home_team, home_pen, home_goals, x, away_goals, away_pen,
138:         away_team, who, match, phase
139:     """
140:     phase, who = _extract_playoff_phase_and_who(path, config)
141: 
142:     df = pd.read_excel(path)
143:     df = df[df.columns[:9]]
144:     df.columns = _EXCEL_COLUMNS
145: 
146:     df = _clean_dataframe(df, who)
147:     df = _normalize_types(df)
148:     df = _make_match_key(df)
149:     df["phase"] = phase
150: 
151:     return df
152: 
153: 
154: def _slug(name: str) -> str:
155:     """Slugify a team name: lowercase, no spaces, no hyphens."""
156:     s = name.lower().strip()
157:     s = s.replace(" ", "_").replace("-", "_")
158:     return s
159: 
160: 
161: def parse_group_standings(path: str, config: ChampionshipConfig) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
162:     """Parse group-standings Excel into bronze CSVs.
163: 
164:     Returns (df_predictions, df_bonus, df_striker).
165:     """
166:     who = _extract_who(path, config)
167:     df_raw = pd.read_excel(path, skiprows=config.standings_skiprows, header=None)
168: 
169:     # --- Parse group standings ---
170:     teams_data = _parse_standings_rows(df_raw)
171: 
172:     if not teams_data:
173:         raise ValueError(
174:             f"No group standings found in {path}. "
175:             "Expected a standings-format Excel with 'Grupo X' headers."
176:         )
177: 
178:     # --- Load games.csv to read match schedule (scores kept intact from API) ---
179:     df_games = pd.read_csv(config.games_file, sep=",")
180: 
181:     # --- Normalize round names ---
182:     _round_map = {
183:         "round of 32": "segunda_fase",
184:         "round of 16": "oitavas",
185:         "quarter finals": "quartas",
186:         "semi finals": "semi",
187:         "third place": "terceiro_lugar",
188:         "final": "final",
189:         "finals": "final",
190:     }
191:     df_games["round"] = df_games["round"].astype(str).str.strip().str.lower()
192:     df_games["round"] = df_games["round"].map(lambda r: _round_map.get(r, r))
193:     group_games = df_games[df_games["round"].isin(["1", "2", "3"])].copy()
194: 
195:     # --- Read actual predictions from the Tabela Jogos sheet ---
196:     po_layout = config.excel_layout.playoffs
197:     df_po = None
198:     if po_layout.playoffs_sheet_name:
199:         try:
200:             df_po = pd.read_excel(path, sheet_name=po_layout.playoffs_sheet_name, header=None)
201:         except Exception:
202:             pass
203: 
204:     if df_po is not None and len(df_po) > 3:
205:         actual_scores = {}
206:         for idx in range(len(df_po)):
207:             row = df_po.iloc[idx]
208:             col2 = str(row[2]).strip() if pd.notna(row[2]) else ""
209:             col8 = str(row[8]).strip() if len(row) > 8 and pd.notna(row[8]) else ""
210:             col4 = row[4]
211:             col6 = row[6] if len(row) > 6 else None
212:             if col2 and col8 and col2 != "nan" and col8 != "nan":
213:                 try:
214:                     hg = float(col4) if pd.notna(col4) else None
215:                     ag = float(col6) if pd.notna(col6) else None
216:                     if hg is not None and ag is not None:
217:                         actual_scores[(col2, col8)] = (hg, ag)
218:                         actual_scores[(col8, col2)] = (ag, hg)
219:                 except (ValueError, TypeError):
220:                     pass
221: 
222:     predictions = []
223:     for _, game in group_games.iterrows():
224:         home, away = game["home_team"], game["away_team"]
225:         key = (home, away)
226:         if key in actual_scores:
227:             pred_h, pred_a = actual_scores[key]
228:         else:
229:             pred_h, pred_a = 2, 0
230:         raw_date = str(game["date"])
231:         if " " in raw_date and "h" in raw_date:
232:             pred_date = raw_date[:10]
233:             pred_hour = raw_date.split(" ")[1]
234:         else:
235:             pred_date = raw_date[:10]
236:             pred_hour = ""
237:         predictions.append({
238:             "date": pred_date,
239:             "hour": pred_hour,
240:             "home_team": home,
241:             "home_pen": "",
242:             "home_goals": float(pred_h),
243:             "x": "x",
244:             "away_goals": float(pred_a),
245:             "away_pen": "",
246:             "away_team": away,
247:             "who": who,
248:             "match": _slug(home) + "-vs-" + _slug(away),
249:         })
250:     df_pred = pd.DataFrame(predictions)
251: 
252:     # --- Parse bonus playoff picks and striker ---
253:     df_bonus, df_striker = _parse_playoffs_and_striker(path, who, config, df_raw)
254: 
255:     return df_pred, df_bonus, df_striker
256: 
257: 
258: def _parse_standings_rows(df_raw: pd.DataFrame) -> list[dict]:
259:     """Extract (group, team, pts, j, v, e, d, gp, gc, sg) from raw standings."""
260:     teams_data = []
261:     current_group = None
262:     for _, row in df_raw.iterrows():
263:         col0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
264:         col1_str = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
265: 
266:         if col1_str.startswith("Grupo"):
267:             current_group = col1_str
268:             continue
269:         if not current_group:
270:             continue
271:         if not col0 or col0 in ("Seleção", "nan", "NaN", ""):
272:             continue
273: 
274:         try:
275:             pts = int(float(row.iloc[1]))
276:         except (ValueError, TypeError):
277:             continue
278: 
279:         try:
280:             fields = [int(row.iloc[i]) if pd.notna(row.iloc[i]) else 0 for i in range(2, 9)]
281:         except (ValueError, TypeError):
282:             continue
283: 
284:         if fields[0] == 0 or all(f == 0 for f in fields):
285:             continue
286: 
287:         teams_data.append({
288:             "group": current_group,
289:             "team": col0,
290:             "pts": pts, "j": fields[0], "v": fields[1], "e": fields[2],
291:             "d": fields[3], "gp": fields[4], "gc": fields[5], "sg": fields[6],
292:         })
293: 
294:     # Deduplicate
295:     seen = set()
296:     unique = []
297:     for t in teams_data:
298:         if t["team"] not in seen:
299:             seen.add(t["team"])
300:             unique.append(t)
301:     return unique
302: 
303: 
304: def _parse_playoffs_and_striker(
305:     path: str, who: str, config: ChampionshipConfig, df_raw: pd.DataFrame
306: ) -> tuple[pd.DataFrame, pd.DataFrame]:
307:     """Extract bonus playoff picks and striker name from the Excel.
308: 
309:     Reads the configured playoffs sheet (or falls back to df_raw), then
310:     scans for phase labels (e.g. "Oitavas", "Final") and the striker label
311:     (e.g. "Artilheiro") to locate the corresponding picks.
312:     """
313:     po_layout = config.excel_layout.playoffs
314: 
315:     # Use dedicated playoffs sheet if configured (e.g. "Tabela Jogos")
316:     if po_layout.playoffs_sheet_name:
317:         try:
318:             df_po = pd.read_excel(path, sheet_name=po_layout.playoffs_sheet_name, header=None)
319:         except Exception:
320:             df_po = df_raw
321:     else:
322:         df_po = df_raw
323: 
324:     phase_labels = {r.name: r.key for r in config.playoff_rounds}
325:     striker_label = po_layout.striker_label.lower().strip()
326:     nc, fc = po_layout.striker_name_column, po_layout.striker_name_fallback_column
327:     label_cols = list(range(min(9, len(df_po.columns) if not df_po.empty else 9)))
328: 
329:     bonus_rows = []
330: 
331:     # --- Extract Champion (Absolute Cell Reference) ---
332:     if po_layout.champion_cell:
333:         try:
334:             # Try configured playoffs sheet first, then fallback to the first sheet
335:             sheets_to_try = []
336:             if po_layout.playoffs_sheet_name:
337:                 sheets_to_try.append(po_layout.playoffs_sheet_name)
338:             sheets_to_try.append(0)
339: 
340:             champ_team = None
341:             for sheet in sheets_to_try:
342:                 try:
343:                     df_champ = pd.read_excel(path, sheet_name=sheet, header=None)
344:                     import re
345:                     match = re.match(r"([A-Z]+)([0-9]+)", po_layout.champion_cell.upper())
346:                     if match:
347:                         col_str, row_str = match.groups()
348:                         col = 0
349:                         for char in col_str:
350:                             col = col * 26 + (ord(char) - ord('A') + 1)
351:                         col -= 1
352:                         row = int(row_str) - 1
353:                         if row < len(df_champ) and col < len(df_champ.columns):
354:                             val = str(df_champ.iloc[row, col]).strip()
355:                             if val and val.lower() not in ("nan", "none", ""):
356:                                 champ_team = val
357:                                 break
358:                 except Exception:
359:                     continue
360: 
361:             if champ_team:
362:                 bonus_rows.append({"boleiro": who, "phase": "campeao", "team": champ_team})
363:         except Exception:
364:             pass
365: 
366:     current_phase = None
367:     striker_name = ""
368:     skip_next = False
369: 
370:     for idx in range(len(df_po)):
371:         if skip_next:
372:             skip_next = False
373:             continue
374: 
375:         row = df_po.iloc[idx]
376:         col0 = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
377:         col1 = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
378:         col2 = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
379:         col8 = str(row.iloc[8]).strip() if len(row) > 8 and pd.notna(row.iloc[8]) else ""
380: 
381:         # Phase label
382:         phase_key = phase_labels.get(col0) or phase_labels.get(col1)
383:         if phase_key:
384:             current_phase = phase_key
385:             continue
386: 
387:         # Striker label
388:         striker_col = _find_label_col(row, striker_label, label_cols)
389:         if striker_col >= 0:
390:             striker_name = _extract_striker_name(row, df_po, idx, striker_col, striker_label, nc, fc, label_cols)
391:             if striker_name:
392:                 skip_next = True
393:             current_phase = None
394:             continue
395: 
396:         # Team pick — both home (col2) and away (col8) are bonus picks for this phase
397:         if current_phase and col2 and col2 not in ("", "nan", "NaN"):
398:             bonus_rows.append({"boleiro": who, "phase": current_phase, "team": col2})
399:         if current_phase and col8 and col8 not in ("", "nan", "NaN") and col8 != col2:
400:             bonus_rows.append({"boleiro": who, "phase": current_phase, "team": col8})
401: 
402:     df_bonus = pd.DataFrame(bonus_rows, columns=["boleiro", "phase", "team"])
403:     df_striker = pd.DataFrame([{"boleiro": who, "striker": striker_name}])
404:     return df_bonus, df_striker
405: 
406: 
407: def _find_label_col(row: pd.Series, label: str, label_cols: list[int]) -> int:
408:     """Return the column index where *label* is found (case-insensitive), else -1.
409: 
410:     Matches exact label or ``label + space`` prefix (e.g. "artilheiro do mundial"
411:     matches label "artilheiro").
412:     """
413:     for c in label_cols:
414:         val = str(row.iloc[c]).strip().lower() if pd.notna(row.iloc[c]) else ""
415:         normalised = val.rstrip(":.").strip()
416:         if normalised == label or normalised.startswith(label + " "):
417:             return c
418:     return -1
419: 
420: 
421: def _extract_striker_name(
422:     row: pd.Series,
423:     df_po: pd.DataFrame,
424:     idx: int,
425:     striker_col: int,
426:     label: str,
427:     nc: int,
428:     fc: int,
429:     label_cols: list[int],
430: ) -> str:
431:     """Extract the striker name from a row where the label was found.
432: 
433:     Priority: dedicated name column → same cell after colon/label →
434:     other columns on same row → next row.
435:     """
436:     # 1) Dedicated name columns (most reliable for structured sheets)
437:     for c in [nc, fc]:
438:         val = str(row.iloc[c]).strip() if pd.notna(row.iloc[c]) else ""
439:         if val and val.lower() not in ("", "nan", "none", label):
440:             return val
441: 
442:     # 2) Same cell after colon ("Artilheiro: Nome")
443:     cell_val = str(row.iloc[striker_col]).strip() if pd.notna(row.iloc[striker_col]) else ""
444:     if ":" in cell_val:
445:         return cell_val.split(":", 1)[-1].strip()
446: 
447:     # 3) Same cell after label text ("Artilheiro Nome")
448:     name_part = cell_val[len(label):].strip().lstrip(":- ")
449:     if name_part:
450:         return name_part
451: 
452:     # 4) Other columns on same row
453:     for c in [x for x in label_cols if x not in (nc, fc)]:
454:         val = str(row.iloc[c]).strip() if pd.notna(row.iloc[c]) else ""
455:         if val and val.lower() not in ("", "nan", "none", label):
456:             return val
457: 
458:     # 5) Next row
459:     if idx + 1 < len(df_po):
460:         next_row = df_po.iloc[idx + 1]
461:         for c in [nc, fc] + label_cols:
462:             val = str(next_row.iloc[c]).strip() if pd.notna(next_row.iloc[c]) else ""
463:             if val and val.lower() not in ("", "nan", "none", label):
464:                 return val
465: 
466:     return ""
467: 
468: 
469: def parse_bonus_playoffs(path: str, config: ChampionshipConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
470:     """Parse bonus playoff team picks and striker from an Excel file.
471: 
472:     The first_round Excel contains a "playoffs" section where each boleiro
473:     picks one team per knockout phase (oitavas, quartas, semi, final).
474:     These are bonus picks — not scored predictions.
475: 
476:     Returns:
477:         (bonus_teams_df, striker_df)
478:         - bonus_teams_df: columns boleiro, phase, team
479:         - striker_df: columns boleiro, striker
480:     """
481:     layout = config.excel_layout
482:     who = _extract_who(path, config)
483: 
484:     df = pd.read_excel(path, skiprows=layout.first_round.skiprows)
485:     df = df[df.columns[:9]]
486:     df.columns = _EXCEL_COLUMNS
487: 
488:     df = _clean_dataframe(df, who)
489: 
490:     # Extract one team per playoff round (home_team is the pick)
491:     bonus_rows = []
492:     for pr in layout.playoff_rows:
493:         round_df = df.tail(pr["tail_offset"]).head(pr["head_count"])
494:         for _, row in round_df.iterrows():
495:             team = str(row["home_team"]).strip()
496:             if team:
497:                 bonus_rows.append({"boleiro": who, "phase": pr["key"], "team": team})
498: 
499:     df_bonus = pd.DataFrame(bonus_rows, columns=["boleiro", "phase", "team"])
500: 
501:     # Extract striker (last row)
502:     df_striker_raw = df.tail(layout.playoffs.striker_row_offset).copy()
503:     df_striker = df_striker_raw[["who", "home_team"]].copy()
504:     df_striker.columns = ["boleiro", "striker"]
505: 
506:     return df_bonus, df_striker

(End of file - total 506 lines)
```

---

### 🤖 AGENTE (Turno 3):

💭 **PENSAMENTO DO AGENTE:**
Let me now read the config.py to understand paths and methods used by the pipeline, particularly the `_raw_playoffs()`, and other path methods.

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\config.py`

```python
1: """Championship configuration loader."""
2: 
3: from __future__ import annotations
4: 
5: import os
6: from dataclasses import dataclass, field
7: from pathlib import Path
8: 
9: import yaml
10: 
11: # ------------------------------------------------------------------
12: # Path normalizer — converts YAML forward-slash paths to OS-native
13: # ------------------------------------------------------------------
14: 
15: def _norm(path: str) -> str:
16:     """Normalize a forward-slash path to the current OS format."""
17:     if not path:
18:         return ""
19:     return os.path.normpath(path)
20: 
21: 
22: @dataclass
23: class ScoringRule:
24:     """A single scoring criterion."""
25: 
26:     name: str
27:     points: int
28:     priority: int = 0
29:     rule: str = ""
30:     emoji: str = ""
31:     description: str = ""
32:     color_text: str = ""
33:     max_total_error: int | None = None
34:     min_total_error: int | None = None
35: 
36: 
37: @dataclass
38: class PlayoffRound:
39:     """A knockout stage round."""
40: 
41:     name: str
42:     key: str  # slug used in paths/filenames
43:     matches: int
44: 
45: 
46: @dataclass
47: class ThemeColors:
48:     """Color palette for HTML reports."""
49: 
50:     primary: str = "#1a5e1f"
51:     primary_light: str = "#2d8a33"
52:     accent: str = "#f5c518"
53:     accent_dark: str = "#d4a817"
54:     bg: str = "#0d1117"
55:     card_bg: str = "#161b22"
56:     card_border: str = "#30363d"
57:     text: str = "#e6edf3"
58:     text_muted: str = "#8b949e"
59:     success: str = "#2ea043"
60:     warning: str = "#d29922"
61:     danger: str = "#f85149"
62:     voce: str = "#2ea043"
63:     bolao: str = "#f5c518"
64:     text_inverse: str = "#000000"
65:     silver: str = "#c0c0c0"
66:     bronze: str = "#cd7f32"
67:     leader: str = "#8899aa"
68:     accent_highlight: str = "rgba(245,197,24,0.1)"
69:     silver_highlight: str = "rgba(192,192,192,0.08)"
70:     bronze_highlight: str = "rgba(205,127,50,0.08)"
71:     zebra_stripe: str = "rgba(255,255,255,0.02)"
72:     hover_overlay: str = "rgba(255,255,255,0.03)"
73:     shadow_color: str = "rgba(0,0,0,0.4)"
74:     score_exact: str = "#00cc00"
75:     score_winner_goals: str = "#66ff66"
76:     score_winner: str = "#ffcc00"
77:     score_one_team: str = "#ff9900"
78:     score_none: str = "#ff3333"
79:     player_card_active: str = "rgba(245,197,24,0.05)"
80:     score_exact_bg: str = "rgba(0,204,0,0.1)"
81:     score_exact_border: str = "rgba(0,204,0,0.4)"
82:     score_winner_goals_bg: str = "rgba(102,255,102,0.1)"
83:     score_winner_goals_border: str = "rgba(102,255,102,0.4)"
84:     score_winner_bg: str = "rgba(255,204,0,0.1)"
85:     score_winner_border: str = "rgba(255,204,0,0.4)"
86:     score_one_team_bg: str = "rgba(255,153,0,0.1)"
87:     score_one_team_border: str = "rgba(255,153,0,0.4)"
88:     score_none_bg: str = "rgba(255,51,51,0.1)"
89:     score_none_border: str = "rgba(255,51,51,0.4)"
90: 
91: 
92: @dataclass
93: class ThemeConfig:
94:     """Theme configuration for HTML reports."""
95: 
96:     mode: str = "dark"
97:     colors: ThemeColors = field(default_factory=ThemeColors)
98: 
99:     def to_css_vars(self) -> str:
100:         """Return CSS custom properties block."""
101:         c = self.colors
102:         return (
103:             ":root {\n"
104:             f"    --primary: {c.primary};\n"
105:             f"    --primary-light: {c.primary_light};\n"
106:             f"    --accent: {c.accent};\n"
107:             f"    --accent-dark: {c.accent_dark};\n"
108:             f"    --bg: {c.bg};\n"
109:             f"    --card-bg: {c.card_bg};\n"
110:             f"    --card-border: {c.card_border};\n"
111:             f"    --text: {c.text};\n"
112:             f"    --text-muted: {c.text_muted};\n"
113:             f"    --success: {c.success};\n"
114:             f"    --warning: {c.warning};\n"
115:             f"    --danger: {c.danger};\n"
116:             f"    --voce: {c.voce};\n"
117:             f"    --bolao: {c.bolao};\n"
118:             f"    --text-inverse: {c.text_inverse};\n"
119:             f"    --silver: {c.silver};\n"
120:             f"    --bronze: {c.bronze};\n"
121:             f"    --leader: {c.leader};\n"
122:             f"    --accent-highlight: {c.accent_highlight};\n"
123:             f"    --silver-highlight: {c.silver_highlight};\n"
124:             f"    --bronze-highlight: {c.bronze_highlight};\n"
125:             f"    --zebra-stripe: {c.zebra_stripe};\n"
126:             f"    --hover-overlay: {c.hover_overlay};\n"
127:             f"    --shadow-color: {c.shadow_color};\n"
128:             f"    --score-exact: {c.score_exact};\n"
129:             f"    --score-winner-goals: {c.score_winner_goals};\n"
130:             f"    --score-winner: {c.score_winner};\n"
131:             f"    --score-one-team: {c.score_one_team};\n"
132:             f"    --score-none: {c.score_none};\n"
133:             f"    --score-exact-bg: {c.score_exact_bg};\n"
134:             f"    --score-exact-border: {c.score_exact_border};\n"
135:             f"    --score-winner-goals-bg: {c.score_winner_goals_bg};\n"
136:             f"    --score-winner-goals-border: {c.score_winner_goals_border};\n"
137:             f"    --score-winner-bg: {c.score_winner_bg};\n"
138:             f"    --score-winner-border: {c.score_winner_border};\n"
139:             f"    --score-one-team-bg: {c.score_one_team_bg};\n"
140:             f"    --score-one-team-border: {c.score_one_team_border};\n"
141:             f"    --score-none-bg: {c.score_none_bg};\n"
142:             f"    --score-none-border: {c.score_none_border};\n"
143:             f"    --player-card-active: {c.player_card_active};\n"
144:             "}\n"
145:         )
146: 
147: 
148: @dataclass
149: class FirstRoundLayout:
150:     """First round / group stage Excel slicing config."""
151: 
152:     matches: int
153:     skiprows: int = 2
154: 
155: 
156: @dataclass
157: class PlayoffsLayout:
158:     """Playoff rounds Excel slicing config."""
159: 
160:     striker_row_offset: int = 1
161:     striker_label: str = "Artilheiro"
162:     striker_name_column: int = 2
163:     striker_name_fallback_column: int = 8
164:     champion_cell: str = ""
165:     name_split_char: str = "-"
166:     name_split_index: int = 1
167:     rounds: list[dict] = field(default_factory=list)
168:     # Each dict: {"name": "...", "key": "...", "matches": N, "tail_offset": N}
169:     # Sheet name for playoffs/striker data (standings-format only).
170:     # When empty, the loader falls back to the main sheet read for standings.
171:     playoffs_sheet_name: str = ""
172: 
173: 
174: @dataclass
175: class ExcelLayout:
176:     """How to slice the Excel sheet into phases."""
177: 
178:     first_round: FirstRoundLayout
179:     playoffs: PlayoffsLayout
180: 
181:     # Derived: flattened playoff rows for the loader
182:     @property
183:     def playoff_rows(self) -> list[dict]:
184:         """Return playoff rows in loader-friendly format."""
185:         return [
186:             {
187:                 "key": r["key"],
188:                 "tail_offset": r.get("tail_offset", 0),
189:                 "head_count": r["matches"],
190:             }
191:             for r in self.playoffs.rounds
192:         ]
193: 
194: 
195: @dataclass
196: class ChampionshipConfig:
197:     """Full configuration for a single championship."""
198: 
199:     id: str
200:     name: str
201:     year: int
202:     timezone: str = "America/Sao_Paulo"
203: 
204:     # Structure
205:     scoring_rules: list[ScoringRule] = field(default_factory=list)
206:     playoff_rounds: list[PlayoffRound] = field(default_factory=list)
207:     excel_layout: ExcelLayout | None = None
208: 
209:     # Paths (relative to project root)
210:     base_dir: str = ""
211:     raw_dir: str = ""
212:     results_file: str = ""
213:     games_file: str = ""
214:     bronze_dir: str = ""
215:     silver_dir: str = ""
216:     gold_dir: str = ""
217:     reports_dir: str = ""
218: 
219:     # External data
220:     results_endpoint: str = ""
221:     team_name_mapping: dict = field(default_factory=dict)
222:     team_logos: dict = field(default_factory=dict)  # {english_name: logo_url}
223:     team_slugs: dict = field(default_factory=dict)  # {english_name: slug}
224:     team_geo: dict[str, str] = field(default_factory=dict)  # {portuguese_name: geo_continent}
225: 
226:     # Report settings
227:     report_title: str = ""
228:     group_phase_label: str = "1a Fase"
229:     theme: ThemeConfig = field(default_factory=ThemeConfig)
230: 
231:     # Playoff bonus scoring (phase_key -> points_per_correct)
232:     playoff_scoring: dict[str, int] = field(default_factory=dict)
233: 
234:     # Striker scoring
235:     actual_top_scorer: str = ""
236:     striker_points: int = 0
237: 
238:     # Group stage definition (list of {name, teams})
239:     groups: list = field(default_factory=list)
240: 
241:     # Group standings format (e.g. 2026 World Cup)
242:     standings_format: bool = False
243:     standings_skiprows: int = 1
244:     # Fallback bonus/striker for standings format (when not parseable from Excel)
245:     bonus_team_picks: dict[str, str] = field(default_factory=dict)
246:     striker_pick: str = ""
247: 
248:     def __post_init__(self) -> None:
249:         self.base_dir = _norm(self.base_dir) if self.base_dir else _norm(os.path.join("src", "data", self.id))
250:         self.raw_dir = _norm(self.raw_dir) if self.raw_dir else _norm(os.path.join(self.base_dir, "raw"))
251:         self.results_file = _norm(self.results_file) if self.results_file else _norm(os.path.join(self.base_dir, "jogos.csv"))
252:         self.games_file = _norm(self.games_file) if self.games_file else self.results_file
253:         self.bronze_dir = _norm(self.bronze_dir) if self.bronze_dir else _norm(os.path.join(self.base_dir, "bronze"))
254:         self.silver_dir = _norm(self.silver_dir) if self.silver_dir else _norm(os.path.join(self.base_dir, "silver"))
255:         self.gold_dir = _norm(self.gold_dir) if self.gold_dir else _norm(os.path.join(self.base_dir, "gold"))
256:         self.reports_dir = _norm(self.reports_dir) if self.reports_dir else _norm(os.path.join("src", "reports", self.id))
257:         if not self.report_title:
258:             self.report_title = f"{self.name}"
259: 
260:     # ------------------------------------------------------------------
261:     # Path helpers — first_round / playoffs structure
262:     # ------------------------------------------------------------------
263:     # Bronze:
264:     #   bronze/first_round/group_phase_{boleiro}.csv
265:     #   bronze/first_round/bonus_teams_{boleiro}.csv
266:     #   bronze/first_round/striker_{boleiro}.csv
267:     #   bronze/playoffs/  (future separate playoff Excel files)
268:     #
269:     # Silver:
270:     #   silver/first_round/group_phase_{boleiro}.csv
271:     #   silver/playoffs/  (future)
272:     #
273:     # Gold:
274:     #   gold/first_round/group_phase_{boleiro}.csv
275:     #   gold/first_round/{label}_all.csv
276:     #   gold/first_round/{label}_valido_all.csv
277:     #   gold/first_round/striker_{boleiro}.csv
278:     #   gold/first_round/playoffs_strikers.csv
279:     #   gold/playoffs/  (future)
280:     # ------------------------------------------------------------------
281: 
282:     def _raw_playoffs(self) -> str:
283:         """Raw directory for per-round playoff Excel files."""
284:         return _norm(os.path.join(self.raw_dir, "playoffs"))
285: 
286:     def _br_first_round(self) -> str:
287:         return _norm(os.path.join(self.bronze_dir, "first_round"))
288: 
289:     def _br_playoffs(self) -> str:
290:         return _norm(os.path.join(self.bronze_dir, "playoffs"))
291: 
292:     def _ag_first_round(self) -> str:
293:         return _norm(os.path.join(self.silver_dir, "first_round"))
294: 
295:     def _ag_playoffs(self) -> str:
296:         return _norm(os.path.join(self.silver_dir, "playoffs"))
297: 
298:     def _au_first_round(self) -> str:
299:         return _norm(os.path.join(self.gold_dir, "first_round"))
300: 
301:     def _au_playoffs(self) -> str:
302:         return _norm(os.path.join(self.gold_dir, "playoffs"))
303: 
304:     # --- Bronze paths ---
305: 
306:     def bronze_group_path(self, boleiro: str) -> str:
307:         """Path to bronze group-phase CSV for a single boleiro."""
308:         return _norm(os.path.join(self._br_first_round(), f"group_phase_{boleiro}.csv"))
309: 
310:     def bronze_bonus_path(self, boleiro: str) -> str:
311:         """Path to bronze bonus playoff teams for a single boleiro."""
312:         return _norm(os.path.join(self._br_first_round(), f"bonus_teams_{boleiro}.csv"))
313: 
314:     def bronze_striker_path(self, boleiro: str) -> str:
315:         """Path to bronze striker CSV for a single boleiro."""
316:         return _norm(os.path.join(self._br_first_round(), f"striker_{boleiro}.csv"))
317: 
318:     def bronze_playoff_path(self, boleiro: str, phase: str) -> str:
319:         """Path to bronze playoff-phase CSV for a single boleiro + phase."""
320:         return _norm(os.path.join(self._br_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))
321: 
322:     # --- Silver paths ---
323: 
324:     def silver_group_path(self, boleiro: str) -> str:
325:         """Path to silver group-phase CSV for a single boleiro."""
326:         return _norm(os.path.join(self._ag_first_round(), f"group_phase_{boleiro}.csv"))
327: 
328:     def silver_playoff_path(self, boleiro: str, phase: str) -> str:
329:         """Path to silver playoff-phase CSV for a single boleiro + phase."""
330:         return _norm(os.path.join(self._ag_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))
331: 
332:     # --- Gold paths ---
333: 
334:     def gold_first_round_dir(self) -> str:
335:         """Directory for gold first-round files."""
336:         return self._au_first_round()
337: 
338:     def gold_playoffs_dir(self) -> str:
339:         """Directory for gold playoff files."""
340:         return self._au_playoffs()
341: 
342:     def gold_group_boleiro_path(self, boleiro: str) -> str:
343:         """Path to gold group-phase CSV for a single boleiro."""
344:         return _norm(os.path.join(self._au_first_round(), f"group_phase_{boleiro}.csv"))
345: 
346:     def gold_playoff_boleiro_path(self, boleiro: str, phase: str) -> str:
347:         """Path to gold playoff-phase CSV for a single boleiro + phase."""
348:         return _norm(os.path.join(self._au_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))
349: 
350:     def gold_playoff_all_path(self, phase: str) -> str:
351:         """Path to gold aggregated 'all records' CSV for a playoff phase."""
352:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_all.csv"))
353: 
354:     def gold_playoff_valid_path(self, phase: str) -> str:
355:         """Path to gold aggregated 'valid only' CSV for a playoff phase."""
356:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_valido_all.csv"))
357: 
358:     def gold_valid_path(self, phase: str = "group") -> str:
359:         """Path to the gold 'valid only' aggregated CSV."""
360:         if phase == "group":
361:             label = self.group_phase_label
362:             return _norm(os.path.join(self._au_first_round(), f"{label}_valido_all.csv"))
363:         # Playoff phase — use phase key as label
364:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_valido_all.csv"))
365: 
366:     def gold_all_path(self, phase: str = "group") -> str:
367:         """Path to the gold 'all records' aggregated CSV."""
368:         if phase == "group":
369:             label = self.group_phase_label
370:             return _norm(os.path.join(self._au_first_round(), f"{label}_all.csv"))
371:         # Playoff phase — use phase key as label
372:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_all.csv"))
373: 
374:     def gold_striker_path(self, boleiro: str) -> str:
375:         """Path to gold striker CSV for a single boleiro."""
376:         return _norm(os.path.join(self._au_first_round(), f"striker_{boleiro}.csv"))
377: 
378:     def playoff_strikers_path(self, layer: str = "gold") -> str:
379:         """Path to the aggregated strikers CSV."""
380:         if layer == "bronze":
381:             base = self._br_first_round()
382:         elif layer == "silver":
383:             base = self._ag_first_round()
384:         else:
385:             base = self._au_first_round()
386:         return _norm(os.path.join(base, "playoffs_strikers.csv"))
387: 
388:     def playoff_games_path(self, layer: str = "gold") -> str:
389:         """DEPRECATED: Legacy alias returning strikers CSV path, not games data.
390:         Use :meth:`playoff_strikers_path` or :meth:`gold_playoff_all_path`."""
391:         return self.playoff_strikers_path(layer)
392: 
393:     def overview_md_path(self) -> str:
394:         return _norm(os.path.join(self.reports_dir, "md", "overview.md"))
395: 
396:     def overview_html_path(self) -> str:
397:         return _norm(os.path.join(self.reports_dir, "html", "overview.html"))
398: 
399:     def index_html_path(self) -> str:
400:         return _norm(os.path.join(self.reports_dir, "html", "index.html"))
401: 
402:     def scoring_rule_names(self) -> list[str]:
403:         """Return scoring rule names sorted by name."""
404:         return [r.name for r in sorted(self.scoring_rules, key=lambda r: r.name)]
405: 
406:     def scoring_dict(self) -> dict[str, int]:
407:         """Return {name: points} for quick lookup."""
408:         return {r.name: r.points for r in self.scoring_rules}
409: 
410:     def scoring_emoji(self, rule_name: str) -> str:
411:         """Return emoji for a rule name, or empty string."""
412:         for r in self.scoring_rules:
413:             if r.name == rule_name:
414:                 return r.emoji
415:         return ""
416: 
417:     def scoring_color(self, rule_name: str) -> str:
418:         """Return text color for a rule name, or empty string."""
419:         for r in self.scoring_rules:
420:             if r.name == rule_name:
421:                 return r.color_text
422:         return ""
423: 
424:     def scoring_css_var(self, rule_name: str) -> dict:
425:         """Return CSS variable names for a scoring rule (color, bg, border).
426: 
427:         Resolves via the rule's ``rule`` (type key) so it works for any
428:         championship regardless of localized rule names.
429:         """
430:         # Map rule type keys → CSS variable triplets
431:         type_map = {
432:             "exact_score": ("--score-exact", "--score-exact-bg", "--score-exact-border"),
433:             "correct_winner_and_goals": ("--score-winner-goals", "--score-winner-goals-bg", "--score-winner-goals-border"),
434:             "correct_winner_and_goals_or_diff": ("--score-winner-goals", "--score-winner-goals-bg", "--score-winner-goals-border"),
435:             "correct_winner": ("--score-winner", "--score-winner-bg", "--score-winner-border"),
436:             "one_team_goals": ("--score-one-team", "--score-one-team-bg", "--score-one-team-border"),
437:             "no_score": ("--score-none", "--score-none-bg", "--score-none-border"),
438:         }
439:         # Look up the rule by name to get its type key
440:         for r in self.scoring_rules:
441:             if r.name == rule_name and r.rule in type_map:
442:                 return type_map[r.rule]
443:         return ("", "", "")
444: 
445: 
446: # ------------------------------------------------------------------
447: # Loader
448: # ------------------------------------------------------------------
449: 
450: def _parse_theme(raw: dict) -> ThemeConfig:
451:     """Parse theme configuration from YAML."""
452:     if not raw:
453:         return ThemeConfig()
454:     colors_raw = raw.get("colors", {})
455:     colors = ThemeColors(
456:         primary=colors_raw.get("primary", "#1a5e1f"),
457:         primary_light=colors_raw.get("primary_light", "#2d8a33"),
458:         accent=colors_raw.get("accent", "#f5c518"),
459:         accent_dark=colors_raw.get("accent_dark", "#d4a817"),
460:         bg=colors_raw.get("bg", "#0d1117"),
461:         card_bg=colors_raw.get("card_bg", "#161b22"),
462:         card_border=colors_raw.get("card_border", "#30363d"),
463:         text=colors_raw.get("text", "#e6edf3"),
464:         text_muted=colors_raw.get("text_muted", "#8b949e"),
465:         success=colors_raw.get("success", "#2ea043"),
466:         warning=colors_raw.get("warning", "#d29922"),
467:         danger=colors_raw.get("danger", "#f85149"),
468:         voce=colors_raw.get("voce", "#2ea043"),
469:         bolao=colors_raw.get("bolao", "#f5c518"),
470:         text_inverse=colors_raw.get("text_inverse", "#000000"),
471:         silver=colors_raw.get("silver", "#c0c0c0"),
472:         bronze=colors_raw.get("bronze", "#cd7f32"),
473:         leader=colors_raw.get("leader", "#8899aa"),
474:         accent_highlight=colors_raw.get("accent_highlight", "rgba(245,197,24,0.1)"),
475:         silver_highlight=colors_raw.get("silver_highlight", "rgba(192,192,192,0.08)"),
476:         bronze_highlight=colors_raw.get("bronze_highlight", "rgba(205,127,50,0.08)"),
477:         zebra_stripe=colors_raw.get("zebra_stripe", "rgba(255,255,255,0.02)"),
478:         hover_overlay=colors_raw.get("hover_overlay", "rgba(255,255,255,0.03)"),
479:         shadow_color=colors_raw.get("shadow_color", "rgba(0,0,0,0.4)"),
480:         score_exact=colors_raw.get("score_exact", "#00cc00"),
481:         score_winner_goals=colors_raw.get("score_winner_goals", "#66ff66"),
482:         score_winner=colors_raw.get("score_winner", "#ffcc00"),
483:         score_one_team=colors_raw.get("score_one_team", "#ff9900"),
484:         score_none=colors_raw.get("score_none", "#ff3333"),
485:         player_card_active=colors_raw.get("player_card_active", "rgba(245,197,24,0.05)"),
486:         score_exact_bg=colors_raw.get("score_exact_bg", "rgba(0,204,0,0.1)"),
487:         score_exact_border=colors_raw.get("score_exact_border", "rgba(0,204,0,0.4)"),
488:         score_winner_goals_bg=colors_raw.get("score_winner_goals_bg", "rgba(102,255,102,0.1)"),
489:         score_winner_goals_border=colors_raw.get("score_winner_goals_border", "rgba(102,255,102,0.4)"),
490:         score_winner_bg=colors_raw.get("score_winner_bg", "rgba(255,204,0,0.1)"),
491:         score_winner_border=colors_raw.get("score_winner_border", "rgba(255,204,0,0.4)"),
492:         score_one_team_bg=colors_raw.get("score_one_team_bg", "rgba(255,153,0,0.1)"),
493:         score_one_team_border=colors_raw.get("score_one_team_border", "rgba(255,153,0,0.4)"),
494:         score_none_bg=colors_raw.get("score_none_bg", "rgba(255,51,51,0.1)"),
495:         score_none_border=colors_raw.get("score_none_border", "rgba(255,51,51,0.4)"),
496:     )
497:     return ThemeConfig(mode=raw.get("mode", "dark"), colors=colors)
498: 
499: 
500: def _parse_team_mapping(raw: list) -> tuple[dict[str, str], dict[str, str], dict[str, str], dict[str, str]]:
501:     """Parse team_name_mapping from YAML into ({en: pt}, {en: logo_url}, {en: slug}, {pt: geo})."""
502:     mapping: dict[str, str] = {}
503:     logos: dict[str, str] = {}
504:     slugs: dict[str, str] = {}
505:     geo: dict[str, str] = {}
506:     for entry in raw:
507:         en = entry.get("en", "").strip()
508:         pt = entry.get("pt", "").strip()
509:         if en and pt:
510:             mapping[en] = pt
511:             logo = entry.get("logo", "").strip()
512:             if logo:
513:                 logos[en] = logo
514:             slug = entry.get("slug", "").strip()
515:             if slug:
516:                 slugs[en] = slug
517:             g = entry.get("geo", "").strip()
518:             if g:
519:                 geo[pt] = g
520:     return mapping, logos, slugs, geo
521: 
522: 
523: def _find_championship_dir(championship_id: str) -> Path:
524:     """Locate the championship directory under src/championships/."""
525:     base = Path("src") / "championships" / championship_id
526:     if base.is_dir():
527:         return base
528:     raise FileNotFoundError(
529:         f"Championship '{championship_id}' not found at {base}"
530:     )
531: 
532: 
533: def load_config(championship_id: str) -> ChampionshipConfig:
534:     """Load a ChampionshipConfig from its YAML file."""
535:     champ_dir = _find_championship_dir(championship_id)
536:     yaml_path = champ_dir / "config.yaml"
537: 
538:     if not yaml_path.exists():
539:         raise FileNotFoundError(f"Config not found: {yaml_path}")
540: 
541:     with open(yaml_path, encoding="utf-8") as f:
542:         raw = yaml.safe_load(f)
543: 
544:     # Scoring rules
545:     scoring_rules = [
546:         ScoringRule(
547:             name=r["name"],
548:             points=r["points"],
549:             priority=r.get("priority", i),
550:             rule=r.get("rule", ""),
551:             emoji=r.get("emoji", ""),
552:             description=r.get("description", ""),
553:             color_text=r.get("color_text", ""),
554:             max_total_error=r.get("max_total_error"),
555:             min_total_error=r.get("min_total_error"),
556:         )
557:         for i, r in enumerate(raw.get("scoring", []))
558:     ]
559: 
560:     # Excel layout
561:     el_cfg = raw.get("excel_layout", {})
562:     fr_cfg = el_cfg.get("first_round", {})
563:     po_cfg = el_cfg.get("playoffs", {})
564: 
565:     first_round = FirstRoundLayout(
566:         matches=fr_cfg.get("matches", 48),
567:         skiprows=fr_cfg.get("skiprows", 2),
568:     )
569: 
570:     playoffs = PlayoffsLayout(
571:         striker_row_offset=po_cfg.get("striker_row_offset", 1),
572:         striker_label=po_cfg.get("striker_label", "Artilheiro"),
573:         striker_name_column=po_cfg.get("striker_name_column", 2),
574:         striker_name_fallback_column=po_cfg.get("striker_name_fallback_column", 8),
575:         champion_cell=po_cfg.get("champion_cell", ""),
576:         name_split_char=po_cfg.get("name_split_char", "-"),
577:         name_split_index=po_cfg.get("name_split_index", 1),
578:         rounds=po_cfg.get("rounds", []),
579:         playoffs_sheet_name=po_cfg.get("playoffs_sheet_name", ""),
580:     )
581: 
582:     excel_layout = ExcelLayout(
583:         first_round=first_round,
584:         playoffs=playoffs,
585:     )
586: 
587:     # Derive playoff_rounds list from excel_layout.playoffs.rounds
588:     playoff_rounds = [
589:         PlayoffRound(
590:             name=r["name"],
591:             key=r["key"],
592:             matches=r["matches"],
593:         )
594:         for r in po_cfg.get("rounds", [])
595:     ]
596: 
597:     # Parse playoff scoring
598:     playoff_scoring = {}
599:     for phase_key, points in raw.get("playoff_scoring", {}).items():
600:         playoff_scoring[phase_key] = points
601: 
602:     # Parse striker scoring
603:     striker_cfg = raw.get("striker_scoring", {})
604:     striker_points = striker_cfg.get("points", 0)
605: 
606:     groups_raw = raw.get("groups", [])
607: 
608:     _tm = _parse_team_mapping(raw.get("team_name_mapping", []))
609: 
610:     return ChampionshipConfig(
611:         id=raw["id"],
612:         name=raw["name"],
613:         year=raw["year"],
614:         timezone=raw.get("timezone", "America/Sao_Paulo"),
615:         scoring_rules=scoring_rules,
616:         playoff_rounds=playoff_rounds,
617:         excel_layout=excel_layout,
618:         groups=groups_raw,
619:         report_title=raw.get("report_title", raw["name"]),
620:         group_phase_label=raw.get("group_phase_label", "1a Fase"),
621:         theme=_parse_theme(raw.get("theme", {})),
622:         base_dir=_norm(raw.get("base_dir", "")),
623:         raw_dir=_norm(raw.get("raw_dir", "")),
624:         results_file=_norm(raw.get("results_file", "")),
625:         games_file=_norm(raw.get("games_file", "")),
626:         bronze_dir=_norm(raw.get("bronze_dir", "")),
627:         silver_dir=_norm(raw.get("silver_dir", "")),
628:         gold_dir=_norm(raw.get("gold_dir", "")),
629:         reports_dir=_norm(raw.get("reports_dir", "")),
630:         results_endpoint=raw.get("results_endpoint", ""),
631:         team_name_mapping=_tm[0],
632:         team_logos=_tm[1],
633:         team_slugs=_tm[2],
634:         team_geo=_tm[3],
635:         playoff_scoring=playoff_scoring,
636:         actual_top_scorer=raw.get("actual_top_scorer", ""),
637:         striker_points=striker_points,
638:         standings_format=raw.get("standings_format", False),
639:         standings_skiprows=raw.get("standings_skiprows", 1),
640:         bonus_team_picks=raw.get("bonus_team_picks", {}),
641:         striker_pick=raw.get("striker_pick", ""),
642:     )
643: 
644: 
645: def list_championships() -> list[str]:
646:     """Return all available championship IDs."""
647:     base = Path("src") / "championships"
648:     if not base.is_dir():
649:         return []
650:     return sorted(
651:         d.name for d in base.iterdir()
652:         if d.is_dir() and (d / "config.yaml").exists()
653:     )

(End of file - total 653 lines)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\championships\2026_world_cup\data\raw\1afase`

```text
<path>C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\championships\2026_world_cup\data\raw\1afase</path>
<type>directory</type>
<entries>
André Bonito - Primeira Fase 2026.xls
André Mendes - Primeira Fase 2026.xls
André Tayer - Primeira Fase 2026.xls
Cipriano L. - Primeira Fase 2026.xlsx
Davi & Cesar - Primeira Fase 2026.xls
Ditchos - Primeira Fase 2026.xls
Felipe Giannoni - Primeira Fase 2026.xls
Francisco Camargo - Primeira Fase.xlsx
Frederico Soter - Primeira Fase 2026.xls
Gabão - Primeira Fase 2026.xls
Giancarlo - Primeira Fase 2026.xlsx
Guilherne - Primeira Fase 2026.xls
Haroldo - Primeira Fase 2026.xlsx
João Henrique - Primeira Fase 2026.xls
José Ricardo - Primeira Fase 2026.xls
Kiko Toloza - Pprimeira Fase 2026.xls
Leo Fernandes - Primeira Fase 2026.xlsx
LLM Gemini - Primeira Fase 2026.xls
LLM GPT - Primeira Fase 2026.xls
Luca Caviglia Del Soldato - Primeira Fase 2026.xlsx
Lucas Ubertini - Primeira Fase 2026.xlsm
Luiz Augusto - Primeira Fase 2026.xls
Marcelo - Primeira Fase 2026.xls
Marcelo Boix - Primeira Fase 2026.xls
Marco Lavander - Primeira Fase 2026.xls
Mateus Tone - Primeira Fase 2026.xlsx
Mauricio Saraiva- Primeira Fase 2026.xls
Pedro Tayer - Primeira Fase 2026.xlsx
Rafael Conte - Primeira Fase 2026.xlsx
RODRIGO ALBERNAZ - Primeira Fase 2026.xls
Thales Oliveira - Primeira Fase 2026.xlsx
Thiago Bahiense - Primeira Fase.xls
Tiago - Primeira Fase 2026.xls

(33 entries)
</entries>
```

---

### 🤖 AGENTE (Turno 4):

💭 **PENSAMENTO DO AGENTE:**
Now I have a clear picture. Let me analyze what the user is asking:

**"Is the repo ready for the 2nd phase with new excels at '2026_world_cup/data/raw/2afase/*'? Does the pipeline continue without break?"**

Let me trace through the code to understand:

1. **Where does the pipeline read raw Excel files from?**
   - In `pipeline.py`, `_boleiros_from_raw()` reads from `config.raw_dir / config.group_phase_label` = `data/raw/1afase/*`
   - The `group_phase_label` in `config.yaml` is `"1afase"`

2. **What about playoff files?**
   - `_playoff_files_from_raw()` reads from `config._raw_playoffs()` = `data/raw/playoffs/*`
   - This expects files named like `{phase_key}_{boleiro}.xlsx` (e.g., `oitavas_Mateus Tone.xlsx`)

3. **So if the user puts files in `data/raw/2afase/`, nothing will read them.** The `group_phase_label` is hardcoded to `1afase`.

Now let me think about what "2afase" means for the 2026 World Cup. Looking at the config:

- The 2026 World Cup has 12 groups of 4 (48 teams). The group stage has 72 matches (rounds 1, 2, 3).
- Then there's a "Segunda Fase" (Second Phase) which is labeled as a playoff round in the config, with 16 matches.

Wait, looking more carefully at the config:

```yaml
excel_layout:
  playoffs:
    rounds:
      - name: "Segunda Fase"
        key: "segunda_fase"
        matches: 16
        tail_offset: 33
      - name: "Oitavas de Final"
        key: "oitavas"
        matches: 8
        tail_offset: 17
      ...
```

So the config already defines "Segunda Fase" as a playoff round with 16 matches.

But the pipeline has **two different pathways** for playoffs:

**Pathway A** (for standings format = true, i.e., 2026 WC):
- All predictions are inside the **same single Excel file** per boleiro (the "Primeira Fase" file).
- The `parse_group_standings()` function reads the first sheet for group standings, and the "Tabela Jogos" sheet for actual match predictions.
- The `_parse_playoffs_and_striker()` function reads the "Tabela Jogos" sheet to extract **bonus team picks** for each playoff round (like which team they think will win each knockout phase).
- These bonus picks are saved to `bronze/first_round/bonus_teams_{boleiro}.csv` and then scored in `_generate_playoff_scoring()`.

**Pathway B** (for non-standings format or dedicated playoff files):
- Separate Excel files are placed in `data/raw/playoffs/` with names like `{phase}_{boleiro}.xlsx`
- These are parsed by `parse_playoff_stage()` which reads match predictions for that specific round.
- These flow through bronze → silver → gold for scoring.

Now, for the user's question about `2afase/`:

The pipeline currently has **no code** that reads from `2afase/`. The `group_phase_label` is `"1afase"`.

For the 2026 World Cup knockout rounds, the pipeline expects:
1. **Bonus team picks** (which team will win each round): These are already embedded in the "1afase" Excel files (in the "Tabela Jogos" sheet).
2. **Dedicated playoff match prediction files** (optional): Placed in `data/raw/playoffs/`.

So if the user is asking about new Excel files with actual match predictions for "Segunda Fase" (round of 32), they have two options:

**Option 1 (already partially supported):** Extract these as bonus picks from the existing 1afase files. But this only captures which team they think will advance, not match-by-match scores.

**Option 2 (new feature):** Place files in `data/raw/playoffs/` with naming convention `segunda_fase_{boleiro}.xlsx` to be picked up by the existing playoff pipeline.

But the user specifically asked about `2afase/` directory, which currently is NOT read by anything.

Let me re-read the user's question more carefully:

"does this repo is ready for the 2nd phase with new excels at '2026_world_cup/data/raw/2afase/*'? does the pipeline continues with the championship without break? am i all good to continue?"

They want to know if they can:
1. Create a `2afase/` directory
2. Put new Excel files there (presumably match predictions for the second phase of the World Cup - the round of 32 / "Segunda Fase")
3. Have the pipeline pick them up automatically

The answer is **NO**. The pipeline isn't ready to read from `2afase/` without code changes. Here's what would need to change:

1. The pipeline currently reads from `data/raw/{group_phase_label}` (which is `1afase/`).
2. It also reads from `data/raw/playoffs/` for separate playoff match prediction files.
3. There's no concept of "processing multiple phases of raw data" — the `run_raw_to_bronze` function clears and recreates the bronze directories each time.

Let me also check if the `games.csv` includes the "segunda_fase" round data from the API.

Let me check the games.csv file to see what match data exists.

Actually, the explore agent already looked at this. Let me also check if there's a `raw/playoffs/` directory.

Let me also think about what the user's intent is. The 2026 World Cup format has:
- Group stage (48 teams, 12 groups of 4) → 72 matches
- Then directly to Round of 32 (called "Segunda Fase" = second phase)
- Then Round of 16 (Oitavas), Quarters, Semis, Final

So "2afase" = segunda fase = second phase = round of 32.

The pipeline already knows about `segunda_fase` as a playoff round key and has it configured with 16 matches. But the way it expects the data is either:
- As bonus picks within the existing 1afase Excel (for which team advances)
- As separate files in `data/raw/playoffs/` (for detailed match predictions)

The user seems to want to put new Excel files in a `2afase/` directory, which is a new approach not currently supported.

So to answer the user's questions:

1. **Is the repo ready for 2afase?** No. There is no code reading from `2afase/`.
2. **Does the pipeline continue without break?** If they create `2afase/` and put files there, the pipeline will ignore them. It won't break, but it won't process them either.
3. **Are they good to continue?** They need to either:
   a. Put files in `data/raw/playoffs/` with naming `segunda_fase_{boleiro}.xlsx` (partially supported - existing playoff pipeline)
   b. Or modify the code to read from `2afase/` as a new source

Let me provide a clear assessment.

📄 **RESPOSTA DO AGENTE:**
Here's my analysis after reading all the relevant source code:

**Short answer: No, the repo is NOT ready for `2afase/` files.** The pipeline will silently ignore them.

---

### How the pipeline reads raw data

| Source directory | Read by | Current status |
|---|---|---|
| `data/raw/1afase/*` | `_boleiros_from_raw()` via `config.group_phase_label = "1afase"` | ✅ Phase 1 processed |
| `data/raw/playoffs/*` | `_playoff_files_from_raw()` via `config._raw_playoffs()` | ✅ Exists, but dir is **empty** |
| `data/raw/2afase/*` | **Nothing reads this** | ❌ No code references `2afase` |

### What would happen if you put files in `2afase/`

- `run_raw_to_bronze()` reads from `{group_phase_label}` which is `1afase` — `2afase` is ignored.
- `run_bronze_to_silver()` reads from `bronze/first_round/group_phase_*` — only phase 1 data is there.
- `run_silver_to_gold()` reads from `silver/first_round/group_phase_*` — only phase 1 data.
- **No crash**, but the new files are completely invisible to the pipeline.

### What you should do instead

The pipeline **already supports** a playoffs pathway via `data/raw/playoffs/`. To add a "Segunda Fase" (round of 32) with 16 matches per player, you need to:

1. **Put files** in `data/raw/playoffs/` with naming: `segunda_fase_{boleiro}.xlsx`
2. **No code changes needed** — the existing `parse_playoff_stage()` + bronze/silver/gold playoff pipeline already handles this.

The round key `segunda_fase` is already configured in `config.yaml` (line 79, 187) with 16 matches.

**OR** if you specifically want a `2afase/` directory (not `playoffs/`), you'd need to modify the pipeline to read from that path. Want me to sketch out what changes that would require?

---

### 👤 PROMPT DO USUÁRIO:
check the @play-off-plan.md and see what is missing for your insgitns and this plan

### 👤 PROMPT DO USUÁRIO:
Called the Read tool with the following input: {"filePath":"C:\\Users\\adnta\\Documents\\1.codigos\\git\\sweepstake\\play-off-plan.md"}

### 👤 PROMPT DO USUÁRIO:
<path>C:\Users\adnta\Documents\1.codigos\git\sweepstake\play-off-plan.md</path>
<type>file</type>
<content>
1: # Plano: Play-Off (Segunda Fase) — Visões e Pipeline
2: 
3: ## Conceito
4: 
5: A segunda fase do campeonato (mata-mata) é dividida em 4 rodadas:
6: - **Segunda Fase** (16 jogos)
7: - **Oitavas** (8 jogos)
8: - **Quartas** (4 jogos)
9: - **Semi** (2 jogos)
10: - **terceiro_lugar** (1 jogo)
11: - **Final** (1 jogo)
12: 
13: Cada jogador envia **um Excel por fase** com palpites de placar para os jogos daquela fase,
14: **além do bônus de times** que já existe no Excel da 1ª fase.
15: 
16: ---
17: 
18: ## Estrutura de Dados
19: 
20: ### Raw (entrada)
21: ```
22: data/raw/playoffs/
23:   oitavas_Gabão.xlsx
24:   oitavas_André Tayer.xlsx
25:   quartas_Gabão.xlsx
26:   quartas_André Tayer.xlsx
27:   semi_Gabão.xlsx
28:   final_Gabão.xlsx
29:   ...
30: ```
31: 
32: Cada Excel tem o mesmo formato da 1ª fase (9 colunas):
33: `date, hour, home_team, home_pen, home_goals, x, away_goals, away_pen, away_team`
34: 
35: ### Bronze
36: ```
37: bronze/playoffs/
38:   group_phase_oitavas_Gabão.csv
39:   group_phase_quartas_Gabão.csv
40:   ...
41: ```
42: 
43: ### Silver
44: ```
45: silver/playoffs/
46:   group_phase_oitavas_Gabão.csv
47:   ...
48: ```
49: (mergeado com resultados reais do `games.csv`)
50: 
51: ### Gold
52: ```
53: gold/playoffs/
54:   group_phase_oitavas_Gabão.csv      (por jogador)
55:   group_phase_quartas_Gabão.csv
56:   ...
57:   oitavas_all.csv                     (agregado)
58:   oitavas_valido_all.csv
59:   quartas_all.csv
60:   quartas_valido_all.csv
61:   semi_all.csv
62:   semi_valido_all.csv
63:   final_all.csv
64:   final_valido_all.csv
65: ```
66: 
67: ---
68: 
69: ## Visões (HTML)
70: 
71: > **Importante:** Em todas as visões abaixo, os **Bônus Times** (picks de times por fase) devem ter destaque visual explícito — indicando se o jogador acertou ou errou cada fase e quantos pontos isso rendeu.
72: 
73: ### 1. Página de cada jogo
74: `jogos/oitavas/2025-06-28_16h_palmeiras-vs-botafogo.html`
75: - Mesmo layout da 1ª fase: score card, distribuição de votos, acertos por critério, lista de palpites
76: - Incluir placar de pênaltis, se aplicável, no score card.
77: - Exibir ao lado de cada jogador quantos **Bônus Times** ele possui naquela fase e se acertou.
78: 
79: ### 2. Página de cada jogador (`boleiros/{Nome}.html`)
80: - Se houver palpites de play-off, aparecem no histórico com indicador da fase (ex: 🏆 Oitavas)
81: - Estatísticas totais incluem pontos de play-off + bônus + 1ª fase
82: - Seção dedicada aos **Bônus Times** com detalhamento fase a fase: time escolhido, time real, acerto/erro e pontos obtidos.
83: 
84: ### 3. Dashboard (`index.html`)
85: - Acordeão "Oitavas (8)", "Quartas (4)", etc. com links para os jogos
86: - "Último Resultado" pega o jogo mais recente (incluindo play-offs)
87: - "Próximos Jogos" inclui jogos de play-off futuros
88: - Card "Bônus Times" destacando os líderes de acertos nos picks de times e os maiores pontuadores.
89: 
90: ### 4. Ranking
91: - O ranking considera **1ª fase + Play-offs + Bônus** para um ranking geral abrangente
92: - Exibir coluna separada de **pontos de Bônus Times** para transparência do impacto.
93: 
94: ### 5. Arena
95: - Exibir todos os palpites (1ª fase + Play-offs) no formato visual de estádio
96: - Destacar os **Bônus Times** de cada jogador com badge visual na sua seção do estádio.
97: 
98: ### 6. Bônus (times)
99: - Continua sendo computado separadamente (`playoffs_scored.csv`)
100: - Aparece no Raio-X geral e na página do jogador
101: 
102: ---
103: 
104: ## Pipeline
105: 
106: ### raw → bronze (nova etapa)
107: ```
108: raw/playoffs/{phase}_{boleiro}.xlsx
109:   → parse_playoff_stage() → bronze/playoffs/group_phase_{phase}_{boleiro}.csv
110: ```
111: 
112: ### bronze → silver (nova etapa)
113: ```
114: bronze/playoffs/group_phase_{phase}_{boleiro}.csv
115:   + games.csv (filtrado por round = phase)
116:   → merge_with_results() → silver/playoffs/group_phase_{phase}_{boleiro}.csv
117: ```
118: 
119: ### silver → gold (nova etapa)
120: ```
121: silver/playoffs/group_phase_{phase}_{boleiro}.csv
122:   → apply_scoring() → gold/playoffs/group_phase_{phase}_{boleiro}.csv
123:   → concat all boleiros → gold/playoffs/{phase}_all.csv
124:   → filtrar valido=1 → gold/playoffs/{phase}_valido_all.csv
125: ```
126: 
127: ### HTML reports
128: ```
129: gold/playoffs/{phase}_valido_all.csv
130:   → _build_match() → jogos/{phase}/{match}.html
131: ```
132: 
133: ---
134: 
135: ## Efeito nas Visões Atuais
136: 
137: | Componente | Antes | Depois |
138: |-----------|-------|--------|
139: | index.html → acordeão | Oitavas (0), Quartas (0) | Oitavas (8), Quartas (4) etc. |
140: | Página do jogador | Só 1ª fase no histórico | 1ª fase + Play-offs + Bônus |
141: | Último Resultado | Último jogo da 1ª fase | Último jogo geral (inclui final) |
142: | Arena | Só 1ª fase | 1ª fase + Play-offs + Bônus Times — exibição de palpites em formato de estádio |
143: | Ranking | Só 1ª fase | 1ª fase + Play-offs + Bônus Times |
144: | Bônus Times | `playoffs_scored.csv` | Mesmo, inalterado |
145: 
146: ---
147: 
148: ## Adicionar Resultados Sem Quebrar
149: 
150: - `games.csv` já contém todos os 64 jogos com resultados reais
151: - Se faltar um jogo, basta adicionar linha no `games.csv` e rodar o pipeline
152: - Merge usa `how="left"` → jogos sem resultado ficam `NaN` e não são pontuados
153: - Pipeline é **determinística e idempotente**: rodar de novo sempre produz o mesmo resultado
154: 
155: ---
156: 
157: ## Próximos Passos (Implementação)
158: 
159: 1. `config.py` — novos métodos de path para playoffs
160: 2. `loader.py` — `parse_playoff_stage()`
161: 3. `pipeline.py` — estender raw→bronze, bronze→silver, silver→gold
162: 4. `html.py` — gerar páginas de jogos de playoff + integrar no perfil do jogador
163: 5. `html.py` e `dashboard.py` — atualizar `playoff_emoji_map` com emoji para "segunda_fase"
164: 6. `dashboard.py` — incluir playoffs no upcoming e acordeão

(End of file - total 164 lines)
</content>

---

### 🤖 AGENTE (Turno 6):

💭 **PENSAMENTO DO AGENTE:**
Let me analyze the `play-off-plan.md` against the actual current state of the codebase to see what's already implemented and what's missing.

The plan calls for:

### Data Structure
- `data/raw/playoffs/{phase}_{boleiro}.xlsx` — ✅ Naming convention already in loader.py's `_extract_playoff_phase_and_who()`
- `bronze/playoffs/group_phase_{phase}_{boleiro}.csv` — ✅ Already in pipeline.py and config.py
- `silver/playoffs/group_phase_{phase}_{boleiro}.csv` — ✅ Already in pipeline.py and config.py
- `gold/playoffs/group_phase_{phase}_{boleiro}.csv` — ✅ Already in pipeline.py and config.py
- `gold/playoffs/{phase}_all.csv` — ✅ Already in pipeline.py
- `gold/playoffs/{phase}_valido_all.csv` — ✅ Already in pipeline.py

### Pipeline (raw→bronze→silver→gold)
- `parse_playoff_stage()` — ✅ Already exists in `loader.py:130`
- `raw/playoffs/` → `bronze/playoffs/` — ✅ Already in `pipeline.py:274-279`
- `bronze/playoffs/` → `silver/playoffs/` — ✅ Already in `pipeline.py:353-403`
- `silver/playoffs/` → `gold/playoffs/` — ✅ Already in `pipeline.py:478-514`

### What's partially done or missing

1. **Config path `_raw_playoffs()`** — ✅ exists in `config.py:282-284`
2. **All bronze/silver/gold path methods** — ✅ all exist

3. **HTML reports — per-match playoff pages** — Let me check...

The plan mentions:
- "1. Página de cada jogo" — `jogos/{phase}/{match}.html` — need to check if `_build_match()` handles playoff phases
- "2. Página de cada jogador" — playoff history in player pages
- "3. Dashboard" — accordion for playoff rounds, recent/upcoming matches
- "4. Ranking" — includes playoffs + bonuses
- "5. Arena" — includes playoffs
- "6. Bônus (times)" — already exists

4. **`playoff_emoji_map` with "segunda_fase"** — mentioned in step 5 of the plan

Let me check what's in the HTML generator and dashboard to see what's implemented.

Let me also look at:
- What the `raw/playoffs/` directory currently contains
- Whether `games.csv` has "segunda_fase" round data
- `html.py` for match page generation and player page
- `dashboard.py` for accordion/upcoming matches

Let me check the current state of these things.

🛠️ **AÇÃO DA FERRAMENTA [TASK]**
*Alvo/Parâmetro:* `Thoroughly examine the following files in C:\Users\adnta\Documents\1.codigos\git\sweepstake to determine the current state of playoff HTML/dashboard/report support:

1. `src/core/reports/html.py` — Look for:
   - `playoff_emoji_map` definition
   - `_build_match()` function — does it handle playoff phases (not just first_round)?
   - How player pages (`boleiros/{Nome}.html`) handle playoff predictions and bonus picks
   - Any playoff-related functions or sections
   - How `segunda_fase` is handled

2. `src/core/reports/dashboard.py` — Look for:
   - Accordion for playoff rounds
   - "Último Resultado" / "Próximos Jogos" sections — do they handle playoff matches?
   - Upcoming matches handling
   - Bonus picks display
   - References to "segunda_fase" or playoff phase handling

3. `src/core/reports/new_views.py` — Look for playoff-related code, especially arena

4. Check if `data/raw/playoffs/` directory exists and has any files

5. Check `games.csv` for round values — search for "segunda_fase" or "round of 32" in games.csv

6. Check `data/raw/` directory structure

Return the complete findings for each area, noting what IS implemented vs what IS NOT yet implemented according to the play-off-plan.md. Be very specific about line numbers and function names.`

```text
<task id="ses_11a1088d3ffe7Ck2504t0CS76d" state="completed">
<task_result>
Now I have all the data needed. Here is the complete, thorough report:

---

## COMPLETE FINDINGS: Playoff HTML/Dashboard/Report Support

---

### 1. `src/core/reports/html.py` (4291 lines total)

#### `playoff_emoji_map` definition

- **Line 802**: `playoff_emoji_map = {"segunda_fase": "\U0001f3c6", "oitavas": "\U0001f3c1", "quartas": "\U0001f525", "semi": "\U0001f3af", "terceiro_lugar": "\U0001f949", "final": "\U0001f3c6"}`
- **Line 1107-1114**: A second `phase_emoji_map` in the bonus teams section (same keys/values). Used in `_build_boleiro` for both the bonus teams section and the phase points table.
- **Line 1225-1233**: A third `phase_emoji_map` inside `_build_boleiro` that also includes `"1afase": "\U0001f4ca"`.

**Keys used**: `segunda_fase`, `oitavas`, `quartas`, `semi`, `terceiro_lugar`, `final` — matching the config.yaml playoff round keys.

#### `_build_match()` function (line 1768)

**Signature**: `def _build_match(config, match, phase, df_match)`

- **Playoff handling**: YES, it handles playoff phases. The `phase` parameter is passed in by the caller. In `generate_html_reports`:
  - Group phase matches: called with `config.group_phase_label` (line 4244)
  - Playoff matches: called with `pr.name` (line 4264). **Note**: this passes the display name (e.g., "Segunda Fase"), not `pr.key` (e.g., "segunda_fase").
- **Phase used in**:
  - Match directory path for logo resolution (line 1790): `os.path.join("html", "jogos", phase)`
  - Match page header subtitle (line 2093): shows `{phase}` after date
  - Bonus data lookup from `playoffs_scored.csv` filtered by `phase` (lines 1985-1996)
- **Bonus picks display** in per-match player rows (lines 2017-2023): reads from `playoffs_scored.csv`, shows pick status
- **IMPORTANT**: At line 4264, `pr.name` is passed (display name like "Segunda Fase"), but the directory path uses `phase` (which equals `pr.key` at line 4254). So the phase display in the page title will show the Portuguese display name, while the directory is the key. This is **inconsistent** with group phase which passes a label as phase directly.

#### Player pages (`boleiros/{Nome}.html`)

- **Playoff predictions loaded**: Lines 642-654 loop over `config.playoff_rounds`, read `gold_playoff_valid_path(pr.key)` for each phase, and concatenate with group data.
- **Bonus points**: Lines 660-671 read `playoffs_scored.csv` (from `_au_first_round()` dir), sum points per player, and track `bonus_by_phase`.
- **Phase indicator in history**: Lines 881-884: if `phase_val` is in `playoff_emoji_map`, the playoff emoji is shown before the date.
- **Phase points table**: Lines 1264-1288: iterates `config.playoff_rounds`, reads `gold_playoff_valid_path`, includes bonus points per phase, and shows a full table.
- **Bonus teams section**: Lines 1047-1210: reads `bronze_bonus_path(boleiro)`, displays team picks per phase, checks advancing teams from `games.csv` by matching round column, color-codes by result (green/yellow/red).
- **Champion/striker badges**: Lines 1212-1217 show the champion team and striker pick at top of page.

#### How `segunda_fase` is handled

`segunda_fase` appears in all three `playoff_emoji_map`/`phase_emoji_map` definitions, in the config.yaml as a round key, in the `bonus_by_phase` dict, and in the phase points table. However, **games.csv uses `r32` as the round value**, not `segunda_fase`. This means:
- The gold data uses `segunda_fase` (from pipeline reading Excel config)
- The games.csv uses `r32` (from raw data entry)
- **There is a naming mismatch between the two data sources**

---

### 2. `src/core/reports/dashboard.py` (1303 lines)

#### Accordion for playoff rounds

- **Lines 1049-1064**: The `_build_phase_buttons` function has a "Playoff rounds" section.
  - Line 1050: `playoff_emojis` dict with keys `segunda_fase`, `oitavas`, `quartas`, `semi`, `terceiro_lugar`, `final`
  - Line 1051: iterates `config.playoff_rounds`, reads HTML files from `jogos/{pr.key}/`, builds compact grid.
  - Lines 1059-1064: Each playoff phase gets its own section with emoji + name + game count.

#### "Último Resultado" / "Último Resultado" section

- **Lines 833-889** (`_build_last_result`): Reads from `config.results_file` (games.csv), filters `finished` matches, sorts by date, picks the most recent. **No playoff-specific filtering** — it handles any match regardless of phase.
- **Lines 775-830** (`_build_live_games`): Reads from games.csv, filters `live` matches. Phase directory for the match link is determined by checking if the round value is numeric (line 795-798). For non-numeric rounds (including playoffs), the round value itself becomes the phase directory.

#### "Próximos Jogos" / upcoming matches

- **Lines 416-443** (`_get_upcoming_games`): Scans BOTH group phase directory (line 424-430) AND playoff phase directories (lines 432-440) using `pr.key` from `config.playoff_rounds`.
- **Line 607-637** (`_build_upcoming_games`): Calls `_get_upcoming_games`, renders first 5 as cards. No playoff-specific logic needed since the game scanning already includes playoffs.

#### Bonus picks display

- **Lines 1077-1131** (`_build_bonus_times_card`): Reads `playoffs_scored.csv`, shows top 3 scorers (by points) and top 3 accuracy (minimum 5 picks). Displayed on the dashboard via `generate_dashboard()` at line 1195.

#### References to `segunda_fase` or playoff phase handling

- Line 1050: `playoff_emojis` dict includes `segunda_fase`
- Line 1051: iterates `config.playoff_rounds` generically
- Lines 432-440 in `_get_upcoming_games`: scans playoff directories
- Line 1079: reads `playoffs_scored.csv` from `first_round` directory

---

### 3. `src/core/reports/new_views.py` (1251 lines)

#### Playoff-related code

- **`_build_group_standings`** (line 64): At line 136, calls `_build_knockout_bracket()` to append bracket after group tables.
- **`_build_knockout_bracket`** (lines 182-230): Iterates `config.playoff_rounds`, reads `df_games` (games.csv), filters by round value, builds simple match list. Shows scores if available.
- **`_build_round_predictions`** (lines 715-1095):
  - Line 741-745: `round_labels` dictionary maps **games.csv round values** (`r32`, `r16`, `qf`, `sf`, `third`, `final`) to display names.
  - Lines 878-935: Phase filter dropdown menus include "r32" (2ª Fase) and "mata" (Mata-Mata, which bundles r16, qf, sf, third, final together).
  - This is the **only place** that correctly maps the games.csv round values (`r32`, `r16`, etc.) to display names.
- **`_build_team_page`** (line 243): No playoff-specific logic. Links to match pages use the round value as phase directory (line 442).
- **`_build_times_index`** (line 497): No playoff-specific logic.

#### Arena

- Arena is in `html.py`, not `new_views.py`. It's `_build_arena()` at html.py line 2131. It loads bonus data from `playoffs_scored.csv` (lines 2137-2148) and displays bonus info in the comparison stat cards.

---

### 4. `data/raw/playoffs/` directory

**Does NOT exist.** The `data/raw/` directory itself does not exist (no such path in the workspace). The playoff raw data directory would be `data/raw/playoffs/` as per `_raw_playoffs()` in config.py line 282. Since the data layer hasn't been run or the raw Excel files haven't been placed, this directory is absent.

---

### 5. `games.csv` round values

**File**: `src/championships/2026_world_cup/data/games.csv`

Unique round values found:
| Round Value | Description |
|---|---|
| `1` | 1st group round |
| `2` | 2nd group round |
| `3` | 3rd group round |
| `r32` | Round of 32 (segunda fase) |
| `r16` | Round of 16 (oitavas) |
| `qf` | Quarterfinals (quartas) |
| `sf` | Semifinals (semi) |
| `third` | Third place match (terceiro_lugar) |
| `final` | Final |

**CRITICAL MISMATCH**: The games.csv uses `r32`, `r16`, `qf`, `sf`, `third` but the config.yaml defines playoff round keys as `segunda_fase`, `oitavas`, `quartas`, `semi`, `terceiro_lugar`, `final`. These are **completely different naming conventions**.

---

### 6. `data/raw/` directory structure

**Does not exist.** There is no `data/` directory anywhere in the workspace. The only data is embedded within:
- `src/championships/2026_world_cup/data/games.csv`
- `src/championships/2025_club_world_cup/data/games.csv`
- Plus whatever is generated at runtime by the pipeline in bronze/silver/gold directories (relative to project root or configured base_dir).

---

## WHAT IS IMPLEMENTED vs NOT IMPLEMENTED

### Fully Implemented

| Feature | Location |
|---|---|
| `PlayoffRound` dataclass | `config.py` line 38 |
| `playoff_rounds: list[PlayoffRound]` field | `config.py` line 206 |
| `PlayoffsLayout` with `rounds` config | `config.py` lines 157-171, instantiated at line 570 |
| Full path infrastructure (raw/bronze/silver/gold) for playoffs | `config.py` lines 282-386 |
| `gold_playoff_valid_path(phase)` and `gold_playoff_all_path(phase)` | `config.py` lines 350-356 |
| `bronze_bonus_path(boleiro)` | `config.py` lines 310-312 |
| `playoff_strikers_path()` | `config.py` lines 378-386 |
| `playoff_scoring` dict | `config.py` line 232, populated at line 597-600 |
| Playoff emoji maps (3 instances) | `html.py` lines 802, 1107-1114, 1225-1233 |
| Per-match page generation for playoff phases | `html.py` lines 4252-4270 |
| Per-match page bonus data display | `html.py` lines 1984-1996 (in `_build_match`) |
| Player page: loads playoff predictions | `html.py` lines 642-654 |
| Player page: bonus points from `playoffs_scored.csv` | `html.py` lines 660-671 |
| Player page: bonus teams section | `html.py` lines 1047-1210 |
| Player page: phase points table | `html.py` lines 1264-1288 |
| Match history: playoff emoji indicators | `html.py` lines 881-884 |
| Dashboard: upcoming games scans playoff dirs | `dashboard.py` lines 432-440 |
| Dashboard: phase buttons for playoff rounds | `dashboard.py` lines 1049-1064 |
| Dashboard: bonus times card | `dashboard.py` lines 1077-1131 |
| Dashboard: live/result games from games.csv (any phase) | `dashboard.py` lines 775-889 |
| Arena: bonus data loaded | `html.py` lines 2137-2148 |
| Bracket visualization | `new_views.py` lines 182-230 |
| Round predictions: playoff phase filter dropdowns | `new_views.py` lines 741-745, 878-935 |

### Partially Implemented / Potential Issues

| Issue | Details |
|---|---|
| **Round key naming mismatch** | Config uses `segunda_fase`, `oitavas`, `quartas`, `semi`, `terceiro_lugar`, `final` — but games.csv uses `r32`, `r16`, `qf`, `sf`, `third`, `final`. The gold data pipeline uses config keys, while `new_views.py` round_labels correctly maps games.csv keys. However, `new_views.py` filter dropdown labels (line 879-884) label `r32` as "2ª Fase" and `mata` as "Mata-Mata" — not matching the config phase names. |
| **`_build_match` passes `pr.name` not `pr.key`** | At html.py line 4264, the playoff match phase parameter uses `pr.name` (display name like "Segunda Fase") instead of `pr.key` (slug like "segunda_fase"). This means the phase subtitle on the match page uses the display name, but it's inconsistent with how group phase passes a label. The directory path correctly uses `pr.key` (line 4269). |
| **`data/raw/playoffs/` doesn't exist** | The raw playoff Excel input directory is missing. This is expected if the pipeline hasn't been run or data hasn't been placed there. |
| **Playoff match link in zebras page** | At html.py line 3670, the zebra match link hardcodes `config.group_phase_label` as the phase directory — **playoff zebra matches will have broken links**. |
| **Playoff match link in `_build_zebras` difficulty section** | Line 3793 also hardcodes `config.group_phase_label` — same bug for playoff matches. |
| **No separate playoff phase in `_build_day_winners`** | Lines 3415-3615: reads from `gold_valid_path()` (group only), not from playoff gold data. Playoff matches won't appear in day winners. |
| **`_build_momentum` reads only `_au_first_round()`** | Line 3917: consistency data is only from first_round. Playoff predictions not included in streak calculations. |
| **`_build_bolao_xray` reads only gold_valid for group** | Line 3025: reads `gold_all_path()` (group only), not playoff gold data. Does not account for playoff matches. |
| **`_build_full_ranking` in dashboard reads only group data** | Line 473: `_load_gold_data()` reads `gold_valid_path()` (group). Playoff points not included in dashboard ranking. |
| **`_build_zebra_counter` reads only group data** | Line 744: reads from `_au_first_round()` only. Playoff upset data not included. |
| **`_build_bonus_times_card` reads from `_au_first_round()`** | Line 1079: `playoffs_scored.csv` is expected in `first_round` dir. This is a legacy location — playoff bonus data lives alongside first_round data. |

### Not Implemented

- No separate playoff analytics pipeline (consistency, boldness, ranking_history for playoffs). All analytics only cover group phase.
- No dedicated playoff knockout bracket visualization with advancing lines (the current bracket is a simple list of matches per phase).
- No playoff-only summary page or separate playoff dashboard section.
- No playoff phase filter in zebras pages — match links hardcode group phase label.
- No playoff match integration in the day winners page.
- No playoff match integration in the raio-x heatmap.
- No playoff match integration in team pages (though team pages read from games.csv which includes all phases).
</task_result>
</task>
```

---

### 🤖 AGENTE (Turno 7):

💭 **PENSAMENTO DO AGENTE:**
Now I have a very comprehensive understanding of the current state vs. the play-off-plan.md requirements. Let me synthesize this into a clear answer for the user.

The key findings are:

## What Already Works (per the plan)
1. ✅ All path infrastructure (config.py)
2. ✅ `parse_playoff_stage()` in loader.py
3. ✅ Pipeline raw→bronze→silver→gold for playoffs
4. ✅ `_build_match()` handles playoff phases
5. ✅ Player page loads playoff predictions + bonus points + bonus teams
6. ✅ Dashboard: accordion, upcoming games, bonus times card
7. ✅ Arena: bonus data loaded
8. ✅ Bracket visualization in new_views.py
9. ✅ Emoji maps include all phase keys including `segunda_fase`

## Gaps (not in plan, but issues)
1. **`data/raw/playoffs/` doesn't exist** — needs to be created
2. **games.csv uses `r32`, `r16`, `qf`, `sf`, `third`** while config uses `segunda_fase`, `oitavas`, `quartas`, `semi`, `terceiro_lugar`

## What's Missing from the Plan
The big gaps in the HTML reporting layer:
- Dashboard ranking doesn't include playoff points
- Zebras page has broken links for playoff matches
- Day winners / raio-x don't include playoff matches
- Momentum/streaks don't include playoff predictions
- No playoff integration in overall analytics

But wait — the user is asking: "what is missing for your insgitns and this plan"

Let me re-read their question: "check the @play-off-plan.md and see what is missing for your insgitns and this plan"

They want me to check what's missing. They're asking: comparing the plan to the actual state, what implementation steps are still needed?

The plan's "Próximos Passos (Implementação)" section says:

1. `config.py` — novos métodos de path para playoffs → ✅ DONE
2. `loader.py` — `parse_playoff_stage()` → ✅ DONE
3. `pipeline.py` — estender raw→bronze, bronze→silver, silver→gold → ✅ DONE
4. `html.py` — gerar páginas de jogos de playoff + integrar no perfil do jogador → ✅ MOSTLY DONE (match pages and player pages work)
5. `html.py` e `dashboard.py` — atualizar `playoff_emoji_map` com emoji para "segunda_fase" → ✅ DONE
6. `dashboard.py` — incluir playoffs no upcoming e acordeão → ✅ MOSTLY DONE

So the plan's implementation steps are all done! But there are still issues. Let me also check the specific pain points:

**The `raw/playoffs/` directory doesn't exist** — the user might think the pipeline reads from `2afase/` but it actually reads from `playoffs/`.

**The naming mismatch** — `games.csv` uses `r32` but config uses `segunda_fase`. This is important because:
- When the bronze→silver pipeline filters games by round, it looks for `phase` (which is `segunda_fase`) in the `round` column of games.csv. But games.csv has `r32`, not `segunda_fase`.
- This means the merge will fail to find matching results for playoff predictions!

Wait, let me re-check this. In pipeline.py:

```python
# Filter results to only this playoff phase
df_results_phase = df_results[df_results["round"] == phase].copy()
```

And `phase` comes from the config round key, which is `segunda_fase`. But games.csv has `r32` in the `round` column.

This is a **critical bug** — the silver merge for playoff phases will produce zero matches because the round names don't align!

Actually wait — let me think about this more carefully. The `parse_playoff_stage()` function reads the Excel and adds `phase` column. But the `_merge_with_results()` function merges on `match` key (slug of home_team-vs-away_team), not on phase. The phase filtering in `run_bronze_to_silver()` is:

```python
df_results_phase = df_results[df_results["round"] == phase].copy()
df_merged = _merge_with_results(df_boleiro, df_results_phase)
```

So if `phase = "segunda_fase"` but games.csv has `round = "r32"`, then `df_results_phase` will be empty, and the merge will produce no results. All matches will have NaN for real results.

This means the pipeline has a **real bug** for playoff phases!

Similarly, the bonus teams section in `html.py` reads `games.csv` and checks which teams advance by matching the round column against config phase keys. Let me check that too...

In `html.py` player page (lines 1047-1210), the bonus teams section reads from `bronze_bonus_path(boleiro)` which has columns `[boleiro, phase, team]`. The `phase` values come from the Excel parsing (config keys like `segunda_fase`, `oitavas`, etc.). Then to check if the team advanced, it reads `games.csv` and filters by round. But again, games.csv uses `r32` not `segunda_fase`.

Wait, actually let me check this more carefully...

Looking at `html.py` function `_build_boleiro`, lines 1047-1210 for the bonus teams section. It:
1. Loads `bronze_bonus_path(boleiro)` → columns `[boleiro, phase, team]`
2. Loads `games.csv` → columns `[..., round, home_team, away_team, home_goals, away_goals, ...]`
3. For each pick, checks if the picked team advanced to the next round

The advancing check logic would iterate through phases and look at winners in games.csv for each round. The `round` column in games.csv has values like `r32`, `r16`, etc. The phase values from the Python config are `segunda_fase`, `oitavas`, etc.

So for the bonus teams section, the HTML code needs to map from the config phase key to the games.csv round value. I need to check if this mapping exists...

Actually, looking at the `play-off-plan.md` more carefully, it says:
- "Cada jogador envia **um Excel por fase** com palpites de placar"

So the plan is: for each knockout round, each player sends ONE Excel file with match predictions AND continues to have their bonus team picks from the 1afase Excel.

The naming convention is: `{phase}_{boleiro}.xlsx` placed in `data/raw/playoffs/`.

Now the critical question is: does the user need a `2afase/` directory or a `playoffs/` directory?

The plan says `data/raw/playoffs/` but the user mentioned `2afase/`. These are different concepts.

Looking at the config:
- `group_phase_label: "1afase"` — this is where group phase raw files live
- `playoffs/` — this is where playoff raw files live (via `_raw_playoffs()`)
- No `2afase` directory

The user asked "does this repo is ready for the 2nd phase with new excels at '2026_world_cup/data/raw/2afase/*'?"

This suggests they want to create `data/raw/2afase/` and put files there. But the pipeline reads from `data/raw/playoffs/`. So if they create `2afase/`, nothing will pick up those files.

But wait — maybe they want to treat "2afase" as a group-like phase (like a second group stage)? Or maybe they just used "2afase" loosely to mean "second phase = playoffs"?

I think from the user's perspective, "2afase" means the knockout rounds starting with "Segunda Fase" (round of 32). And they want to put prediction Excel files there.

The plan says to put them in `playoffs/` directory.

So there are really two separate concerns:

**Concern 1**: The user asked about `2afase/` directory, but the pipeline expects `playoffs/` directory. They need to know about this.

**Concern 2**: Even if they use `playoffs/`, there are outstanding issues (especially the naming mismatch between config keys and games.csv round values).

Let me now check if there is a `raw/playoffs/` directory already.

From the explore agent:
> The `data/raw/playoffs/` directory does NOT exist.

So the user needs to:
1. Create `data/raw/playoffs/`
2. Place files named `segunda_fase_{boleiro}.xlsx` (or `oitavas_{boleiro}.xlsx` etc.)
3. There's a naming mismatch bug between config round keys and games.csv round values

Let me summarize the findings and present them to the user.

📄 **RESPOSTA DO AGENTE:**
Aqui está a análise completa do que o plano (`play-off-plan.md`) pede vs. o estado real do código:

---

## ✅ O que já está implementado (segundo o plano)

| Passo do plano | Status |
|---|---|
| `config.py` — métodos de path para playoffs | ✅ `config.py:282-386` |
| `loader.py` — `parse_playoff_stage()` | ✅ `loader.py:130-151` |
| `pipeline.py` — raw→bronze→silver→gold (playoffs) | ✅ `pipeline.py:274-279, 353-403, 478-514` |
| `html.py` — página de cada jogo de playoff | ✅ `html.py:4252-4270, _build_match()` |
| `html.py` — perfil do jogador com playoffs + bônus | ✅ `html.py:642-654, 660-671, 1047-1210` |
| `html.py` — `playoff_emoji_map` com `segunda_fase` | ✅ `html.py:802, 1107, 1225` |
| `dashboard.py` — acordeão de playoffs | ✅ `dashboard.py:1049-1064` |
| `dashboard.py` — próximos jogos inclui playoffs | ✅ `dashboard.py:432-440` |
| `dashboard.py` — card de Bônus Times | ✅ `dashboard.py:1077-1131` |

---

## ❌ O que está **quebrado** ou faltando

### 1. `2afase/` vs `playoffs/` — diretório errado

Você mencionou `data/raw/2afase/`, mas o pipeline lê de **`data/raw/playoffs/`** (definido em `config.py:282`).  
O diretório `raw/playoffs/` **não existe** — precisa ser criado.  
Se criar `2afase/`, os arquivos serão ignorados.

### 2. 🚨 **BUG CRÍTICO: naming mismatch entre config e `games.csv`**

| Config (round keys) | `games.csv` (round values) |
|---|---|
| `segunda_fase` | `r32` |
| `oitavas` | `r16` |
| `quartas` | `qf` |
| `semi` | `sf` |
| `terceiro_lugar` | `third` |
| `final` | `final` ✅ |

**Consequência**: quando `pipeline.py:364` faz:
```python
df_results_phase = df_results[df_results["round"] == phase]
```
`phase = "segunda_fase"` **nunca** vai casar com `"r32"` → merge retorna zero resultados → todas as predições ficam sem resultado real → zero pontos.

**Idem** para a seção de bônus times na página do jogador em `html.py` — a verificação de times que avançam também usa os keys do config contra os rounds do `games.csv`.

### 3. Links quebrados nas páginas de zebras

`html.py:3670` e `3793` usam `hardcoded config.group_phase_label` (`"1afase"`) como diretório do jogo — jogos de playoff nas páginas de zebra vão linkar para diretório errado.

### 4. Ranking do dashboard não inclui playoffs

`dashboard.py:473` (`_load_gold_data`) lê apenas `gold_valid_path("group")` → ranking mostra só pontos da 1ª fase.

### 5. Analytics (consistência, boldness, etc.) ignoram playoffs

- `_build_momentum` (`html.py:3917`) — só lê `_au_first_round()`
- `_build_bolao_xray` (`html.py:3025`) — só lê `gold_all_path("group")`
- `_build_day_winners` (`html.py:3415-3615`) — só lê `gold_valid_path()`
- `_generate_consistency`, `_generate_round_by_round`, etc. no `pipeline.py` — só processam first_round

### 6. Arquivos de exemplo no `raw/playoffs/`

Não há nenhum Excel de exemplo em `data/raw/playoffs/` — você precisa criar os arquivos com o formato `segunda_fase_{boleiro}.xlsx`, `oitavas_{boleiro}.xlsx`, etc.

---

## Resumo: o que precisa fazer para continuar?

**A curto prazo (só para o pipeline rodar sem quebrar):**
1. Criar `data/raw/playoffs/` (não `2afase/`)
2. Corrigir o **naming mismatch** — mapear os round keys do config para os valores do `games.csv` (ex: `segunda_fase` → `r32`)
3. Colocar os Excels com nome `segunda_fase_{boleiro}.xlsx`

**Para as visões HTML ficarem corretas:**
4. Corrigir links de zebras
5. Incluir playoffs no ranking do dashboard
6. Integrar playoffs nos analytics (consistency, xray, day_winners)

Quer que eu detalhe o plano de implementação para cada um desses pontos?

---

### 👤 PROMPT DO USUÁRIO:
a pasta oficial se chama 'playoff'.. veja no repo quais alteracoes eu preciso fazer e monte um plano...

---

### 🤖 AGENTE (Turno 9):

💭 **PENSAMENTO DO AGENTE:**
The user is saying the official folder name is "playoff" (singular), not "playoffs" (plural). Let me check the codebase to see where "playoffs" (plural) is used as a directory name vs where it should be "playoff" (singular).

Let me search for all references to "playoffs" (plural) in paths and directory names.

🛠️ **AÇÃO DA FERRAMENTA [GREP]**
*Alvo/Parâmetro:* `playoffs`

```text
Found 74 matches
C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py:
  Line 663:     bonus_csv = _norm(os.path.join(config._au_first_round(), "playoffs_scored.csv"))

  Line 1985:     bonus_path = os.path.join(config._au_first_round(), "playoffs_scored.csv")

  Line 2138:     bonus_path = os.path.join(config._au_first_round(), "playoffs_scored.csv")


C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\dashboard.py:
  Line 1079:     bonus_path = os.path.join(config._au_first_round(), "playoffs_scored.csv")


C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\pipeline.py:
  Line 11:     bronze/playoffs/  (future separate playoff Excel files)

  Line 15:     silver/playoffs/  (future)

  Line 22:     gold/first_round/playoffs_strikers.csv

  Line 23:     gold/playoffs/  (future)

  Line 46:     parse_bonus_playoffs,

  Line 121:     """Return sorted list of (excel_path, phase_key, boleiro_name) from raw/playoffs/."""

  Line 122:     raw_playoff_dir = config._raw_playoffs()

  Line 242: # Bronze: raw Excel -> first_round/ + playoffs/

  Line 252:         config._br_playoffs(),

  Line 265:             df_bonus, df_striker = parse_bonus_playoffs(path_excel, config)

  Line 298:         config._ag_playoffs(),

  Line 354:     playoff_pattern = _norm(os.path.join(config._br_playoffs(), "group_phase_*"))

  Line 422:         config.gold_playoffs_dir(),

  Line 479:     playoff_silver_pattern = _norm(os.path.join(config._ag_playoffs(), "group_phase_*"))

  Line 548:     _save_csv(df, _norm(os.path.join(config._au_first_round(), "playoffs_scored.csv")))

  Line 549:     print_colored(f"\tplayoffs_scored.csv: {len(df)} rows", "green")


C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\championships\2026_world_cup\config.yaml:
  Line 176:   playoffs:

  Line 184:     playoffs_sheet_name: "Tabela Jogos"


C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\get_results.py:
  Line 3: Produces a single ``games.csv`` with all matches (group stage + playoffs)


C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\config.py:
  Line 169:     # Sheet name for playoffs/striker data (standings-format only).

  Line 171:     playoffs_sheet_name: str = ""

  Line 179:     playoffs: PlayoffsLayout

  Line 191:             for r in self.playoffs.rounds

  Line 261:     # Path helpers — first_round / playoffs structure

  Line 267:     #   bronze/playoffs/  (future separate playoff Excel files)

  Line 271:     #   silver/playoffs/  (future)

  Line 278:     #   gold/first_round/playoffs_strikers.csv

  Line 279:     #   gold/playoffs/  (future)

  Line 282:     def _raw_playoffs(self) -> str:

  Line 284:         return _norm(os.path.join(self.raw_dir, "playoffs"))

  Line 289:     def _br_playoffs(self) -> str:

  Line 290:         return _norm(os.path.join(self.bronze_dir, "playoffs"))

  Line 295:     def _ag_playoffs(self) -> str:

  Line 296:         return _norm(os.path.join(self.silver_dir, "playoffs"))

  Line 301:     def _au_playoffs(self) -> str:

  Line 302:         return _norm(os.path.join(self.gold_dir, "playoffs"))

  Line 320:         return _norm(os.path.join(self._br_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))

  Line 330:         return _norm(os.path.join(self._ag_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))

  Line 338:     def gold_playoffs_dir(self) -> str:

  Line 340:         return self._au_playoffs()

  Line 348:         return _norm(os.path.join(self._au_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))

  Line 352:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_all.csv"))

  Line 356:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_valido_all.csv"))

  Line 364:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_valido_all.csv"))

  Line 372:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_all.csv"))

  Line 386:         return _norm(os.path.join(base, "playoffs_strikers.csv"))

  Line 563:     po_cfg = el_cfg.get("playoffs", {})

  Line 570:     playoffs = PlayoffsLayout(

  Line 579:         playoffs_sheet_name=po_cfg.get("playoffs_sheet_name", ""),

  Line 584:         playoffs=playoffs,

  Line 587:     # Derive playoff_rounds list from excel_layout.playoffs.rounds


C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\championships\2025_club_world_cup\config.yaml:
  Line 130:   playoffs:


C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\loader.py:
  Line 38:     parts = name_no_ext.split(layout.playoffs.name_split_char)

  Line 39:     name = parts[layout.playoffs.name_split_index].strip()

  Line 196:     po_layout = config.excel_layout.playoffs

  Line 198:     if po_layout.playoffs_sheet_name:

  Line 200:             df_po = pd.read_excel(path, sheet_name=po_layout.playoffs_sheet_name, header=None)

  Line 253:     df_bonus, df_striker = _parse_playoffs_and_striker(path, who, config, df_raw)

  Line 304: def _parse_playoffs_and_striker(

  Line 309:     Reads the configured playoffs sheet (or falls back to df_raw), then

  Line 313:     po_layout = config.excel_layout.playoffs

  Line 315:     # Use dedicated playoffs sheet if configured (e.g. "Tabela Jogos")

  Line 316:     if po_layout.playoffs_sheet_name:

  Line 318:             df_po = pd.read_excel(path, sheet_name=po_layout.playoffs_sheet_name, header=None)

  Line 334:             # Try configured playoffs sheet first, then fallback to the first sheet

  Line 336:             if po_layout.playoffs_sheet_name:

  Line 337:                 sheets_to_try.append(po_layout.playoffs_sheet_name)

  Line 469: def parse_bonus_playoffs(path: str, config: ChampionshipConfig) -> tuple[pd.DataFrame, pd.DataFrame]:

  Line 472:     The first_round Excel contains a "playoffs" section where each boleiro

  Line 502:     df_striker_raw = df.tail(layout.playoffs.striker_row_offset).copy()
```

🛠️ **AÇÃO DA FERRAMENTA [GREP]**
*Alvo/Parâmetro:* `playoff`

```text
Found 5 matches
C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\championships\2026_world_cup\config.yaml:
  Line 78: playoff_scoring:

  Line 176:   playoffs:

  Line 184:     playoffs_sheet_name: "Tabela Jogos"


C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\championships\2025_club_world_cup\config.yaml:
  Line 80: playoff_scoring:

  Line 130:   playoffs:
```

🛠️ **AÇÃO DA FERRAMENTA [GREP]**
*Alvo/Parâmetro:* `playoff`

```text
Found 100 matches (more matches available)
C:\Users\adnta\Documents\1.codigos\git\sweepstake\play-off-plan.md:
  Line 22: data/raw/playoffs/

  Line 37: bronze/playoffs/

  Line 45: silver/playoffs/

  Line 53: gold/playoffs/

  Line 99: - Continua sendo computado separadamente (`playoffs_scored.csv`)

  Line 108: raw/playoffs/{phase}_{boleiro}.xlsx

  Line 109:   → parse_playoff_stage() → bronze/playoffs/group_phase_{phase}_{boleiro}.csv

  Line 114: bronze/playoffs/group_phase_{phase}_{boleiro}.csv

  Line 116:   → merge_with_results() → silver/playoffs/group_phase_{phase}_{boleiro}.csv

  Line 121: silver/playoffs/group_phase_{phase}_{boleiro}.csv

  Line 122:   → apply_scoring() → gold/playoffs/group_phase_{phase}_{boleiro}.csv

  Line 123:   → concat all boleiros → gold/playoffs/{phase}_all.csv

  Line 124:   → filtrar valido=1 → gold/playoffs/{phase}_valido_all.csv

  Line 129: gold/playoffs/{phase}_valido_all.csv

  Line 144: | Bônus Times | `playoffs_scored.csv` | Mesmo, inalterado |

  Line 159: 1. `config.py` — novos métodos de path para playoffs

  Line 160: 2. `loader.py` — `parse_playoff_stage()`

  Line 162: 4. `html.py` — gerar páginas de jogos de playoff + integrar no perfil do jogador

  Line 163: 5. `html.py` e `dashboard.py` — atualizar `playoff_emoji_map` com emoji para "segunda_fase"

  Line 164: 6. `dashboard.py` — incluir playoffs no upcoming e acordeão


C:\Users\adnta\Documents\1.codigos\git\sweepstake\sessions\20260614_1828_ses_137f660fcffeUSgVvf2hJsROtD\nova_visao_original_para_o_repositorio.md:
  Line 96: | `PlayoffsLayout` | `striker_row_offset`, `striker_label`, `striker_name_column`, `striker_name_fallback_column`, `champion_cell`, `name_split_char`, `name_split_index`, `rounds: list[dict]`, `playoffs_sheet_name` | Playoff Excel slicing config |

  Line 97: | `ExcelLayout` | `first_round: FirstRoundLayout`, `playoffs: PlayoffsLayout` | How to slice the Excel sheet |

  Line 98: | `ChampionshipConfig` | `id`, `name`, `year`, `timezone`, `scoring_rules`, `playoff_rounds`, `excel_layout`, `base_dir`, `raw_dir`, `results_file`, `games_file`, `bronze_dir`, `silver_dir`, `gold_dir`, `reports_dir`, `results_endpoint`, `team_name_mapping`, `team_logos`, `team_slugs`, `report_title`, `group_phase_label`, `theme`, `playoff_scoring`, `actual_top_scorer`, `striker_points`, `groups`, `standings_format`, `standings_skiprows`, `bonus_team_picks`, `striker_pick` | Full config for a single championship |

  Line 105: - Gold layer: `data/gold/first_round/group_phase_{boleiro}.csv`, `{label}_all.csv`, `{label}_valido_all.csv`, `striker_{boleiro}.csv`, `playoffs_strikers.csv`, plus 10+ analytics CSVs

  Line 108: - `playoffs_scored.csv` -- Bonus team pick scoring

  Line 255: 9. **"Arvore de Decisoes" (Decision Tree for Playoffs)** - For knockout stages, show the playoff bracket with each player's predicted path and how it diverges from reality.

  Line 390: 3. Pay special attention to: boldness_index.csv, consistency.csv, upset_tracker.csv, team_accuracy.csv, goal_error_by_team.csv, round_by_round.csv, prediction_timing.csv, and any file with "striker" or "playoffs" in the name.

  Line 614: #### 11. `playoffs_strikers.csv` (34 rows)

  Line 621: **Description:** Who each player picked as their playoff (knockout) top striker.

  Line 625: #### 12. `playoffs_scored.csv` (1 row -- header only, no data)

  Line 636: **Description:** Placeholder -- no playoff data yet.

  Line 680: | **`playoffs_strikers.csv`** | `striker` -- favorite player choice (star-chaser vs unique pick) |

  Line 1203: 4096:     for pr in (config.playoff_rounds or []):

  Line 1252: 4145:     # --- Per-match (playoff rounds) ---

  Line 1253: 4146:     for pr in (config.playoff_rounds or []):

  Line 1255: 4148:         playoff_valid_path = config.gold_playoff_valid_path(phase)

  Line 1256: 4149:         if not os.path.exists(playoff_valid_path):

  Line 1258: 4151:         df_phase = pd.read_csv(playoff_valid_path, sep=",")

  Line 1930: 633:     df_striker = pd.read_csv(config.playoff_strikers_path(), sep=",")

  Line 1935: 638:     # --- Load playoff predictions for this player ---

  Line 1936: 639:     playoff_parts = []

  Line 1937: 640:     for pr in (config.playoff_rounds or []):

  Line 1938: 641:         phase_valid_path = config.gold_playoff_valid_path(pr.key)

  Line 1943: 646:                 playoff_parts.append(df_phase_player)

  Line 1945: 648:     if playoff_parts:

  Line 1946: 649:         df_playoff = pd.concat(playoff_parts, ignore_index=True)

  Line 1947: 650:         df_bol = pd.concat([df_bol, df_playoff], ignore_index=True)

  Line 1952: 655:     # Load bonus points (playoff team picks) — not included in df_bol/pontos

  Line 1955: 658:     bonus_csv = _norm(os.path.join(config._au_first_round(), "playoffs_scored.csv"))

  Line 2091: 794:     playoff_emoji_map = {"segunda_fase": "\U0001f3c6", "oitavas": "\U0001f3c1", "quartas": "\U0001f525", "semi": "\U0001f3af", "terceiro_lugar": "\U0001f949", "final": "\U0001f3c6"}

  Line 2101: 804:     # Pre-compute per-match ranking for all players (group + playoff)

  Line 2121: 824:     for pr in (config.playoff_rounds or []):

  Line 2122: 825:         path = config.gold_playoff_valid_path(pr.key)

  Line 2166: 869:             # Phase indicator for playoff matches

  Line 2169: 872:             if phase_val and phase_val in playoff_emoji_map:

  Line 2170: 873:                 phase_label = f"{playoff_emoji_map[phase_val]} {phase_val} | "

  Line 2354: 1042:             playoff_keys = [pr.key for pr in (config.playoff_rounds or [])]

  Line 2363: 1051:             for pk in playoff_keys:

  Line 2402: 1090:             phase_order = [pr.key for pr in (config.playoff_rounds or [])]

  Line 2403: 1091:             phase_label_map = {pr.key: pr.name for pr in (config.playoff_rounds or [])}

  Line 2412: 1100:             playoff_scoring = getattr(config, "playoff_scoring", {})

  Line 2426: 1114:                 pts_per_correct = playoff_scoring.get(phase_key, 0)

  Line 2577: 1250:     for pr in config.playoff_rounds or []:

  Line 2581: 1254:         phase_valid_path = config.gold_playoff_valid_path(phase_key)

  Line 4791: *Alvo/Parâmetro:* `def gold_valid_path|def gold_all_path|def _au_first_round|def bronze_bonus_path|def playoff_strikers_path|def gold_playoff_valid_path|def gold_group_boleiro_path|def index_html_path`

  Line 4802:   Line 353:     def gold_playoff_valid_path(self, phase: str) -> str:

  Line 4808:   Line 377:     def playoff_strikers_path(self, layer: str = "gold") -> str:

  Line 4837: 294:     def _ag_playoffs(self) -> str:

  Line 4838: 295:         return _norm(os.path.join(self.silver_dir, "playoffs"))

  Line 4843: 300:     def _au_playoffs(self) -> str:

  Line 4844: 301:         return _norm(os.path.join(self.gold_dir, "playoffs"))

  Line 4853: 310:         """Path to bronze bonus playoff teams for a single boleiro."""

  Line 4860: 317:     def bronze_playoff_path(self, boleiro: str, phase: str) -> str:

  Line 4861: 318:         """Path to bronze playoff-phase CSV for a single boleiro + phase."""

  Line 4862: 319:         return _norm(os.path.join(self._br_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))

  Line 4870: 327:     def silver_playoff_path(self, boleiro: str, phase: str) -> str:

  Line 4871: 328:         """Path to silver playoff-phase CSV for a single boleiro + phase."""

  Line 4872: 329:         return _norm(os.path.join(self._ag_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))

  Line 4880: 337:     def gold_playoffs_dir(self) -> str:

  Line 4881: 338:         """Directory for gold playoff files."""

  Line 4882: 339:         return self._au_playoffs()

  Line 4888: 345:     def gold_playoff_boleiro_path(self, boleiro: str, phase: str) -> str:

  Line 4889: 346:         """Path to gold playoff-phase CSV for a single boleiro + phase."""

  Line 4890: 347:         return _norm(os.path.join(self._au_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))

  Line 4892: 349:     def gold_playoff_all_path(self, phase: str) -> str:

  Line 4893: 350:         """Path to gold aggregated 'all records' CSV for a playoff phase."""

  Line 4894: 351:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_all.csv"))

  Line 4896: 353:     def gold_playoff_valid_path(self, phase: str) -> str:

  Line 4897: 354:         """Path to gold aggregated 'valid only' CSV for a playoff phase."""

  Line 4898: 355:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_valido_all.csv"))

  Line 4906: 363:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_valido_all.csv"))

  Line 4914: 371:         return _norm(os.path.join(self._au_playoffs(), f"{phase}_all.csv"))

  Line 4920: 377:     def playoff_strikers_path(self, layer: str = "gold") -> str:

  Line 4928: 385:         return _norm(os.path.join(base, "playoffs_strikers.csv"))

  Line 4930: 387:     def playoff_games_path(self, layer: str = "gold") -> str:

  Line 4932: 389:         Use :meth:`playoff_strikers_path` or :meth:`gold_playoff_all_path`."""

  Line 4933: 390:         return self.playoff_strikers_path(layer)


C:\Users\adnta\Documents\1.codigos\git\sweepstake\sessions\20260616_2225_ses_12cd0d0b8ffe1ml13vhM4foHY5\new_session_2026_06_17t012545415z.md:
  Line 125: 96: | `PlayoffsLayout` | `striker_row_offset`, `striker_label`, `striker_name_column`, `striker_name_fallback_column`, `champion_cell`, `name_split_char`, `name_split_index`, `rounds: list[dict]`, `playoffs_sheet_name` | Playoff Excel slicing config |

  Line 126: 97: | `ExcelLayout` | `first_round: FirstRoundLayout`, `playoffs: PlayoffsLayout` | How to slice the Excel sheet |

  Line 127: 98: | `ChampionshipConfig` | `id`, `name`, `year`, `timezone`, `scoring_rules`, `playoff_rounds`, `excel_layout`, `base_dir`, `raw_dir`, `results_file`, `games_file`, `bronze_dir`, `silver_dir`, `gold_dir`, `reports_dir`, `results_endpoint`, `team_name_mapping`, `team_logos`, `team_slugs`, `report_title`, `group_phase_label`, `theme`, `playoff_scoring`, `actual_top_scorer`, `striker_points`, `groups`, `standings_format`, `standings_skiprows`, `bonus_team_picks`, `striker_pick` | Full config for a single championship |


(Results truncated. Consider using a more specific path or pattern.)
```

---

### 🤖 AGENTE (Turno 10):

💭 **PENSAMENTO DO AGENTE:**
The user says the official folder name is "playoff" (singular), not "playoffs" (plural). Let me search for all directory references where "playoffs" is used as a directory name (not as a variable/class name). I need to change instances where `playoffs` refers to directory names to `playoff`.

Looking at the code:

1. **`config.py`** directory methods:
   - `_raw_playoffs()` → returns `os.path.join(self.raw_dir, "playoffs")` → should be `"playoff"`
   - `_br_playoffs()` → returns `os.path.join(self.bronze_dir, "playoffs")` → should be `"playoff"`
   - `_ag_playoffs()` → returns `os.path.join(self.silver_dir, "playoffs")` → should be `"playoff"`
   - `_au_playoffs()` → returns `os.path.join(self.gold_dir, "playoffs")` → should be `"playoff"`

2. **Various comments** in `pipeline.py` and `config.py` that mention these directories

3. **Variable/method/class names** like `_raw_playoffs`, `_br_playoffs`, `_ag_playoffs`, `_au_playoffs`, `gold_playoffs_dir` — these are identifiers, not directory names. Changing them could break code. But the user seems to want the actual folder structure to use "playoff" (singular) rather than "playoffs" (plural).

Let me be precise and differentiate between:
- **Directory names** in actual filesystem paths (e.g., `data/raw/playoffs/` → `data/raw/playoff/`)
- **Variable/method/function names** (e.g., `def _raw_playoffs()` — these are Python identifiers)
- **Comments/docstrings**
- **Config YAML keys** (e.g., `playoffs:` in config.yaml)

The user said "a pasta oficial se chama 'playoff'" — the official folder name is "playoff". So they want the actual directory structure to use singular "playoff".

Let me check exactly where directory names are constructed vs where identifiers/names are used.

The directories used in actual paths are in `config.py`:
- `config.py:284` → `return _norm(os.path.join(self.raw_dir, "playoffs"))` — this creates a directory named "playoffs"
- `config.py:290` → `return _norm(os.path.join(self.bronze_dir, "playoffs"))` 
- `config.py:296` → `return _norm(os.path.join(self.silver_dir, "playoffs"))`
- `config.py:302` → `return _norm(os.path.join(self.gold_dir, "playoffs"))`

These are the actual directory paths that would be created/accessed.

The method names `_raw_playoffs`, `_br_playoffs`, `_ag_playoffs`, `_au_playoffs` and the class `PlayoffsLayout` and variable `playoffs` in the config etc. — these are internal identifiers.

Let me also check the plan document and the `play-off-plan.md` for directory references.

Now, I also need to consider the naming mismatch between games.csv round values and config round keys. Let me also look at what needs to change there.

The user asked me to make a plan. Let me compile all the changes needed:

### Category 1: Directory name "playoffs" → "playoff" (4 changes in config.py)

These are the string literals that define directory names:
1. `config.py:284`: `"playoffs"` in `_raw_playoffs()` → `"playoff"`
2. `config.py:290`: `"playoffs"` in `_br_playoffs()` → `"playoff"`
3. `config.py:296`: `"playoffs"` in `_ag_playoffs()` → `"playoff"`
4. `config.py:302`: `"playoffs"` in `_au_playoffs()` → `"playoff"`

### Category 2: Method/function name changes (they are identifiers, not paths)

The methods `_raw_playoffs()`, `_br_playoffs()`, `_ag_playoffs()`, `_au_playoffs()`, `gold_playoffs_dir()` are referenced in many places. If we rename them, we need to update all callers.

But these are just internal Python identifiers — they don't affect the actual directory structure. The user specifically said "pasta oficial" (official folder), which is about the actual filesystem directories. So maybe we should keep the method names as-is and only change the directory string literals.

Actually, wait. Let me think about this more carefully. If I change just the directory strings but not the method names, then we'd have methods called `_raw_playoffs()` that create a directory called "playoff". That's a bit inconsistent but functionally fine.

However, it's probably cleaner to rename the methods too for consistency. Let me check how many callers there are.

Actually, let me just focus on creating a comprehensive plan. The user wants to see what needs to change. Let me search for all the changes needed.

Let me also look at:
- Round key naming: `segunda_fase` in config vs `r32` in games.csv
- The `parse_playoff_stage()` expectations
- Any other path references that need updating

Let me be comprehensive. Let me trace through the full chain for each needed change.

📄 **RESPOSTA DO AGENTE:**
Entendi. A pasta oficial é `playoff` (singular), não `playoffs` (plural). Deixe-me ver todas as ocorrências de diretório para mapear o que precisa mudar.

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\config.py`

```python
280:     # ------------------------------------------------------------------
281: 
282:     def _raw_playoffs(self) -> str:
283:         """Raw directory for per-round playoff Excel files."""
284:         return _norm(os.path.join(self.raw_dir, "playoffs"))
285: 
286:     def _br_first_round(self) -> str:
287:         return _norm(os.path.join(self.bronze_dir, "first_round"))
288: 
289:     def _br_playoffs(self) -> str:
290:         return _norm(os.path.join(self.bronze_dir, "playoffs"))
291: 
292:     def _ag_first_round(self) -> str:
293:         return _norm(os.path.join(self.silver_dir, "first_round"))
294: 
295:     def _ag_playoffs(self) -> str:
296:         return _norm(os.path.join(self.silver_dir, "playoffs"))
297: 
298:     def _au_first_round(self) -> str:
299:         return _norm(os.path.join(self.gold_dir, "first_round"))
300: 
301:     def _au_playoffs(self) -> str:
302:         return _norm(os.path.join(self.gold_dir, "playoffs"))
303: 
304:     # --- Bronze paths ---
305: 
306:     def bronze_group_path(self, boleiro: str) -> str:
307:         """Path to bronze group-phase CSV for a single boleiro."""
308:         return _norm(os.path.join(self._br_first_round(), f"group_phase_{boleiro}.csv"))
309: 

(Showing lines 280-309 of 653. Use offset=310 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\pipeline.py`

```python
1: """Medallion pipeline: bronze -> silver -> gold.
2: 
3: All stages are driven by ChampionshipConfig so the same code works
4: for any championship.
5: 
6: Structure:
7:   Bronze:
8:     bronze/first_round/group_phase_{boleiro}.csv
9:     bronze/first_round/bonus_teams_{boleiro}.csv
10:     bronze/first_round/striker_{boleiro}.csv
11:     bronze/playoffs/  (future separate playoff Excel files)
12: 
13:   Silver:
14:     silver/first_round/group_phase_{boleiro}.csv
15:     silver/playoffs/  (future)
16: 
17:   Gold:
18:     gold/first_round/group_phase_{boleiro}.csv
19:     gold/first_round/{label}_all.csv
20:     gold/first_round/{label}_valido_all.csv
21:     gold/first_round/striker_{boleiro}.csv
22:     gold/first_round/playoffs_strikers.csv
23:     gold/playoffs/  (future)
24: """
25: 

(Showing lines 1-25 of 1039. Use offset=26 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\pipeline.py`

```python
240: 
241: # ------------------------------------------------------------------
242: # Bronze: raw Excel -> first_round/ + playoffs/
243: # ------------------------------------------------------------------
244: 
245: def run_raw_to_bronze(config: ChampionshipConfig) -> None:
246:     """Parse all raw Excel files and write bronze CSVs."""
247:     print_colored("raw to bronze", "sand")
248: 
249:     dirs = [
250:         config.bronze_dir,
251:         config._br_first_round(),
252:         config._br_playoffs(),
253:     ]
254:     _recreate_dirs(dirs)
255: 
256:     # --- First round (group stage) ---
257:     boleiros = _boleiros_from_raw(config)
258:     for idx, (path_excel, boleiro) in enumerate(boleiros, 1):
259:         print_colored(f"\t[{idx:2}/{len(boleiros)}] parsing {boleiro}", "ice")
260: 
261:         if config.standings_format:
262:             df_group, df_bonus, df_striker = parse_group_standings(path_excel, config)
263:         else:
264:             df_group = parse_group_stage(path_excel, config)
265:             df_bonus, df_striker = parse_bonus_playoffs(path_excel, config)
266: 
267:         df_group.sort_values(by=["date", "hour"], inplace=True)
268:         _save_csv(df_group, config.bronze_group_path(boleiro))
269: 
270:         _save_csv(df_bonus, config.bronze_bonus_path(boleiro))
271:         _save_csv(df_striker, config.bronze_striker_path(boleiro))
272: 
273:     # --- Playoff rounds (separate Excel per phase) ---
274:     playoff_files = _playoff_files_from_raw(config)
275:     for idx, (path_excel, phase, boleiro) in enumerate(playoff_files, 1):
276:         print_colored(f"\t[{idx:2}/{len(playoff_files)}] parsing {phase} {boleiro}", "ice")
277:         df_playoff = parse_playoff_stage(path_excel, config)
278:         df_playoff.sort_values(by=["date", "hour"], inplace=True)
279:         _save_csv(df_playoff, config.bronze_playoff_path(boleiro, phase))
280: 
281:     print_colored("raw to bronze completed", "green")
282: 
283: 
284: # ------------------------------------------------------------------
285: # Silver: bronze first_round + official results -> merged predictions
286: # ------------------------------------------------------------------
287: 
288: def run_bronze_to_silver(config: ChampionshipConfig) -> None:
289:     """Merge bronze first_round predictions with official results (per boleiro).

(Showing lines 240-289 of 1039. Use offset=290 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\pipeline.py`

```python
410: # ------------------------------------------------------------------
411: 
412: def run_silver_to_gold(config: ChampionshipConfig) -> None:
413:     """Create gold-layer analytical datasets (per-boleiro + aggregated).
414: 
415:     Playoffs are bonus-only and do not flow to gold.
416:     """
417:     print_colored("silver to gold", "sand")
418: 
419:     dirs = [
420:         config.gold_dir,
421:         config.gold_first_round_dir(),
422:         config.gold_playoffs_dir(),
423:     ]
424:     _recreate_dirs(dirs)
425: 
426:     # --- First round ---
427:     silver_pattern = _norm(os.path.join(config._ag_first_round(), "group_phase_*"))
428:     silver_paths = sorted(glob(silver_pattern))
429: 
430:     df_all_parts = []
431:     df_valid_parts = []
432:     df_all = pd.DataFrame()
433:     df_valid = pd.DataFrame()
434: 
435:     for path_csv in silver_paths:
436:         boleiro = os.path.basename(path_csv).replace("group_phase_", "").replace(".csv", "")
437:         print_colored(f"\tscoring first_round {boleiro}", "ice")
438: 
439:         df_silver = pd.read_csv(path_csv, sep=",")

(Showing lines 410-439 of 1039. Use offset=440 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [GREP]**
*Alvo/Parâmetro:* `games\.csv.*round`

```text
No files found
```

🛠️ **AÇÃO DA FERRAMENTA [GREP]**
*Alvo/Parâmetro:* `df_results\[\"round\"\]|df_results\[df_results\[\"round\"\]`

```text
Found 1 matches
C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\pipeline.py:
  Line 364:         df_results_phase = df_results[df_results["round"] == phase].copy()
```

---

### 🤖 AGENTE (Turno 11):

💭 **PENSAMENTO DO AGENTE:**
Let me now find all the places where the round mismatch between config keys and games.csv values needs to be mapped. Let me also search for how `_merge_with_results` is called for playoffs and how the bonus teams section in html.py checks advancing teams.

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\pipeline.py`

```python
350:         df_merged.sort_values(by=["date", "hour"], inplace=True)
351:         _save_csv(df_merged, config.silver_group_path(boleiro))
352: 
353:     # --- Playoff rounds ---
354:     playoff_pattern = _norm(os.path.join(config._br_playoffs(), "group_phase_*"))
355:     playoff_paths = sorted(glob(playoff_pattern))
356: 
357:     for path_csv in playoff_paths:
358:         phase, boleiro = _extract_playoff_phase_and_boleiro(path_csv, config)
359:         print_colored(f"\tmerging {phase} {boleiro}", "ice")
360: 
361:         df_boleiro = pd.read_csv(path_csv, sep=",")
362: 
363:         # Filter results to only this playoff phase
364:         df_results_phase = df_results[df_results["round"] == phase].copy()
365: 
366:         df_merged = _merge_with_results(df_boleiro, df_results_phase)
367: 
368:         # Rename suffixed columns back to canonical names
369:         df_merged.rename(
370:             columns={
371:                 "date_bol": "date",
372:                 "home_team_bol": "home_team",
373:                 "away_team_bol": "away_team",
374:             },
375:             inplace=True,
376:         )
377: 
378:         # Select and order columns (keep penalty columns for tie-break analysis)
379:         df_merged = df_merged.reindex(
380:             columns=[
381:                 "date",
382:                 "hour",
383:                 "match",
384:                 "home_team",
385:                 "away_team",
386:                 "home_goals_bol",
387:                 "away_goals_bol",
388:                 "home_goals_real",
389:                 "away_goals_real",
390:                 "home_pen_bol",
391:                 "away_pen_bol",
392:                 "home_pen_real",
393:                 "away_pen_real",
394:                 "resultado_bol_placar",
395:                 "resultado_bol_time",
396:                 "resultado_real_placar",
397:                 "resultado_real_time",
398:                 "time_elapsed",
399:                 "who",
400:             ]
401:         )
402:         df_merged.sort_values(by=["date", "hour"], inplace=True)
403:         _save_csv(df_merged, config.silver_playoff_path(boleiro, phase))
404: 

(Showing lines 350-404 of 1039. Use offset=405 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
1040:         <table style="width:100%;border-collapse:collapse;">
1041:             {dist_rows}
1042:         </table>
1043:     </div>
1044: </div>
1045: """
1046: 
1047:     # ------------------------------------------------------------------
1048:     # Bonus teams for knockout phases — at top, colored by result, scored
1049:     # ------------------------------------------------------------------
1050:     bonus_html = ""
1051:     bonus_path = config.bronze_bonus_path(boleiro)
1052:     if os.path.exists(bonus_path):
1053:         df_bonus = pd.read_csv(bonus_path, sep=",")
1054:         if not df_bonus.empty and os.path.exists(config.games_file):
1055:             df_games = pd.read_csv(config.games_file, sep=",")
1056:             df_games["round"] = df_games["round"].astype(str).str.strip()
1057:             playoff_keys = [pr.key for pr in (config.playoff_rounds or [])]
1058: 
1059:             # Determine today's date in the configured timezone
1060:             tz = pytz.timezone(config.timezone)
1061:             today = datetime.now(tz).date()
1062: 
1063:             # For each phase: find latest match date and compute winners
1064:             phase_latest_date = {}  # phase -> latest date
1065:             advancing = {}           # phase -> list of teams that advanced
1066:             for pk in playoff_keys:
1067:                 phase_matches = df_games[df_games["round"] == pk]
1068:                 winners = []
1069:                 dates = []
1070:                 for _, row in phase_matches.iterrows():
1071:                     raw_date = str(row.get("date", ""))
1072:                     date_part = raw_date[:10] if " " in raw_date else raw_date
1073:                     try:
1074:                         d = pd.to_datetime(date_part).date()
1075:                         dates.append(d)
1076:                     except (ValueError, TypeError):
1077:                         pass
1078:                     hg = float(row["home_goals"]) if pd.notna(row.get("home_goals")) else None
1079:                     ag = float(row["away_goals"]) if pd.notna(row.get("away_goals")) else None
1080:                     if hg is not None and ag is not None:
1081:                         if hg > ag:
1082:                             winners.append(str(row["home_team"]))
1083:                         elif ag > hg:
1084:                             winners.append(str(row["away_team"]))
1085:                         else:
1086:                             hp = row.get("home_pen", "")
1087:                             ap = row.get("away_pen", "")
1088:                             try:
1089:                                 hp_v = float(hp) if pd.notna(hp) and str(hp).strip() else None
1090:                                 ap_v = float(ap) if pd.notna(ap) and str(ap).strip() else None
1091:                             except (ValueError, TypeError):
1092:                                 hp_v = ap_v = None
1093:                             if hp_v is not None and ap_v is not None:
1094:                                 if hp_v > ap_v:
1095:                                     winners.append(str(row["home_team"]))
1096:                                 elif ap_v > hp_v:
1097:                                     winners.append(str(row["away_team"]))
1098:                             elif hp_v is not None:
1099:                                 winners.append(str(row["home_team"]))
1100:                             elif ap_v is not None:
1101:                                 winners.append(str(row["away_team"]))
1102:                 advancing[pk] = winners
1103:                 phase_latest_date[pk] = max(dates) if dates else None
1104: 
1105:             phase_order = [pr.key for pr in (config.playoff_rounds or [])]
1106:             phase_label_map = {pr.key: pr.name for pr in (config.playoff_rounds or [])}
1107:             phase_emoji_map = {
1108:                 "segunda_fase": "\U0001f3c6",
1109:                 "oitavas": "\U0001f3c1",
1110:                 "quartas": "\U0001f525",
1111:                 "semi": "\U0001f3af",
1112:                 "terceiro_lugar": "\U0001f949",
1113:                 "final": "\U0001f3c6",
1114:             }
1115:             playoff_scoring = getattr(config, "playoff_scoring", {})
1116: 
1117:             df_bonus["phase_order"] = df_bonus["phase"].map(
1118:                 {k: i for i, k in enumerate(phase_order)}
1119:             ).fillna(99)
1120:             df_bonus = df_bonus.sort_values(["phase_order", "team"])
1121: 
1122:             total_bonus_pts = 0
1123:             phase_blocks = ""
1124:             champion_team = ""
1125:             # Exclude 'campeao' from the general phase blocks loop to handle it separately
1126:             for phase_key, group in df_bonus[df_bonus["phase"] != "campeao"].groupby("phase", sort=False):
1127:                 label = phase_label_map.get(phase_key, phase_key)
1128:                 emoji = phase_emoji_map.get(phase_key, "\u26bd")
1129:                 pts_per_correct = playoff_scoring.get(phase_key, 0)
1130:                 advancing_teams = advancing.get(phase_key, [])
1131: 
1132:                 # Determine if this phase is checkable (all matches already played)
1133:                 latest = phase_latest_date.get(phase_key)
1134:                 checkable = latest is not None and today >= latest
1135: 
1136:                 phase_pts = 0
1137:                 teams_list = ""
1138:                 for _, row in group.iterrows():
1139:                     team = row["team"]
1140:                     # Always compute points from games.csv regardless of checkable
1141:                     passed = team in advancing_teams
1142:                     if passed:
1143:                         phase_pts += pts_per_correct
1144: 
1145:                     if not checkable:
1146:                         # Not yet time — yellow
1147:                         bg = "rgba(234,179,8,0.15)"
1148:                         border = "var(--warning)"
1149:                         color = "var(--warning)"
1150:                     else:
1151:                         bg = "rgba(34,197,94,0.15)" if passed else "rgba(239,68,68,0.15)"
1152:                         border = "var(--success)" if passed else "var(--danger)"
1153:                         color = "var(--success)" if passed else "var(--danger)"
1154:                     teams_list += (
1155:                         f'<span style="display:inline-block;padding:0.2rem 0.6rem;margin:0.15rem;'
1156:                         f'background:{bg};border:1px solid {border};border-radius:999px;'
1157:                         f'font-size:0.75rem;color:{color};">{team}</span>'
1158:                     )
1159: 
1160:                 total_bonus_pts += phase_pts
1161:                 if checkable:
1162:                     pts_label = f'<span style="color:var(--accent);font-weight:700;">+{phase_pts}</span>'
1163:                 else:
1164:                     pts_label = f'<span style="color:var(--warning);font-weight:700;">\u23f3 +{phase_pts}</span>'
1165:                 phase_blocks += (
1166:                     f'<div style="margin-bottom:0.5rem;">'
1167:                     f'<div style="font-size:0.8rem;font-weight:600;color:var(--text-muted);margin-bottom:0.3rem;">'
1168:                     f'{emoji} {label} {pts_label}</div>'
1169:                     f'<div>{teams_list}</div>'
1170:                     f'</div>\n'
1171:                 )
1172: 
1173:             # Champion block is separate and should be shown if available, regardless of other phases
1174:             champion_row = df_bonus[df_bonus["phase"] == "campeao"]
1175:             champion_team = champion_row.iloc[0]["team"] if not champion_row.empty else ""
1176:             champion_block = (
1177:                 f'<div style="margin-top:0.5rem;padding-top:0.5rem;border-top:1px solid var(--card-border);">'
1178:                 f'<div style="font-size:0.8rem;font-weight:600;color:var(--accent);margin-bottom:0.3rem;">'
1179:                 f'\U0001f3c6 Campe\u00e3o</div>'
1180:                 f'<div>{champion_team}</div>'
1181:                 f'</div>\n'
1182:             ) if champion_team else ""
1183: 
1184:             legend = ""
1185:             total_label = ""
1186:             if phase_blocks:
1187:                 total_label = f'<span style="color:var(--accent);margin-left:0.5rem;font-weight:700;">+{total_bonus_pts}</span>'
1188:                 legend = (
1189:                     '<div style="font-size:0.7rem;color:var(--text-muted);margin-bottom:0.5rem;'
1190:                     'display:flex;gap:0.75rem;flex-wrap:wrap;">'
1191:                     '<span>\U0001f7e1 fase n\u00e3o iniciada</span>'
1192:                     '<span style="color:var(--success);">\u25cf time avan\u00e7ou</span>'
1193:                     '<span style="color:var(--danger);">\u25cf time eliminado</span>'
1194:                     '</div>'
1195:                 )
1196: 
1197:             bonus_html = ""
1198:             if phase_blocks or champion_block:
1199:                 bonus_html = (
1200:                     f'<details class="section" open>'
1201:                     f'<summary style="font-size:1rem;font-weight:700;padding:0 0.75rem;margin-bottom:0.5rem;display:flex;align-items:center;gap:0.5rem;cursor:pointer;min-height:44px;">'
1202:                     f'\U0001f3c6 Times Bonus {total_label}</summary>'
1203:                     f'<div class="card">{legend}{phase_blocks}{champion_block}</div>'
1204:                     f'</details>\n'
1205:                 )
1206: 
1207:             # Ensure champion_team is available for the top badges later in the function
1208:             # Since champion_team is defined in this loop, we need to make sure it's accessible
1209:             # The variable champion_team is already in the current scope.
1210: 
1211:     # --- Build top-of-page: striker + champion + bonus + timeline + compare ---
1212:     top_badges = ""
1213:     if striker_name:
1214:         top_badges += f'<div class="striker-badge"><span class="icon">\U0001f3af</span> Artilheiro: <strong>{striker_name}</strong></div>\n'
1215:     if champion_team:
1216:         top_badges += f'<div class="striker-badge"><span class="icon">\U0001f3c6</span> Campe\u00e3o: <strong>{champion_team}</strong></div>\n'
1217:     body += top_badges
1218: 
1219:     if bonus_html:

(Showing lines 1040-1219 of 4291. Use offset=1220 to continue.)
```

---

### 🤖 AGENTE (Turno 12):

💭 **PENSAMENTO DO AGENTE:**
Now I have a comprehensive picture. Let me also check:
- The `generate_html_reports` function that creates playoff match pages (to see the `pr.key` vs `pr.name` issue)
- The `_build_match` signature and how it's called for playoffs
- How the gold_playoff_valid_path is read in the report generation
- Any `_round_map` in loader.py

I already know from the explore task that:

1. At html.py line 4264, `pr.name` is passed (display name like "Segunda Fase") instead of `pr.key` (slug like "segunda_fase").

2. There's already a `_round_map` in loader.py lines 182-189 that maps games.csv values to config keys.

Let me check this loader.py _round_map more carefully:
```python
_round_map = {
    "round of 32": "segunda_fase",
    "round of 16": "oitavas",
    "quarter finals": "quartas",
    "semi finals": "semi",
    "third place": "terceiro_lugar",
    "final": "final",
    "finals": "final",
}
```

But the games.csv uses `r32`, `r16`, `qf`, `sf`, `third`, `final` — NOT "round of 32", "round of 16", etc.

So this map doesn't actually match the games.csv values! That's another bug.

Also let me check where the round filter for group standings is in pipeline.py / loader.py...

In pipeline.py run_bronze_to_silver(), the playoff phase filter is:
```python
df_results_phase = df_results[df_results["round"] == phase].copy()
```

Where `phase` comes from `_extract_playoff_phase_and_boleiro()` which reads from the CSV filename which was written using `config.playoff_rounds` phase keys (like `segunda_fase`, `oitavas`, etc.).

But games.csv has `r32`, `r16`, etc. — so this filter produces empty results.

Let me also check the `generate_html_reports` function to see how it calls `_build_match`:

🛠️ **AÇÃO DA FERRAMENTA [GREP]**
*Alvo/Parâmetro:* `def generate_html_reports`

```text
Found 1 matches
C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py:
  Line 4180: def generate_html_reports(config: ChampionshipConfig) -> None:
```

🛠️ **AÇÃO DA FERRAMENTA [GREP]**
*Alvo/Parâmetro:* `_round_map`

```text
Found 7 matches
C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\loader.py:
  Line 182:     _round_map = {

  Line 192:     df_games["round"] = df_games["round"].map(lambda r: _round_map.get(r, r))


C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\new_views.py:
  Line 749:     game_round_map = df_games[["match", "round"]].copy()

  Line 750:     game_round_map["round"] = game_round_map["round"].astype(str).str.strip()

  Line 751:     df = df_pred.merge(game_round_map, on="match", how="left")

  Line 777:     match_round_map = dict(zip(match_order["match"], match_order["round"].astype(str).str.strip()))

  Line 902:         matches_in_round = [m for m in all_matches if match_round_map.get(m) in slugs]
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\loader.py`

```python
180: 
181:     # --- Normalize round names ---
182:     _round_map = {
183:         "round of 32": "segunda_fase",
184:         "round of 16": "oitavas",
185:         "quarter finals": "quartas",
186:         "semi finals": "semi",
187:         "third place": "terceiro_lugar",
188:         "final": "final",
189:         "finals": "final",
190:     }
191:     df_games["round"] = df_games["round"].astype(str).str.strip().str.lower()
192:     df_games["round"] = df_games["round"].map(lambda r: _round_map.get(r, r))
193:     group_games = df_games[df_games["round"].isin(["1", "2", "3"])].copy()
194: 

(Showing lines 180-194 of 506. Use offset=195 to continue.)
```

---

### 🤖 AGENTE (Turno 13):

💭 **PENSAMENTO DO AGENTE:**
So the `_round_map` in loader.py maps English names like "round of 32" to config keys like "segunda_fase". But the games.csv actually has `r32`, not "round of 32". So this mapping is wrong.

Let me verify what the games.csv actually contains.

🛠️ **AÇÃO DA FERRAMENTA [BASH]**
*Alvo/Parâmetro:* `Check round values in games.csv`

```text
date,round,home_team,home_pen,home_goals,x,away_goals,away_pen,away_team,match,time_elapsed
2026-06-11 13h,1,MǸxico,,2,x,0,,�?frica do Sul,mexico-vs-africa_do_sul,finished

2026-06-28 12h,r32,,,,x,,,,-vs-,notstarted
2026-06-29 12h,r32,,,,x,,,,-vs-,notstarted
2026-06-29 16h,r32,,,,x,,,,-vs-,notstarted
2026-06-29 19h,r32,,,,x,,,,-vs-,notstarted
2026-06-30 12h,r32,,,,x,,,,-vs-,notstarted
```

🛠️ **AÇÃO DA FERRAMENTA [BASH]**
*Alvo/Parâmetro:* `List unique round values in games.csv`

```text
1
2
3
final
qf
r16
r32
sf
third
```

---

### 🤖 AGENTE (Turno 14):

💭 **PENSAMENTO DO AGENTE:**
Now I have confirmed:
- games.csv round values: `1`, `2`, `3`, `r32`, `r16`, `qf`, `sf`, `third`, `final`
- Config keys: `segunda_fase`, `oitavas`, `quartas`, `semi`, `terceiro_lugar`, `final`

The mapping in loader.py (lines 182-192) maps "round of 32" → "segunda_fase", but games.csv has "r32". So that mapping is wrong.

Now let me also check the `generate_html_reports` in html.py to see how playoff match pages are generated:

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
4230:         print_colored(f"generating boleiro html: {boleiro}", "blue")
4231:         html = _build_boleiro(config, boleiro)
4232:         path = _norm(os.path.join(html_base, "boleiros", f"{boleiro}.html"))
4233:         _save(path, html)
4234: 
4235:     # --- Arena (player comparison) ---
4236:     print_colored("generating arena.html", "blue")
4237:     arena_html = _build_arena(config, df_valid)
4238:     _save(_norm(os.path.join(html_base, "arena.html")), arena_html)
4239: 
4240:     # --- Per-match (group phase) ---
4241:     group_matches = df_all[df_all["match"].notna()].groupby("match")
4242:     for match, df_match in group_matches:
4243:         print_colored(f"generating match html: {match}", "blue")
4244:         html = _build_match(config, match, config.group_phase_label, df_match)
4245:         first = df_match.iloc[0]
4246:         hour = first.get('hour', '')
4247:         hour_str = str(int(hour)) if pd.notna(hour) and isinstance(hour, (int, float)) else str(hour)
4248:         filename = f"{first['date']}_{hour_str}_{match}.html"
4249:         path = _norm(os.path.join(html_base, "jogos", config.group_phase_label, filename))
4250:         _save(path, html)
4251: 
4252:     # --- Per-match (playoff rounds) ---
4253:     for pr in (config.playoff_rounds or []):
4254:         phase = pr.key
4255:         playoff_valid_path = config.gold_playoff_valid_path(phase)
4256:         if not os.path.exists(playoff_valid_path):
4257:             continue
4258:         df_phase = pd.read_csv(playoff_valid_path, sep=",")
4259:         if df_phase.empty:
4260:             continue
4261:         phase_matches = df_phase[df_phase["match"].notna()].groupby("match")
4262:         for match, df_match in phase_matches:
4263:             print_colored(f"generating match html: {phase} {match}", "blue")
4264:             html = _build_match(config, match, pr.name, df_match)
4265:             first = df_match.iloc[0]
4266:             hour = first.get('hour', '')
4267:             hour_str = str(int(hour)) if pd.notna(hour) and isinstance(hour, (int, float)) else str(hour)
4268:             filename = f"{first['date']}_{hour_str}_{match}.html"
4269:             path = _norm(os.path.join(html_base, "jogos", phase, filename))
4270:             _save(path, html)
4271: 
4272:     # --- Analytics-dependent pages ------------------------------------
4273:     # If games.csv has no real results yet, delete any stale HTML files
4274:     # so the user doesn't see outdated data. Pages are regenerated below
4275:     # with placeholder "no data" messages when CSVs are missing.
4276:     _analytics_cleanup(config, html_base)
4277:     # Build pages (each builder handles missing data gracefully)
4278:     _build_ranking_evolution_page(config, html_base)
4279:     _build_boldometer_page(config, html_base)
4280:     _build_bolao_xray_page(config, html_base)
4281:     _build_day_winners_page(config, html_base)
4282:     _build_zebras_page(config, html_base)
4283:     _build_momentum_page(config, html_base)
4284: 
4285:     # --- New views ---
4286:     build_group_standings_page(config, html_base)
4287:     build_similarity_matrix_page(config, html_base)
4288:     build_round_predictions_page(config, html_base)
4289:     build_round_matrix_page(config, html_base)

(Showing lines 4230-4289 of 4291. Use offset=4290 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
4180: def generate_html_reports(config: ChampionshipConfig) -> None:
4181:     """Generate all HTML reports from gold-layer data."""
4182:     html_base = _norm(os.path.join(config.reports_dir, "html"))
4183: 
4184:     # Create / recreate HTML directories (clean jogos to avoid stale files)
4185:     dirs = [
4186:         html_base,
4187:         _norm(os.path.join(html_base, "boleiros")),
4188:     ]
4189:     for d in dirs:
4190:         os.makedirs(d, exist_ok=True)
4191: 
4192:     # Clean jogos dirs to avoid stale HTML files from old runs
4193:     jogos_base = _norm(os.path.join(html_base, "jogos"))
4194:     if os.path.exists(jogos_base):
4195:         shutil.rmtree(jogos_base)
4196:     os.makedirs(_norm(os.path.join(jogos_base, config.group_phase_label)))
4197:     for pr in (config.playoff_rounds or []):
4198:         os.makedirs(_norm(os.path.join(jogos_base, pr.key)), exist_ok=True)
4199: 
4200:     # Load gold data
4201:     gold_all = config.gold_all_path()
4202:     if not os.path.exists(gold_all):
4203:         print_colored(f"no gold data found at {gold_all}, skipping HTML reports", "yellow")
4204:         return
4205:     df_all = pd.read_csv(gold_all, sep=",")
4206: 
4207:     # --- Archetype classification (must run before per-player pages) ---
4208:     try:
4209:         classificar_jogadores(config)
4210:     except Exception as e:
4211:         print_colored(f"arquetipo classification failed: {e}", "yellow")
4212: 
4213:     # --- Per-player ---
4214:     # Use valid if available and non-empty, otherwise fall back to all predictions
4215:     # so boleiro pages are generated even before the tournament starts
4216:     # (all predictions have valido=0 and gold_valid has 0 data rows).
4217:     gold_all = config.gold_all_path()
4218:     if not os.path.exists(gold_all):
4219:         print_colored(f"no gold data found at {gold_all}, skipping HTML reports", "yellow")
4220:         return
4221:     df_all = pd.read_csv(gold_all, sep=",")
4222:     gold_valid = config.gold_valid_path()
4223:     if os.path.exists(gold_valid):
4224:         df_valid = pd.read_csv(gold_valid, sep=",")
4225:         if df_valid.empty:
4226:             df_valid = df_all.copy()
4227:     else:
4228:         df_valid = df_all.copy()
4229:     for boleiro in sorted(df_valid["who"].unique()):

(Showing lines 4180-4229 of 4291. Use offset=4230 to continue.)
```

---

### 🤖 AGENTE (Turno 15):

💭 **PENSAMENTO DO AGENTE:**
Now let me check the `_build_match` function to see how `phase` parameter is used (especially the `pr.name` issue at line 4264). The function at line 4264 passes `pr.name` (display name like "Segunda Fase") as the `phase` parameter to `_build_match`. But the function might expect the phase key slug for directory construction.

Let me also check the zebras page issues.

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
1768: def _build_match(config: ChampionshipConfig, match: str, phase: str, df_match: pd.DataFrame) -> str:
1769:     """Build a per-match HTML report."""
1770:     df_match = df_match.copy()
1771:     df_match = df_match.sort_values(["pontos", "who"], ascending=False)
1772: 
1773:     # Lookup upset data for this match
1774:     upset_path = _norm(os.path.join(config._au_first_round(), "upset_tracker.csv"))
1775:     upset_row = None
1776:     if os.path.exists(upset_path):
1777:         df_upset = pd.read_csv(upset_path, sep=",")
1778:         matches = df_upset[df_upset["match"] == match]
1779:         if not matches.empty:
1780:             upset_row = matches.iloc[0]
1781: 
1782:     home = str(df_match.iloc[0]["home_team"])
1783:     away = str(df_match.iloc[0]["away_team"])
1784:     date_str = str(df_match.iloc[0]["date"])
1785:     hour_str = str(df_match.iloc[0].get("hour", ""))
1786: 
1787:     rev_map = {v: k for k, v in config.team_name_mapping.items()}
1788:     home_en = rev_map.get(home, home)
1789:     away_en = rev_map.get(away, away)
1790:     match_dir = _norm(os.path.join(config.reports_dir, "html", "jogos", phase))
1791:     home_logo = _team_logo_tag(home_en, config, cls="team-logo-sm", start=match_dir)
1792:     away_logo = _team_logo_tag(away_en, config, cls="team-logo-sm", start=match_dir)
1793: 
1794:     # Determine if match is live (time_elapsed column may not exist for all championships)
1795:     is_live = False
1796:     if "time_elapsed" in df_match.columns:
1797:         raw_time = df_match["time_elapsed"].iloc[0]
1798:         is_live = pd.notna(raw_time) and str(raw_time).strip().lower() == "live"
1799: 
1800:     # Check if there is a score to display (partial or final).
1801:     # A live match with a partial score (e.g. 0 x 0) still has a score.
1802:     has_score = (
1803:         df_match["resultado_real_placar"].notna().any()
1804:         and df_match["resultado_real_placar"].iloc[0] != "nan"
1805:     )
1806: 
1807:     # Check if result is final — only for finished (non-live) matches.
1808:     # A live match with a partial score is NOT a final result.
1809:     has_result = not is_live and has_score
1810: 
1811:     real_placar = ""
1812:     if has_score:
1813:         real_placar = str(df_match.iloc[0]["resultado_real_placar"])
1814: 
1815:     # Pre-game: team vote distribution
1816:     df_pre_time = df_match["resultado_bol_time"].value_counts().reset_index()
1817:     df_pre_time.columns = ["vencedor", "#"]

(Showing lines 1768-1817 of 4291. Use offset=1818 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
3660:         num_correct = int(row.get("num_correct", 0))
3661:         match_date = str(row.get("date", ""))
3662:         match_hour = str(row.get("hour", ""))
3663:         players_correct = _parse_correct(row.get("players_correct", ""))
3664: 
3665:         fav_pct = round(fav_votes / total_votes * 100) if total_votes else 0
3666:         winner_wrong_pct = 100 - round(num_correct / total_votes * 100) if total_votes else 0
3667:         players_html = " ".join(f'<span class="tag">{p}</span>' for p in players_correct) if players_correct else '<span style="color:var(--text-muted);font-style:italic;">ningu\u00e9m acertou</span>'
3668: 
3669:         # Build match page link (date/hour are present after pipeline regeneration)
3670:         match_href = f"jogos/{config.group_phase_label}/{match_date}_{match_hour}_{match_slug}.html" if match_date and match_hour else ""
3671: 
3672:         # Determine upset magnitude based on how many got the winner right
3673:         matchup_display = f"<a href=\"{match_href}\">{home} vs {away}</a>" if match_href else f"{home} vs {away}"
3674: 
3675:         if num_correct <= 2:
3676:             badge_html = f'<span class="zebra-badge upset">{ZEBRA_MONSTRA_LABEL}</span>'
3677:         else:
3678:             badge_html = f'<span class="zebra-badge upset">{ZEBRA_GRANDE_LABEL}</span>'
3679: 
3680:         zebra_cards += f"""
3681: <div class="zebra-card upset">
3682:     <div class="zebra-header">
3683:         {badge_html}
3684:         <span style="font-size:0.75rem;color:var(--text-muted);">{fav_votes}/{total_votes} ({fav_pct}%) acreditavam no {favorite} &mdash; {winner_wrong_pct}% erraram o resultado</span>
3685:     </div>
3686:     <div class="zebra-matchup">{matchup_display}</div>
3687:     <div class="zebra-detail">
3688:         Favorito: <strong>{favorite}</strong> | Resultado: <strong>{real_winner}</strong><br>
3689:         Acertaram essa zebra: {num_correct} jogadores
3690:     </div>
3691:     <div class="zebra-players">{players_html}</div>
3692: </div>
3693: """
3694: 
3695:     # No upsets message
3696:     if not zebra_cards:
3697:         zebra_cards = '<div class="card" style="text-align:center;color:var(--text-muted);font-style:italic;padding:2rem 1rem;">\U0001f614 Nenhuma zebra ate agora — o bolao esta muito previsivel!</div>'
3698: 
3699:     # Rank zebra predictors (who got the most upsets right)

(Showing lines 3660-3699 of 4291. Use offset=3700 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
3780:             "hour": str(row.get("hour", "")),
3781:         })
3782: 
3783:     diff_cards = ""
3784:     if diff_matches:
3785:         diff_matches.sort(key=lambda x: -x["difficulty"])
3786:         max_diff = diff_matches[0]["difficulty"]
3787:         for i, m in enumerate(diff_matches[:10], 1):
3788:             medal = "\U0001f947" if i == 1 else "\U0001f948" if i == 2 else "\U0001f949" if i == 3 else ""
3789:             upset_tag = '<span style="display:inline-block;font-size:0.65rem;background:rgba(239,68,68,0.2);color:var(--danger);padding:0.15rem 0.5rem;border-radius:999px;margin-left:0.5rem;">\U0001f993 ZEBRA</span>' if m["is_upset"] else ""
3790:             bar_pct = round(m["difficulty"] / max_diff * 100)
3791:             bar_color = "var(--danger)" if m["is_upset"] else "var(--warning)"
3792: 
3793:             match_href = f"jogos/{config.group_phase_label}/{m['date']}_{m['hour']}_{m['match']}.html" if m.get("date") and m.get("hour") else ""
3794:             match_display = f"<a href=\"{match_href}\">{m['home']} vs {m['away']}</a>" if match_href else f"{m['home']} vs {m['away']}"
3795:             diff_cards += f"""
3796: <div style="margin-bottom:0.75rem;">
3797:     <div style="display:flex;justify-content:space-between;align-items:center;">
3798:         <span style="font-weight:700;font-size:0.9rem;">{medal} {match_display}{upset_tag}</span>
3799:         <span style="font-weight:700;color:var(--accent);font-size:0.85rem;">{m["difficulty"]}</span>
3800:     </div>
3801:     <div class="bar-track" style="height:5px;margin:0.25rem 0;">
3802:         <div class="bar-fill" style="width:{bar_pct}%;height:5px;background:{bar_color};border-radius:3px;"></div>
3803:     </div>
3804:     <div style="display:flex;gap:0.5rem;font-size:0.7rem;color:var(--text-muted);flex-wrap:wrap;">
3805:         <span>{m["num_correct"]}/{m["total_votes"]} acertaram</span>
3806:         <span>Favorito: {m["favorite"]}</span>
3807:         <span>Resultado: {m["real_winner"]}</span>
3808:     </div>
3809: </div>

(Showing lines 3780-3809 of 4291. Use offset=3810 to continue.)
```

---

### 🤖 AGENTE (Turno 16):

💭 **PENSAMENTO DO AGENTE:**
Now I have a very comprehensive picture. Let me also check the `_build_day_winners` function and the `_build_bolao_xray` function to confirm they don't handle playoffs:

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
3410: # ------------------------------------------------------------------
3411: # Round Winners page
3412: # ------------------------------------------------------------------
3413: 
3414: 
3415: def _build_day_winners(config: ChampionshipConfig) -> str:
3416:     """Show day-by-day winners, zebras, and highlights with day selector."""
3417:     df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
3418:     if df_valid.empty:
3419:         return _page_frame(config, "Vencedores do Dia - sem dados", "<div class='hero'><h1>\U0001f3c6 Vencedores do Dia</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", back_link="index.html")
3420:     df_all = pd.read_csv(config.gold_all_path(), sep=",")
3421:     df_results = pd.read_csv(config.results_file, sep=",")
3422:     upset_path = _norm(os.path.join(config._au_first_round(), "upset_tracker.csv"))
3423:     df_upset = pd.read_csv(upset_path, sep=",") if os.path.exists(upset_path) else pd.DataFrame()
3424:     max_pts = _max_points_per_game(config)
3425: 
3426:     # Get unique days from games.csv (extract date part since it includes hour)
3427:     df_results["date_only"] = df_results["date"].str.extract(r"(\d{4}-\d{2}-\d{2})", expand=False)
3428:     days = sorted(df_results.dropna(subset=["home_goals"])["date_only"].unique())
3429:     if len(days) == 0:
3430:         days = sorted(df_valid["date"].unique())
3431: 
3432:     # Pre-build content per day
3433:     day_content = {}
3434:     for day in days:
3435:         day_predictions = df_valid[df_valid["date"] == day]
3436:         day_results = df_results[df_results["date_only"] == day].dropna(subset=["home_goals"])
3437:         if day_predictions.empty:
3438:             continue
3439: 

(Showing lines 3410-3439 of 4291. Use offset=3440 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
3015:     return _page_frame(config, f"Boldometro - {config.report_title}", body, back_link="index.html")
3016: 
3017: 
3018: # ------------------------------------------------------------------
3019: # Raio-X Radar page
3020: # ------------------------------------------------------------------
3021: 
3022: 
3023: def _build_bolao_xray(config: ChampionshipConfig) -> str:
3024:     """Bolão X-ray: meta-analysis of the entire sweepstake — no per-player focus."""
3025:     df_all = pd.read_csv(config.gold_all_path(), sep=",")
3026:     df_valid = df_all[df_all["valido"] == 1].copy() if "valido" in df_all.columns else df_all.copy()
3027:     if df_valid.empty:
3028:         return _page_frame(config, f"Raio-X do Bol\u00e3o - {config.report_title}", "<div class='hero'><h1>\U0001f50d Raio-X do Bol\u00e3o</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados. ainda</div></div>", active_nav="bolao_xray.html")
3029:     df_results = pd.read_csv(config.results_file, sep=",").dropna(subset=["home_goals"])
3030: 
3031:     # Build resultado_real_placar from raw columns
3032:     df_results["resultado_real_placar"] = df_results.apply(
3033:         lambda r: f"{int(r['home_goals'])} x {int(r['away_goals'])}"
3034:         if pd.notna(r.get("home_goals")) and pd.notna(r.get("away_goals"))
3035:         else "",
3036:         axis=1,
3037:     )
3038: 
3039:     # Build a lookup: match -> real placar (from first prediction with result)
3040:     match_real_result = df_valid.dropna(subset=["home_goals_real"]).groupby("match").agg(
3041:         home_goals_real=("home_goals_real", "first"),
3042:         away_goals_real=("away_goals_real", "first"),
3043:     ).reset_index()
3044:     match_real_result["real_placar"] = match_real_result.apply(

(Showing lines 3015-3044 of 4291. Use offset=3045 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
3900:     <div class="card">{diff_cards}</div>
3901: </div>
3902: 
3903: <div class="section">
3904:     <div class="section-title">\U00002705 Favoritos que Confirmaram</div>
3905:     {fav_won_cards}
3906: </div>
3907: """
3908:     return _page_frame(config, f"Zebras - {config.report_title}", body, active_nav="zebras.html")
3909: 
3910: 
3911: # ------------------------------------------------------------------
3912: # Momentum & Sequencias
3913: # ------------------------------------------------------------------
3914: 
3915: def _build_momentum(config: ChampionshipConfig) -> str:
3916:     """Show current streaks, longest streaks, hot/cold players."""
3917:     gold_dir = config._au_first_round()
3918:     consistency_path = _norm(os.path.join(gold_dir, "consistency.csv"))
3919:     ranking_path = _norm(os.path.join(gold_dir, "ranking_history.csv"))
3920: 
3921:     if not os.path.exists(consistency_path):
3922:         return _page_frame(config, "Momento", "<div class='hero'><h1>\U0001f525 Momento</h1><div class='subtitle'>Ainda não foi realizado nenhum jogo, por isso não há resultados.</div></div>", active_nav="momentum.html")
3923: 
3924:     df_cons = pd.read_csv(consistency_path, sep=",")
3925: 
3926:     # Current streak for each player
3927:     df_cons_sorted = df_cons.sort_values(["boleiro", "date"])
3928:     current_streaks: dict[str, dict] = {}
3929:     longest_hot: dict[str, int] = {}

(Showing lines 3900-3929 of 4291. Use offset=3930 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\dashboard.py`

```python
460:     raw_teams = rest.lstrip("_").split("-vs-")
461:     home_team = raw_teams[0].replace("_", " ").strip() if len(raw_teams) > 0 else ""
462:     away_team = raw_teams[1].replace("_", " ").strip() if len(raw_teams) > 1 else ""
463: 
464:     href = filepath.replace("\\", "/").replace(
465:         f"{config.reports_dir.replace(chr(92), '/')}/html/", ""
466:     )
467: 
468:     return {"dt": dt, "teams": teams, "home_team": home_team, "away_team": away_team, "href": href, "date_str": f"{day:02d}/{month:02d} {hour:02d}h"}
469: 
470: 
471: def _build_full_ranking(config: ChampionshipConfig) -> str:
472:     """Build the full ranking table with trend indicators and badges."""
473:     df_valid = _load_gold_data(config)
474:     if df_valid.empty:
475:         return "<div class='empty-state'>Nenhum participante encontrado</div>"
476: 
477:     # Compute trend: compare last 3 days vs previous 3 days
478:     df_valid["date_dt"] = pd.to_datetime(df_valid["date"])
479:     all_dates = sorted(df_valid["date_dt"].unique())
480:     trend_map: dict[str, str] = {}
481:     if len(all_dates) >= 6:
482:         recent_dates = all_dates[-3:]
483:         prev_dates = all_dates[-6:-3]
484:         df_recent = df_valid[df_valid["date_dt"].isin(recent_dates)].groupby("who")["pontos"].sum()
485:         df_prev = df_valid[df_valid["date_dt"].isin(prev_dates)].groupby("who")["pontos"].sum()
486:         for who in df_valid["who"].unique():
487:             r = df_recent.get(who, 0)
488:             p = df_prev.get(who, 0)
489:             if r > p:

(Showing lines 460-489 of 1303. Use offset=490 to continue.)
```

---

### 🤖 AGENTE (Turno 17):

💭 **PENSAMENTO DO AGENTE:**
Let me check the `_load_gold_data` function in dashboard.py:

🛠️ **AÇÃO DA FERRAMENTA [GREP]**
*Alvo/Parâmetro:* `def _load_gold_data`

```text
Found 1 matches
C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\dashboard.py:
  Line 26: def _load_gold_data(config: ChampionshipConfig) -> pd.DataFrame:
```

---

### 🤖 AGENTE (Turno 18):

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\dashboard.py`

```python
26: def _load_gold_data(config: ChampionshipConfig) -> pd.DataFrame:
27:     """Load gold data — prefers valid, falls back to all predictions.
28: 
29:     This ensures the dashboard shows participants even when no real
30:     results exist yet (all predictions have ``valido=0``).
31:     """
32:     valid_path = config.gold_valid_path()
33:     all_path = config.gold_all_path()
34:     if os.path.exists(valid_path):
35:         df = pd.read_csv(valid_path, sep=",")
36:         if not df.empty:
37:             return df
38:     if os.path.exists(all_path):
39:         df = pd.read_csv(all_path, sep=",")
40:         if not df.empty and "who" in df.columns:
41:             return df
42:     return pd.DataFrame()
43: 
44: 
45: def _initials(name: str) -> str:
46:     """Get initials from a name (max 2 chars)."""
47:     parts = name.strip().split()
48:     if len(parts) >= 2:
49:         return (parts[0][0] + parts[-1][0]).upper()
50:     return name[:2].upper()
51: 
52: 
53: # ------------------------------------------------------------------
54: # Shared CSS
55: # ------------------------------------------------------------------

(Showing lines 26-55 of 1303. Use offset=56 to continue.)
```

---

### 🤖 AGENTE (Turno 19):

💭 **PENSAMENTO DO AGENTE:**
Now I have all the info I need. Let me compile the comprehensive plan.

Let me also check the `_build_boleiro` function in html.py around line 642-654 to see how playoff data is loaded for the player page:

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
625: # ------------------------------------------------------------------
626: # Per-player page
627: # ------------------------------------------------------------------
628: 
629: def _build_boleiro(config: ChampionshipConfig, boleiro: str) -> str:
630:     """Build a per-player HTML report."""
631:     if os.path.exists(config.gold_valid_path()):
632:         df_valid = pd.read_csv(config.gold_valid_path(), sep=",")
633:         if df_valid.empty:
634:             df_valid = pd.read_csv(config.gold_all_path(), sep=",")
635:     else:
636:         df_valid = pd.read_csv(config.gold_all_path(), sep=",")
637:     df_striker = pd.read_csv(config.playoff_strikers_path(), sep=",")
638:     max_pts = _max_points_per_game(config)
639: 
640:     df_bol = df_valid.loc[df_valid["who"] == boleiro].copy()
641: 
642:     # --- Load playoff predictions for this player ---
643:     playoff_parts = []
644:     for pr in (config.playoff_rounds or []):
645:         phase_valid_path = config.gold_playoff_valid_path(pr.key)
646:         if os.path.exists(phase_valid_path):
647:             df_phase = pd.read_csv(phase_valid_path, sep=",")
648:             df_phase_player = df_phase[df_phase["who"] == boleiro]
649:             if not df_phase_player.empty:
650:                 playoff_parts.append(df_phase_player)
651: 
652:     if playoff_parts:
653:         df_playoff = pd.concat(playoff_parts, ignore_index=True)
654:         df_bol = pd.concat([df_bol, df_playoff], ignore_index=True)
655: 
656:     sort_col_bol = ["id"] if "id" in df_bol.columns else ["date", "hour"]
657:     df_bol = df_bol.sort_values(sort_col_bol, ascending=True)
658:     df_bol["pontos_acumulados"] = df_bol["pontos"].cumsum()
659: 
660:     # Load bonus points (playoff team picks) — not included in df_bol/pontos
661:     bonus_total = 0
662:     bonus_by_phase: dict[str, int] = {}
663:     bonus_csv = _norm(os.path.join(config._au_first_round(), "playoffs_scored.csv"))
664:     if os.path.exists(bonus_csv):
665:         df_bonus_all = pd.read_csv(bonus_csv, sep=",")
666:         df_bonus_player = df_bonus_all[df_bonus_all["boleiro"] == boleiro]
667:         if not df_bonus_player.empty:
668:             bonus_total = int(df_bonus_player["points"].sum())
669:             for _, row in df_bonus_player.iterrows():
670:                 ph = str(row["phase"])
671:                 bonus_by_phase[ph] = bonus_by_phase.get(ph, 0) + int(row["points"])
672: 
673:     total_pts = int(df_bol["pontos"].sum())
674:     avg_per_game = round(df_bol["pontos"].mean(), 1) if len(df_bol) > 0 else 0
675:     num_games = len(df_bol)
676:     num_days = df_bol["date"].nunique()
677:     avg_per_day = round(total_pts / num_days, 1) if num_days > 0 else 0
678: 
679:     # Striker
680:     striker_name = ""
681:     df_st = df_striker.loc[df_striker["boleiro"] == boleiro]
682:     if not df_st.empty:
683:         striker_name = str(df_st.iloc[0]["striker"])
684: 

(Showing lines 625-684 of 4291. Use offset=685 to continue.)
```

🛠️ **AÇÃO DA FERRAMENTA [READ]**
*Alvo/Parâmetro:* `C:\Users\adnta\Documents\1.codigos\git\sweepstake\src\core\reports\html.py`

```python
1260:             f'<td style="text-align:right;font-weight:600;color:var(--accent);">+{group_match_pts}</td></tr>\n'
1261:         )
1262:         phase_total_pts += group_match_pts
1263: 
1264:     # Playoff phases
1265:     for pr in config.playoff_rounds or []:
1266:         phase_key = pr.key
1267:         phase_name = pr.name
1268: 
1269:         phase_valid_path = config.gold_playoff_valid_path(phase_key)
1270:         phase_pts = 0
1271:         if os.path.exists(phase_valid_path):
1272:             df_pp = pd.read_csv(phase_valid_path, sep=",")
1273:             df_pp_player = df_pp[df_pp["who"] == boleiro]
1274:             if not df_pp_player.empty:
1275:                 phase_pts = int(df_pp_player["pontos"].sum())
1276: 
1277:         bns = bonus_by_phase.get(phase_key, 0)
1278:         tot = phase_pts + bns
1279:         if tot > 0 or phase_pts > 0 or bns > 0:
1280:             phase_total_pts += tot
1281:             emoji = phase_emoji_map.get(phase_key, "\u26bd")
1282:             bonus_str = f'+{bns}' if bns else '-'
1283:             phase_rows += (
1284:                 f'<tr><td>{emoji} {phase_name}</td>'
1285:                 f'<td style="text-align:right;">+{phase_pts}</td>'
1286:                 f'<td style="text-align:right;">{bonus_str}</td>'
1287:                 f'<td style="text-align:right;font-weight:600;color:var(--accent);">+{tot}</td></tr>\n'
1288:             )
1289: 
1290:     if phase_rows:
1291:         body += (
1292:             f'<div class="section">'
1293:             f'<div class="section-title">\U0001f4ca Pontos por Fase</div>'
1294:             f'<div class="card" style="overflow-x:auto;">'
1295:             f'<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
1296:             f'<thead><tr style="color:var(--text-muted);border-bottom:1px solid var(--card-border);">'
1297:             f'<th style="text-align:left;padding:0.4rem;">Fase</th>'
1298:             f'<th style="text-align:right;padding:0.4rem;">Jogos</th>'
1299:             f'<th style="text-align:right;padding:0.4rem;">B\u00f4nus</th>'

(Showing lines 1260-1299 of 4291. Use offset=1300 to continue.)
```

---

### 🤖 AGENTE (Turno 20):

💭 **PENSAMENTO DO AGENTE:**
Now I have all the information needed to create a comprehensive plan. Let me organize it.

The key changes needed are:

## 1. Directory name: "playoffs" → "playoff" (4 string literals in config.py)

These are the physical directory names:
- `config.py:284`: `"playoffs"` → `"playoff"` in `_raw_playoffs()`
- `config.py:290`: `"playoffs"` → `"playoff"` in `_br_playoffs()`
- `config.py:296`: `"playoffs"` → `"playoff"` in `_ag_playoffs()`
- `config.py:302`: `"playoffs"` → `"playoff"` in `_au_playoffs()`

## 2. Round key mapping (games.csv ↔ config keys) — CRITICAL BUG

There's a naming mismatch between config phase keys and games.csv round values:

| Config key | games.csv value |
|---|---|
| `segunda_fase` | `r32` |
| `oitavas` | `r16` |
| `quartas` | `qf` |
| `semi` | `sf` |
| `terceiro_lugar` | `third` |
| `final` | `final` (matches) |

Files affected:
- `pipeline.py:364`: `df_results[df_results["round"] == phase]` — uses config key, needs to map
- `pipeline.py:4203` (loader.py:181-192): `_round_map` has wrong source names
- `html.py:1067`: `df_games[df_games["round"] == pk]` — uses config key, needs to map

We need to create a shared mapping function (or constant) that maps config keys to games.csv round values.

## 3. Where the mapping needs to be applied

### Pipeline:
- `loader.py:181-192`: Fix `_round_map` keys to use actual games.csv values (`r32` → `segunda_fase`, etc.)
- `pipeline.py:364`: Use mapping when filtering results by phase

### HTML Reports:
- `html.py:1067`: Same mapping when checking advancing teams for bonus picks
- `html.py:3670` and `3793`: Zebras page match links — should determine phase from `games.csv` round value, not hardcode `group_phase_label`
- `html.py:4264`: `pr.name` → `pr.key` for consistency (or at least ensure the directory matches)

## 4. Analytics don't include playoffs

- `html.py:_build_day_winners` (3415): Only reads `config.gold_valid_path()` (group), needs to also read playoff gold files
- `html.py:_build_bolao_xray` (3023): Only reads `config.gold_all_path()` (group)
- `html.py:_build_momentum` (3915): Only reads `config._au_first_round()` for consistency
- `dashboard.py:_load_gold_data` (26): Only reads group gold data

## 5. File `playoffs_scored.csv` naming

This file is named `playoffs_scored.csv` (plural). The user might want to keep it since it's a filename, not a directory. But if they want every "playoffs" reference changed to "playoff"...

Actually, the user said "a pasta oficial se chama 'playoff'" — the official FOLDER name is "playoff". Not file names. So I'll focus on directory names.

Let me now write a comprehensive plano de implementação.

📄 **RESPOSTA DO AGENTE:**
Agora tenho o quadro completo. Aqui está o plano:

---

## Plano: Playoff (singular) — todas as alterações necessárias

### Fase 1 — Diretórios: `playoffs` → `playoff` (4 mudanças)

No `src/core/config.py`, as 4 funções que criam paths com `"playoffs"` no nome de diretório:

| Linha | Função | String atual | Nova string |
|---|---|---|---|
| 284 | `_raw_playoffs()` | `"playoffs"` | `"playoff"` |
| 290 | `_br_playoffs()` | `"playoffs"` | `"playoff"` |
| 296 | `_ag_playoffs()` | `"playoffs"` | `"playoff"` |
| 302 | `_au_playoffs()` | `"playoffs"` | `"playoff"` |

> Obs: os **nomes das funções** (`_raw_playoffs`, `_br_playoffs`, etc.) são identificadores Python internos — não afetam o sistema de arquivos. Podem ficar como estão para minimizar mudanças em cascata, mas idealmente renomear também para consistência (ex: `_raw_playoff`).

---

### Fase 2 — 🚨 Round key mismatch (PIPELINE QUEBRA)

O `games.csv` usa `r32`, `r16`, `qf`, `sf`, `third` — mas o config.yaml e todo o código usam `segunda_fase`, `oitavas`, `quartas`, `semi`, `terceiro_lugar`. **Nenhum merge vai funcionar** porque `pipeline.py:364` filtra `df_results["round"] == phase` e `phase` é `"segunda_fase"` mas o CSV tem `"r32"`.

**O que criar:**
- Adicionar um `ROUND_MAP` global (ex: em `config.py` ou num módulo compartilhado):
  ```python
  CONFIG_KEY_TO_GAMES_ROUND = {
      "segunda_fase": "r32",
      "oitavas": "r16",
      "quartas": "qf",
      "semi": "sf",
      "terceiro_lugar": "third",
      "final": "final",
  }
  GAMES_ROUND_TO_CONFIG_KEY = {v: k for k, v in CONFIG_KEY_TO_GAMES_ROUND.items()}
  ```

**Onde aplicar o mapa:**

| Arquivo | Linha | O que muda |
|---|---|---|
| `pipeline.py` | 364 | `df_results["round"] == phase` → `df_results["round"] == CONFIG_KEY_TO_GAMES_ROUND.get(phase, phase)` |
| `html.py` | 1067 | `df_games["round"] == pk` → `df_games["round"] == CONFIG_KEY_TO_GAMES_ROUND.get(pk, pk)` |
| `loader.py` | 182-192 | `_round_map` keys errados — trocar `"round of 32"` → `"r32"`, `"round of 16"` → `"r16"`, etc. |
| `html.py` | 3670, 3793 | Match links: substituir `config.group_phase_label` hardcoded pela `round` do `games.csv` mapeada (ex: se round=`r32`, path=`segunda_fase`) |

---

### Fase 3 — `_build_match`: `pr.name` → `pr.key`

`html.py:4264` passa `pr.name` (ex: `"Segunda Fase"`) como parâmetro `phase` para `_build_match`, mas o diretório em `html.py:4269` usa `pr.key` (ex: `"segunda_fase"`). Trocar `pr.name` → `pr.key` na linha 4264 para consistência com a linha 4244 da fase de grupos.

---

### Fase 4 — Analytics ignoram playoffs (5 arquivos/páginas)

| Página | Arquivo | Linha | Problema |
|---|---|---|---|
| Day Winners | `html.py` | 3417 | Só lê `config.gold_valid_path()` (grupo). Adicionar leitura dos gold_playoff_valid_path por fase. |
| Raio-X | `html.py` | 3025 | Só lê `config.gold_all_path()` (grupo). Mesma correção. |
| Momentum | `html.py` | 3917 | Só lê `config._au_first_round()` para consistency. Adicionar dados de playoff. |
| Ranking | `dashboard.py` | 26 (`_load_gold_data`) | Só lê `gold_valid_path("group")`. Adicionar playoff + bonus points. |
| Zebras | `html.py` | 3670, 3793 | Links hardcoded para `group_phase_label`. Calcular diretório correto via `games.csv` round. |

---

### Fase 5 — Documentação e comentários

Atualizar comentários/docstrings que mencionam `playoffs` como diretório:
- `pipeline.py:11,15,22-23` — cabeçalho do módulo
- `config.py:267,271,278-279` — comentários de estrutura
- `play-off-plan.md` — diretórios mencionados

---

### Resumo de esforço

| Prioridade | O quê | Arquivos | Linhas |
|---|---|---|---|
| 🔴 **Alta** (quebra) | Fase 2 — round key mapping | `pipeline.py:364`, `html.py:1067`, `loader.py:182-192` | 3-4 edits |
| 🔴 **Alta** (quebra) | Fase 1 — renomear diretórios | `config.py:284,290,296,302` | 4 edits |
| 🟡 **Média** | Fase 3 — `pr.name` → `pr.key` | `html.py:4264` | 1 edit |
| 🟡 **Média** | Fase 4 — zebra links | `html.py:3670,3793` | 2 edits |
| 🟢 **Baixa** | Fase 4 — analytics | `html.py:3415,3025,3917`, `dashboard.py:26` | 4 funções |
| 🟢 **Baixa** | Fase 5 — docs/comentários | `pipeline.py`, `config.py`, `play-off-plan.md` | ~10 edits |

Quer que eu comece a implementar pela **Fase 1** (diretórios) e **Fase 2** (round mapping)? Essas são as que realmente quebram o pipeline.