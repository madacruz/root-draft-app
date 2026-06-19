from __future__ import annotations

from datetime import date

import streamlit as st

import storage_gsheet as storage
from data import (
    SHEET_CONFIG_EXPANSIONS,
    SHEET_CONFIG_FACTIONS,
    SHEET_CONFIG_MAPS,
    SHEET_CONFIG_VAGABONDS,
    truthy,
)

st.set_page_config(
    page_title="Accueil & Setup",
    page_icon="🏠",
    layout="wide",
)

st.title("🏠 Accueil & Setup")
st.caption("Préparation, draft et suivi des parties de Root.")

st.markdown(
    """
Bienvenue dans **Root Draft App**.

Cette application permet de préparer rapidement une partie de **Root** entre amis, 
avec un tirage partagé et stable entre tous les joueurs.

Fonctionnalités principales :

- créer une partie avec les joueurs, extensions et maps disponibles ;
- tirer au sort l’ordre du tour ;
- faire choisir la map par le premier joueur ;
- tirer automatiquement les factions disponibles pour la draft ;
- garantir que la première faction tirée est une faction **Militant** ;
- permettre une partie personnalisée avec sélection manuelle des factions ;
- permettre un ordre du tour personnalisé ;
- faire drafter les factions en ordre inverse de l’ordre du tour ;
- conserver l’état de la partie pour que chaque joueur voie les choix déjà faits ;
- enregistrer les résultats après la partie ;
- consulter les statistiques par joueur et par faction.
Les factions restent masquées jusqu’au choix de la map, afin que le premier joueur choisisse la map sans connaître le pool de draft.
"""
)

st.info(
    "Commence par configurer la partie ci-dessous. Une fois la partie créée, "
    "va dans la page `🎲 Draft` pour lancer la sélection des maps et factions."
)

expansions_df = storage.read_df(SHEET_CONFIG_EXPANSIONS)
maps_df = storage.read_df(SHEET_CONFIG_MAPS)
factions_df = storage.read_df(SHEET_CONFIG_FACTIONS)
vagabonds_df = storage.read_df(SHEET_CONFIG_VAGABONDS)
players_df = storage.read_df("config_players")

if expansions_df.empty:
    st.error("L'onglet `config_expansions` est vide ou inaccessible.")
    st.stop()

if maps_df.empty:
    st.error("L'onglet `config_maps` est vide ou inaccessible.")
    st.stop()

if factions_df.empty:
    st.error("L'onglet `config_factions` est vide ou inaccessible.")
    st.stop()
    
if vagabonds_df.empty:
    st.error("L'onglet `config_vagabonds` est vide ou inaccessible.")
    st.stop()

expansions_df["enabled_default_bool"] = expansions_df["enabled_default"].apply(truthy)
expansion_name_to_id = dict(
    zip(expansions_df["expansion_name"], expansions_df["expansion_id"])
)

default_expansion_names = expansions_df.loc[
    expansions_df["enabled_default_bool"],
    "expansion_name",
].tolist()

st.subheader("1. Setup")

selected_expansion_names = st.multiselect(
    "Extensions disponibles",
    options=expansions_df["expansion_name"].tolist(),
    default=default_expansion_names,
)

selected_expansion_ids = [
    expansion_name_to_id[name]
    for name in selected_expansion_names
]

available_maps = maps_df[maps_df["expansion_id"].isin(selected_expansion_ids)].copy()
map_name_to_id = dict(zip(available_maps["map_name"], available_maps["map_id"]))

selected_map_names = st.multiselect(
    "Maps disponibles",
    options=available_maps["map_name"].tolist(),
    default=available_maps["map_name"].tolist(),
)

available_factions = factions_df[
    factions_df["expansion_id"].isin(selected_expansion_ids)
].copy()

faction_name_to_id = dict(
    zip(available_factions["faction_name"], available_factions["faction_id"])
)

use_custom_factions = st.checkbox(
    "Remplacer le tirage au sort par une sélection de factions",
    value=False,
)

selected_custom_faction_names = []

if use_custom_factions:
    selected_custom_faction_names = st.multiselect(
        "Factions disponibles pour la draft",
        options=available_factions["faction_name"].tolist(),
        default=[],
        help=(
            "Sélectionne les factions qui apparaîtront dans la draft. "
            "Il faut au moins autant de factions que de joueurs."
        ),
    )
    
custom_vagabond_name = None

vagabond_selected = (
    use_custom_factions
    and "Vagabond" in selected_custom_faction_names
)

