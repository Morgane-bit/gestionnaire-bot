import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# ─────────────────────────────────────────
# UTILISATEURS
# ─────────────────────────────────────────

def get_user(user_id: int):
    result = supabase.table("users").select("*").eq("id", user_id).execute()
    return result.data[0] if result.data else None

def create_user(user_id: int, name: str, profile: str):
    supabase.table("users").upsert({
        "id": user_id,
        "name": name,
        "profile": profile
    }).execute()

def update_revenu(user_id: int, revenu: float):
    supabase.table("users").update({
        "revenu_mensuel": revenu
    }).eq("id", user_id).execute()

def get_tous_utilisateurs(profile: str = None):
    query = supabase.table("users").select("*")
    if profile:
        query = query.eq("profile", profile)
    return query.execute().data

# ─────────────────────────────────────────
# DÉPENSES (PARTICULIERS)
# ─────────────────────────────────────────

def save_depense(user_id: int, montant: float, categorie: str, description: str = ""):
    supabase.table("depenses").insert({
        "user_id": user_id,
        "montant": montant,
        "categorie": categorie.lower(),
        "description": description,
        "date": str(date.today())
    }).execute()

def get_depenses_aujourd_hui(user_id: int):
    return supabase.table("depenses")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("date", str(date.today()))\
        .order("created_at", desc=True)\
        .execute().data

def get_depenses_semaine(user_id: int):
    debut = str(date.today() - timedelta(days=7))
    return supabase.table("depenses")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("date", debut)\
        .order("date", desc=True)\
        .execute().data

def get_depenses_mois(user_id: int):
    debut = str(date.today().replace(day=1))
    return supabase.table("depenses")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("date", debut)\
        .execute().data

def get_total_par_categorie(user_id: int, periode: str = "semaine"):
    if periode == "semaine":
        depenses = get_depenses_semaine(user_id)
    else:
        depenses = get_depenses_mois(user_id)

    totaux = {}
    for d in depenses:
        cat = d["categorie"]
        totaux[cat] = totaux.get(cat, 0) + float(d["montant"])
    return dict(sorted(totaux.items(), key=lambda x: x[1], reverse=True))

# ─────────────────────────────────────────
# VENTES (COMMERÇANTS)
# ─────────────────────────────────────────

def save_vente(user_id: int, produit: str, quantite: int, prix_unitaire: float):
    supabase.table("ventes").insert({
        "user_id": user_id,
        "produit": produit.lower(),
        "quantite": quantite,
        "prix_unitaire": prix_unitaire,
        "date": str(date.today())
    }).execute()
    # Diminuer le stock automatiquement
    diminuer_stock(user_id, produit, quantite)

def get_ventes_aujourd_hui(user_id: int):
    return supabase.table("ventes")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("date", str(date.today()))\
        .execute().data

def get_ventes_semaine(user_id: int):
    debut = str(date.today() - timedelta(days=7))
    return supabase.table("ventes")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("date", debut)\
        .execute().data

def get_chiffre_affaires_aujourd_hui(user_id: int):
    ventes = get_ventes_aujourd_hui(user_id)
    return sum(v["quantite"] * v["prix_unitaire"] for v in ventes)

# ─────────────────────────────────────────
# STOCKS (COMMERÇANTS)
# ─────────────────────────────────────────

def save_stock(user_id: int, produit: str, quantite: int, prix_vente: float = 0, seuil: int = 5):
    supabase.table("stocks").upsert({
        "user_id": user_id,
        "produit": produit.lower(),
        "quantite": quantite,
        "prix_vente": prix_vente,
        "seuil_alerte": seuil
    }, on_conflict="user_id,produit").execute()

def get_stocks(user_id: int):
    return supabase.table("stocks")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("produit")\
        .execute().data

def get_stocks_critiques(user_id: int):
    stocks = get_stocks(user_id)
    return [s for s in stocks if s["quantite"] <= s["seuil_alerte"]]

def diminuer_stock(user_id: int, produit: str, quantite: int):
    result = supabase.table("stocks")\
        .select("quantite")\
        .eq("user_id", user_id)\
        .eq("produit", produit.lower())\
        .execute()
    if result.data:
        nouvelle_qte = max(0, result.data[0]["quantite"] - quantite)
        supabase.table("stocks")\
            .update({"quantite": nouvelle_qte})\
            .eq("user_id", user_id)\
            .eq("produit", produit.lower())\
            .execute()

# ─────────────────────────────────────────
# SUPPRESSION
# ─────────────────────────────────────────

