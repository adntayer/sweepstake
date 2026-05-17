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
    rule: str = ""  # e.g. "exact_score", "correct_winner_and_goals"
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
    bronze_dir: str = ""
    silver_dir: str = ""
    gold_dir: str = ""
    reports_dir: str = ""

    # Report settings
    report_title: str = ""
    group_phase_label: str = "1a Fase"
    theme: ThemeConfig = field(default_factory=ThemeConfig)

    def __post_init__(self) -> None:
        self.base_dir = _norm(self.base_dir) if self.base_dir else _norm(os.path.join("src", "data", self.id))
        self.raw_dir = _norm(self.raw_dir) if self.raw_dir else _norm(os.path.join(self.base_dir, "raw"))
        self.results_file = _norm(self.results_file) if self.results_file else _norm(os.path.join(self.base_dir, "jogos.csv"))
        self.bronze_dir = _norm(self.bronze_dir) if self.bronze_dir else _norm(os.path.join(self.base_dir, "bronze"))
        self.silver_dir = _norm(self.silver_dir) if self.silver_dir else _norm(os.path.join(self.base_dir, "silver"))
        self.gold_dir = _norm(self.gold_dir) if self.gold_dir else _norm(os.path.join(self.base_dir, "gold"))
        self.reports_dir = _norm(self.reports_dir) if self.reports_dir else _norm(os.path.join("src", "reports", self.id))
        if not self.report_title:
            self.report_title = f"{self.name}"

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def gold_valid_path(self, phase: str = "group") -> str:
        """Path to the gold 'valid only' CSV for a phase."""
        key = self.group_phase_label if phase == "group" else phase
        return _norm(os.path.join(self.gold_dir, key, f"{key}_valido_all.csv"))

    def gold_all_path(self, phase: str = "group") -> str:
        """Path to the gold 'all records' CSV for a phase."""
        key = self.group_phase_label if phase == "group" else phase
        return _norm(os.path.join(self.gold_dir, key, f"{key}_all.csv"))

    def silver_all_path(self, phase: str = "group") -> str:
        """Path to the silver merged CSV for a phase."""
        key = self.group_phase_label if phase == "group" else phase
        return _norm(os.path.join(self.silver_dir, key, "all_games.csv"))

    def playoff_strikers_path(self, layer: str = "gold") -> str:
        """Path to the strikers CSV."""
        if layer == "bronze":
            base = self.bronze_dir
        elif layer == "silver":
            base = self.silver_dir
        else:
            base = self.gold_dir
        return _norm(os.path.join(base, "playoffs", "full", "playoffs_strikers.csv"))

    def playoff_games_path(self, layer: str = "gold") -> str:
        """Path to the playoff games CSV."""
        if layer == "bronze":
            base = self.bronze_dir
        elif layer == "silver":
            base = self.silver_dir
        else:
            base = self.gold_dir
        return _norm(os.path.join(base, "playoffs", "full", "playoffs_full_games.csv"))

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
    )
    return ThemeConfig(mode=raw.get("mode", "dark"), colors=colors)


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
        bronze_dir=_norm(raw.get("bronze_dir", "")),
        silver_dir=_norm(raw.get("silver_dir", "")),
        gold_dir=_norm(raw.get("gold_dir", "")),
        reports_dir=_norm(raw.get("reports_dir", "")),
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
