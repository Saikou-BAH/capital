# 💼 Suivi Capital Familial

Application Streamlit de suivi d'un capital d'investissement familial.
Gestion des investisseurs, comptes, mouvements (apports / transferts / retraits / ajustements), objectifs et taux de conversion EUR → GNF.

**Backend par défaut : CSV local** — fonctionne immédiatement sans aucun compte cloud.
**Backend optionnel : Google Sheets** — pour le partage et la collaboration.

---

## Structure du projet

```
suivi-capital-app/
├── app.py                              # Dashboard principal
├── pages/
│   ├── 2_Investisseurs.py
│   ├── 3_Comptes.py
│   ├── 4_Mouvements.py
│   ├── 5_Objectifs.py
│   ├── 6_Taux_de_conversion.py
│   └── 7_Historique.py
├── utils/
│   ├── config.py                       # Constantes (capital cible, devises, types…)
│   ├── data_loader.py                  # Couche de routage → backend actif
│   ├── calculs.py                      # Logique métier pure
│   ├── formatting.py                   # CSS, composants HTML, helpers
│   ├── charts.py                       # Graphiques Plotly
│   └── backends/
│       ├── csv_backend.py              # Backend CSV (défaut)
│       └── sheets_backend.py           # Backend Google Sheets (optionnel)
├── data/                               # Fichiers CSV (backend local)
│   ├── investisseurs.csv
│   ├── comptes.csv
│   ├── mouvements.csv
│   ├── objectifs.csv
│   └── taux_conversion.csv
├── .streamlit/
│   ├── config.toml                     # Thème
│   └── secrets.toml.example            # Modèle secrets Streamlit Cloud
├── .env.example                        # Modèle variables d'environnement
├── requirements.txt
└── README.md
```

---

## Démarrage rapide en local (mode CSV — aucune config requise)

```bash
# 1. Cloner le projet
git clone https://github.com/VOTRE-COMPTE/suivi-capital-app.git
cd suivi-capital-app

# 2. Créer l'environnement Python
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt

# 3. Lancer l'application
streamlit run app.py
```

Les fichiers CSV de démonstration dans `data/` sont créés automatiquement au premier lancement s'ils n'existent pas. Ils contiennent des données réalistes (3 investisseurs, 5 comptes, 11 mouvements, 396 M GNF de capital).

---

## Structure des fichiers CSV

### `data/taux_conversion.csv`
```
id;date_taux;eur_to_gnf;commentaire;created_at
tx-001;2024-01-01;9500;Taux initial;2024-01-01 09:00
```

### `data/mouvements.csv`
```
id;date;type_mouvement;investisseur_id;compte_source_id;compte_destination_id;montant_origine;devise_origine;taux_eur_gnf;montant_converti_gnf;commentaire;compte_dans_capital;date_creation
```
> `taux_eur_gnf` = taux effectivement utilisé lors du mouvement.
> Pour les mouvements en GNF, `taux_eur_gnf = 1` (pas de conversion).

### `data/investisseurs.csv`
```
id;nom;statut;notes;date_creation
```

### `data/comptes.csv`
```
id;nom;investisseur_id;pays;devise;type_compte;actif;description
```

### `data/objectifs.csv`
```
id;nom_objectif;montant_cible_gnf;date_cible;description;actif
```

---

## Commandes Git

### Initialiser le dépôt et faire le premier commit

```bash
cd suivi-capital-app

# Initialiser Git
git init
git branch -M main

# Ajouter tous les fichiers (sauf ceux dans .gitignore)
git add .

# Premier commit
git commit -m "feat: initialisation application suivi capital familial

- Dashboard avec KPIs, graphiques Plotly, progression objectifs
- Pages : Investisseurs, Comptes, Mouvements, Objectifs, Taux, Historique
- Backend CSV local (défaut) + Google Sheets (optionnel)
- Données de démonstration réalistes
- Export CSV sur les pages Historique et Taux"

# Lier à GitHub (remplacez VOTRE-COMPTE par votre username GitHub)
git remote add origin https://github.com/VOTRE-COMPTE/suivi-capital-app.git

# Pousser sur GitHub
git push -u origin main
```

### Commits suivants (workflow quotidien)

```bash
git add .
git commit -m "feat: description de votre modification"
git push
```

---

## Passer au backend Google Sheets

### 1. Créer le service account Google

