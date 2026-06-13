"""Championship-agnostic sweepstake engine.

Architecture:
  core/         - Generic pipeline, scoring, reports
  championships/ - Per-championship YAML configs
  services/     - Shared utilities (printing, writing)
  data/         - Bronze/silver/gold data layers
"""
