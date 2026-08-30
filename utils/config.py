"""Configuration globale et constantes de l'application."""

# ── Identité du projet ───────────────────────────────────────────────────────
PROJECT_NAME = "Legend Farm"

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

# ── Paliers de capital — section « Suivi des objectifs » ──────────────────────
# 5 paliers fixes de la trajectoire de capital de Legend Farm. Uniquement les
# cibles (montant, date) sont figées ici : le capital actuel et toute la
# progression restent calculés dynamiquement depuis les données réelles.
PALIERS_CAPITAL = [
    {
        "id": "palier-01",
        "nom": "Capital initial",
        "icone": "🏁",
        "montant_cible_gnf": 200_000_000,
        "date_cible": "2026-09-01",
    },
    {
        "id": "palier-02",
        "nom": "Infrastructures sécurisées",
        "icone": "🏗️",
        "montant_cible_gnf": 250_000_000,
        "date_cible": "2026-12-01",
    },
    {
        "id": "palier-03",
        "nom": "Lancement de l'exploitation",
        "icone": "🚀",
        "montant_cible_gnf": 300_000_000,
        "date_cible": "2027-01-01",
    },
    {
        "id": "palier-04",
        "nom": "Développement de la ferme",
        "icone": "🌱",
        "montant_cible_gnf": 400_000_000,
        "date_cible": "2027-09-01",
    },
    {
        "id": "palier-05",
        "nom": "Capital cible Legend Farm",
        "icone": "🏆",
        "montant_cible_gnf": 500_000_000,
        "date_cible": "2028-01-01",
    },
]

# ── Devises ───────────────────────────────────────────────────────────────────
DEVISES = ["GNF", "EUR"]
DEVISE_REFERENCE = "GNF"
TAUX_EUR_GNF_DEFAUT = 0  # 0 = aucun taux connu, l'utilisateur doit le saisir

# ── Référentiels métier ───────────────────────────────────────────────────────
TYPES_MOUVEMENT  = ["apport", "transfert", "retrait"]
TYPES_MOUVEMENT_FILTRE = ["apport", "transfert", "retrait", "frais_retrait"]
TYPES_COMPTE     = ["banque", "espèces", "mobile money", "YMO", "autre"]
PAYS_DISPONIBLES = ["France", "Guinée", "Belgique", "Sénégal", "Autre"]
STATUTS_INVESTISSEUR = ["actif", "inactif", "potentiel"]

# ── Noms des onglets Google Sheets ─────────────────────────────────────────────
SHEET_INVESTISSEURS = "investisseurs"
SHEET_COMPTES       = "comptes"
SHEET_MOUVEMENTS    = "mouvements"
SHEET_OBJECTIFS     = "objectifs"
SHEET_TAUX          = "taux_conversion"
SHEET_PLANIFICATION = "planification_mensuelle"

# ── Colonnes attendues par onglet ─────────────────────────────────────────────
COLS_INVESTISSEURS = ["id", "nom", "statut", "notes", "date_creation"]

COLS_COMPTES = [
    "id", "nom", "investisseur_id", "pays", "devise",
    "type_compte", "actif", "description", "date_creation", "frais_pct",
]

COLS_MOUVEMENTS = [
    "id", "date", "type_mouvement", "investisseur_id",
    "compte_source_id", "compte_destination_id",
    "montant_origine", "devise_origine", "taux_eur_gnf",
    "montant_converti_gnf", "commentaire",
    "compte_dans_capital", "apport_source_id", "date_creation",
]

COLS_OBJECTIFS = [
    "id", "nom_objectif", "montant_cible_gnf",
    "date_cible", "description", "actif",
    "cloture", "capital_gele_gnf", "date_cloture",
]

COLS_TAUX = ["id", "date_taux", "eur_to_gnf", "commentaire", "created_at"]

# Un montant planifié par mois calendaire (format "YYYY-MM"), utilisé pour
# projeter le capital de fin de mois dans la section « Suivi des objectifs ».
COLS_PLANIFICATION = ["id", "mois", "apports_prevus_gnf", "date_creation"]

# ── Plan d'apports prévisionnels (planning personnel, distinct du capital réel) ─
# Une ligne par mois planifié. "mois" = premier jour du mois ("YYYY-MM-01").
# Montant stocké directement en GNF — aucune devise étrangère, aucun taux de
# change, aucune conversion. Jamais mélangé aux vrais mouvements financiers.
SHEET_PLAN_APPORTS = "plan_apports_previsionnels"
COLS_PLAN_APPORTS = ["id", "mois", "montant_prevu_gnf", "date_creation"]

# Modes de backend disponibles
BACKENDS_DISPONIBLES = ["csv", "sheets"]

# ── Palette de couleurs — identité Legend Farm (terre cuite chaude, tons
#    coordonnés plutôt qu'un arc-en-ciel saturé générique) ─────────────────────
COULEURS_CHART = [
    "#B65C2E", "#3E7C51", "#99651A", "#46688A",
    "#6B5B95", "#8C6E4A", "#5C8374", "#A24D4D",
]

