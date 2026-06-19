from __future__ import annotations

import random
from datetime import date, datetime
from typing import Any, Callable

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

from data import (
    DONE,
    PENDING,
    SHEET_CONFIG_DECKS,
    SHEET_CONFIG_FACTIONS,
    SHEET_CONFIG_MAPS,
    SHEET_CONFIG_VAGABONDS,
    SHEET_GAMES,
    SHEET_PLAYERS,
    SHEET_POOL,
    SHEET_RESULTS,
    SHEET_STEPS,
    STATUS_CANCELLED,
    STATUS_DRAFTING,
    STATUS_FINISHED,
    STATUS_READY_TO_PLAY,
    STEP_PICK_DECK,
    STEP_PICK_FACTION,
    STEP_PICK_MAP,
    as_int,
    csv_to_list,
    list_to_csv,
    truthy,
)
from draft_logic import (
    build_custom_faction_pool,
    build_steps,
    draw_faction_pool,
    draw_turn_order,
    make_game_id,
    normalize_player_id,
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@st.cache_resource(show_spinner=False)
def get_spreadsheet() -> gspread.Spreadsheet:
    credentials = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=SCOPES,
    )
    client = gspread.authorize(credentials)
    settings = st.secrets["google_sheets"]

    spreadsheet_id = settings.get("spreadsheet_id", "")
    if spreadsheet_id:
        return client.open_by_key(spreadsheet_id)

    return client.open(settings["spreadsheet_name"])


@st.cache_resource(show_spinner=False)
def get_worksheets_by_title() -> dict[str, gspread.Worksheet]:
    spreadsheet = get_spreadsheet()
    return {worksheet.title: worksheet for worksheet in spreadsheet.worksheets()}


def get_worksheet(sheet_name: str) -> gspread.Worksheet:
    worksheets = get_worksheets_by_title()

    if sheet_name not in worksheets:
        get_worksheets_by_title.clear()
        worksheets = get_worksheets_by_title()

    if sheet_name not in worksheets:
        raise ValueError(f"Onglet Google Sheet introuvable : {sheet_name}")

    return worksheets[sheet_name]


@st.cache_data(ttl=20, show_spinner=False)
def get_header(sheet_name: str) -> list[str]:
    return get_worksheet(sheet_name).row_values(1)


@st.cache_data(ttl=10, show_spinner=False)
def read_records(sheet_name: str) -> list[dict[str, str]]:
    worksheet = get_worksheet(sheet_name)
    values = worksheet.get_all_values()
    if not values:
        return []

    headers = values[0]
    records = []

    for row in values[1:]:
        padded = row + [""] * max(0, len(headers) - len(row))
        record = {
            header: padded[index] if index < len(padded) else ""
            for index, header in enumerate(headers)
        }
        if any(str(value).strip() for value in record.values()):
            records.append(record)

    return records


def clear_cached_sheet_data() -> None:
    read_records.clear()


def read_df(sheet_name: str) -> pd.DataFrame:
    records = read_records(sheet_name)
    if records:
        return pd.DataFrame(records)
    return pd.DataFrame(columns=get_header(sheet_name))


def append_records(sheet_name: str, records: list[dict[str, Any]]) -> None:
    if not records:
        return

    worksheet = get_worksheet(sheet_name)
    headers = get_header(sheet_name)
    rows = [[record.get(header, "") for header in headers] for record in records]
    worksheet.append_rows(rows, value_input_option="USER_ENTERED")
    clear_cached_sheet_data()


def replace_records(sheet_name: str, records: list[dict[str, Any]]) -> None:
    worksheet = get_worksheet(sheet_name)
    headers = get_header(sheet_name)
    rows = [headers] + [[record.get(header, "") for header in headers] for record in records]
    worksheet.clear()
    worksheet.update(range_name="A1", values=rows, value_input_option="USER_ENTERED")
    clear_cached_sheet_data()


def find_rows(
    sheet_name: str,
    predicate: Callable[[dict[str, str]], bool],
) -> list[tuple[int, dict[str, str]]]:
    records = read_records(sheet_name)
    return [
        (index + 2, record)
        for index, record in enumerate(records)
        if predicate(record)
    ]


