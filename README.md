# Root Draft App

Petite application Streamlit pour préparer, drafter et suivre les parties du jeu de société **Root**.

L’application est pensée pour un usage simple entre amis : une personne crée la partie, puis les joueurs peuvent accéder à la même app pour voir l’état de la draft, faire leurs choix, puis renseigner les résultats après la partie.

## Fonctionnalités

### Setup d’une partie

* Création d’une partie avec un nom et une date.
* Sélection des extensions disponibles.
* Sélection des maps disponibles.
* Sélection des joueurs.
* Récupération automatique des joueurs déjà vus dans les anciennes parties.
* Tirage aléatoire de l’ordre du tour.
* Option pour définir manuellement l’ordre du tour.
* Option pour remplacer le tirage aléatoire des factions par une sélection manuelle.

### Draft

* Le premier joueur choisit la map.
* Les factions sont masquées jusqu’au choix de la map.
* Les joueurs draftent ensuite les factions en ordre inverse de l’ordre du tour.
* Une faction choisie disparaît des factions disponibles.
* L’état de la draft est partagé via Google Sheets.
* Les joueurs peuvent revenir sur la partie en cours depuis la page Draft.

### Factions

* Tirage de factions parmi les factions disponibles.
* La première faction tirée est obligatoirement une faction **Militant**.
* Gestion du **Vagabond** :

  * tirage automatique du type de Vagabond ;
  * choix manuel du type de Vagabond en partie personnalisée.
* Les factions de l’extension **The Homeland Expansion** peuvent être configurées mais ne sont pas sélectionnées par défaut.

### Résultats

* Consultation des parties créées.
* Saisie du vainqueur.
* Saisie du type de victoire :

  * points ;
  * domination ;
  * autre.
* Saisie des points par joueur.
* Possibilité d’indiquer qu’un joueur a tenté une domination et n’a donc plus de score.
* Résumé de la partie avec joueurs, factions, score ou domination, et vainqueur.

### Statistiques

* Statistiques par joueur :

  * nombre de parties ;
  * nombre de victoires ;
  * taux de victoire ;
  * score moyen ;
  * meilleur score ;
  * dominations tentées ;
  * nombre de factions différentes jouées.

* Statistiques globales par faction :

  * nombre de parties ;
  * nombre de victoires ;
  * taux de victoire ;
  * score moyen ;
  * meilleur score ;
  * dominations tentées ;
  * nombre de joueurs différents.

* Statistiques par joueur et faction.

* Les statistiques du **Vagabond** sont agrégées au niveau `Vagabond`, quel que soit le type de Vagabond joué. Le détail du type reste visible dans les résultats bruts.

## Stack technique

* Python
* Streamlit
* Google Sheets
* gspread
* pandas

Le Google Sheet sert de base de données partagée.
Streamlit sert uniquement d’interface.

## Architecture

```text
root-draft-app/
├── 🏠_Accueil_&_Setup.py
├── data.py
├── draft_logic.py
├── storage_gsheet.py
├── requirements.txt
├── README.md
└── pages/
    ├── 🎲_Draft.py
    ├── 📜_Parties.py
    └── 📊_Stats_joueurs.py
```

## Rôle des fichiers

| Fichier                     | Rôle                                                 |
| --------------------------- | ---------------------------------------------------- |
| `🏠_Accueil_&_Setup.py`     | Page d’accueil et création d’une partie              |
| `pages/🎲_Draft.py`         | Draft de la map et des factions                      |
| `pages/📜_Parties.py`       | Consultation des parties et saisie des résultats     |
| `pages/📊_Stats_joueurs.py` | Statistiques joueurs et factions                     |
| `data.py`                   | Constantes et helpers simples                        |
| `draft_logic.py`            | Logique de tirage, ordre du tour et pool de factions |
| `storage_gsheet.py`         | Connexion et lecture/écriture dans Google Sheets     |

## Structure du Google Sheet

Le Google Sheet doit contenir les onglets suivants :

```text
config_expansions
config_factions
config_vagabonds
config_maps
config_decks
config_players
games
players
pool
steps
results
```

### Onglets de configuration