COULEUR_PRIMAIRE = "#B65C2E"
COULEUR_SUCCES   = "#3E7C51"
COULEUR_DANGER   = "#B3432F"
COULEUR_WARNING  = "#99651A"
COULEUR_VIOLET   = "#6B5B95"
COULEUR_NEUTRE   = "#6B6155"

# ── Labels par type de mouvement ──────────────────────────────────────────────
EMOJI_MOUVEMENT = {
    "apport":                    "💰",
    "transfert":                 "↔️",
    "depense":                   "💸",
    "retrait":                   "📤",
    "ajustement":                "🔧",
    "frais_retrait":             "🏧",
    "frais_orange_marchand":     "🏪",
}

# Labels d'affichage visuels (remplacent le type brut dans les badges)
LABELS_MOUVEMENT = {
    "apport":                "Apport",
    "transfert":             "Transfert",
    "depense":               "Dépense",
    "retrait":               "Retrait",
    "ajustement":            "Ajustement",
    "frais_retrait":         "Frais retrait",
    "frais_orange_marchand": "Frais Orange Marchand",
}

COULEUR_BADGE_MOUVEMENT = {
    "apport":                ("#166534", "#dcfce7"),
    "transfert":             ("#1e40af", "#dbeafe"),
    "depense":               ("#991b1b", "#fee2e2"),
    "retrait":               ("#991b1b", "#fee2e2"),
    "ajustement":            ("#92400e", "#fef3c7"),
    "frais_retrait":         ("#6b21a8", "#f3e8ff"),
    "frais_orange_marchand": ("#7c2d12", "#ffedd5"),
}

# ── Dépenses avant exploitation ───────────────────────────────────────────────
SHEET_DEPENSES = "depenses_avant_exploitation"
COLS_DEPENSES = [
    "id", "nom", "categorie", "sous_categorie", "description",
    "montant_gnf", "frais_gnf", "transport_gnf", "compte_utilise", "date",
    "statut_paiement", "justificatif_note", "date_creation",
]

# Répartition d'une dépense entre plusieurs investisseurs (qui paie quoi)
SHEET_DEPENSES_REPARTITION = "depenses_repartition_investisseurs"
COLS_DEPENSES_REPARTITION = [
    "id", "depense_id", "investisseur_id", "montant_gnf", "date_creation",
]

CATEGORIES_DEPENSES = [
    "Formation",
    "Étude du terrain",
    "Transport",
    "Clôture",
    "Bâtiments",
    "Forage",
    "Énergie",
    "Main-d'œuvre",
    "Gestionnaire",
]

CATEGORIES_DEPENSES_DESCRIPTIONS = {
    "Formation":         "Formation du gestionnaire, accompagnement expert avicole, conseils techniques, frais de formation et autres dépenses liées à l'apprentissage ou l'accompagnement technique.",
    "Étude du terrain":  "Visite et analyse du terrain, conseils constructeurs, plan d'implantation, études et préparation technique du chantier avant travaux.",
    "Transport":         "Transport des matériaux, frais de livraison, carburant de livraison, location de véhicule pour le transport de matériaux et autres frais logistiques du projet.",
    "Clôture":           "Matériaux et petit matériel de chantier utilisés spécifiquement pour la réalisation de la clôture de Legend Farm.",
    "Bâtiments":         "Matériaux et équipements pour poulaillers, magasins, logement, toilettes, bureau, toiture, portes, fenêtres et autres travaux de construction des bâtiments.",
    "Forage":            "Forage, pompe, tuyaux, château d'eau, réservoirs, raccordements et installation d'eau.",
    "Énergie":           "Panneaux solaires, batteries, câbles, lampes, équipements et installation électrique.",
    "Main-d'œuvre":      "Rémunération des artisans, ouvriers et prestataires qui réalisent physiquement les travaux : maçons, ferrailleurs, coffreurs, puisatiers, ouvriers, électriciens, plombiers, soudeurs, menuisiers et suivi de chantier.",
    "Gestionnaire":      "Dépenses personnelles du gestionnaire de Legend Farm : salaire, transport/déplacements, indemnités, carburant et autres frais professionnels liés à ses missions.",
}

