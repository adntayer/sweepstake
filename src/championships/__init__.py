"""Championship registry.

Each subdirectory contains a config.yaml that defines:
  - Championship metadata (name, year, timezone)
  - Scoring rules
  - Playoff structure
  - Excel parsing layout

To add a new championship, create a new directory with a config.yaml.
"""

from src.core.config import list_championships, load_config, ChampionshipConfig

__all__ = ["list_championships", "load_config", "ChampionshipConfig"]
