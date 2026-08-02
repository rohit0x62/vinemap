"""Vinemap Teams client — shared graph server integration."""

from vinemap.teams.client import TeamsClient
from vinemap.teams.config import get_client, load_teams_config, save_teams_config

__all__ = [
    "TeamsClient",
    "get_client",
    "load_teams_config",
    "save_teams_config",
]