def supprimer_derniere_depense(user_id: int):
    result = supabase.table("depenses")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("date", str(date.today()))\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    if result.data:
        derniere = result.data[0]
        supabase.table("depenses").delete().eq("id", derniere["id"]).execute()
        return derniere
    return None

def supprimer_derniere_vente(user_id: int):
    result = supabase.table("ventes")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("date", str(date.today()))\
        .order("created_at", desc=True)\
        .limit(1)\
        .execute()
    if result.data:
        derniere = result.data[0]
        supabase.table("ventes").delete().eq("id", derniere["id"]).execute()
        # Remettre le stock
        save_stock(user_id, derniere["produit"], 0)
        return derniere
    return None

# ─────────────────────────────────────────
# OBJECTIFS & ALERTES
# ─────────────────────────────────────────

def save_objectif(user_id: int, categorie: str, seuil: float, epargne: float = 0):
    supabase.table("objectifs").upsert({
        "user_id": user_id,
        "categorie": categorie.lower(),
        "seuil_alerte": seuil,
        "objectif_epargne": epargne
    }, on_conflict="user_id,categorie").execute()

def get_objectifs(user_id: int):
    return supabase.table("objectifs")\
        .select("*")\
        .eq("user_id", user_id)\
        .execute().data

def supprimer_objectif(user_id: int, categorie: str):
    supabase.table("objectifs")\
        .delete()\
        .eq("user_id", user_id)\
        .eq("categorie", categorie.lower())\
        .execute()

def verifier_alertes_categories(user_id: int):
    """Retourne les catégories qui dépassent leur seuil aujourd'hui"""
    depenses = get_depenses_aujourd_hui(user_id)
    objectifs = get_objectifs(user_id)
    if not depenses or not objectifs:
        return []

    totaux = {}
    for d in depenses:
        cat = d["categorie"]
        totaux[cat] = totaux.get(cat, 0) + float(d["montant"])

    alertes = []
    for obj in objectifs:
        cat = obj["categorie"]
        if cat in totaux and totaux[cat] > float(obj["seuil_alerte"]):
            alertes.append({
                "categorie": cat,
                "depense": totaux[cat],
                "seuil": float(obj["seuil_alerte"])
            })
    return alertes

# ─────────────────────────────────────────
# HISTORIQUE PAR MOIS
# ─────────────────────────────────────────

def get_depenses_par_mois(user_id: int, annee: int, mois: int):
    from datetime import date
    debut = str(date(annee, mois, 1))
    if mois == 12:
        fin = str(date(annee + 1, 1, 1))
    else:
        fin = str(date(annee, mois + 1, 1))
    return supabase.table("depenses")\
        .select("*")\
        .eq("user_id", user_id)\
        .gte("date", debut)\
        .lt("date", fin)\
        .order("date")\
        .execute().data

def get_mois_disponibles(user_id: int):
    """Retourne la liste des mois qui ont des dépenses"""
    result = supabase.table("depenses")\
        .select("date")\
        .eq("user_id", user_id)\
        .order("date")\
        .execute().data
    mois = set()
    for d in result:
        date_str = d["date"][:7]  # "2026-05"
        mois.add(date_str)
    return sorted(list(mois), reverse=True)

# ─────────────────────────────────────────
# CLIENTS & DETTES
# ─────────────────────────────────────────

def save_client(user_id: int, nom: str, telephone: str = ""):
    result = supabase.table("clients").upsert({
        "user_id": user_id,
        "nom": nom.lower(),
        "telephone": telephone
    }, on_conflict="user_id,nom").execute()
    return result.data[0] if result.data else None

def get_clients(user_id: int):
    return supabase.table("clients")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("nom")\
        .execute().data

def get_client_par_nom(user_id: int, nom: str):
    result = supabase.table("clients")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("nom", nom.lower())\
        .execute()
    return result.data[0] if result.data else None

def save_dette(user_id: int, client_id: str, montant: float, description: str = ""):
    supabase.table("dettes").insert({
        "user_id": user_id,
        "client_id": client_id,
        "montant": montant,
        "description": description,
        "statut": "impayé",
        "date": str(date.today())
    }).execute()

def get_dettes_client(client_id: str):
    return supabase.table("dettes")\
        .select("*")\
        .eq("client_id", client_id)\
        .eq("statut", "impayé")\
        .order("date")\
        .execute().data

def get_toutes_dettes(user_id: int):
    return supabase.table("dettes")\
        .select("*, clients(nom, telephone)")\
        .eq("user_id", user_id)\
        .eq("statut", "impayé")\
        .order("date")\
        .execute().data

