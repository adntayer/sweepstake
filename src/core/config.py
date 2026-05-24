"""Championship configuration loader."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# ------------------------------------------------------------------
# Path normalizer — converts YAML forward-slash paths to OS-native
# ------------------------------------------------------------------

def _norm(path: str) -> str:
    """Normalize a forward-slash path to the current OS format."""
    if not path:
        return ""
    return os.path.normpath(path)


@dataclass
class ScoringRule:
    """A single scoring criterion."""

    name: str
    points: int
    priority: int = 0
    rule: str = ""
    emoji: str = ""
    color_text: str = ""
    max_total_error: int | None = None
    min_total_error: int | None = None


@dataclass
class PlayoffRound:
    """A knockout stage round."""

    name: str
    key: str  # slug used in paths/filenames
    matches: int


@dataclass
class ThemeColors:
    """Color palette for HTML reports."""

    primary: str = "#1a5e1f"
    primary_light: str = "#2d8a33"
    accent: str = "#f5c518"
    accent_dark: str = "#d4a817"
    bg: str = "#0d1117"
    card_bg: str = "#161b22"
    card_border: str = "#30363d"
    text: str = "#e6edf3"
    text_muted: str = "#8b949e"
    success: str = "#2ea043"
    warning: str = "#d29922"
    danger: str = "#f85149"
    voce: str = "#2ea043"
    bolao: str = "#f5c518"
    text_inverse: str = "#000000"
    silver: str = "#c0c0c0"
    bronze: str = "#cd7f32"
    leader: str = "#8899aa"
    accent_highlight: str = "rgba(245,197,24,0.1)"
    silver_highlight: str = "rgba(192,192,192,0.08)"
    bronze_highlight: str = "rgba(205,127,50,0.08)"
    zebra_stripe: str = "rgba(255,255,255,0.02)"
    hover_overlay: str = "rgba(255,255,255,0.03)"
    shadow_color: str = "rgba(0,0,0,0.4)"
    score_exact: str = "#00cc00"
    score_winner_goals: str = "#66ff66"
    score_winner: str = "#ffcc00"
    score_one_team: str = "#ff9900"
    score_none: str = "#ff3333"
    player_card_active: str = "rgba(245,197,24,0.05)"
    score_exact_bg: str = "rgba(0,204,0,0.1)"
    score_exact_border: str = "rgba(0,204,0,0.4)"
    score_winner_goals_bg: str = "rgba(102,255,102,0.1)"
    score_winner_goals_border: str = "rgba(102,255,102,0.4)"
    score_winner_bg: str = "rgba(255,204,0,0.1)"
    score_winner_border: str = "rgba(255,204,0,0.4)"
    score_one_team_bg: str = "rgba(255,153,0,0.1)"
    score_one_team_border: str = "rgba(255,153,0,0.4)"
    score_none_bg: str = "rgba(255,51,51,0.1)"
    score_none_border: str = "rgba(255,51,51,0.4)"


@dataclass
class ThemeConfig:
    """Theme configuration for HTML reports."""

    mode: str = "dark"
    colors: ThemeColors = field(default_factory=ThemeColors)

    def to_css_vars(self) -> str:
        """Return CSS custom properties block."""
        c = self.colors
        return (
            ":root {\n"
            f"    --primary: {c.primary};\n"
            f"    --primary-light: {c.primary_light};\n"
            f"    --accent: {c.accent};\n"
            f"    --accent-dark: {c.accent_dark};\n"
            f"    --bg: {c.bg};\n"
            f"    --card-bg: {c.card_bg};\n"
            f"    --card-border: {c.card_border};\n"
            f"    --text: {c.text};\n"
            f"    --text-muted: {c.text_muted};\n"
            f"    --success: {c.success};\n"
            f"    --warning: {c.warning};\n"
            f"    --danger: {c.danger};\n"
            f"    --voce: {c.voce};\n"
            f"    --bolao: {c.bolao};\n"
            f"    --text-inverse: {c.text_inverse};\n"
            f"    --silver: {c.silver};\n"
            f"    --bronze: {c.bronze};\n"
            f"    --leader: {c.leader};\n"
            f"    --accent-highlight: {c.accent_highlight};\n"
            f"    --silver-highlight: {c.silver_highlight};\n"
            f"    --bronze-highlight: {c.bronze_highlight};\n"
            f"    --zebra-stripe: {c.zebra_stripe};\n"
            f"    --hover-overlay: {c.hover_overlay};\n"
            f"    --shadow-color: {c.shadow_color};\n"
            f"    --score-exact: {c.score_exact};\n"
            f"    --score-winner-goals: {c.score_winner_goals};\n"
            f"    --score-winner: {c.score_winner};\n"
            f"    --score-one-team: {c.score_one_team};\n"
            f"    --score-none: {c.score_none};\n"
            f"    --score-exact-bg: {c.score_exact_bg};\n"
            f"    --score-exact-border: {c.score_exact_border};\n"
            f"    --score-winner-goals-bg: {c.score_winner_goals_bg};\n"
            f"    --score-winner-goals-border: {c.score_winner_goals_border};\n"
            f"    --score-winner-bg: {c.score_winner_bg};\n"
            f"    --score-winner-border: {c.score_winner_border};\n"
            f"    --score-one-team-bg: {c.score_one_team_bg};\n"
            f"    --score-one-team-border: {c.score_one_team_border};\n"
            f"    --score-none-bg: {c.score_none_bg};\n"
            f"    --score-none-border: {c.score_none_border};\n"
            f"    --player-card-active: {c.player_card_active};\n"
            "}\n"
        )


@dataclass
class FirstRoundLayout:
    """First round / group stage Excel slicing config."""

    matches: int
    skiprows: int = 2


@dataclass
class PlayoffsLayout:
    """Playoff rounds Excel slicing config."""

    striker_row_offset: int = 1
    name_split_char: str = "-"
    name_split_index: int = 1
    rounds: list[dict] = field(default_factory=list)
    # Each dict: {"name": "...", "key": "...", "matches": N, "tail_offset": N}


@dataclass
class ExcelLayout:
    """How to slice the Excel sheet into phases."""

    first_round: FirstRoundLayout
    playoffs: PlayoffsLayout

    # Derived: flattened playoff rows for the loader
    @property
    def playoff_rows(self) -> list[dict]:
        """Return playoff rows in loader-friendly format."""
        return [
            {
                "key": r["key"],
                "tail_offset": r.get("tail_offset", 0),
                "head_count": r["matches"],
            }
            for r in self.playoffs.rounds
        ]


@dataclass
class ChampionshipConfig:
    """Full configuration for a single championship."""

    id: str
    name: str
    year: int
    timezone: str = "America/Sao_Paulo"

    # Structure
    scoring_rules: list[ScoringRule] = field(default_factory=list)
    playoff_rounds: list[PlayoffRound] = field(default_factory=list)
    excel_layout: ExcelLayout | None = None

    # Paths (relative to project root)
    base_dir: str = ""
    raw_dir: str = ""
    results_file: str = ""
    games_file: str = ""
    bronze_dir: str = ""
    silver_dir: str = ""
    gold_dir: str = ""
    reports_dir: str = ""

    # External data
    results_endpoint: str = ""
    team_name_mapping: dict = field(default_factory=dict)

    # Report settings
    report_title: str = ""
    group_phase_label: str = "1a Fase"
    theme: ThemeConfig = field(default_factory=ThemeConfig)

    # Playoff bonus scoring (phase_key -> points_per_correct)
    playoff_scoring: dict[str, int] = field(default_factory=dict)

    # Striker scoring
    actual_top_scorer: str = ""
    striker_points: int = 0

    def __post_init__(self) -> None:
        self.base_dir = _norm(self.base_dir) if self.base_dir else _norm(os.path.join("src", "data", self.id))
        self.raw_dir = _norm(self.raw_dir) if self.raw_dir else _norm(os.path.join(self.base_dir, "raw"))
        self.results_file = _norm(self.results_file) if self.results_file else _norm(os.path.join(self.base_dir, "jogos.csv"))
        self.games_file = _norm(self.games_file) if self.games_file else self.results_file
        self.bronze_dir = _norm(self.bronze_dir) if self.bronze_dir else _norm(os.path.join(self.base_dir, "bronze"))
        self.silver_dir = _norm(self.silver_dir) if self.silver_dir else _norm(os.path.join(self.base_dir, "silver"))
        self.gold_dir = _norm(self.gold_dir) if self.gold_dir else _norm(os.path.join(self.base_dir, "gold"))
        self.reports_dir = _norm(self.reports_dir) if self.reports_dir else _norm(os.path.join("src", "reports", self.id))
        if not self.report_title:
            self.report_title = f"{self.name}"

    # ------------------------------------------------------------------
    # Path helpers — first_round / playoffs structure
    # ------------------------------------------------------------------
    # Bronze:
    #   bronze/first_round/group_phase_{boleiro}.csv
    #   bronze/first_round/bonus_teams_{boleiro}.csv
    #   bronze/first_round/striker_{boleiro}.csv
    #   bronze/playoffs/  (future separate playoff Excel files)
    #
    # Silver:
    #   silver/first_round/group_phase_{boleiro}.csv
    #   silver/playoffs/  (future)
    #
    # Gold:
    #   gold/first_round/group_phase_{boleiro}.csv
    #   gold/first_round/{label}_all.csv
    #   gold/first_round/{label}_valido_all.csv
    #   gold/first_round/striker_{boleiro}.csv
    #   gold/first_round/playoffs_strikers.csv
    #   gold/playoffs/  (future)
    # ------------------------------------------------------------------

    def _raw_playoffs(self) -> str:
        """Raw directory for per-round playoff Excel files."""
        return _norm(os.path.join(self.raw_dir, "playoffs"))

    def _br_first_round(self) -> str:
        return _norm(os.path.join(self.bronze_dir, "first_round"))

    def _br_playoffs(self) -> str:
        return _norm(os.path.join(self.bronze_dir, "playoffs"))

    def _ag_first_round(self) -> str:
        return _norm(os.path.join(self.silver_dir, "first_round"))

    def _ag_playoffs(self) -> str:
        return _norm(os.path.join(self.silver_dir, "playoffs"))

    def _au_first_round(self) -> str:
        return _norm(os.path.join(self.gold_dir, "first_round"))

    def _au_playoffs(self) -> str:
        return _norm(os.path.join(self.gold_dir, "playoffs"))

    # --- Bronze paths ---

    def bronze_group_path(self, boleiro: str) -> str:
        """Path to bronze group-phase CSV for a single boleiro."""
        return _norm(os.path.join(self._br_first_round(), f"group_phase_{boleiro}.csv"))

    def bronze_bonus_path(self, boleiro: str) -> str:
        """Path to bronze bonus playoff teams for a single boleiro."""
        return _norm(os.path.join(self._br_first_round(), f"bonus_teams_{boleiro}.csv"))

    def bronze_striker_path(self, boleiro: str) -> str:
        """Path to bronze striker CSV for a single boleiro."""
        return _norm(os.path.join(self._br_first_round(), f"striker_{boleiro}.csv"))

    def bronze_playoff_path(self, boleiro: str, phase: str) -> str:
        """Path to bronze playoff-phase CSV for a single boleiro + phase."""
        return _norm(os.path.join(self._br_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))

    # --- Silver paths ---

    def silver_group_path(self, boleiro: str) -> str:
        """Path to silver group-phase CSV for a single boleiro."""
        return _norm(os.path.join(self._ag_first_round(), f"group_phase_{boleiro}.csv"))

    def silver_playoff_path(self, boleiro: str, phase: str) -> str:
        """Path to silver playoff-phase CSV for a single boleiro + phase."""
        return _norm(os.path.join(self._ag_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))

    # --- Gold paths ---

    def gold_first_round_dir(self) -> str:
        """Directory for gold first-round files."""
        return self._au_first_round()

    def gold_playoffs_dir(self) -> str:
        """Directory for gold playoff files."""
        return self._au_playoffs()

    def gold_group_boleiro_path(self, boleiro: str) -> str:
        """Path to gold group-phase CSV for a single boleiro."""
        return _norm(os.path.join(self._au_first_round(), f"group_phase_{boleiro}.csv"))

    def gold_playoff_boleiro_path(self, boleiro: str, phase: str) -> str:
        """Path to gold playoff-phase CSV for a single boleiro + phase."""
        return _norm(os.path.join(self._au_playoffs(), f"group_phase_{phase}_{boleiro}.csv"))

    def gold_playoff_all_path(self, phase: str) -> str:
        """Path to gold aggregated 'all records' CSV for a playoff phase."""
        return _norm(os.path.join(self._au_playoffs(), f"{phase}_all.csv"))

    def gold_playoff_valid_path(self, phase: str) -> str:
        """Path to gold aggregated 'valid only' CSV for a playoff phase."""
        return _norm(os.path.join(self._au_playoffs(), f"{phase}_valido_all.csv"))

    def gold_valid_path(self, phase: str = "group") -> str:
        """Path to the gold 'valid only' aggregated CSV."""
        label = self.group_phase_label
        return _norm(os.path.join(self._au_first_round(), f"{label}_valido_all.csv"))

    def gold_all_path(self, phase: str = "group") -> str:
        """Path to the gold 'all records' aggregated CSV."""
        label = self.group_phase_label
        return _norm(os.path.join(self._au_first_round(), f"{label}_all.csv"))

    def gold_striker_path(self, boleiro: str) -> str:
        """Path to gold striker CSV for a single boleiro."""
        return _norm(os.path.join(self._au_first_round(), f"striker_{boleiro}.csv"))

    def playoff_strikers_path(self, layer: str = "gold") -> str:
        """Path to the aggregated strikers CSV."""
        if layer == "bronze":
            base = self._br_first_round()
        elif layer == "silver":
            base = self._ag_first_round()
        else:
            base = self._au_first_round()
        return _norm(os.path.join(base, "playoffs_strikers.csv"))

    def playoff_games_path(self, layer: str = "gold") -> str:
        """Path to the aggregated playoff games CSV (legacy compat, returns strikers)."""
        return self.playoff_strikers_path(layer)

    def overview_md_path(self) -> str:
        return _norm(os.path.join(self.reports_dir, "md", "overview.md"))

    def overview_html_path(self) -> str:
        return _norm(os.path.join(self.reports_dir, "html", "overview.html"))

    def index_html_path(self) -> str:
        return _norm(os.path.join(self.reports_dir, "html", "index.html"))

    def scoring_rule_names(self) -> list[str]:
        """Return scoring rule names sorted by name."""
        return [r.name for r in sorted(self.scoring_rules, key=lambda r: r.name)]

    def scoring_dict(self) -> dict[str, int]:
        """Return {name: points} for quick lookup."""
        return {r.name: r.points for r in self.scoring_rules}

    def scoring_emoji(self, rule_name: str) -> str:
        """Return emoji for a rule name, or empty string."""
        for r in self.scoring_rules:
            if r.name == rule_name:
                return r.emoji
        return ""

    def scoring_color(self, rule_name: str) -> str:
        """Return text color for a rule name, or empty string."""
        for r in self.scoring_rules:
            if r.name == rule_name:
                return r.color_text
        return ""

    def scoring_css_var(self, rule_name: str) -> dict:
        """Return CSS variable names for a scoring rule (color, bg, border)."""
        mapping = {
            "1-Placar exato": ("--score-exact", "--score-exact-bg", "--score-exact-border"),
            "2-Vencedor + gols de um time": ("--score-winner-goals", "--score-winner-goals-bg", "--score-winner-goals-border"),
            "3-Vencedor correto": ("--score-winner", "--score-winner-bg", "--score-winner-border"),
            "4-Gols de um time": ("--score-one-team", "--score-one-team-bg", "--score-one-team-border"),
            "5-Nenhum acerto": ("--score-none", "--score-none-bg", "--score-none-border"),
        }
        return mapping.get(rule_name, ("", "", ""))


# ------------------------------------------------------------------
# Loader
# ------------------------------------------------------------------

def _parse_theme(raw: dict) -> ThemeConfig:
    """Parse theme configuration from YAML."""
    if not raw:
        return ThemeConfig()
    colors_raw = raw.get("colors", {})
    colors = ThemeColors(
        primary=colors_raw.get("primary", "#1a5e1f"),
        primary_light=colors_raw.get("primary_light", "#2d8a33"),
        accent=colors_raw.get("accent", "#f5c518"),
        accent_dark=colors_raw.get("accent_dark", "#d4a817"),
        bg=colors_raw.get("bg", "#0d1117"),
        card_bg=colors_raw.get("card_bg", "#161b22"),
        card_border=colors_raw.get("card_border", "#30363d"),
        text=colors_raw.get("text", "#e6edf3"),
        text_muted=colors_raw.get("text_muted", "#8b949e"),
        success=colors_raw.get("success", "#2ea043"),
        warning=colors_raw.get("warning", "#d29922"),
        danger=colors_raw.get("danger", "#f85149"),
        voce=colors_raw.get("voce", "#2ea043"),
        bolao=colors_raw.get("bolao", "#f5c518"),
        text_inverse=colors_raw.get("text_inverse", "#000000"),
        silver=colors_raw.get("silver", "#c0c0c0"),
        bronze=colors_raw.get("bronze", "#cd7f32"),
        leader=colors_raw.get("leader", "#8899aa"),
        accent_highlight=colors_raw.get("accent_highlight", "rgba(245,197,24,0.1)"),
        silver_highlight=colors_raw.get("silver_highlight", "rgba(192,192,192,0.08)"),
        bronze_highlight=colors_raw.get("bronze_highlight", "rgba(205,127,50,0.08)"),
        zebra_stripe=colors_raw.get("zebra_stripe", "rgba(255,255,255,0.02)"),
        hover_overlay=colors_raw.get("hover_overlay", "rgba(255,255,255,0.03)"),
        shadow_color=colors_raw.get("shadow_color", "rgba(0,0,0,0.4)"),
        score_exact=colors_raw.get("score_exact", "#00cc00"),
        score_winner_goals=colors_raw.get("score_winner_goals", "#66ff66"),
        score_winner=colors_raw.get("score_winner", "#ffcc00"),
        score_one_team=colors_raw.get("score_one_team", "#ff9900"),
        score_none=colors_raw.get("score_none", "#ff3333"),
        player_card_active=colors_raw.get("player_card_active", "rgba(245,197,24,0.05)"),
        score_exact_bg=colors_raw.get("score_exact_bg", "rgba(0,204,0,0.1)"),
        score_exact_border=colors_raw.get("score_exact_border", "rgba(0,204,0,0.4)"),
        score_winner_goals_bg=colors_raw.get("score_winner_goals_bg", "rgba(102,255,102,0.1)"),
        score_winner_goals_border=colors_raw.get("score_winner_goals_border", "rgba(102,255,102,0.4)"),
        score_winner_bg=colors_raw.get("score_winner_bg", "rgba(255,204,0,0.1)"),
        score_winner_border=colors_raw.get("score_winner_border", "rgba(255,204,0,0.4)"),
        score_one_team_bg=colors_raw.get("score_one_team_bg", "rgba(255,153,0,0.1)"),
        score_one_team_border=colors_raw.get("score_one_team_border", "rgba(255,153,0,0.4)"),
        score_none_bg=colors_raw.get("score_none_bg", "rgba(255,51,51,0.1)"),
        score_none_border=colors_raw.get("score_none_border", "rgba(255,51,51,0.4)"),
    )
    return ThemeConfig(mode=raw.get("mode", "dark"), colors=colors)


def _parse_team_mapping(raw: list) -> dict[str, str]:
    """Parse team_name_mapping from YAML into {english: portuguese} dict."""
    mapping: dict[str, str] = {}
    for entry in raw:
        en = entry.get("en", "").strip()
        pt = entry.get("pt", "").strip()
        if en and pt:
            mapping[en] = pt
    return mapping


def _find_championship_dir(championship_id: str) -> Path:
    """Locate the championship directory under src/championships/."""
    base = Path("src") / "championships" / championship_id
    if base.is_dir():
        return base
    raise FileNotFoundError(
        f"Championship '{championship_id}' not found at {base}"
    )


def load_config(championship_id: str) -> ChampionshipConfig:
    """Load a ChampionshipConfig from its YAML file."""
    champ_dir = _find_championship_dir(championship_id)
    yaml_path = champ_dir / "config.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"Config not found: {yaml_path}")

    with open(yaml_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    # Scoring rules
    scoring_rules = [
        ScoringRule(
            name=r["name"],
            points=r["points"],
            priority=r.get("priority", i),
            rule=r.get("rule", ""),
            emoji=r.get("emoji", ""),
            color_text=r.get("color_text", ""),
            max_total_error=r.get("max_total_error"),
            min_total_error=r.get("min_total_error"),
        )
        for i, r in enumerate(raw.get("scoring", []))
    ]

    # Excel layout
    el_cfg = raw.get("excel_layout", {})
    fr_cfg = el_cfg.get("first_round", {})
    po_cfg = el_cfg.get("playoffs", {})

    first_round = FirstRoundLayout(
        matches=fr_cfg.get("matches", 48),
        skiprows=fr_cfg.get("skiprows", 2),
    )

    playoffs = PlayoffsLayout(
        striker_row_offset=po_cfg.get("striker_row_offset", 1),
        name_split_char=po_cfg.get("name_split_char", "-"),
        name_split_index=po_cfg.get("name_split_index", 1),
        rounds=po_cfg.get("rounds", []),
    )

    excel_layout = ExcelLayout(
        first_round=first_round,
        playoffs=playoffs,
    )

    # Derive playoff_rounds list from excel_layout.playoffs.rounds
    playoff_rounds = [
        PlayoffRound(
            name=r["name"],
            key=r["key"],
            matches=r["matches"],
        )
        for r in po_cfg.get("rounds", [])
    ]

    # Parse playoff scoring
    playoff_scoring = {}
    for phase_key, points in raw.get("playoff_scoring", {}).items():
        playoff_scoring[phase_key] = points

    # Parse striker scoring
    striker_cfg = raw.get("striker_scoring", {})
    striker_points = striker_cfg.get("points", 0)

    return ChampionshipConfig(
        id=raw["id"],
        name=raw["name"],
        year=raw["year"],
        timezone=raw.get("timezone", "America/Sao_Paulo"),
        scoring_rules=scoring_rules,
        playoff_rounds=playoff_rounds,
        excel_layout=excel_layout,
        report_title=raw.get("report_title", raw["name"]),
        group_phase_label=raw.get("group_phase_label", "1a Fase"),
        theme=_parse_theme(raw.get("theme", {})),
        base_dir=_norm(raw.get("base_dir", "")),
        raw_dir=_norm(raw.get("raw_dir", "")),
        results_file=_norm(raw.get("results_file", "")),
        games_file=_norm(raw.get("games_file", "")),
        bronze_dir=_norm(raw.get("bronze_dir", "")),
        silver_dir=_norm(raw.get("silver_dir", "")),
        gold_dir=_norm(raw.get("gold_dir", "")),
        reports_dir=_norm(raw.get("reports_dir", "")),
        results_endpoint=raw.get("results_endpoint", ""),
        team_name_mapping=_parse_team_mapping(raw.get("team_name_mapping", [])),
        playoff_scoring=playoff_scoring,
        actual_top_scorer=raw.get("actual_top_scorer", ""),
        striker_points=striker_points,
    )


def list_championships() -> list[str]:
    """Return all available championship IDs."""
    base = Path("src") / "championships"
    if not base.is_dir():
        return []
    return sorted(
        d.name for d in base.iterdir()
        if d.is_dir() and (d / "config.yaml").exists()
    )
