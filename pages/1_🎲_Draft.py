from __future__ import annotations

import streamlit as st

import storage_gsheet as storage
from data import (
    STATUS_DRAFTING,
    STEP_PICK_FACTION,
    STEP_PICK_MAP,
    as_int,
)

st.set_page_config(page_title="Draft Root", page_icon="🎲", layout="wide")
st.title("🎲 Draft")


def get_query_game_id() -> str:
    query_game_id = st.query_params.get("game_id", "")
    if isinstance(query_game_id, list):
        return query_game_id[0] if query_game_id else ""
    return str(query_game_id)


def get_done_choice(steps, step_type: str) -> str:
    if steps.empty:
        return ""

    done_steps = steps[
        (steps["step_type"] == step_type)
        & (steps["status"].astype(str).str.lower() == "done")
    ]

    if done_steps.empty:
        return ""

    done_steps = done_steps.copy()
    done_steps["step_order_int"] = done_steps["step_order"].apply(as_int)

    return str(
        done_steps.sort_values("step_order_int")
        .iloc[-1]
        .get("choice_value", "")
    )


def sort_by_int(df, column: str):
    if df.empty or column not in df.columns:
        return df

    sorted_df = df.copy()
    sorted_df[f"{column}_int"] = sorted_df[column].apply(as_int)
    return sorted_df.sort_values(f"{column}_int")


def build_game_labels(games):
    labels = {}

    for _, row in games.iterrows():
        game_id = row.get("game_id", "")
        game_name = row.get("game_name", game_id)
        game_date = row.get("game_date", "")
        status = row.get("status", "")

        labels[game_id] = f"{game_date} — {game_name} — {game_id} — {status}"

    return labels


query_game_id = get_query_game_id()

if "loaded_game_id" not in st.session_state:
    st.session_state["loaded_game_id"] = query_game_id

games = storage.list_games()
game_labels = build_game_labels(games) if not games.empty else {}

with st.form("load_game_form"):
    st.markdown("### Charger une partie")

    selected_game_id = ""

    if game_labels:
        game_ids = list(game_labels.keys())

        default_index = 0
        if st.session_state["loaded_game_id"] in game_ids:
            default_index = game_ids.index(st.session_state["loaded_game_id"])

        selected_label = st.selectbox(
            "Partie existante",
            options=[game_labels[game_id] for game_id in game_ids],
            index=default_index,
        )

        selected_game_id = next(
            game_id
            for game_id, label in game_labels.items()
            if label == selected_label
        )

    manual_game_id = st.text_input(
        "Ou saisir un game_id manuellement",
        value=st.session_state["loaded_game_id"],
        placeholder="Exemple : ROOT-ABCDE",
    ).strip()

    load_submitted = st.form_submit_button("Charger la partie")

if load_submitted:
    game_id_to_load = manual_game_id or selected_game_id
    st.session_state["loaded_game_id"] = game_id_to_load

    if game_id_to_load:
        st.query_params["game_id"] = game_id_to_load

    storage.clear_cached_sheet_data()
    st.rerun()

game_id = st.session_state["loaded_game_id"]

if not game_id:
    st.info("Sélectionne une partie puis clique sur `Charger la partie`.")
    st.stop()

state = storage.load_game_state(game_id)

if not state:
    st.error("Partie introuvable.")
    st.stop()

game = state["game"]
players = state["players"].copy()
pool = state["pool"].copy()
steps = state["steps"].copy()

st.subheader(game.get("game_name", game_id))
st.write(
    f"Statut : `{game.get('status', '')}` | "
    f"Date : `{game.get('game_date', '')}` | "
    f"Étape : `{game.get('current_step', '')}`"
)

chosen_map = get_done_choice(steps, STEP_PICK_MAP)

if chosen_map:
    st.markdown("### Choix déjà validés")
    st.success(f"Map choisie : **{chosen_map}**")

if st.button("Rafraîchir l'état"):
    storage.clear_cached_sheet_data()
    st.rerun()

left, right = st.columns(2)

with left:
    st.markdown("### Ordre du tour")

    if players.empty:
        st.write("Aucun joueur trouvé.")
    else:
        display_players = sort_by_int(players, "turn_order")
        display_players = display_players[["turn_order", "player_name"]]
        st.dataframe(display_players, use_container_width=True, hide_index=True)

