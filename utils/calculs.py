"""Logique métier : calculs du capital, parts, soldes, objectifs."""

import pandas as pd
from datetime import date, datetime, timedelta
from utils.config import TAUX_EUR_GNF_DEFAUT, CAPITAL_CIBLE_GNF, FRAIS_RETRAIT_BAREME


# ── Conversion de devises ─────────────────────────────────────────────────────

EXPENSE_TYPES = {"depense", "retrait", "frais_retrait"}

def convertir_en_gnf(montant: float, devise: str, taux: float) -> float:
    """Convertit un montant dans n'importe quelle devise en GNF."""
    if devise == "GNF":
        return round(float(montant))
    if devise == "EUR":
        return round(float(montant) * float(taux))
    return round(float(montant))


def get_dernier_taux(df_taux: pd.DataFrame, avant_date: str | None = None) -> float:
    """
    Renvoie le dernier taux EUR→GNF connu, optionnellement avant une date donnée.
    Compatible avec les colonnes : date_taux / eur_to_gnf (spec utilisateur).
    """
    if df_taux is None or df_taux.empty:
        return TAUX_EUR_GNF_DEFAUT
    df = df_taux.copy()

    # Support des deux nommages de colonnes date
    date_col = "date_taux" if "date_taux" in df.columns else "date"
    taux_col = "eur_to_gnf" if "eur_to_gnf" in df.columns else "taux_eur_gnf"

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col, taux_col])
    df[taux_col] = pd.to_numeric(df[taux_col], errors="coerce")
    df = df.dropna(subset=[taux_col])

    if avant_date:
        df = df[df[date_col] <= pd.Timestamp(avant_date)]
    if df.empty:
        return TAUX_EUR_GNF_DEFAUT
    df = df.sort_values(date_col, ascending=False)
    return float(df.iloc[0][taux_col])


# ── Capital total ─────────────────────────────────────────────────────────────

def _mouvements_actifs(df_mvt: pd.DataFrame) -> pd.DataFrame:
    """Filtre les mouvements qui comptent dans le capital."""
    if df_mvt is None or df_mvt.empty:
        return pd.DataFrame()
    df = df_mvt.copy()
    # compte_dans_capital peut être "True"/"False" (string) ou bool
    df["compte_dans_capital"] = df["compte_dans_capital"].astype(str).str.lower().isin(
        ["true", "1", "oui", "yes"]
    )
    return df[df["compte_dans_capital"]]


def _compte_devise_map(df_comptes: pd.DataFrame) -> dict:
    if df_comptes is None or df_comptes.empty:
        return {}
    if "id" not in df_comptes.columns or "devise" not in df_comptes.columns:
        return {}
    comptes = df_comptes.copy()
    comptes["id"] = comptes["id"].astype(str).str.strip()
    comptes["devise"] = comptes["devise"].astype(str).str.upper().str.strip()
    return comptes.set_index("id")["devise"].to_dict()


def _compte_pays_map(df_comptes: pd.DataFrame) -> dict:
    if df_comptes is None or df_comptes.empty:
        return {}
    if "id" not in df_comptes.columns or "pays" not in df_comptes.columns:
        return {}
    comptes = df_comptes.copy()
    comptes["id"] = comptes["id"].astype(str).str.strip()
    return comptes.set_index("id")["pays"].to_dict()


def _sort_mouvements(df: pd.DataFrame) -> pd.DataFrame:
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.sort_values("date", ascending=True, na_position="first")


def _consume_eur_lots(lots: list[dict], montant_eur: float) -> float:
    """Débite des lots EUR existants en FIFO et renvoie la valeur GNF retirée."""
    montant_restant = float(montant_eur)
    valeur_retiree = 0.0

    for lot in lots:
        if montant_restant <= 0:
            break
        if lot["amount_eur"] <= 0:
            continue

        prise = min(montant_restant, lot["amount_eur"])
        valeur_retiree += prise * lot["taux"]
        lot["amount_eur"] -= prise
        montant_restant -= prise

    return valeur_retiree


def _move_eur_lots(lots: list[dict], compte_source_id: str, compte_destination_id: str, montant_eur: float) -> float:
    """Déplace des lots EUR entre comptes et renvoie leur valeur GNF historique."""
    montant_restant = float(montant_eur)
    valeur_deplacee = 0.0
    nouveaux_lots: list[dict] = []

    for lot in lots:
        if montant_restant <= 0:
            break
        if lot["account_id"] != compte_source_id or lot["amount_eur"] <= 0:
            continue

        prise = min(montant_restant, lot["amount_eur"])
        valeur_deplacee += prise * lot["taux"]
        lot["amount_eur"] -= prise
        montant_restant -= prise
        nouveaux_lots.append({
            "account_id": compte_destination_id,
            "amount_eur": prise,
            "taux": lot["taux"],
        })

    lots.extend(nouveaux_lots)
    return valeur_deplacee


def _simulate_account_values(df_mvt: pd.DataFrame, df_comptes: pd.DataFrame) -> dict[str, float]:
    """Simule la valeur GNF courante par compte, après transferts."""
    if df_mvt is None or df_mvt.empty or df_comptes is None or df_comptes.empty:
        return {}

    devise_map = _compte_devise_map(df_comptes)
    df = df_mvt.copy()
    df["type_mouvement"] = df["type_mouvement"].astype(str).str.lower()
    df["devise_origine"] = df["devise_origine"].astype(str).str.upper()
    df["montant_origine"] = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0.0)
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0.0)
    df["taux_eur_gnf"] = pd.to_numeric(df["taux_eur_gnf"], errors="coerce").fillna(0.0)
    df = _sort_mouvements(df)

    values = {str(account_id): 0.0 for account_id in df_comptes["id"].astype(str)}
    lots_eur: list[dict] = []

    for _, row in df.iterrows():
        typ = str(row["type_mouvement"]).lower()
        src_id = str(row.get("compte_source_id", ""))
        dst_id = str(row.get("compte_destination_id", ""))
        src_dev = devise_map.get(src_id, "").upper()
        dst_dev = devise_map.get(dst_id, "").upper()
        devise = str(row.get("devise_origine", "")).upper()
        montant = float(row["montant_origine"])
        montant_gnf = float(row["montant_converti_gnf"])
        taux = float(row["taux_eur_gnf"])

        if typ in ("apport", "ajustement") and dst_id:
            if devise == "EUR" and dst_dev == "EUR":
                values[dst_id] = values.get(dst_id, 0.0) + montant_gnf
                lots_eur.append({"account_id": dst_id, "amount_eur": montant, "taux": taux})
            elif devise == "GNF" and dst_dev == "GNF":
                values[dst_id] = values.get(dst_id, 0.0) + montant

        elif typ == "transfert" and src_id and dst_id:
            if src_dev == "EUR" and dst_dev == "GNF":
                valeur_sortie = _move_eur_lots(lots_eur, src_id, dst_id, montant)
                values[src_id] = values.get(src_id, 0.0) - valeur_sortie
                values[dst_id] = values.get(dst_id, 0.0) + montant_gnf
            elif src_dev == "EUR" and dst_dev == "EUR":
                valeur_deplacee = _move_eur_lots(lots_eur, src_id, dst_id, montant)
                values[src_id] = values.get(src_id, 0.0) - valeur_deplacee
                values[dst_id] = values.get(dst_id, 0.0) + valeur_deplacee
            elif src_dev == "GNF" and dst_dev == "GNF":
                values[src_id] = values.get(src_id, 0.0) - montant
                values[dst_id] = values.get(dst_id, 0.0) + montant

        elif typ in EXPENSE_TYPES and src_id:
            if src_dev == "EUR":
                values[src_id] = values.get(src_id, 0.0) - _move_eur_lots(lots_eur, src_id, "", montant)
            elif src_dev == "GNF":
                values[src_id] = values.get(src_id, 0.0) - montant

    return {account_id: round(value) for account_id, value in values.items() if round(value) > 0}