# Sous-catégories disponibles pour chaque catégorie principale — un choix direct
# du type précis de dépense (ex : "Ciment", "Maçon", "Salaire du gestionnaire"),
# sans niveau intermédiaire générique ("Matériaux", "Divers"...).
SOUS_CATEGORIES_DEPENSES: dict[str, list[str]] = {
    "Formation": [
        "Formation du gestionnaire",
        "Accompagnement expert avicole",
        "Conseils techniques",
        "Déplacements liés à la formation",
        "Autres frais de formation",
    ],
    "Étude du terrain": [
        "Visite du terrain",
        "Analyse du terrain",
        "Conseils constructeurs",
        "Plan d'implantation",
        "Études techniques",
        "Autres frais d'étude du terrain",
    ],
    "Transport": [
        "Transport des matériaux",
        "Livraison des matériaux",
        "Carburant lié à la logistique",
        "Location de véhicule",
        "Déplacements logistiques",
        "Autres frais de transport",
    ],
    "Clôture": [
        "Briques",
        "Ciment",
        "Sable",
        "Granite / gravier",
        "Blocs / pierres pour soubassement",
        "Fer à béton Ø6",
        "Fer à béton Ø8",
        "Fer à béton Ø10",
        "Fil d'attache",
        "Planches de coffrage",
        "Chevrons",
        "Pointes ordinaires",
        "Pointes acier",
        "Ficelle / corde de maçon",
        "Portail",
        "Peinture / finition du portail",
        "Eau de chantier",
        "Brouette",
        "Pioche",
        "Pelle",
        "Seau",
        "Gamate",
        "Fût",
        "Bassin de chantier",
        "Autres fournitures de clôture",
    ],
    "Bâtiments": [
        "Briques",
        "Ciment",
        "Sable",
        "Granite / gravier",
        "Fer à béton",
        "Bois",
        "Planches",
        "Chevrons",
        "Tôles / toiture",
        "Portes",
        "Fenêtres",
        "Carrelage",
        "Peinture",
        "Plomberie",
        "Électricité bâtiment",
        "Matériaux poulailler",
        "Matériaux magasin",
        "Matériaux logement",
        "Matériaux toilettes",
        "Matériaux bureau",
        "Autres matériaux de bâtiment",
    ],
    "Forage": [
        "Forage",
        "Pompe",
        "Tuyaux",
        "Château d'eau",
        "Réservoir",
        "Raccords",
        "Accessoires hydrauliques",
        "Installation d'eau",
        "Autres dépenses de forage",
    ],
    "Énergie": [
        "Panneaux solaires",
        "Batteries",
        "Onduleur",
        "Régulateur",
        "Câbles électriques",
        "Lampes",
        "Protections électriques",
        "Installation électrique",
        "Autres équipements énergétiques",
    ],
    "Main-d'œuvre": [
        "Maçon",
        "Ferrailleur",
        "Coffreur",
        "Puisatier",
        "Ouvrier",
        "Soudeur",
        "Plombier",
        "Électricien",
        "Menuisier",
        "Peintre",
        "Supervision / suivi de chantier",
        "Autre artisan ou prestataire",
    ],
    "Gestionnaire": [
        "Salaire du gestionnaire",
        "Transport / déplacements du gestionnaire",
        "Carburant du gestionnaire",
        "Indemnités du gestionnaire",
        "Communication / téléphone du gestionnaire",
        "Autres frais professionnels du gestionnaire",
    ],
}

# Sous-catégories Clôture qui relèvent du petit matériel de chantier (outils),
# par opposition aux matériaux de construction — utilisé uniquement pour la
# lecture du panneau devis ci-dessous, ce n'est pas un niveau de classement
# proposé dans le formulaire de saisie.
DEVIS_CLOTURE_SOUSCATS_OUTILS = {
    "Brouette", "Pioche", "Pelle", "Seau", "Gamate", "Fût", "Bassin de chantier",
}

# ── Devis de référence — chantier Clôture ──────────────────────────────────────
# Montants de référence issus du devis fournisseur. Ce sont des PRÉVISIONS,
# jamais enregistrées automatiquement comme dépenses réelles — elles servent
# uniquement de repère (devis vs dépensé) affiché sur la page Dépenses.
DEVIS_CLOTURE_MATERIAUX_GNF          = 157_380_000
DEVIS_CLOTURE_MATERIEL_CHANTIER_GNF  = 4_895_000
DEVIS_CLOTURE_MAIN_OEUVRE_GNF        = 33_500_000
DEVIS_CLOTURE_TOTAL_GNF              = 195_775_000

DEVIS_CLOTURE_MATERIEL_CHANTIER_QUANTITES: dict[str, int] = {
    "Brouette": 2, "Pioche": 3, "Pelle": 4, "Seau": 7, "Corde": 10,
    "Fût / récipient de stockage d'eau": 1, "Bassin de chantier": 1,
}

DEVIS_CLOTURE_MAIN_OEUVRE_DETAIL: dict[str, int] = {
    "Maçon": 14_000_000,
    "Ferrailleur": 3_500_000,
    "Coffreur": 4_000_000,
    "Puisatier": 4_000_000,
    "Suivi de chantier / supervision": 8_000_000,
}

COMPTES_GNF_DEPENSES  = ["Ymo", "Orange Money", "Orange Marchand", "Espèces"]
STATUTS_DEPENSE       = ["En attente", "Payé", "Partiellement payé"]

# ── Frais de retrait cash — barème opérateur (par nom de compte) ──────────────
# Chaque entrée : liste de (montant_min, montant_max, taux)
FRAIS_RETRAIT_BAREME: dict = {
    "Orange Money": [
        (2_000,      5_000_000,  0.01),   # 1 %
        (5_000_001, 15_000_000,  0.008),  # 0,80 %
    ]
}
ORANGE_MONEY_MAX_RETRAIT_GNF = 15_000_000