1. Allez sur [console.cloud.google.com](https://console.cloud.google.com)
2. Créez un projet → activez **Google Sheets API** + **Google Drive API**
3. **IAM & Admin > Service Accounts** → créez un compte → générez une clé JSON
4. Téléchargez le JSON → renommez-le `credentials.json` à la racine du projet
5. Ne commitez JAMAIS ce fichier (il est dans `.gitignore`)

### 2. Créer et partager le Spreadsheet

1. Créez un nouveau Google Spreadsheet vide
2. Copiez l'ID depuis l'URL : `.../spreadsheets/d/**VOTRE_ID**/edit`
3. Partagez le Spreadsheet avec l'email du service account → rôle **Éditeur**

> Les onglets et leurs en-têtes sont créés automatiquement au premier lancement.

### 3. Configurer `.env`

```bash
cp .env.example .env
```

Éditez `.env` :
```env
BACKEND=sheets
GOOGLE_CREDENTIALS_PATH=credentials.json
SPREADSHEET_ID=votre_spreadsheet_id_ici
```

### 4. Migrer les données CSV vers Sheets (optionnel)

```bash
python -c "
import pandas as pd, gspread
from google.oauth2.service_account import Credentials
from utils.config import *
from dotenv import load_dotenv; load_dotenv()
import os

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds  = Credentials.from_service_account_file(os.getenv('GOOGLE_CREDENTIALS_PATH'), scopes=SCOPES)
gc     = gspread.authorize(creds)
ss     = gc.open_by_key(os.getenv('SPREADSHEET_ID'))

for name, cols in {
    SHEET_INVESTISSEURS: COLS_INVESTISSEURS,
    SHEET_COMPTES:       COLS_COMPTES,
    SHEET_MOUVEMENTS:    COLS_MOUVEMENTS,
    SHEET_OBJECTIFS:     COLS_OBJECTIFS,
    SHEET_TAUX:          COLS_TAUX,
}.items():
    df  = pd.read_csv(f'data/{name}.csv', sep=';', encoding='utf-8-sig', dtype=str).fillna('')
    try: ws = ss.worksheet(name)
    except: ws = ss.add_worksheet(name, 2000, len(cols))
    ws.clear()
    ws.append_row(cols)
    for _, row in df.iterrows():
        ws.append_row([str(row.get(c, '')) for c in cols])
    print(f'✅ {name} importé ({len(df)} lignes)')
"
```

---

## Déploiement sur Streamlit Community Cloud

### 1. Pousser sur GitHub (voir section Git ci-dessus)

### 2. Créer l'app sur Streamlit Cloud

1. Allez sur [share.streamlit.io](https://share.streamlit.io)
2. Connectez votre GitHub → sélectionnez le repo, branche `main`, fichier `app.py`
3. Cliquez **Deploy**

### 3. Configurer les secrets (Settings > Secrets)

```toml
spreadsheet_id = "votre_spreadsheet_id_ici"

[gcp_service_account]
type                        = "service_account"
project_id                  = "votre-projet"
private_key_id              = "..."
private_key                 = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email                = "votre-compte@votre-projet.iam.gserviceaccount.com"
client_id                   = "..."
auth_uri                    = "https://accounts.google.com/o/oauth2/auth"
token_uri                   = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url        = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

> Vous trouverez toutes ces valeurs dans le fichier JSON du service account.

Pour Streamlit Cloud, ajoutez aussi dans les secrets :
```toml
BACKEND = "sheets"
```

---

## Architecture — couche d'accès aux données

```
pages/*.py  →  utils/data_loader.py  →  BACKEND=csv   →  utils/backends/csv_backend.py
                                      →  BACKEND=sheets →  utils/backends/sheets_backend.py
```

Pour ajouter un nouveau backend (SQLite, Supabase, Airtable…) :
1. Créez `utils/backends/mon_backend.py` avec les mêmes fonctions publiques
2. Ajoutez un `elif` dans `data_loader.py`
3. Aucune page de l'app n'a besoin d'être modifiée

---

## Règles métier clés

| Type de mouvement | Effet sur le capital total | Usage |
|---|---|---|
| **apport** | ✅ Augmente | Nouvel argent injecté dans le projet |
| **transfert** | ❌ Aucun effet | Argent qui se déplace entre comptes |
| **retrait** | ✅ Diminue | Argent qui sort définitivement |
| **ajustement** | ❌ Aucun effet | Correction d'une erreur |

**Exemple :** 5 000 € envoyés de France vers la Guinée = 1 apport (en France) + 1 transfert (France → Guinée). Cela n'augmente le capital qu'une seule fois.

**Taux de change :** Pour chaque mouvement en EUR, le taux EUR→GNF utilisé est stocké dans `taux_eur_gnf`. L'app permet de :
- saisir le taux manuellement
- ou récupérer automatiquement le dernier taux connu à la date du mouvement

**Devise de référence :** GNF. Tous les calculs de capital sont en GNF.

---

## Technologies

- **Python 3.10+** · **Streamlit ≥ 1.35** · **Pandas** · **Plotly**
- **gspread** + **google-auth** pour Google Sheets
- **python-dotenv** pour la configuration locale