def update_row_fields(sheet_name: str, row_number: int, fields: dict[str, Any]) -> None:
    worksheet = get_worksheet(sheet_name)
    headers = get_header(sheet_name)

    for field, value in fields.items():
        if field not in headers:
            continue
        column_number = headers.index(field) + 1
        worksheet.update_cell(row_number, column_number, value)
    clear_cached_sheet_data()


def get_enabled_config(sheet_name: str) -> list[dict[str, str]]:
    records = read_records(sheet_name)
    return [record for record in records if truthy(record.get("enabled_default", "TRUE"))]


def create_game(
    game_name: str,
    game_date: date,
    player_names: list[str],
    selected_expansion_ids: list[str],
    selected_map_ids: list[str],
    selected_deck_ids: list[str],
    use_deck_pick: bool,
    notes: str = "",
    custom_faction_ids: list[str] | None = None,
    custom_turn_order: list[str] | None = None,
    custom_vagabond_name: str | None = None,
) -> str:
    player_names = [name.strip() for name in player_names if name.strip()]

    if not 3 <= len(player_names) <= 6:
        raise ValueError("La V1 accepte entre 3 et 6 joueurs.")

    normalized_ids = [normalize_player_id(name) for name in player_names]
    if len(set(normalized_ids)) != len(normalized_ids):
        raise ValueError("Les noms de joueurs doivent être distincts.")

    if not selected_map_ids:
        raise ValueError("Sélectionne au moins une map.")

    selected_expansion_ids = [str(value) for value in selected_expansion_ids]
    expansion_set = set(selected_expansion_ids)

    factions = [
        faction
        for faction in get_enabled_config(SHEET_CONFIG_FACTIONS)
        if faction.get("expansion_id") in expansion_set
    ]
    vagabonds = get_enabled_config(SHEET_CONFIG_VAGABONDS)

    if len(factions) < len(player_names):
        raise ValueError(
            "Il faut au moins autant de factions disponibles que de joueurs."
        )

    if not any(faction.get("faction_type") == "Militant" for faction in factions):
        raise ValueError("Il faut au moins une faction Militant disponible.")

    existing_ids = {record.get("game_id", "") for record in read_records(SHEET_GAMES)}
    game_id = make_game_id(existing_ids)

    random_seed = random.SystemRandom().randint(1, 999_999_999)
    rng = random.Random(random_seed)

    custom_faction_ids = custom_faction_ids or []

    if custom_faction_ids:
        if len(custom_faction_ids) < len(player_names):
            raise ValueError(
                "En sélection personnalisée, il faut au moins autant de factions que de joueurs."
            )

        pool = build_custom_faction_pool(
            factions=factions,
            selected_faction_ids=custom_faction_ids,
            vagabonds=vagabonds,
            rng=rng,
            custom_vagabond_name=custom_vagabond_name,
        )
    else:
        pool = draw_faction_pool(factions, vagabonds, rng)

    custom_turn_order = custom_turn_order or []

    if custom_turn_order:
        if set(custom_turn_order) != set(player_names):
            raise ValueError(
                "L'ordre du tour personnalisé doit contenir exactement les joueurs de la partie."
            )

        turn_order_by_player = {
            player_name: index
            for index, player_name in enumerate(custom_turn_order, start=1)
        }
    else:
        turn_order_by_player = draw_turn_order(player_names, rng)

    turn_order_players = [
        player_name
        for player_name, _ in sorted(
            turn_order_by_player.items(),
            key=lambda item: item[1],
        )
    ]

    # Le deck n'est plus drafté dans la V1 actuelle.
    steps = build_steps(turn_order_players, use_deck_pick=False)

    append_records(
        SHEET_GAMES,
        [
            {
                "game_id": game_id,
                "status": STATUS_DRAFTING,
                "created_at": now_str(),
                "game_date": str(game_date),
                "game_name": game_name.strip() or game_id,
                "nb_players": len(player_names),
                "use_deck_pick": "FALSE",
                "current_step": 1,
                "version": 1,
                "selected_extensions": list_to_csv(selected_expansion_ids),
                "selected_maps": list_to_csv(selected_map_ids),
                "selected_decks": "",
                "random_seed": random_seed,
                "notes": notes.strip(),
            }
        ],
    )

    append_records(
        SHEET_PLAYERS,
        [
            {
                "game_id": game_id,
                "player_order": index,
                "player_id": normalize_player_id(player_name),
                "player_name": player_name,
                "turn_order": turn_order_by_player[player_name],
            }
            for index, player_name in enumerate(player_names, start=1)
        ],
    )

    append_records(
        SHEET_POOL,
        [
            {
                "game_id": game_id,
                "pool_order": item["pool_order"],
                "faction_id": item["faction_id"],
                "faction_name": item["faction_name"],
                "faction_type": item["faction_type"],
                "vagabond_type": item["vagabond_type"],
                "picked_by": "",
                "picked_at": "",
            }
            for item in pool
        ],
    )

    append_records(
        SHEET_STEPS,
        [
            {
                "game_id": game_id,
                "step_order": step["step_order"],
                "step_type": step["step_type"],
                "expected_player": step["expected_player"],
                "status": PENDING,
                "choice_value": "",
                "done_at": "",
            }
            for step in steps
        ],
    )

    return game_id