def _simulate_capital_positions(df_mvt: pd.DataFrame, df_comptes: pd.DataFrame) -> tuple[list[dict], float]:
    """Simule les positions EUR/GNF en fonction des mouvements et des comptes."""
    if df_mvt is None or df_mvt.empty:
        return [], 0.0

    comptes_map = _compte_devise_map(df_comptes)
    df = df_mvt.copy()
    df["type_mouvement"] = df["type_mouvement"].astype(str).str.lower()
    df["montant_origine"] = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0.0)
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0.0)
    df["taux_eur_gnf"] = pd.to_numeric(df["taux_eur_gnf"], errors="coerce").fillna(0.0)
    df = _sort_mouvements(df)

    lots_eur: list[dict] = []
    solde_gnf = 0.0

    for _, row in df.iterrows():
        typ = str(row["type_mouvement"]).lower()
        src_dev = comptes_map.get(str(row.get("compte_source_id", "")), "").upper()
        dst_dev = comptes_map.get(str(row.get("compte_destination_id", "")), "").upper()

        if typ == "apport":
            if str(row.get("devise_origine", "")).upper() == "EUR":
                if dst_dev == "EUR":
                    lots_eur.append({
                        "amount_eur": float(row["montant_origine"]),
                        "taux": float(row["taux_eur_gnf"]),
                    })
                elif dst_dev == "GNF":
                    solde_gnf += float(row["montant_converti_gnf"])
            elif str(row.get("devise_origine", "")).upper() == "GNF":
                solde_gnf += float(row["montant_origine"])

        elif typ == "transfert":
            if src_dev == "EUR" and dst_dev == "GNF":
                _consume_eur_lots(lots_eur, float(row["montant_origine"]))
                solde_gnf += float(row["montant_converti_gnf"])
            elif src_dev == "EUR" and dst_dev == "EUR":
                # Transfert interne en EUR : aucune variation de capital.
                pass
            elif src_dev == "GNF" and dst_dev == "GNF":
                # Transfert interne en GNF : aucune variation de capital.
                pass
            elif src_dev == "GNF" and dst_dev == "EUR":
                solde_gnf -= float(row["montant_origine"])
                if row["taux_eur_gnf"] > 0:
                    lots_eur.append({
                        "amount_eur": float(row["montant_converti_gnf"]),
                        "taux": float(row["taux_eur_gnf"]),
                    })

        elif typ in EXPENSE_TYPES:
            if src_dev == "EUR":
                _consume_eur_lots(lots_eur, float(row["montant_origine"]))
            elif src_dev == "GNF":
                solde_gnf -= float(row["montant_origine"])

        elif typ == "ajustement":
            if str(row.get("devise_origine", "")).upper() == "EUR" and dst_dev == "EUR":
                lots_eur.append({
                    "amount_eur": float(row["montant_origine"]),
                    "taux": float(row["taux_eur_gnf"]),
                })
            elif str(row.get("devise_origine", "")).upper() == "GNF":
                solde_gnf += float(row["montant_origine"])

    return lots_eur, solde_gnf


def _capital_breakdown(df_mvt: pd.DataFrame, df_comptes: pd.DataFrame) -> dict:
    lots_eur, solde_gnf = _simulate_capital_positions(df_mvt, df_comptes)
    total_eur = sum(max(0.0, lot["amount_eur"]) for lot in lots_eur)
    valorisation_eur = sum(max(0.0, lot["amount_eur"]) * lot["taux"] for lot in lots_eur)

    return {
        "total_eur": float(total_eur),
        "total_gnf": float(solde_gnf),
        "valorisation_eur_gnf": float(valorisation_eur),
        "capital_total": float(solde_gnf + valorisation_eur),
    }


def calculer_capital_breakdown(df_mvt: pd.DataFrame, df_comptes: pd.DataFrame) -> dict:
    return _capital_breakdown(df_mvt, df_comptes)


def valeurs_par_compte(df_mvt: pd.DataFrame, df_comptes: pd.DataFrame) -> pd.DataFrame:
    """Retourne la valeur courante de chaque compte en GNF de reporting."""
    if df_comptes is None or df_comptes.empty:
        return pd.DataFrame(columns=["id", "nom", "pays", "devise", "type_compte", "valeur_gnf"])

    comptes = df_comptes.copy()
    values = _simulate_account_values(df_mvt, df_comptes)
    comptes["valeur_gnf"] = comptes["id"].astype(str).map(values).fillna(0.0)
    return comptes[["id", "nom", "pays", "devise", "type_compte", "valeur_gnf"]]


def calculer_capital_total(df_mvt: pd.DataFrame, df_comptes: pd.DataFrame | None = None) -> float:
    """
    Capital = valeur de reporting GNF des positions réelles en EUR et GNF.
    Les apports en EUR non transférés restent en EUR, valorisés en GNF.
    Les transferts EUR→GNF mettent à jour le reporting selon le taux réel saisi.
    """
    if df_mvt is None or df_mvt.empty:
        return 0.0

    if df_comptes is None or df_comptes.empty:
        df = _mouvements_actifs(df_mvt)
        if df.empty:
            return 0.0
        df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
        apports = df[df["type_mouvement"] == "apport"]["montant_converti_gnf"].sum()
        retraits = df[df["type_mouvement"].isin(EXPENSE_TYPES)]["montant_converti_gnf"].sum()
        return float(apports - retraits)

    breakdown = _capital_breakdown(df_mvt, df_comptes)
    return breakdown["capital_total"]


def calculer_capital_a_date(df_mvt: pd.DataFrame, target_date: str, df_comptes: pd.DataFrame | None = None) -> float:
    """Capital cumulé jusqu'à une date donnée (incluse)."""
    if df_mvt is None or df_mvt.empty:
        return 0.0
    df = df_mvt.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["date"] <= pd.Timestamp(target_date)]
    return calculer_capital_total(df, df_comptes)


# ── Parts par investisseur ────────────────────────────────────────────────────

def parts_par_investisseur(
    df_mvt: pd.DataFrame,
    df_inv: pd.DataFrame,
) -> pd.DataFrame:
    """
    Renvoie un DataFrame avec :
      investisseur_id, nom, apports_gnf, retraits_gnf, net_gnf, part_pct
    """
    if df_mvt is None or df_mvt.empty:
        return pd.DataFrame(
            columns=["investisseur_id", "nom", "apports_gnf", "retraits_gnf", "net_gnf", "part_pct"]
        )

    df = _mouvements_actifs(df_mvt).copy()
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)

    apports = (
        df[df["type_mouvement"] == "apport"]
        .groupby("investisseur_id")["montant_converti_gnf"]
        .sum()
        .rename("apports_gnf")
    )
    retraits = (
        df[df["type_mouvement"].isin(EXPENSE_TYPES)]
        .groupby("investisseur_id")["montant_converti_gnf"]
        .sum()
        .rename("retraits_gnf")
    )

    result = pd.concat([apports, retraits], axis=1).fillna(0).reset_index()
    result.columns = ["investisseur_id", "apports_gnf", "retraits_gnf"]
    result["net_gnf"] = result["apports_gnf"] - result["retraits_gnf"]

    total = result["net_gnf"].sum()
    result["part_pct"] = (result["net_gnf"] / total * 100).round(2) if total > 0 else 0.0

    # Jointure avec les noms des investisseurs
    if df_inv is not None and not df_inv.empty:
        noms = df_inv[["id", "nom"]].rename(columns={"id": "investisseur_id"})
        result = result.merge(noms, on="investisseur_id", how="left")
        result["nom"] = result["nom"].fillna(result["investisseur_id"])
    else:
        result["nom"] = result["investisseur_id"]

    return result[["investisseur_id", "nom", "apports_gnf", "retraits_gnf", "net_gnf", "part_pct"]].sort_values(
        "net_gnf", ascending=False
    )


def apports_par_devise_investisseur(df_mvt: pd.DataFrame, df_inv: pd.DataFrame) -> pd.DataFrame:
    """Synthèse des apports natifs EUR/GNF par investisseur."""
    columns = [
        "investisseur_id", "nom", "apports_eur", "apports_gnf_nat",
        "apports_equiv_gnf", "part_pct",
    ]
    if df_mvt is None or df_mvt.empty:
        return pd.DataFrame(columns=columns)

    df = _mouvements_actifs(df_mvt).copy()
    df["type_mouvement"] = df["type_mouvement"].astype(str).str.lower()
    df = df[df["type_mouvement"] == "apport"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    df["devise_origine"] = df["devise_origine"].astype(str).str.upper()
    df["montant_origine"] = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0.0)
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0.0)
    df["apports_eur"] = df.apply(
        lambda row: row["montant_origine"] if row["devise_origine"] == "EUR" else 0.0,
        axis=1,
    )
    df["apports_gnf_nat"] = df.apply(
        lambda row: row["montant_origine"] if row["devise_origine"] == "GNF" else 0.0,
        axis=1,
    )

    result = (
        df.groupby("investisseur_id")[["apports_eur", "apports_gnf_nat", "montant_converti_gnf"]]
        .sum()
        .reset_index()
        .rename(columns={"montant_converti_gnf": "apports_equiv_gnf"})
    )
    total = result["apports_equiv_gnf"].sum()
    result["part_pct"] = (result["apports_equiv_gnf"] / total * 100).round(2) if total > 0 else 0.0

    if df_inv is not None and not df_inv.empty:
        noms = df_inv[["id", "nom"]].rename(columns={"id": "investisseur_id"})
        result = result.merge(noms, on="investisseur_id", how="left")
        result["nom"] = result["nom"].fillna(result["investisseur_id"])
    else:
        result["nom"] = result["investisseur_id"]

    return result[columns].sort_values("apports_equiv_gnf", ascending=False)


