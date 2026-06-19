from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import storage_gsheet as storage
from data import truthy

st.set_page_config(page_title="Parties Root", page_icon="📜", layout="wide")
st.title("📜 Parties")

if "metadata_saved_message" in st.session_state:
    st.success(st.session_state.pop("metadata_saved_message"))


def build_game_label(row) -> str:
    return (
        f"{row.get('game_date', '')} — "
        f"{row.get('game_name', row.get('game_id', ''))} — "
        f"{row.get('game_id', '')} — "
        f"{row.get('status', '')}"
    )


def make_results_summary(results: pd.DataFrame, choices: list[dict]) -> pd.DataFrame:
    if results.empty:
        rows = []

        for choice in choices:
            rows.append(
                {
                    "player_name": choice["player_name"],
                    "faction_name": choice["faction_name"],
                    "vagabond_type": choice["vagabond_type"],
                    "score": "",
                    "attempted_dominance": "",
                    "is_winner": "",
                    "win_type": "",
                }
            )

        return pd.DataFrame(rows)

    display = results.copy()

    expected_columns = [
        "player_name",
        "faction_name",
        "vagabond_type",
        "score",
        "attempted_dominance",
        "is_winner",
        "win_type",
    ]

    for column in expected_columns:
        if column not in display.columns:
            display[column] = ""

    return display[expected_columns]


def format_result(row) -> str:
    if truthy(row.get("is_winner", "")) and row.get("win_type", "") == "dominance":
        return "Victoire par domination"

    if truthy(row.get("attempted_dominance", "")):
        return "Domination tentée"

    score = row.get("score", "")
    if str(score).strip():
        return str(score)

    return ""


games = storage.list_games()
if games.empty:
    st.info("Aucune partie créée pour le moment.")
    st.stop()

games = games.copy()
games["label"] = games.apply(build_game_label, axis=1)

previous_selected_game_id = st.session_state.get("selected_game_id_parties", "")

default_index = 0
if previous_selected_game_id and previous_selected_game_id in games["game_id"].tolist():
    default_index = games["game_id"].tolist().index(previous_selected_game_id)

selected_label = st.selectbox(
    "Partie",
    options=games["label"].tolist(),
    index=default_index,
)

selected_game = games[games["label"] == selected_label].iloc[0].to_dict()
selected_game_id = selected_game["game_id"]
st.session_state["selected_game_id_parties"] = selected_game_id

state = storage.load_game_state(selected_game_id)
if not state:
    st.error("Partie introuvable.")
    st.stop()

game = state["game"]
players = state["players"]
pool = state["pool"]
steps = state["steps"]
results = state["results"]

choices = storage.get_faction_choices(selected_game_id)

st.subheader("Résumé de la partie")

summary = make_results_summary(results, choices)

if summary.empty:
    st.warning("Aucune faction choisie pour cette partie.")
else:
    summary_display = summary.copy()
    summary_display["points_ou_resultat"] = summary_display.apply(format_result, axis=1)
    summary_display["vainqueur"] = summary_display["is_winner"].apply(
        lambda value: "✅" if truthy(value) else "❌"
    )

    summary_display = summary_display[
        [
            "player_name",
            "faction_name",
            "vagabond_type",
            "points_ou_resultat",
            "vainqueur",
        ]
    ]

    st.dataframe(summary_display, use_container_width=True, hide_index=True)

st.divider()

st.subheader("Informations")

with st.form("metadata_form"):
    game_name = st.text_input("Nom", value=str(game.get("game_name", "")))
    game_date = st.text_input("Date", value=str(game.get("game_date", "")))
    notes = st.text_area("Notes", value=str(game.get("notes", "")))
    save_metadata = st.form_submit_button("Mettre à jour les infos")

if save_metadata:
    ok, message = storage.save_game_metadata(
        selected_game_id,
        game_name,
        game_date,
        notes,
    )

    if ok:
        st.session_state["metadata_saved_message"] = "Informations de la partie mises à jour."
        storage.clear_cached_sheet_data()
        st.rerun()
    else:
        st.error(message)

left, right = st.columns(2)

with left:
    st.markdown("### Joueurs")
    if not players.empty:
        st.dataframe(players.sort_values("turn_order"), use_container_width=True, hide_index=True)

with right:
    st.markdown("### Factions")
    if not pool.empty:
        st.dataframe(pool.sort_values("pool_order"), use_container_width=True, hide_index=True)

st.markdown("### Draft")
if not steps.empty:
    st.dataframe(steps.sort_values("step_order"), use_container_width=True, hide_index=True)

st.divider()
st.subheader("Saisie des résultats")

if not choices:
    st.warning("Aucune faction choisie pour cette partie. Termine d'abord la draft.")
