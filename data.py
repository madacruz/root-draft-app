from __future__ import annotations

SHEET_CONFIG_EXPANSIONS = "config_expansions"
SHEET_CONFIG_FACTIONS = "config_factions"
SHEET_CONFIG_VAGABONDS = "config_vagabonds"
SHEET_CONFIG_MAPS = "config_maps"
SHEET_CONFIG_DECKS = "config_decks"
SHEET_CONFIG_PLAYERS = "config_players"
SHEET_GAMES = "games"
SHEET_PLAYERS = "players"
SHEET_POOL = "pool"
SHEET_STEPS = "steps"
SHEET_RESULTS = "results"

STATUS_DRAFTING = "drafting"
STATUS_READY_TO_PLAY = "ready_to_play"
STATUS_FINISHED = "finished"
STATUS_CANCELLED = "cancelled"

STEP_PICK_MAP = "pick_map"
STEP_PICK_DECK = "pick_deck"
STEP_PICK_FACTION = "pick_faction"

DONE = "done"
PENDING = "pending"


def truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "vrai", "yes", "y", "1", "x"}


def list_to_csv(values: list[str]) -> str:
    return ",".join(str(value).strip() for value in values if str(value).strip())


def csv_to_list(value: object) -> list[str]:
    if value is None:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def as_int(value: object, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).strip()))
    except ValueError:
        return default