def evolution_apports_par_investisseur(df_mvt: pd.DataFrame, df_inv: pd.DataFrame) -> pd.DataFrame:
    """Évolution cumulée des apports natifs EUR et équivalent GNF par investisseur."""
    columns = ["date", "investisseur_id", "nom", "apports_eur_cumule", "apports_gnf_cumule"]
    if df_mvt is None or df_mvt.empty:
        return pd.DataFrame(columns=columns)

    df = _mouvements_actifs(df_mvt).copy()
    df["type_mouvement"] = df["type_mouvement"].astype(str).str.lower()
    df = df[df["type_mouvement"] == "apport"]
    if df.empty:
        return pd.DataFrame(columns=columns)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.normalize()
    df["devise_origine"] = df["devise_origine"].astype(str).str.upper()
    df["montant_origine"] = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0.0)
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0.0)
    df["apport_eur"] = df.apply(
        lambda row: row["montant_origine"] if row["devise_origine"] == "EUR" else 0.0,
        axis=1,
    )

    daily = (
        df.groupby(["date", "investisseur_id"])[["apport_eur", "montant_converti_gnf"]]
        .sum()
        .reset_index()
        .sort_values(["investisseur_id", "date"])
    )
    daily["apports_eur_cumule"] = daily.groupby("investisseur_id")["apport_eur"].cumsum()
    daily["apports_gnf_cumule"] = daily.groupby("investisseur_id")["montant_converti_gnf"].cumsum()

    if df_inv is not None and not df_inv.empty:
        noms = df_inv[["id", "nom"]].rename(columns={"id": "investisseur_id"})
        daily = daily.merge(noms, on="investisseur_id", how="left")
        daily["nom"] = daily["nom"].fillna(daily["investisseur_id"])
    else:
        daily["nom"] = daily["investisseur_id"]

    return daily[columns].sort_values(["nom", "date"])


# ── Suivi par apport ─────────────────────────────────────────────────────────

def get_apports_disponibles(df_mvt: pd.DataFrame) -> pd.DataFrame:
    """Retourne les apports EUR ayant encore un solde à transférer."""
    if df_mvt is None or df_mvt.empty:
        return pd.DataFrame()

    df = df_mvt.copy()
    df["montant_origine"] = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0)
    df["apport_source_id"] = df["apport_source_id"].astype(str).str.strip() if "apport_source_id" in df.columns else ""

    apports = df[
        (df["type_mouvement"] == "apport") &
        (df["devise_origine"].astype(str).str.upper() == "EUR")
    ].copy()

    if apports.empty:
        return pd.DataFrame()

    transferts = df[
        (df["type_mouvement"] == "transfert") &
        (df["apport_source_id"] != "")
    ]
    if not transferts.empty:
        eur_transfere = transferts.groupby("apport_source_id")["montant_origine"].sum().rename("eur_transfere")
        apports = apports.join(eur_transfere, on="id", how="left")
    else:
        apports["eur_transfere"] = 0.0

    apports["eur_transfere"] = pd.to_numeric(apports["eur_transfere"], errors="coerce").fillna(0.0)
    apports["eur_restant"] = apports["montant_origine"] - apports["eur_transfere"]
    return apports[apports["eur_restant"] > 0.01].copy()


def get_frais_retrait_cash(nom_compte: str, montant_gnf: float) -> tuple:
    """
    Retourne (taux, frais_gnf) pour un retrait cash selon le barème de l'opérateur.
    Retourne (None, None) si hors tranche ou aucun barème pour ce compte.
    """
    for min_m, max_m, taux in FRAIS_RETRAIT_BAREME.get(nom_compte, []):
        if min_m <= montant_gnf <= max_m:
            return taux, round(montant_gnf * taux)
    return None, None


def get_transferts_gnf_sur_compte(compte_id: str, df_mvt: pd.DataFrame) -> pd.DataFrame:
    """Retourne les transferts EUR→GNF reçus sur un compte GNF, avec leur apport source."""
    if df_mvt is None or df_mvt.empty or not compte_id:
        return pd.DataFrame()

    df = df_mvt.copy()
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
    if "apport_source_id" not in df.columns:
        return pd.DataFrame()
    df["apport_source_id"] = df["apport_source_id"].astype(str).str.strip()

    return df[
        (df["type_mouvement"] == "transfert") &
        (df["compte_destination_id"].astype(str).str.strip() == str(compte_id)) &
        (df["devise_origine"].astype(str).str.upper() == "EUR") &
        (~df["apport_source_id"].isin(["", "nan", "None"]))
    ].copy()


def calcul_valeur_apport(apport_id: str, df_mvt: pd.DataFrame) -> dict:
    """Valorisation détaillée d'un apport : cristallisé + estimé + frais."""
    if df_mvt is None or df_mvt.empty:
        return {}

    df = df_mvt.copy()
    df["montant_origine"] = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0)
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
    df["taux_eur_gnf"] = pd.to_numeric(df["taux_eur_gnf"], errors="coerce").fillna(0)
    df["apport_source_id"] = df["apport_source_id"].astype(str).str.strip() if "apport_source_id" in df.columns else ""

    apport_rows = df[df["id"] == apport_id]
    if apport_rows.empty:
        return {}
    apport = apport_rows.iloc[0]
    eur_initial = float(apport["montant_origine"])
    taux_estimatif = float(apport["taux_eur_gnf"])

    linked_transfers = df[(df["apport_source_id"] == apport_id) & (df["type_mouvement"] == "transfert")]
    eur_transfere = float(linked_transfers["montant_origine"].sum())
    gnf_cristallise = float(linked_transfers["montant_converti_gnf"].sum())

    linked_frais = df[(df["apport_source_id"] == apport_id) & (df["type_mouvement"] == "frais_retrait")]
    frais_gnf = float(linked_frais["montant_converti_gnf"].sum())

    eur_restant = max(0.0, eur_initial - eur_transfere)
    gnf_estime_restant = eur_restant * taux_estimatif
    valeur_totale_gnf = gnf_cristallise + gnf_estime_restant

    return {
        "apport_id": apport_id,
        "investisseur_id": str(apport["investisseur_id"]),
        "date": str(apport.get("date", "")),
        "compte_destination_id": str(apport.get("compte_destination_id", "")),
        "eur_initial": eur_initial,
        "taux_estimatif": taux_estimatif,
        "eur_transfere": eur_transfere,
        "eur_restant": eur_restant,
        "gnf_cristallise": gnf_cristallise,
        "gnf_estime_restant": gnf_estime_restant,
        "valeur_totale_gnf": valeur_totale_gnf,
        "frais_gnf": frais_gnf,
        "valeur_nette_gnf": valeur_totale_gnf - frais_gnf,
        "pct_transfere": (eur_transfere / eur_initial * 100) if eur_initial > 0 else 0.0,
        "commentaire": str(apport.get("commentaire", "")),
    }