def list_games() -> pd.DataFrame:
    games = read_df(SHEET_GAMES)
    if games.empty:
        return games
    return games.sort_values("created_at", ascending=False)


def load_game_state(game_id: str) -> dict[str, Any] | None:
    games = read_df(SHEET_GAMES)
    if games.empty or "game_id" not in games.columns:
        return None

    matching_games = games[games["game_id"] == game_id]
    if matching_games.empty:
        return None

    def filter_game(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "game_id" not in df.columns:
            return df.iloc[0:0]
        return df[df["game_id"] == game_id].copy()

    return {
        "game": matching_games.iloc[0].to_dict(),
        "players": filter_game(read_df(SHEET_PLAYERS)),
        "pool": filter_game(read_df(SHEET_POOL)),
        "steps": filter_game(read_df(SHEET_STEPS)),
        "results": filter_game(read_df(SHEET_RESULTS)),
    }


def complete_step(game_id: str, expected_player: str, choice_value: str) -> tuple[bool, str]:
    game_matches = find_rows(SHEET_GAMES, lambda record: record.get("game_id") == game_id)
    if not game_matches:
        return False, "Partie introuvable."

    game_row_number, game = game_matches[0]
    current_step = as_int(game.get("current_step"), default=1)
    version = as_int(game.get("version"), default=1)

    step_matches = find_rows(
        SHEET_STEPS,
        lambda record: record.get("game_id") == game_id
        and as_int(record.get("step_order")) == current_step,
    )
    if not step_matches:
        return False, "Étape courante introuvable."

    step_row_number, step = step_matches[0]

    if step.get("status") == DONE:
        return False, "Cette étape est déjà terminée. Recharge la page."

    if step.get("expected_player") != expected_player:
        return False, "Ce n'est pas le tour de ce joueur."

    step_type = step.get("step_type")
    choice_label = choice_value

    if step_type == STEP_PICK_MAP:
        maps = read_records(SHEET_CONFIG_MAPS)
        choice_label = next(
            (item.get("map_name", choice_value) for item in maps if item.get("map_id") == choice_value),
            choice_value,
        )

    elif step_type == STEP_PICK_DECK:
        decks = read_records(SHEET_CONFIG_DECKS)
        choice_label = next(
            (item.get("deck_name", choice_value) for item in decks if item.get("deck_id") == choice_value),
            choice_value,
        )

    elif step_type == STEP_PICK_FACTION:
        pool_matches = find_rows(
            SHEET_POOL,
            lambda record: record.get("game_id") == game_id
            and record.get("faction_id") == choice_value,
        )
        if not pool_matches:
            return False, "Faction introuvable dans le tirage."

        pool_row_number, pool_item = pool_matches[0]
        if pool_item.get("picked_by"):
            return False, "Cette faction a déjà été choisie. Recharge la page."

        vagabond_type = pool_item.get("vagabond_type", "")
        choice_label = pool_item.get("faction_name", choice_value)
        if vagabond_type:
            choice_label = f"{choice_label} ({vagabond_type})"

        update_row_fields(
            SHEET_POOL,
            pool_row_number,
            {
                "picked_by": expected_player,
                "picked_at": now_str(),
            },
        )

    update_row_fields(
        SHEET_STEPS,
        step_row_number,
        {
            "status": DONE,
            "choice_value": choice_label,
            "done_at": now_str(),
        },
    )

    all_step_orders = [
        as_int(record.get("step_order"))
        for _, record in find_rows(SHEET_STEPS, lambda record: record.get("game_id") == game_id)
    ]
    max_step = max(all_step_orders) if all_step_orders else current_step
    next_step = current_step + 1
    next_status = STATUS_READY_TO_PLAY if next_step > max_step else STATUS_DRAFTING

    update_row_fields(
        SHEET_GAMES,
        game_row_number,
        {
            "current_step": next_step,
            "status": next_status,
            "version": version + 1,
        },
    )

    return True, "Choix enregistré."


def save_game_metadata(game_id: str, game_name: str, game_date: str, notes: str) -> tuple[bool, str]:
    matches = find_rows(SHEET_GAMES, lambda record: record.get("game_id") == game_id)
    if not matches:
        return False, "Partie introuvable."

    row_number, _ = matches[0]
    update_row_fields(
        SHEET_GAMES,
        row_number,
        {
            "game_name": game_name,
            "game_date": game_date,
            "notes": notes,
        },
    )
    return True, "Partie mise à jour."


def get_selected_maps(game: dict[str, Any]) -> list[dict[str, str]]:
    selected_ids = set(csv_to_list(game.get("selected_maps", "")))
    return [record for record in read_records(SHEET_CONFIG_MAPS) if record.get("map_id") in selected_ids]


def get_selected_decks(game: dict[str, Any]) -> list[dict[str, str]]:
    selected_ids = set(csv_to_list(game.get("selected_decks", "")))
    return [record for record in read_records(SHEET_CONFIG_DECKS) if record.get("deck_id") in selected_ids]


def get_faction_choices(game_id: str) -> list[dict[str, str]]:
    state = load_game_state(game_id)
    if not state:
        return []

    pool = state["pool"]
    if pool.empty or "picked_by" not in pool.columns:
        return []

    picked = pool[pool["picked_by"].astype(str).str.strip() != ""].copy()
    choices = []

    for _, row in picked.iterrows():
        choices.append(
            {
                "game_id": game_id,
                "player_name": row.get("picked_by", ""),
                "faction_id": row.get("faction_id", ""),
                "faction_name": row.get("faction_name", ""),
                "vagabond_type": row.get("vagabond_type", ""),
            }
        )

    return choices


def replace_results_for_game(game_id: str, result_rows: list[dict[str, Any]]) -> tuple[bool, str]:
    existing_results = read_records(SHEET_RESULTS)
    kept_results = [record for record in existing_results if record.get("game_id") != game_id]
    replace_records(SHEET_RESULTS, kept_results + result_rows)

    matches = find_rows(SHEET_GAMES, lambda record: record.get("game_id") == game_id)
    if matches:
        row_number, game = matches[0]
        update_row_fields(
            SHEET_GAMES,
            row_number,
            {
                "status": STATUS_FINISHED,
                "version": as_int(game.get("version"), default=1) + 1,
            },
        )

    return True, "Résultats enregistrés."

def cancel_game(game_id: str) -> tuple[bool, str]:
    matches = find_rows(SHEET_GAMES, lambda record: record.get("game_id") == game_id)
    if not matches:
        return False, "Partie introuvable."

    row_number, game = matches[0]
    update_row_fields(
        SHEET_GAMES,
        row_number,
        {
            "status": STATUS_CANCELLED,
            "version": as_int(game.get("version"), default=1) + 1,
        },
    )

    return True, "Partie marquée comme annulée."


def delete_game(game_id: str) -> tuple[bool, str]:
    related_sheets = [
        SHEET_GAMES,
        SHEET_PLAYERS,
        SHEET_POOL,
        SHEET_STEPS,
        SHEET_RESULTS,
    ]

    found = False

    for sheet_name in related_sheets:
        records = read_records(sheet_name)
        kept_records = []

        for record in records:
            if record.get("game_id") == game_id:
                found = True
            else:
                kept_records.append(record)

        replace_records(sheet_name, kept_records)

    if not found:
        return False, "Aucune ligne trouvée pour cette partie."

    return True, "Partie supprimée définitivement."