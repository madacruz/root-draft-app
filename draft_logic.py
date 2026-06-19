from __future__ import annotations

import random
import re
import string
import unicodedata
from typing import Any

from data import STEP_PICK_DECK, STEP_PICK_FACTION, STEP_PICK_MAP


def normalize_player_id(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_name.lower()).strip("_")
    return cleaned or "player"


def make_game_id(existing_ids: set[str] | None = None) -> str:
    existing_ids = existing_ids or set()
    alphabet = string.ascii_uppercase + string.digits

    while True:
        suffix = "".join(random.SystemRandom().choice(alphabet) for _ in range(5))
        game_id = f"ROOT-{suffix}"
        if game_id not in existing_ids:
            return game_id


def draw_faction_pool(
    factions: list[dict[str, Any]],
    vagabonds: list[dict[str, Any]],
    rng: random.Random,
) -> list[dict[str, Any]]:
    militants = [f for f in factions if f.get("faction_type") == "Militant"]

    if not militants:
        raise ValueError("Il faut au moins une faction Militant disponible.")

    if len(factions) < 5:
        raise ValueError("Il faut au moins 5 factions disponibles.")

    first = rng.choice(militants)
    remaining = [f for f in factions if f.get("faction_id") != first.get("faction_id")]
    others = rng.sample(remaining, k=4)
    drawn = [first, *others]

    vagabond_type = ""
    if any(f.get("faction_id") == "vagabond" for f in drawn):
        enabled_vagabonds = [v for v in vagabonds if v.get("vagabond_name")]
        if not enabled_vagabonds:
            raise ValueError("Le Vagabond est disponible mais aucun type de Vagabond n'est configuré.")
        vagabond_type = rng.choice(enabled_vagabonds).get("vagabond_name", "")

    pool = []
    for index, faction in enumerate(drawn, start=1):
        pool.append(
            {
                "pool_order": index,
                "faction_id": faction.get("faction_id", ""),
                "faction_name": faction.get("faction_name", ""),
                "faction_type": faction.get("faction_type", ""),
                "vagabond_type": vagabond_type if faction.get("faction_id") == "vagabond" else "",
            }
        )

    return pool

def build_custom_faction_pool(
    factions: list[dict[str, Any]],
    selected_faction_ids: list[str],
    vagabonds: list[dict[str, Any]],
    rng: random.Random,
    custom_vagabond_name: str | None = None,
) -> list[dict[str, Any]]:
    faction_by_id = {
        faction.get("faction_id", ""): faction
        for faction in factions
    }

    missing_factions = [
        faction_id
        for faction_id in selected_faction_ids
        if faction_id not in faction_by_id
    ]

    if missing_factions:
        raise ValueError(
            "Certaines factions sélectionnées sont indisponibles : "
            + ", ".join(missing_factions)
        )

    selected_factions = [
        faction_by_id[faction_id]
        for faction_id in selected_faction_ids
    ]

    vagabond_type = ""
    has_vagabond = any(
        faction.get("faction_id") == "vagabond"
        for faction in selected_factions
    )

    if has_vagabond:
        enabled_vagabonds = [
            vagabond
            for vagabond in vagabonds
            if vagabond.get("vagabond_name")
        ]

        if not enabled_vagabonds:
            raise ValueError(
                "Le Vagabond est sélectionné mais aucun type de Vagabond n'est configuré."
            )

        available_vagabond_names = {
            vagabond.get("vagabond_name", "")
            for vagabond in enabled_vagabonds
        }

        if custom_vagabond_name:
            if custom_vagabond_name not in available_vagabond_names:
                raise ValueError(
                    f"Type de Vagabond indisponible : {custom_vagabond_name}"
                )
            vagabond_type = custom_vagabond_name
        else:
            vagabond_type = rng.choice(enabled_vagabonds).get("vagabond_name", "")

    pool = []
    for index, faction in enumerate(selected_factions, start=1):
        pool.append(
            {
                "pool_order": index,
                "faction_id": faction.get("faction_id", ""),
                "faction_name": faction.get("faction_name", ""),
                "faction_type": faction.get("faction_type", ""),
                "vagabond_type": (
                    vagabond_type
                    if faction.get("faction_id") == "vagabond"
                    else ""
                ),
            }
        )

    return pool


def draw_turn_order(player_names: list[str], rng: random.Random) -> dict[str, int]:
    shuffled = player_names.copy()
    rng.shuffle(shuffled)
    return {player_name: index for index, player_name in enumerate(shuffled, start=1)}


def build_steps(turn_order_players: list[str], use_deck_pick: bool) -> list[dict[str, Any]]:
    if not turn_order_players:
        raise ValueError("Aucun joueur fourni.")

    steps = []
    step_order = 1

    steps.append(
        {
            "step_order": step_order,
            "step_type": STEP_PICK_MAP,
            "expected_player": turn_order_players[0],
        }
    )
    step_order += 1

    if use_deck_pick:
        if len(turn_order_players) < 2:
            raise ValueError("Il faut au moins 2 joueurs pour activer le choix du deck.")
        steps.append(
            {
                "step_order": step_order,
                "step_type": STEP_PICK_DECK,
                "expected_player": turn_order_players[1],
            }
        )
        step_order += 1

    for player_name in reversed(turn_order_players):
        steps.append(
            {
                "step_order": step_order,
                "step_type": STEP_PICK_FACTION,
                "expected_player": player_name,
            }
        )
        step_order += 1

    return steps