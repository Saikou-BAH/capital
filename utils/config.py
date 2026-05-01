"""Configuration globale et constantes de l'application."""

# ── Capital cible ──────────────────────────────────────────────────────────────
CAPITAL_CIBLE_GNF = 500_000_000  # 500 millions GNF

# ── Objectifs principaux ──────────────────────────────────────────────────────
OBJECTIF_SEPTEMBRE_ID = "obj-001"
OBJECTIF_SEPTEMBRE_NOM = "Objectif Septembre 2026"
OBJECTIF_SEPTEMBRE_MONTANT = CAPITAL_CIBLE_GNF * 0.5  # 250 millions GNF
OBJECTIF_SEPTEMBRE_DATE = "2026-09-01"

OBJECTIF_DECEMBRE_ID = "obj-002"
OBJECTIF_DECEMBRE_NOM = "Objectif Décembre 2026"
OBJECTIF_DECEMBRE_MONTANT = CAPITAL_CIBLE_GNF  # 500 millions GNF
OBJECTIF_DECEMBRE_DATE = "2026-12-31"

# ── Devises ───────────────────────────────────────────────────────────────────
DEVISES = ["GNF", "EUR"]
DEVISE_REFERENCE = "GNF"
TAUX_EUR_GNF_DEFAUT = 0  # 0 = aucun taux connu, l'utilisateur doit le saisir

# ── Référentiels métier ───────────────────────────────────────────────────────
TYPES_MOUVEMENT  = ["apport", "transfert", "depense", "retrait", "ajustement"]
TYPES_COMPTE     = ["banque", "espèces", "mobile money", "YMO", "autre"]
PAYS_DISPONIBLES = ["France", "Guinée", "Belgique", "Sénégal", "Autre"]
STATUTS_INVESTISSEUR = ["actif", "inactif", "potentiel"]

# ── Noms des onglets Google Sheets ─────────────────────────────────────────────
SHEET_INVESTISSEURS = "investisseurs"
SHEET_COMPTES       = "comptes"
SHEET_MOUVEMENTS    = "mouvements"
SHEET_OBJECTIFS     = "objectifs"
SHEET_TAUX          = "taux_conversion"

# ── Colonnes attendues par onglet ─────────────────────────────────────────────
COLS_INVESTISSEURS = ["id", "nom", "statut", "notes", "date_creation"]

COLS_COMPTES = [
    "id", "nom", "investisseur_id", "pays", "devise",
    "type_compte", "actif", "description", "date_creation",
]

COLS_MOUVEMENTS = [
    "id", "date", "type_mouvement", "investisseur_id",
    "compte_source_id", "compte_destination_id",
    "montant_origine", "devise_origine", "taux_eur_gnf",
    "montant_converti_gnf", "commentaire",
    "compte_dans_capital", "date_creation",
]

COLS_OBJECTIFS = [
    "id", "nom_objectif", "montant_cible_gnf",
    "date_cible", "description", "actif",
]

COLS_TAUX = ["id", "date_taux", "eur_to_gnf", "commentaire", "created_at"]

# Modes de backend disponibles
BACKENDS_DISPONIBLES = ["csv", "sheets"]

# ── Palette de couleurs ───────────────────────────────────────────────────────
COULEURS_CHART = [
    "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
    "#8b5cf6", "#06b6d4", "#f97316", "#ec4899",
]

COULEUR_PRIMAIRE = "#3b82f6"
COULEUR_SUCCES   = "#10b981"
COULEUR_DANGER   = "#ef4444"
COULEUR_WARNING  = "#f59e0b"
COULEUR_VIOLET   = "#8b5cf6"
COULEUR_NEUTRE   = "#6b7280"

# ── Labels par type de mouvement ──────────────────────────────────────────────
EMOJI_MOUVEMENT = {
    "apport":     "💰",
    "transfert":  "↔️",
    "depense":    "💸",
    "retrait":    "📤",
    "ajustement": "🔧",
}

COULEUR_BADGE_MOUVEMENT = {
    "apport":     ("#166534", "#dcfce7"),
    "transfert":  ("#1e40af", "#dbeafe"),
    "depense":    ("#991b1b", "#fee2e2"),
    "retrait":    ("#991b1b", "#fee2e2"),
    "ajustement": ("#92400e", "#fef3c7"),
}