if vagabond_selected:
    enabled_vagabonds = vagabonds_df[
        vagabonds_df["enabled_default"].apply(truthy)
    ].copy()

    vagabond_names = (
        enabled_vagabonds["vagabond_name"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    vagabond_choice = st.selectbox(
        "Type de Vagabond",
        options=["Tirer au sort", *vagabond_names],
        index=0,
        help=(
            "Si tu choisis `Tirer au sort`, le type de Vagabond sera tiré au moment "
            "de créer la partie. Sinon, le Vagabond sélectionné sera fixé."
        ),
    )

    if vagabond_choice != "Tirer au sort":
        custom_vagabond_name = vagabond_choice

st.subheader("2. Joueurs")

known_players = []

# Joueurs configurés manuellement dans config_players
if not players_df.empty and "player_name" in players_df.columns:
    if "active" in players_df.columns:
        active_players = players_df[players_df["active"].apply(truthy)].copy()
    else:
        active_players = players_df.copy()

    known_players.extend(
        active_players["player_name"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

# Joueurs déjà présents dans les anciennes parties
historical_players_df = storage.read_df("players")
if not historical_players_df.empty and "player_name" in historical_players_df.columns:
    known_players.extend(
        historical_players_df["player_name"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

known_players = list(dict.fromkeys(name for name in known_players if name))

default_player_names = ["Erwan", "Lou", "Fënril", "Thomas"]

default_known_players = [
    player
    for player in default_player_names
    if player in known_players
]

selected_known_players = st.multiselect(
    "Joueurs connus",
    options=known_players,
    default=default_known_players,
)

missing_default_players = [
    player
    for player in default_player_names
    if player not in selected_known_players
]

extra_players_text = st.text_area(
    "Autres joueurs, un par ligne",
    value="\n".join(missing_default_players),
)

extra_players = [
    line.strip()
    for line in extra_players_text.splitlines()
    if line.strip()
]

player_names = []
for name in [*selected_known_players, *extra_players]:
    if name not in player_names:
        player_names.append(name)

st.write(f"Joueurs retenus : **{len(player_names)}**")
st.caption("La V1 accepte entre 3 et 6 joueurs.")
st.write(player_names)

use_custom_turn_order = st.checkbox(
    "Choisir l'ordre du tour",
    value=False,
)

custom_turn_order = []

if use_custom_turn_order:
    st.caption("Sélectionne chaque joueur une seule fois.")

    for index in range(len(player_names)):
        selected_player = st.selectbox(
            f"Rang {index + 1}",
            options=player_names,
            index=index if index < len(player_names) else 0,
            key=f"custom_turn_order_{index}",
        )
        custom_turn_order.append(selected_player)

    if len(set(custom_turn_order)) != len(custom_turn_order):
        st.warning("Chaque joueur doit apparaître une seule fois dans l'ordre du tour.")

st.subheader("3. Infos partie")

game_name = st.text_input("Nom de la partie", value="Soirée Root")
game_date = st.date_input("Date prévue / réelle de la partie", value=date.today())
notes = st.text_area("Notes", value="")

selected_map_ids = [
    map_name_to_id[name]
    for name in selected_map_names
]

selected_custom_faction_ids = [
    faction_name_to_id[name]
    for name in selected_custom_faction_names
]

invalid_player_count = not 3 <= len(player_names) <= 6
invalid_custom_turn_order = (
    use_custom_turn_order
    and len(set(custom_turn_order)) != len(custom_turn_order)
)
invalid_custom_factions = (
    use_custom_factions
    and len(selected_custom_faction_ids) < len(player_names)
)
invalid_maps = not selected_map_ids

if invalid_player_count:
    st.warning("Il faut entre 3 et 6 joueurs.")

if invalid_custom_factions:
    st.warning("En sélection personnalisée, il faut au moins autant de factions que de joueurs.")

if invalid_maps:
    st.warning("Il faut sélectionner au moins une map.")

create_disabled = (
    invalid_player_count
    or invalid_custom_turn_order
    or invalid_custom_factions
    or invalid_maps
)

if st.button("Lancer une partie", type="primary", disabled=create_disabled):
    try:
        game_id = storage.create_game(
            game_name=game_name,
            game_date=game_date,
            player_names=player_names,
            selected_expansion_ids=selected_expansion_ids,
            selected_map_ids=selected_map_ids,
            selected_deck_ids=[],
            use_deck_pick=False,
            notes=notes,
            custom_faction_ids=selected_custom_faction_ids,
            custom_turn_order=custom_turn_order if use_custom_turn_order else None,
            custom_vagabond_name=custom_vagabond_name,
        )
    except Exception as exc:
        st.error(str(exc))
    else:
        st.success(f"Partie créée : {game_id}")
        st.code(game_id)
        st.write(
            "Les joueurs peuvent ouvrir l'app, aller dans `🎲 Draft`, "
            "puis sélectionner cette partie."
        )

st.divider()

st.subheader("Parties récentes")
games = storage.list_games()
if games.empty:
    st.write("Aucune partie créée pour le moment.")
else:
    columns = [
        column
        for column in ["game_id", "game_name", "game_date", "status", "created_at"]
        if column in games.columns
    ]
    st.dataframe(games[columns], use_container_width=True, hide_index=True)