def marquer_dette_payee(dette_id: str):
    supabase.table("dettes")\
        .update({"statut": "payé"})\
        .eq("id", dette_id)\
        .execute()

def get_total_dettes(user_id: int):
    dettes = get_toutes_dettes(user_id)
    return sum(float(d["montant"]) for d in dettes)

# ─────────────────────────────────────────
# MARGES & HISTORIQUE PRODUITS
# ─────────────────────────────────────────

def get_historique_produit(user_id: int, produit: str):
    return supabase.table("ventes")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("produit", produit.lower())\
        .order("date", desc=True)\
        .limit(30)\
        .execute().data

def get_tous_produits_vendus(user_id: int):
    result = supabase.table("ventes")\
        .select("produit")\
        .eq("user_id", user_id)\
        .execute()
    produits = set(r["produit"] for r in result.data)
    return sorted(list(produits))

def get_stats_produit(user_id: int, produit: str):
    ventes = get_historique_produit(user_id, produit)
    if not ventes:
        return None
    total_qte = sum(v["quantite"] for v in ventes)
    total_ca = sum(v["quantite"] * v["prix_unitaire"] for v in ventes)
    prix_moyen = total_ca / total_qte if total_qte > 0 else 0
    
    stock = supabase.table("stocks")\
        .select("quantite, prix_vente")\
        .eq("user_id", user_id)\
        .eq("produit", produit.lower())\
        .execute()
    stock_info = stock.data[0] if stock.data else None
    
    return {
        "produit": produit,
        "total_vendu": total_qte,
        "chiffre_affaires": total_ca,
        "prix_moyen": prix_moyen,
        "stock_actuel": stock_info["quantite"] if stock_info else 0,
        "prix_vente": stock_info["prix_vente"] if stock_info else 0,
        "nb_transactions": len(ventes)
    }

# ─────────────────────────────────────────
# CLIENTS & DETTES (COMMERÇANTS)
# ─────────────────────────────────────────

def save_client(user_id: int, nom: str, telephone: str = ""):
    result = supabase.table("clients").upsert({
        "user_id": user_id,
        "nom": nom.lower(),
        "telephone": telephone
    }, on_conflict="user_id,nom").execute()
    return result.data[0] if result.data else None

def get_clients(user_id: int):
    return supabase.table("clients")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("nom")\
        .execute().data

def get_client_par_nom(user_id: int, nom: str):
    result = supabase.table("clients")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("nom", nom.lower())\
        .execute()
    return result.data[0] if result.data else None

def save_dette(user_id: int, client_id: str, montant: float, description: str = ""):
    supabase.table("dettes").insert({
        "user_id": user_id,
        "client_id": client_id,
        "montant": montant,
        "description": description,
        "statut": "impayé",
        "date": str(date.today())
    }).execute()

def get_dettes_client(client_id: str):
    return supabase.table("dettes")\
        .select("*")\
        .eq("client_id", client_id)\
        .eq("statut", "impayé")\
        .order("date")\
        .execute().data

def get_toutes_dettes(user_id: int):
    return supabase.table("dettes")\
        .select("*, clients(nom, telephone)")\
        .eq("user_id", user_id)\
        .eq("statut", "impayé")\
        .order("date")\
        .execute().data

def marquer_dette_payee(dette_id: str):
    supabase.table("dettes")\
        .update({"statut": "payé"})\
        .eq("id", dette_id)\
        .execute()

def get_total_dettes(user_id: int):
    dettes = get_toutes_dettes(user_id)
    return sum(float(d["montant"]) for d in dettes)

# ─────────────────────────────────────────
# MARGES & HISTORIQUE PRODUITS
# ─────────────────────────────────────────

def save_prix_achat(user_id: int, produit: str, prix_achat: float):
    supabase.table("stocks").update({
        "prix_achat": prix_achat
    }).eq("user_id", user_id).eq("produit", produit.lower()).execute()

def get_historique_produit(user_id: int, produit: str):
    return supabase.table("ventes")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("produit", produit.lower())\
        .order("date", desc=True)\
        .limit(30)\
        .execute().data

def get_top_produits(user_id: int, limite: int = 5):
    ventes = get_ventes_semaine(user_id)
    produits = {}
    for v in ventes:
        p = v["produit"]
        if p not in produits:
            produits[p] = {"quantite": 0, "ca": 0}
        produits[p]["quantite"] += v["quantite"]
        produits[p]["ca"] += v["quantite"] * v["prix_unitaire"]
    return sorted(produits.items(), key=lambda x: x[1]["ca"], reverse=True)[:limite]