| Onglet              | Description                                                      |
| ------------------- | ---------------------------------------------------------------- |
| `config_expansions` | Extensions disponibles                                           |
| `config_factions`   | Factions, types et extensions associées                          |
| `config_vagabonds`  | Types de Vagabond disponibles                                    |
| `config_maps`       | Maps disponibles                                                 |
| `config_decks`      | Ancien onglet conservé mais non utilisé dans la version actuelle |
| `config_players`    | Joueurs connus, facultatif                                       |

### Onglets de partie

| Onglet    | Description                           |
| --------- | ------------------------------------- |
| `games`   | Une ligne par partie                  |
| `players` | Joueurs d’une partie et ordre du tour |
| `pool`    | Factions disponibles pour la draft    |
| `steps`   | Étapes de draft                       |
| `results` | Résultats finaux et scores            |

## Installation locale

Créer l’environnement virtuel :

```bash
python -m venv .venv
source .venv/bin/activate
```

Sous Windows PowerShell :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Installer les dépendances :

```bash
pip install -r requirements.txt
```

Lancer l’application :

```bash
streamlit run "🏠_Accueil_&_Setup.py"
```

## Dépendances

Le fichier `requirements.txt` doit contenir :

```txt
streamlit
gspread
google-auth
pandas
```

## Configuration Google Sheets

L’application utilise un compte de service Google Cloud pour accéder au Google Sheet.

Étapes nécessaires :

1. Créer un projet Google Cloud.
2. Activer **Google Sheets API**.
3. Créer un **service account**.
4. Générer une clé JSON.
5. Partager le Google Sheet avec l’adresse `client_email` du service account.
6. Donner le rôle **Éditeur** au service account sur le Google Sheet.
7. Ajouter les secrets dans `.streamlit/secrets.toml` en local et dans Streamlit Cloud au déploiement.

Exemple de structure attendue pour les secrets :

```toml
[google_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[google_sheets]
spreadsheet_name = "root_draft_app_db"
```

Il est aussi possible d’utiliser directement l’ID du Google Sheet :

```toml
[google_sheets]
spreadsheet_id = "ID_DU_GOOGLE_SHEET"
spreadsheet_name = "root_draft_app_db"
```

## Sécurité

Ne jamais committer les fichiers suivants :

```text
.streamlit/secrets.toml
service_account.json
credentials.json
*.json
```

Le `.gitignore` doit contenir au minimum :

```gitignore
.venv/
__pycache__/
*.pyc

.streamlit/secrets.toml
service_account.json
credentials.json
*.json

.DS_Store
.vscode/
```

## Déploiement Streamlit Cloud

1. Pousser le projet sur GitHub.
2. Aller sur Streamlit Community Cloud.
3. Créer une nouvelle app depuis le repo GitHub.
4. Choisir la branche `main`.
5. Indiquer comme fichier principal :

```text
🏠_Accueil_&_Setup.py
```

6. Coller les secrets dans les paramètres avancés Streamlit.
7. Déployer.

Si le nom de fichier avec emoji pose problème au déploiement, renommer le fichier principal en :

```text
Accueil_Setup.py
```

et mettre à jour le chemin dans Streamlit Cloud.

## Workflow Git

Après chaque modification :

```bash
git status
git add .
git commit -m "Describe change"
git push
```

Streamlit Cloud redéploie automatiquement après le push.

## Limites connues

* Google Sheets est utilisé comme mini base de données. Ce n’est pas une vraie base transactionnelle.
* En cas de nombreux clics rapides ou de nombreux utilisateurs simultanés, les quotas Google Sheets peuvent être atteints.
* L’application est pensée pour un petit groupe de joueurs, pas pour un usage public massif.
* La gestion concurrente est volontairement simple : l’état est relu avant les actions importantes, et les choix déjà pris sont bloqués.

## Idées d’amélioration

* Ajouter une authentification simple.
* Ajouter une vraie base de données type Supabase ou PostgreSQL.
* Ajouter des graphiques dans la page statistiques.
* Ajouter des presets de groupes de joueurs.
* Ajouter des filtres par période dans les statistiques.
* Ajouter un export CSV des résultats.
* Ajouter une page d’administration pour nettoyer les anciennes parties.
