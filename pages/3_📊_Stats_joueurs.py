from __future__ import annotations

import pandas as pd
import streamlit as st

import storage_gsheet as storage
from data import truthy

st.set_page_config(page_title="Stats joueurs", page_icon="📊", layout="wide")
st.title("📊 Stats joueurs et factions")

results = storage.read_df("results")

if results.empty:
    st.info("Aucun résultat enregistré pour le moment.")
    st.stop()

for column in [
    "game_name",
    "game_date",
    "attempted_dominance",
    "score",
    "is_winner",
    "win_type",
]:
    if column not in results.columns:
        results[column] = ""

results["attempted_dominance_bool"] = results["attempted_dominance"].apply(truthy)
results["is_winner_bool"] = results["is_winner"].apply(truthy)

results["score_num"] = pd.to_numeric(results["score"], errors="coerce")
results.loc[results["attempted_dominance_bool"], "score_num"] = pd.NA

st.subheader("Résumé par joueur")

player_stats = (
    results.groupby("player_name", dropna=False)
    .agg(
        parties=("game_id", "nunique"),
        victoires=("is_winner_bool", "sum"),
        score_moyen=("score_num", "mean"),
        meilleur_score=("score_num", "max"),
        dominations_tentees=("attempted_dominance_bool", "sum"),
        factions_differentes=("faction_name", "nunique"),
    )
    .reset_index()
)

player_stats["win_rate"] = 100 * player_stats["victoires"] / player_stats["parties"]
player_stats = player_stats.sort_values(
    ["victoires", "win_rate", "parties"],
    ascending=False,
)

st.dataframe(
    player_stats,
    use_container_width=True,
    hide_index=True,
    column_config={
        "win_rate": st.column_config.ProgressColumn(
            "Win rate",
            format="%.0f %%",
            min_value=0,
            max_value=100,
        ),
        "score_moyen": st.column_config.NumberColumn("Score moyen", format="%.1f"),
    },
)

st.subheader("Résumé global par faction")

faction_global_stats = (
    results.groupby("faction_name", dropna=False)
    .agg(
        parties=("game_id", "nunique"),
        victoires=("is_winner_bool", "sum"),
        score_moyen=("score_num", "mean"),
        meilleur_score=("score_num", "max"),
        dominations_tentees=("attempted_dominance_bool", "sum"),
        joueurs_differents=("player_name", "nunique"),
    )
    .reset_index()
)

faction_global_stats["win_rate"] = (
    100 * faction_global_stats["victoires"] / faction_global_stats["parties"]
)

faction_global_stats = faction_global_stats.sort_values(
    ["victoires", "win_rate", "parties"],
    ascending=False,
)

st.dataframe(
    faction_global_stats,
    use_container_width=True,
    hide_index=True,
    column_config={
        "win_rate": st.column_config.ProgressColumn(
            "Win rate",
            format="%.0f %%",
            min_value=0,
            max_value=100,
        ),
        "score_moyen": st.column_config.NumberColumn("Score moyen", format="%.1f"),
    },
)

st.subheader("Factions jouées par joueur")

faction_player_stats = (
    results.groupby(["player_name", "faction_name"], dropna=False)
    .agg(
        parties=("game_id", "nunique"),
        victoires=("is_winner_bool", "sum"),
        score_moyen=("score_num", "mean"),
        dominations_tentees=("attempted_dominance_bool", "sum"),
    )
    .reset_index()
)

faction_player_stats["win_rate"] = (
    100 * faction_player_stats["victoires"] / faction_player_stats["parties"]
)

faction_player_stats = faction_player_stats.sort_values(
    ["player_name", "parties"],
    ascending=[True, False],
)

st.dataframe(
    faction_player_stats,
    use_container_width=True,
    hide_index=True,
    column_config={
        "win_rate": st.column_config.ProgressColumn(
            "Win rate",
            format="%.0f %%",
            min_value=0,
            max_value=100,
        ),
        "score_moyen": st.column_config.NumberColumn("Score moyen", format="%.1f"),
    },
)

st.subheader("Résultats bruts")

front_columns = [
    "game_id",
    "game_name",
    "game_date",
    "player_name",
    "faction_name",
    "vagabond_type",
    "score",
    "attempted_dominance",
    "rank",
    "is_winner",
    "win_type",
]

existing_front_columns = [
    column
    for column in front_columns
    if column in results.columns
]

other_columns = [
    column
    for column in results.columns
    if column not in existing_front_columns
]

st.dataframe(
    results[existing_front_columns + other_columns],
    use_container_width=True,
    hide_index=True,
)