def detail_par_investisseur(df_mvt: pd.DataFrame, df_inv: pd.DataFrame) -> pd.DataFrame:
    """
    Valorisation agrégée par investisseur basée sur les apports et leurs transferts liés.
    Utilise le taux réel pour les portions transférées, l'estimatif pour le reste.
    """
    if df_mvt is None or df_mvt.empty:
        return pd.DataFrame()

    df = df_mvt.copy()
    df["montant_origine"] = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0)
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
    df["taux_eur_gnf"] = pd.to_numeric(df["taux_eur_gnf"], errors="coerce").fillna(0)

    apports = df[
        (df["type_mouvement"] == "apport") &
        (df["devise_origine"].astype(str).str.upper() == "EUR")
    ]
    if apports.empty:
        return pd.DataFrame()

    rows = [calcul_valeur_apport(str(a["id"]), df) for _, a in apports.iterrows()]
    rows = [r for r in rows if r]
    if not rows:
        return pd.DataFrame()

    df_vals = pd.DataFrame(rows)
    result = (
        df_vals.groupby("investisseur_id")
        .agg(
            eur_initial=("eur_initial", "sum"),
            eur_transfere=("eur_transfere", "sum"),
            eur_restant=("eur_restant", "sum"),
            gnf_cristallise=("gnf_cristallise", "sum"),
            gnf_estime_restant=("gnf_estime_restant", "sum"),
            valeur_totale_gnf=("valeur_totale_gnf", "sum"),
            frais_gnf=("frais_gnf", "sum"),
            valeur_nette_gnf=("valeur_nette_gnf", "sum"),
        )
        .reset_index()
    )

    # Gain/perte taux = GNF cristallisé - (EUR transféré × taux estimatif moyen)
    # On calcule le gain par apport pour être précis
    gains = []
    for _, a in apports.iterrows():
        v = calcul_valeur_apport(str(a["id"]), df)
        if v and v["eur_transfere"] > 0:
            gains.append({
                "investisseur_id": v["investisseur_id"],
                "gain": v["gnf_cristallise"] - (v["eur_transfere"] * v["taux_estimatif"]),
            })
    if gains:
        df_gains = pd.DataFrame(gains).groupby("investisseur_id")["gain"].sum().reset_index().rename(columns={"gain": "gain_taux_gnf"})
        result = result.merge(df_gains, on="investisseur_id", how="left")
    else:
        result["gain_taux_gnf"] = 0.0
    result["gain_taux_gnf"] = result["gain_taux_gnf"].fillna(0.0)

    total = result["valeur_totale_gnf"].sum()
    result["part_pct"] = (result["valeur_totale_gnf"] / total * 100).round(2) if total > 0 else 0.0

    if df_inv is not None and not df_inv.empty:
        noms = df_inv[["id", "nom"]].rename(columns={"id": "investisseur_id"})
        result = result.merge(noms, on="investisseur_id", how="left")
        result["nom"] = result["nom"].fillna(result["investisseur_id"])
    else:
        result["nom"] = result["investisseur_id"]

    return result.sort_values("valeur_totale_gnf", ascending=False)


# ── Répartition par pays ──────────────────────────────────────────────────────

def repartition_par_pays(df_mvt: pd.DataFrame, df_comptes: pd.DataFrame) -> pd.DataFrame:
    """
    Répartition du capital par pays selon le compte de destination.
    Prend en compte les apports EUR valorisés ainsi que les transferts EUR→GNF.
    """
    if df_mvt is None or df_mvt.empty or df_comptes is None or df_comptes.empty:
        return pd.DataFrame(columns=["pays", "montant_gnf", "part_pct"])

    comptes_map = _compte_pays_map(df_comptes)
    account_values = _simulate_account_values(df_mvt, df_comptes)
    rows = [
        {"pays": comptes_map.get(account_id, "Non spécifié"), "montant_gnf": value}
        for account_id, value in account_values.items()
    ]

    if not rows:
        return pd.DataFrame(columns=["pays", "montant_gnf", "part_pct"])

    df_result = pd.DataFrame(rows)
    result = (
        df_result.groupby("pays")["montant_gnf"]
        .sum()
        .reset_index()
    )
    total = result["montant_gnf"].sum()
    result["part_pct"] = (result["montant_gnf"] / total * 100).round(2) if total > 0 else 0.0
    return result.sort_values("montant_gnf", ascending=False)


# ── Répartition par devise ────────────────────────────────────────────────────

def repartition_par_devise(df_mvt: pd.DataFrame, df_comptes: pd.DataFrame) -> pd.DataFrame:
    """Répartition des fonds selon la devise des comptes courants."""
    if df_mvt is None or df_mvt.empty or df_comptes is None or df_comptes.empty:
        return pd.DataFrame(columns=["devise", "montant_gnf", "part_pct"])

    comptes_map = _compte_devise_map(df_comptes)
    account_values = _simulate_account_values(df_mvt, df_comptes)
    rows = [
        {"devise": comptes_map.get(account_id, "Non spécifié"), "montant_gnf": value}
        for account_id, value in account_values.items()
    ]

    if not rows:
        return pd.DataFrame(columns=["devise", "montant_gnf", "part_pct"])

    df_result = pd.DataFrame(rows)
    result = (
        df_result.groupby("devise")["montant_gnf"]
        .sum()
        .reset_index()
    )
    total = result["montant_gnf"].sum()
    result["part_pct"] = (result["montant_gnf"] / total * 100).round(2) if total > 0 else 0.0
    return result.sort_values("montant_gnf", ascending=False)


# ── Solde par compte ──────────────────────────────────────────────────────────