else:
    existing_results = {}
    if not results.empty and "player_name" in results.columns:
        existing_results = {
            row["player_name"]: row.to_dict()
            for _, row in results.iterrows()
        }

    player_names = [choice["player_name"] for choice in choices]

    default_winner = player_names[0]
    for player_name in player_names:
        if truthy(existing_results.get(player_name, {}).get("is_winner", "")):
            default_winner = player_name
            break

    with st.form("results_form"):
        winner_name = st.selectbox(
            "Vainqueur",
            options=player_names,
            index=player_names.index(default_winner),
        )

        winner_previous_win_type = existing_results.get(winner_name, {}).get("win_type", "")
        win_type_options = ["points", "dominance", "other"]

        win_type = st.selectbox(
            "Type de victoire",
            options=win_type_options,
            index=win_type_options.index(winner_previous_win_type)
            if winner_previous_win_type in win_type_options
            else 0,
        )

        st.markdown("### Points par joueur")

        result_rows = []
        score_values = {}

        for choice in sorted(choices, key=lambda item: item["player_name"]):
            player_name = choice["player_name"]
            existing = existing_results.get(player_name, {})

            faction_label = choice["faction_name"]
            if choice.get("vagabond_type"):
                faction_label = f"{faction_label} ({choice['vagabond_type']})"

            st.markdown(f"#### {player_name} — {faction_label}")

            existing_attempted_dominance = truthy(existing.get("attempted_dominance", ""))
            forced_dominance = player_name == winner_name and win_type == "dominance"

            attempted_dominance = st.checkbox(
                "Domination tentée : le joueur n'a plus de score",
                value=existing_attempted_dominance or forced_dominance,
                disabled=forced_dominance,
                key=f"dominance_{selected_game_id}_{player_name}",
            )

            previous_score = existing.get("score", "")
            default_score = 0
            if str(previous_score).strip():
                try:
                    default_score = int(float(previous_score))
                except ValueError:
                    default_score = 0

            score = st.number_input(
                "Points",
                min_value=0,
                max_value=999,
                value=default_score,
                step=1,
                disabled=attempted_dominance,
                key=f"score_{selected_game_id}_{player_name}",
            )

            score_value = "" if attempted_dominance else score
            score_values[player_name] = score_value

            result_rows.append(
                {
                    "game_id": selected_game_id,
                    "game_name": game.get("game_name", ""),
                    "game_date": game.get("game_date", ""),
                    "player_name": player_name,
                    "faction_id": choice["faction_id"],
                    "faction_name": choice["faction_name"],
                    "vagabond_type": choice["vagabond_type"],
                    "score": score_value,
                    "attempted_dominance": str(attempted_dominance).upper(),
                    "rank": "",
                    "is_winner": str(player_name == winner_name).upper(),
                    "win_type": win_type if player_name == winner_name else "",
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

        save_results = st.form_submit_button("Enregistrer les résultats")

    if save_results:
        numeric_scores = {
            player_name: score
            for player_name, score in score_values.items()
            if str(score).strip() != ""
        }

        for row in result_rows:
            score = row["score"]

            if str(score).strip() == "":
                row["rank"] = ""
            else:
                row["rank"] = 1 + sum(
                    other_score > score
                    for other_score in numeric_scores.values()
                )

        ok, message = storage.replace_results_for_game(selected_game_id, result_rows)

        if ok:
            st.session_state["results_saved_message"] = (
                "Résultats enregistrés. Les statistiques joueurs et factions ont été mises à jour. "
                "Tu peux les consulter dans la page 📊 Stats joueurs."
            )
            storage.clear_cached_sheet_data()
            st.rerun()
        else:
            st.error(message)

if "results_saved_message" in st.session_state:
    st.success(st.session_state.pop("results_saved_message"))

st.divider()
st.subheader("Administration")

with st.expander("Annuler ou supprimer cette partie"):
    st.warning(
        "Annuler conserve l'historique dans le Google Sheet. "
        "Supprimer efface définitivement la partie de tous les onglets."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Marquer comme annulée"):
            ok, message = storage.cancel_game(selected_game_id)
            if ok:
                st.success(message)
                storage.clear_cached_sheet_data()
                st.rerun()
            else:
                st.error(message)

    with col2:
        confirm_delete = st.checkbox(
            f"Je confirme la suppression définitive de {selected_game_id}"
        )

        if st.button(
            "Supprimer définitivement",
            disabled=not confirm_delete,
            type="secondary",
        ):
            ok, message = storage.delete_game(selected_game_id)
            if ok:
                st.success(message)
                storage.clear_cached_sheet_data()
                st.rerun()
            else:
                st.error(message)