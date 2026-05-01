"""Logique métier : calculs du capital, parts, soldes, objectifs."""

import pandas as pd
from datetime import date
from utils.config import TAUX_EUR_GNF_DEFAUT, CAPITAL_CIBLE_GNF


# ── Conversion de devises ─────────────────────────────────────────────────────

EXPENSE_TYPES = {"depense", "retrait"}

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
        df[df["type_mouvement"] == "retrait"]
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
            debits = df[(df["compte_source_id"] == cid) & df["type_mouvement"].isin(["retrait", "depense", "transfert"])].apply(
                lambda row: float(row["montant_origine"]) if str(row["devise_origine"]).upper() == "GNF" else float(row["montant_converti_gnf"]),
                axis=1,
            ).sum()

        comptes.at[idx, "solde_gnf"] = credits - debits

    return comptes


# ── Progression objectifs ─────────────────────────────────────────────────────

def progression_objectifs(
    df_objectifs: pd.DataFrame, capital_actuel: float
) -> pd.DataFrame:
    """
    Ajoute les colonnes progress_pct, reste_gnf, atteint pour chaque objectif.
    """
    if df_objectifs is None or df_objectifs.empty:
        return pd.DataFrame()

    df = df_objectifs.copy()
    df["montant_cible_gnf"] = pd.to_numeric(df["montant_cible_gnf"], errors="coerce").fillna(0)
    df["progress_pct"] = (capital_actuel / df["montant_cible_gnf"] * 100).clip(upper=100).round(2)
    df["reste_gnf"]    = (df["montant_cible_gnf"] - capital_actuel).clip(lower=0)
    df["atteint"]      = capital_actuel >= df["montant_cible_gnf"]
    return df


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