with right:
    st.markdown("### Factions tirées")

    if not chosen_map:
        st.info("Les factions seront révélées après le choix de la map.")
    elif pool.empty:
        st.write("Aucune faction trouvée.")
    else:
        display_pool = pool.copy()
        display_pool["display_name"] = display_pool.apply(
            lambda row: f"{row['faction_name']} ({row['vagabond_type']})"
            if str(row.get("vagabond_type", "")).strip()
            else row["faction_name"],
            axis=1,
        )

        display_pool = sort_by_int(display_pool, "pool_order")
        columns = ["pool_order", "display_name", "faction_type", "picked_by"]

        st.dataframe(display_pool[columns], use_container_width=True, hide_index=True)

st.divider()

if game.get("status") != STATUS_DRAFTING:
    st.success("La draft est terminée.")

    st.markdown(
        """
La partie est prête : vous pouvez maintenant jouer.

Bonne partie les p'tits potes !

Une fois la partie terminée, vous pourrez revenir dans la page **📜 Parties**
pour saisir les scores, indiquer le vainqueur et mettre à jour les statistiques.
"""
    )

    st.markdown("### Étapes")
    if not steps.empty:
        display_steps = sort_by_int(steps, "step_order")
        st.dataframe(display_steps, use_container_width=True, hide_index=True)

    st.stop()

current_step = as_int(game.get("current_step"), default=1)

if steps.empty:
    st.error("Aucune étape trouvée pour cette partie.")
    st.stop()

matching_steps = steps[steps["step_order"].apply(as_int) == current_step]

if matching_steps.empty:
    st.error("Étape courante introuvable.")
    st.stop()

step = matching_steps.iloc[0].to_dict()
expected_player = step.get("expected_player", "")
step_type = step.get("step_type", "")

st.markdown(f"## C'est le tour de {expected_player}")

labels = {
    STEP_PICK_MAP: "Choisir la map",
    STEP_PICK_FACTION: "Choisir une faction",
}

st.write(f"Action attendue : **{labels.get(step_type, step_type)}**")

confirmed = st.checkbox(f"Oui, je suis bien {expected_player}")

choice_value = None

if step_type == STEP_PICK_MAP:
    maps = storage.get_selected_maps(game)
    options = {item["map_name"]: item["map_id"] for item in maps}

    if not options:
        st.error("Aucune map disponible pour cette partie.")
        st.stop()

    choice_label = st.radio(
        "Map",
        options=list(options.keys()),
        disabled=not confirmed,
    )
    choice_value = options.get(choice_label)

elif step_type == STEP_PICK_FACTION:
    if "picked_by" not in pool.columns:
        st.error("La colonne `picked_by` est absente de l'onglet `pool`.")
        st.stop()

    available_pool = pool[pool["picked_by"].astype(str).str.strip() == ""].copy()

    if available_pool.empty:
        st.error("Aucune faction disponible.")
        st.stop()

    available_pool["display_name"] = available_pool.apply(
        lambda row: f"{row['faction_name']} ({row['vagabond_type']})"
        if str(row.get("vagabond_type", "")).strip()
        else row["faction_name"],
        axis=1,
    )

    available_pool = sort_by_int(available_pool, "pool_order")
    options = dict(zip(available_pool["display_name"], available_pool["faction_id"]))

    choice_label = st.radio(
        "Faction",
        options=list(options.keys()),
        disabled=not confirmed,
    )
    choice_value = options.get(choice_label)

else:
    st.error(f"Type d'étape non géré : {step_type}")
    st.stop()

if st.button(
    "Valider mon choix",
    type="primary",
    disabled=not confirmed or not choice_value,
):
    ok, message = storage.complete_step(
        game_id=game_id,
        expected_player=expected_player,
        choice_value=choice_value,
    )

    if ok:
        st.success(message)
        storage.clear_cached_sheet_data()
        st.rerun()
    else:
        st.error(message)

st.divider()
st.markdown("### Étapes de draft")

if not steps.empty:
    display_steps = sort_by_int(steps, "step_order")
    st.dataframe(display_steps, use_container_width=True, hide_index=True)