def soldes_par_compte(df_mvt: pd.DataFrame, df_comptes: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule le solde natif de chaque compte en tenant compte de tous les mouvements.
    Pour les comptes EUR, le solde est en EUR. Pour les comptes GNF, le solde est en GNF.
    Retourne un DataFrame avec colonnes : id, nom, pays, devise, solde_gnf.
    """
    if df_comptes is None or df_comptes.empty:
        return pd.DataFrame()

    comptes = df_comptes[["id", "nom", "pays", "devise", "actif"]].copy()
    comptes["solde_gnf"] = 0.0

    if df_mvt is None or df_mvt.empty:
        return comptes

    df = df_mvt.copy()
    df["montant_origine"] = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0)
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
    comptes_map = _compte_devise_map(df_comptes)

    for idx, cpt in comptes.iterrows():
        cid = cpt["id"]
        devise = str(cpt["devise"]).upper()

        if devise == "EUR":
            credits = df[
                (df["compte_destination_id"] == cid)
                & df["type_mouvement"].isin(["apport", "transfert"])
                & (df["devise_origine"].astype(str).str.upper() == "EUR")
            ]["montant_origine"].sum()
            debits = df[
                (df["compte_source_id"] == cid)
                & df["type_mouvement"].isin(["retrait", "depense", "transfert"])
                & (df["devise_origine"].astype(str).str.upper() == "EUR")
            ]["montant_origine"].sum()
        else:
            credits = df[(df["compte_destination_id"] == cid) & df["type_mouvement"].isin(["apport", "transfert"])].apply(
                lambda row: float(row["montant_converti_gnf"]) if str(row["devise_origine"]).upper() == "EUR" else float(row["montant_origine"]),
                axis=1,
            ).sum()
            debits = df[(df["compte_source_id"] == cid) & df["type_mouvement"].isin(["retrait", "depense", "transfert", "frais_retrait"])].apply(
                lambda row: float(row["montant_origine"]) if str(row["devise_origine"]).upper() == "GNF" else float(row["montant_converti_gnf"]),
                axis=1,
            ).sum()

        comptes.at[idx, "solde_gnf"] = credits - debits

    return comptes


def repartition_investisseurs_par_compte(
    df_mvt: pd.DataFrame,
    df_comptes: pd.DataFrame,
    df_inv: pd.DataFrame,
) -> pd.DataFrame:
    """
    Pour chaque compte, répartit le solde natif (EUR ou GNF) par investisseur
    d'après les mouvements qui lui sont rattachés (crédits - débits), en
    reprenant la même logique de valorisation que soldes_par_compte().

    Retourne un DataFrame avec colonnes :
      compte_id, compte_nom, devise, investisseur_id, investisseur_nom, montant, pct
    """
    cols = ["compte_id", "compte_nom", "devise", "investisseur_id", "investisseur_nom", "montant", "pct"]
    if df_comptes is None or df_comptes.empty or df_mvt is None or df_mvt.empty:
        return pd.DataFrame(columns=cols)

    df = df_mvt.copy()
    df["montant_origine"] = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0)
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
    df["investisseur_id"] = df["investisseur_id"].fillna("").astype(str)

    noms_inv = {}
    if df_inv is not None and not df_inv.empty:
        noms_inv = df_inv.set_index("id")["nom"].to_dict()

    rows = []
    for _, cpt in df_comptes.iterrows():
        cid = cpt["id"]
        devise = str(cpt["devise"]).upper()

        if devise == "EUR":
            df_credit = df[
                (df["compte_destination_id"] == cid)
                & df["type_mouvement"].isin(["apport", "transfert"])
                & (df["devise_origine"].astype(str).str.upper() == "EUR")
            ]
            credits = df_credit.groupby("investisseur_id")["montant_origine"].sum()
            df_debit = df[
                (df["compte_source_id"] == cid)
                & df["type_mouvement"].isin(["retrait", "depense", "transfert"])
                & (df["devise_origine"].astype(str).str.upper() == "EUR")
            ]
            debits = df_debit.groupby("investisseur_id")["montant_origine"].sum()
        else:
            df_credit = df[(df["compte_destination_id"] == cid) & df["type_mouvement"].isin(["apport", "transfert"])].copy()
            df_credit["_montant"] = df_credit.apply(
                lambda row: float(row["montant_converti_gnf"]) if str(row["devise_origine"]).upper() == "EUR" else float(row["montant_origine"]),
                axis=1,
            )
            credits = df_credit.groupby("investisseur_id")["_montant"].sum()

            df_debit = df[(df["compte_source_id"] == cid) & df["type_mouvement"].isin(["retrait", "depense", "transfert", "frais_retrait"])].copy()
            df_debit["_montant"] = df_debit.apply(
                lambda row: float(row["montant_origine"]) if str(row["devise_origine"]).upper() == "GNF" else float(row["montant_converti_gnf"]),
                axis=1,
            )
            debits = df_debit.groupby("investisseur_id")["_montant"].sum()

        net = credits.sub(debits, fill_value=0)
        net = net[net.abs() > 0.01]
        total = net.sum()

        for inv_id, montant in net.sort_values(ascending=False).items():
            pct = (montant / total * 100) if total else 0.0
            rows.append({
                "compte_id": cid,
                "compte_nom": cpt["nom"],
                "devise": devise,
                "investisseur_id": inv_id,
                "investisseur_nom": noms_inv.get(inv_id, inv_id) if inv_id else "Non attribué",
                "montant": montant,
                "pct": pct,
            })

    return pd.DataFrame(rows, columns=cols)


# ── Progression objectifs ─────────────────────────────────────────────────────

def progression_objectifs(
    df_objectifs: pd.DataFrame, capital_actuel: float
) -> pd.DataFrame:
    """
    Ajoute les colonnes progress_pct, reste_gnf, atteint pour chaque objectif.

    Un objectif clôturé (colonne "cloture" == "True") n'utilise plus le capital
    actuel en direct : sa progression reste figée sur le capital enregistré au
    moment de la clôture ("capital_gele_gnf"), pour que les apports ultérieurs
    n'augmentent plus artificiellement un objectif déjà refermé.
    """
    if df_objectifs is None or df_objectifs.empty:
        return pd.DataFrame()

    df = df_objectifs.copy()
    df["montant_cible_gnf"] = pd.to_numeric(df["montant_cible_gnf"], errors="coerce").fillna(0)

    if "cloture" in df.columns:
        est_cloture = df["cloture"].astype(str).str.lower() == "true"
    else:
        est_cloture = pd.Series(False, index=df.index)
    capital_gele = pd.to_numeric(df.get("capital_gele_gnf", 0), errors="coerce").fillna(0)
    df["capital_effectif"] = capital_gele.where(est_cloture, capital_actuel)

    df["progress_pct"] = (df["capital_effectif"] / df["montant_cible_gnf"] * 100).clip(upper=100).round(2)
    df["reste_gnf"]    = (df["montant_cible_gnf"] - df["capital_effectif"]).clip(lower=0)
    df["atteint"]      = df["capital_effectif"] >= df["montant_cible_gnf"]
    return df


# ── Effort et statut par objectif ────────────────────────────────────────────

def calculer_effort_objectif(
    capital_actuel: float,
    montant_cible_gnf: float,
    date_cible: str,
) -> dict:
    """
    Calcule l'effort nécessaire pour atteindre un objectif donné.

    Retourne un dict avec :
      - reste_gnf            : montant encore à réunir
      - jours_restants       : jours entre aujourd'hui et date_cible
      - progress_pct         : pourcentage de progression (0-100)
      - effort_mensuel       : apport mensuel moyen nécessaire
      - effort_hebdomadaire  : apport hebdomadaire moyen nécessaire
      - statut               : texte lisible + emoji
      - couleur_statut       : "green" / "blue" / "amber" / "red"
    """
    cible = float(montant_cible_gnf) if montant_cible_gnf else 0.0
    capital = float(capital_actuel) if capital_actuel else 0.0

    reste_gnf = max(0.0, cible - capital)
    progress_pct = min((capital / cible * 100) if cible > 0 else 0.0, 100.0)

    try:
        dc = pd.Timestamp(date_cible).date()
        jours_restants = (dc - date.today()).days
    except Exception:
        jours_restants = 0

    if reste_gnf <= 0:
        return {
            "reste_gnf": 0.0,
            "jours_restants": jours_restants,
            "progress_pct": progress_pct,
            "effort_mensuel": 0.0,
            "effort_hebdomadaire": 0.0,
            "effort_journalier": 0.0,
            "statut": "Atteint ✅",
            "couleur_statut": "green",
        }

    mois_restants = max(jours_restants / 30.0, 0.01)
    semaines_restantes = max(jours_restants / 7.0, 0.01)
    jours_pour_calcul = max(jours_restants, 0.01)
    effort_mensuel = reste_gnf / mois_restants if mois_restants > 0 else 0.0
    effort_hebdomadaire = reste_gnf / semaines_restantes if semaines_restantes > 0 else 0.0
    effort_journalier = reste_gnf / jours_pour_calcul

    # Statut basé sur progression % ET jours restants (l'échéance prime toujours)
    if jours_restants < 0:
        statut, couleur = "Échéance dépassée 🔴", "red"
    elif jours_restants < 30:
        statut, couleur = "Urgent 🔴", "red"
    elif progress_pct >= 70 and jours_restants >= 90:
        statut, couleur = "Bien avancé 🟢", "green"
    elif progress_pct >= 70:
        statut, couleur = "À accélérer 🟡", "amber"
    elif progress_pct >= 45 and jours_restants >= 90:
        statut, couleur = "En bonne voie 🔵", "blue"
    elif progress_pct >= 45:
        statut, couleur = "À surveiller 🟡", "amber"
    elif jours_restants < 90:
        statut, couleur = "En retard 🔴", "red"
    else:
        statut, couleur = "À surveiller 🟡", "amber"

    return {
        "reste_gnf": reste_gnf,
        "jours_restants": jours_restants,
        "progress_pct": round(progress_pct, 2),
        "effort_mensuel": round(effort_mensuel),
        "effort_hebdomadaire": round(effort_hebdomadaire),
        "effort_journalier": round(effort_journalier),
        "statut": statut,
        "couleur_statut": couleur,
    }


# ── Paliers de capital — section « Suivi des objectifs » ──────────────────────
# Logique centralisée pour les 5 paliers fixes (utils.config.PALIERS_CAPITAL) :
# progression, effort mensuel, date prévisionnelle déduite du rythme réel
# d'apport, écart planning et statut dynamique. Toutes les fonctions ci-dessous
# ne font que lire les mouvements existants — aucune valeur n'est inventée.

JOURS_PAR_MOIS = 30.44  # moyenne calendaire, évite le biais des mois à 28-31 jours

# Tolérances (jours) utilisées pour classer l'écart entre la date prévisionnelle
# et la date cible dans le statut dynamique. Ajustable si le rythme du projet
# change, sans toucher à la logique de calcul elle-même.
TOLERANCE_AVANCE_JOURS = 30      # écart ≤ -30 j -> "En avance"
TOLERANCE_SURVEILLER_JOURS = 90  # écart > 90 j -> "Fort risque de retard"


def _statut_reel(atteint: bool, jours_restants: int) -> tuple[str, str] | None:
    """
    Statut RÉEL — une situation constatée, jamais une projection.
      - "Atteint ✅" si le capital réel a atteint la cible.
      - "Retard 🔴"  UNIQUEMENT si l'échéance est déjà passée (jours_restants < 0)
        sans que la cible soit atteinte : date_actuelle > date_cible ET
        capital_reel < cible, exactement comme demandé — jamais avant.
      - None si l'objectif est encore en cours (avant l'échéance, pas encore
        atteint) : c'est alors _statut_projection qui prend le relais.
    """
    if atteint:
        return "Atteint ✅", "green"
    if jours_restants < 0:
        return "Retard 🔴", "red"
    return None


def _statut_projection(ecart_jours: int | None) -> tuple[str, str]:
    """
    Statut de PROJECTION — un risque déduit du rythme réel d'apport, jamais une
    situation constatée. N'est utilisé que tant que l'échéance n'est pas
    passée et que la cible n'est pas atteinte (_statut_reel renvoie None).
    "Fort risque de retard" reste une projection : ce n'est PAS "Retard", qui
    ne s'applique qu'après l'échéance réellement dépassée.
    """
    if ecart_jours is None:
        return "Prévision indisponible", "amber"
    if ecart_jours <= -TOLERANCE_AVANCE_JOURS:
        return "En avance 🟢", "green"
    if ecart_jours <= TOLERANCE_AVANCE_JOURS:
        return "Dans le rythme 🟡", "blue"
    if ecart_jours <= TOLERANCE_SURVEILLER_JOURS:
        return "Risque de retard 🟠", "amber"
    return "Fort risque de retard 🔴", "red"


def apport_moyen_mensuel(df_mvt: pd.DataFrame, mois_recul: int = 3) -> float | None:
    """
    Moyenne mensuelle des apports réellement enregistrés, sur les derniers
    `mois_recul` mois calendaires où au moins un apport existe.
    Renvoie None si aucune donnée fiable n'est disponible (jamais de valeur
    inventée) — à afficher comme "Prévision indisponible" côté UI.
    """
    df = _mouvements_actifs(df_mvt)
    if df.empty or "type_mouvement" not in df.columns:
        return None
    df = df[df["type_mouvement"].astype(str).str.lower() == "apport"].copy()
    if df.empty:
        return None
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return None
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0.0)
    par_mois = df.groupby(df["date"].dt.to_period("M"))["montant_converti_gnf"].sum().sort_index()
    par_mois = par_mois.tail(mois_recul)
    if par_mois.empty:
        return None
    moyenne = float(par_mois.mean())
    return moyenne if moyenne > 0 else None


def date_atteinte_palier(
    df_mvt: pd.DataFrame, df_comptes: pd.DataFrame | None, montant_cible: float
) -> date | None:
    """
    Date réelle à laquelle le capital cumulé a franchi `montant_cible`, déduite
    de l'historique des mouvements. None si l'historique ne permet pas de la
    déterminer (jamais de date inventée).
    """
    hist = evolution_capital(df_mvt, df_comptes)
    if hist is None or hist.empty:
        return None
    atteints = hist[hist["capital_cumule"] >= montant_cible]
    if atteints.empty:
        return None
    return pd.Timestamp(atteints.iloc[0]["date"]).date()


def calculer_palier(
    capital_actuel: float,
    montant_cible: float,
    date_cible: str,
    apport_mensuel: float | None,
    apports_prevus_mois: float = 0.0,
) -> dict:
    """
    Calcule tous les indicateurs d'un palier de capital.

    - progress_pct / reste_gnf : progression brute capital_actuel vs cible.
    - effort_mensuel / effort_mode : l'indicateur d'effort change de forme
      selon la proximité de l'échéance (un taux "par mois" n'a aucun sens à
      quelques jours de la cible) :
        * jours_restants >= 30  -> effort_mode="mensuel", effort_mensuel = reste / mois_restants
        * 1 <= jours_restants < 30 -> effort_mode="avant_echeance" (effort_mensuel=None, utiliser reste_gnf)
        * jours_restants == 0   -> effort_mode="aujourdhui" (effort_mensuel=None, utiliser reste_gnf)
        * jours_restants < 0, non atteint -> effort_mode="depasse" (effort_mensuel=None, utiliser reste_gnf)
        * atteint -> effort_mode="atteint"
    - date_previsionnelle : projetée à partir du rythme réel d'apport
      (apport_mensuel). None si ce rythme est inconnu — jamais inventée.
    - ecart_planning_jours : (date_previsionnelle - date_cible), positif =
      retard prévu, négatif = avance prévue sur le planning.
    - statut/couleur_statut : classement dynamique combinant l'atteinte, le
      dépassement d'échéance et l'écart de planning.
    """
    cible = float(montant_cible) if montant_cible else 0.0
    capital = float(capital_actuel) if capital_actuel else 0.0
    reste = max(0.0, cible - capital)
    progress_pct = min((capital / cible * 100) if cible > 0 else 0.0, 100.0)
    atteint = cible > 0 and capital >= cible

    try:
        dc = pd.Timestamp(date_cible).date()
        jours_restants = (dc - date.today()).days
    except Exception:
        dc = None
        jours_restants = 0

    # Effort nécessaire pour tenir la date cible — la forme de l'indicateur
    # dépend de la proximité de l'échéance ("349 M GNF/mois" à J-2 n'a aucun
    # sens : il ne reste pas un mois entier pour apporter quoi que ce soit).
    if atteint:
        effort_mensuel, effort_mode = 0.0, "atteint"
    elif jours_restants < 0:
        effort_mensuel, effort_mode = None, "depasse"
    elif jours_restants == 0:
        effort_mensuel, effort_mode = None, "aujourdhui"
    elif jours_restants < 30:
        effort_mensuel, effort_mode = None, "avant_echeance"
    else:
        mois_restants = max(jours_restants / JOURS_PAR_MOIS, 1 / JOURS_PAR_MOIS)
        effort_mensuel, effort_mode = reste / mois_restants, "mensuel"

    # Date prévisionnelle d'atteinte, déduite du rythme réel d'apport
    if atteint:
        date_prev = date.today()
    elif not apport_mensuel or apport_mensuel <= 0:
        date_prev = None
    else:
        mois_necessaires = reste / apport_mensuel
        date_prev = date.today() + timedelta(days=mois_necessaires * JOURS_PAR_MOIS)

    # Écart planning : positif = projection après la cible (retard)
    ecart_jours = (date_prev - dc).days if (dc is not None and date_prev is not None) else None

    capital_prevu_fin_mois = capital + float(apports_prevus_mois or 0.0)

    # Statut affiché = statut RÉEL (constaté) s'il y en a un (atteint, ou
    # échéance réellement dépassée) ; sinon statut de PROJECTION (un risque,
    # jamais une lateness constatée) déduit de l'écart avec le rythme réel.
    statut, couleur = _statut_reel(atteint, jours_restants) or _statut_projection(ecart_jours)

    return {
        "capital_actuel": capital,
        "montant_cible": cible,
        "progress_pct": round(progress_pct, 2),
        "reste_gnf": reste,
        "atteint": atteint,
        "date_cible": dc,
        "jours_restants": jours_restants,
        "date_previsionnelle": date_prev,
        "apport_mensuel_moyen": apport_mensuel,
        "effort_mensuel": effort_mensuel,
        "effort_mode": effort_mode,
        "apports_prevus_mois": float(apports_prevus_mois or 0.0),
        "capital_prevu_fin_mois": capital_prevu_fin_mois,
        "ecart_planning_jours": ecart_jours,
        "statut": statut,
        "couleur_statut": couleur,
    }


# ── Plan d'apports prévisionnels — projection distincte du capital réel ───────
# Module 100% GNF : aucune devise étrangère, aucun taux de change, aucune
# conversion. Tout ce bloc lit le capital réel (calculer_capital_total,
# calculer_palier — jamais modifiés ici) et un plan d'apports séparé, déjà
# exprimé en GNF, pour SIMULER une trajectoire. Aucune fonction ci-dessous
# n'écrit de mouvement ni ne modifie le capital réel : le plan reste un
# calcul en lecture seule, à côté.
#
# Anti double-comptage : seuls les mois STRICTEMENT postérieurs au mois
# courant sont sommés comme "apports futurs". Le mois en cours et les mois
# passés sont exclus de la projection — s'ils ont réellement été apportés,
# c'est déjà dans capital_reel_actuel ; sinon, les reprojeter romprait la
# séparation réel/prévisionnel (cf. calculer_palier pour le "réel").

TOLERANCE_PLAN_AVANCE = 30       # date du plan ≥ 30 j avant la cible -> "En avance selon le plan"
TOLERANCE_PLAN_PROCHE = 45       # jusqu'à 45 j après la cible -> "Très proche de l'objectif"
TOLERANCE_PLAN_SURVEILLER = 90   # jusqu'à 90 j après la cible -> "À surveiller"
TOLERANCE_CONFORME_GNF = 1.0     # écart absolu (GNF) toléré comme "Conforme" — absorbe l'arrondi flottant, rien de plus


def _mois_period(valeur) -> "pd.Period | None":
    """Convertit une date/chaîne quelconque en période mensuelle. None si invalide."""
    try:
        ts = pd.Timestamp(valeur)
        if pd.isna(ts):
            return None
        return ts.to_period("M")
    except Exception:
        return None


def _plan_futur(df_plan: pd.DataFrame, aujourdhui: date | None = None) -> pd.DataFrame:
    """
    Lignes du plan (montants en GNF) dont le mois est strictement postérieur
    au mois courant, triées chronologiquement. C'est la seule porte d'entrée
    du plan vers les calculs de projection — elle exclut mécaniquement le
    mois en cours et le passé, ce qui empêche tout double-comptage avec le
    capital réel.
    """
    aujourdhui = aujourdhui or date.today()
    auj_periode = pd.Timestamp(aujourdhui).to_period("M")
    cols = ["mois_periode", "montant_prevu_gnf"]
    if df_plan is None or df_plan.empty:
        return pd.DataFrame(columns=cols)
    df = df_plan.copy()
    df["mois_periode"] = df["mois"].apply(_mois_period)
    df["montant_prevu_gnf"] = pd.to_numeric(df["montant_prevu_gnf"], errors="coerce").fillna(0.0)
    df = df.dropna(subset=["mois_periode"])
    df = df[df["mois_periode"] > auj_periode]
    return df.sort_values("mois_periode")


def capital_previsionnel_a_date(
    capital_reel_actuel: float,
    df_plan: pd.DataFrame,
    date_limite,
    aujourdhui: date | None = None,
) -> float:
    """
    capital_previsionnel = capital_reel_actuel + somme des apports FUTURS
    planifiés en GNF (mois > mois courant) jusqu'à `date_limite` inclus.
    Aucune conversion de devise : le plan est déjà exprimé en GNF. Ne modifie
    jamais capital_reel_actuel.
    """
    limite_periode = _mois_period(date_limite)
    futur = _plan_futur(df_plan, aujourdhui)
    if limite_periode is not None:
        futur = futur[futur["mois_periode"] <= limite_periode]
    somme_gnf = float(futur["montant_prevu_gnf"].sum()) if not futur.empty else 0.0
    return float(capital_reel_actuel) + somme_gnf


def date_selon_plan(
    capital_reel_actuel: float,
    montant_cible: float,
    df_plan: pd.DataFrame,
    aujourdhui: date | None = None,
) -> date | None:
    """
    Première date (premier jour du mois planifié) où le capital simulé —
    capital réel actuel + cumul chronologique des apports GNF futurs
    planifiés — franchit `montant_cible`. None si le planning actuel ne
    permet jamais de l'atteindre : jamais de date inventée ("Non atteint
    avec le planning actuel" côté UI).
    """
    if capital_reel_actuel >= montant_cible:
        return aujourdhui or date.today()
    futur = _plan_futur(df_plan, aujourdhui)
    cumul = float(capital_reel_actuel)
    for _, ligne in futur.iterrows():
        cumul += float(ligne["montant_prevu_gnf"])
        if cumul >= montant_cible:
            return ligne["mois_periode"].to_timestamp().date()
    return None


def calculer_projection_plan(
    capital_reel_actuel: float,
    montant_cible: float,
    date_cible,
    df_plan: pd.DataFrame,
    aujourdhui: date | None = None,
) -> dict:
    """
    Projection d'un palier SELON LE PLAN PERSONNEL (100% GNF) — strictement
    distincte de calculer_palier (rythme réel), jamais utilisée pour décider
    du statut réel "Atteint". Ne fait aucune écriture : simulation en lecture
    seule, aucune notion de devise étrangère.
    """
    try:
        dc = pd.Timestamp(date_cible).date()
    except Exception:
        dc = None

    capital_prevu_echeance = capital_previsionnel_a_date(
        capital_reel_actuel, df_plan, dc if dc is not None else date_cible, aujourdhui,
    )
    ecart_capital = capital_prevu_echeance - float(montant_cible)
    date_plan = date_selon_plan(capital_reel_actuel, montant_cible, df_plan, aujourdhui)

    # Apports prévus (GNF) avant/à l'échéance, et couverture du reste réel par
    # ce seul planning — ecart_capital équivaut exactement à
    # (apports_prevus_avant_echeance - reste), donc jamais recalculé deux fois.
    reste_reel = max(0.0, float(montant_cible) - float(capital_reel_actuel))
    apports_prevus_avant_echeance = capital_prevu_echeance - float(capital_reel_actuel)
    # Plafonnée à 100% comme la barre de progression : au-delà, l'excédent est
    # déjà visible dans "Marge prévisionnelle", pas besoin d'un % à rallonge.
    couverture_plan_pct = min(apports_prevus_avant_echeance / reste_reel * 100, 100.0) if reste_reel > 0 else None

    if date_plan is None:
        statut, couleur = "Non atteint selon le plan 🔴", "red"
    elif dc is None:
        statut, couleur = "À surveiller 🟠", "amber"
    else:
        ecart_jours = (date_plan - dc).days
        if ecart_jours <= -TOLERANCE_PLAN_AVANCE:
            statut, couleur = "En avance selon le plan 🟢", "green"
        elif ecart_jours <= TOLERANCE_PLAN_AVANCE:
            statut, couleur = "Objectif atteint selon le plan ✅", "green"
        elif ecart_jours <= TOLERANCE_PLAN_PROCHE:
            statut, couleur = "Très proche de l'objectif 🟡", "blue"
        elif ecart_jours <= TOLERANCE_PLAN_SURVEILLER:
            statut, couleur = "À surveiller 🟠", "amber"
        else:
            statut, couleur = "Non atteint selon le plan 🔴", "red"

    return {
        "date_selon_plan": date_plan,
        "capital_prevu_echeance": capital_prevu_echeance,
        "ecart_capital_planning": ecart_capital,
        "apports_prevus_avant_echeance": apports_prevus_avant_echeance,
        "couverture_plan_pct": couverture_plan_pct,
        "statut_plan": statut,
        "couleur_statut_plan": couleur,
    }


def total_apports_reels(df_mvt: pd.DataFrame) -> float:
    """Somme brute (GNF) de tous les vrais apports enregistrés, jamais le plan."""
    df = _mouvements_actifs(df_mvt)
    if df.empty:
        return 0.0
    df = df[df["type_mouvement"].astype(str).str.lower() == "apport"]
    return float(pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0.0).sum())


def realise_par_mois(df_mvt: pd.DataFrame) -> pd.Series:
    """Total des vrais apports (GNF) groupés par mois calendaire (index = pd.Period 'M')."""
    df = _mouvements_actifs(df_mvt)
    if df.empty:
        return pd.Series(dtype=float)
    df = df[df["type_mouvement"].astype(str).str.lower() == "apport"].copy()
    if df.empty:
        return pd.Series(dtype=float)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return pd.Series(dtype=float)
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0.0)
    return df.groupby(df["date"].dt.to_period("M"))["montant_converti_gnf"].sum()


# Couleur de badge associée à chaque statut mensuel (cohérent avec les autres
# badges de statut de la page — mêmes 4 couleurs terre/brun existantes).
COULEUR_STATUT_APPORT = {
    "⏳ À venir":      "slate",
    "✅ Conforme":     "green",
    "🟠 Partiel":      "amber",
    "🟢 Dépassé":      "green",
    "🔴 Non réalisé":  "red",
}


def statut_apport_mensuel(
    mois, montant_prevu_gnf: float, montant_reel_gnf: float, aujourdhui: date | None = None,
) -> str:
    """
    Statut d'un apport mensuel planifié, comparé au réel du même mois calendaire :
      - "⏳ À venir"     : mois futur (ou en cours) sans rien reçu pour l'instant.
      - "🔴 Non réalisé" : mois déjà passé, rien reçu.
      - "✅ Conforme"    : réel == prévu (à TOLERANCE_CONFORME_GNF près, pur arrondi flottant).
      - "🟠 Partiel"     : réel < prévu, même de peu — aucune tolérance de pourcentage.
      - "🟢 Dépassé"     : réel > prévu, ou réel reçu sans rien de prévu.
    """
    aujourdhui = aujourdhui or date.today()
    mois_periode = _mois_period(mois)
    auj_periode = pd.Timestamp(aujourdhui).to_period("M")

    if montant_reel_gnf <= 0:
        if mois_periode is not None and mois_periode < auj_periode:
            return "🔴 Non réalisé"
        return "⏳ À venir"

    if montant_prevu_gnf <= 0:
        return "🟢 Dépassé"

    if abs(montant_reel_gnf - montant_prevu_gnf) <= TOLERANCE_CONFORME_GNF:
        return "✅ Conforme"
    return "🟠 Partiel" if montant_reel_gnf < montant_prevu_gnf else "🟢 Dépassé"


def synthese_plan_vs_reel(
    df_plan: pd.DataFrame, df_mvt: pd.DataFrame, aujourdhui: date | None = None,
) -> dict:
    """
    Compare, sur les mois déjà échus uniquement, le plan (GNF) et la réalité.
    taux_realisation = apports_reels / apports_prevus_echus * 100.
    Les mois non échus ne comptent jamais dans "prévu échu" (sinon un planning
    tout juste commencé serait pénalisé pour des mois qui n'ont pas eu lieu).
    """
    aujourdhui = aujourdhui or date.today()
    auj_periode = pd.Timestamp(aujourdhui).to_period("M")

    if df_plan is None or df_plan.empty:
        prevu_echu_gnf = 0.0
    else:
        df = df_plan.copy()
        df["mois_periode"] = df["mois"].apply(_mois_period)
        df["montant_prevu_gnf"] = pd.to_numeric(df["montant_prevu_gnf"], errors="coerce").fillna(0.0)
        echus = df[df["mois_periode"].notna() & (df["mois_periode"] <= auj_periode)]
        prevu_echu_gnf = float(echus["montant_prevu_gnf"].sum())

    reel_gnf = total_apports_reels(df_mvt)
    ecart = reel_gnf - prevu_echu_gnf
    taux_realisation = (reel_gnf / prevu_echu_gnf * 100) if prevu_echu_gnf > 0 else None

    return {
        "prevu_echu_gnf": prevu_echu_gnf,
        "reel_gnf": reel_gnf,
        "ecart_gnf": ecart,
        "taux_realisation_pct": round(taux_realisation, 1) if taux_realisation is not None else None,
    }


# ── Bilan capital ─────────────────────────────────────────────────────────────

def calculer_bilan_capital(
    df_mvt: pd.DataFrame,
    df_cpt: pd.DataFrame,
    df_depenses: pd.DataFrame | None = None,
) -> dict:
    """
    Bilan consolidé du capital pour le Dashboard.

    Le capital_total_valorise est calculé via calculer_capital_total() (simulation
    FIFO avec écarts de taux réels/estimatifs). Chaque dépense au statut "Payé"
    crée un mouvement réel (type "depense") qui réduit déjà le solde du compte
    utilisé — donc les dépenses payées sont déjà comptées dans
    capital_total_valorise. Seules les dépenses encore "en attente" (pas
    encore réellement décaissées) doivent être projetées en plus.

    Retourne :
      - capital_total_valorise         : valeur officielle (= calculer_capital_total),
                                          déjà nette des dépenses payées
      - capital_brut_apporte           : Σ apports (montant_converti_gnf)
      - total_frais                    : Σ frais_retrait (montant_converti_gnf)
      - depenses_construction_payees   : Σ dépenses avec statut "Payé"
      - depenses_construction_total    : Σ toutes dépenses (tous statuts)
      - depenses_construction_attente  : Σ dépenses non encore payées
      - capital_liquide_apres_depenses : capital_total_valorise - depenses_construction_attente
                                          (liquidités projetées une fois les dépenses en
                                          attente réellement décaissées)
    """
    capital_total_valorise = calculer_capital_total(df_mvt, df_cpt)

    if df_mvt is None or df_mvt.empty:
        capital_brut = 0.0
        total_frais = 0.0
    else:
        df = df_mvt.copy()
        df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0.0)
        capital_brut = float(
            df[df["type_mouvement"] == "apport"]["montant_converti_gnf"].sum()
        )
        total_frais = float(
            df[df["type_mouvement"] == "frais_retrait"]["montant_converti_gnf"].sum()
        )

    dep_payees = 0.0
    dep_total = 0.0
    if df_depenses is not None and not df_depenses.empty:
        df_d = df_depenses.copy()
        for c in ("montant_gnf", "frais_gnf", "transport_gnf"):
            df_d[c] = pd.to_numeric(df_d.get(c, 0), errors="coerce").fillna(0.0)
        df_d["_total"] = df_d["montant_gnf"] + df_d["frais_gnf"] + df_d["transport_gnf"]
        dep_total = float(df_d["_total"].sum())
        dep_payees = float(
            df_d[df_d["statut_paiement"].astype(str).str.strip() == "Payé"]["_total"].sum()
        )

    dep_attente = dep_total - dep_payees

    return {
        "capital_total_valorise": capital_total_valorise,
        "capital_brut_apporte": capital_brut,
        "total_frais": total_frais,
        "depenses_construction_payees": dep_payees,
        "depenses_construction_total": dep_total,
        "depenses_construction_attente": dep_attente,
        "capital_liquide_apres_depenses": max(0.0, capital_total_valorise - dep_attente),
    }


# ── Évolution temporelle ──────────────────────────────────────────────────────

def evolution_capital(df_mvt: pd.DataFrame, df_comptes: pd.DataFrame | None = None) -> pd.DataFrame:
    """
    Série temporelle du capital cumulé en valeur de reporting GNF.
    Les apports EUR non transférés restent valorisés, les transferts EUR→GNF font évoluer la valeur réelle.
    Retourne un DataFrame avec colonnes : date, capital_cumule.
    """
    if df_mvt is None or df_mvt.empty:
        return pd.DataFrame(columns=["date", "capital_cumule"])

    df = df_mvt.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return pd.DataFrame(columns=["date", "capital_cumule"])

    if df_comptes is None or df_comptes.empty:
        df = _mouvements_actifs(df).copy()
        df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0)
        df.loc[df["type_mouvement"].isin(EXPENSE_TYPES), "montant_converti_gnf"] *= -1
        daily = df.groupby("date")["montant_converti_gnf"].sum().reset_index()
        daily = daily.sort_values("date")
        daily["capital_cumule"] = daily["montant_converti_gnf"].cumsum()
        return daily[["date", "capital_cumule"]]

    df["type_mouvement"] = df["type_mouvement"].astype(str).str.lower()
    df["montant_origine"] = pd.to_numeric(df["montant_origine"], errors="coerce").fillna(0.0)
    df["montant_converti_gnf"] = pd.to_numeric(df["montant_converti_gnf"], errors="coerce").fillna(0.0)
    df["taux_eur_gnf"] = pd.to_numeric(df["taux_eur_gnf"], errors="coerce").fillna(0.0)
    df = _sort_mouvements(df)

    comptes_map = _compte_devise_map(df_comptes)
    lots_eur: list[dict] = []
    solde_gnf = 0.0
    history = []

    for _, row in df.iterrows():
        typ = str(row["type_mouvement"]).lower()
        src_dev = comptes_map.get(str(row.get("compte_source_id", "")), "").upper()
        dst_dev = comptes_map.get(str(row.get("compte_destination_id", "")), "").upper()

        if typ == "apport":
            if str(row.get("devise_origine", "")).upper() == "EUR":
                if dst_dev == "EUR":
                    lots_eur.append({
                        "amount_eur": float(row["montant_origine"]),
                        "taux": float(row["taux_eur_gnf"]),
                    })
                elif dst_dev == "GNF":
                    solde_gnf += float(row["montant_converti_gnf"])
            elif str(row.get("devise_origine", "")).upper() == "GNF":
                solde_gnf += float(row["montant_origine"])

        elif typ == "transfert":
            if src_dev == "EUR" and dst_dev == "GNF":
                _consume_eur_lots(lots_eur, float(row["montant_origine"]))
                solde_gnf += float(row["montant_converti_gnf"])
            elif src_dev == "EUR" and dst_dev == "EUR":
                pass
            elif src_dev == "GNF" and dst_dev == "GNF":
                pass
            elif src_dev == "GNF" and dst_dev == "EUR":
                solde_gnf -= float(row["montant_origine"])
                if row["taux_eur_gnf"] > 0:
                    lots_eur.append({
                        "amount_eur": float(row["montant_converti_gnf"]),
                        "taux": float(row["taux_eur_gnf"]),
                    })

        elif typ in EXPENSE_TYPES:
            if src_dev == "EUR":
                _consume_eur_lots(lots_eur, float(row["montant_origine"]))
            elif src_dev == "GNF":
                solde_gnf -= float(row["montant_origine"])

        elif typ == "ajustement":
            if str(row.get("devise_origine", "")).upper() == "EUR" and dst_dev == "EUR":
                lots_eur.append({
                    "amount_eur": float(row["montant_origine"]),
                    "taux": float(row["taux_eur_gnf"]),
                })
            elif str(row.get("devise_origine", "")).upper() == "GNF":
                solde_gnf += float(row["montant_origine"])

        total_eur = sum(max(0.0, lot["amount_eur"]) * lot["taux"] for lot in lots_eur)
        history.append({
            "date": row["date"],
            "capital_cumule": float(solde_gnf + total_eur),
        })

    df_history = pd.DataFrame(history)
    if df_history.empty:
        return pd.DataFrame(columns=["date", "capital_cumule"])

    df_history = df_history.groupby("date")["capital_cumule"].last().reset_index()
    return df_history.sort_values("date")
