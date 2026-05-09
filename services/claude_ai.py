import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# ─────────────────────────────────────────
# MODULE PARTICULIER
# ─────────────────────────────────────────

def analyser_depenses(depenses: list, revenu_mensuel: float = 0) -> str:
    if not depenses:
        return "Aucune dépense enregistrée cette semaine."

    resume = "\n".join([
        f"- {d['categorie']}: {float(d['montant']):,.0f} FCFA"
        + (f" ({d['description']})" if d.get('description') else "")
        for d in depenses
    ])

    total = sum(float(d["montant"]) for d in depenses)
    revenu_info = f"Revenu mensuel déclaré : {revenu_mensuel:,.0f} FCFA\n" if revenu_mensuel > 0 else ""

    prompt = f"""Tu es un conseiller financier bienveillant pour des personnes en Afrique de l'Ouest (Bénin).
{revenu_info}
Dépenses de la semaine (total : {total:,.0f} FCFA) :
{resume}

Génère un bilan structuré court avec :
1. 📊 Répartition par catégorie (les 3 plus importantes)
2. ⚠️ Un point d'attention si une catégorie semble excessive
3. 💡 2 conseils concrets et réalistes adaptés au contexte local
4. 🎯 Une estimation du budget optimal pour la semaine prochaine si le revenu est renseigné

Réponds en français simple, chaleureux, sans jargon financier complexe. Maximum 15 lignes."""

    response = model.generate_content(prompt)
    return response.text


def estimer_budget_optimal(depenses_mois: list, revenu: float) -> str:
    if revenu <= 0:
        return "Renseigne ton revenu mensuel avec /revenu pour obtenir une estimation."

    total_depenses = sum(float(d["montant"]) for d in depenses_mois)
    categories = {}
    for d in depenses_mois:
        cat = d["categorie"]
        categories[cat] = categories.get(cat, 0) + float(d["montant"])

    prompt = f"""Tu es un conseiller financier pour quelqu'un vivant au Bénin.
Revenu mensuel : {revenu:,.0f} FCFA
Dépenses ce mois-ci : {total_depenses:,.0f} FCFA
Répartition : {categories}

Donne une répartition budgétaire optimale pour le mois prochain en FCFA.
Utilise la règle 50/30/20 adaptée au contexte béninois (besoins essentiels / désirs / épargne).
Sois précis avec des montants concrets. Maximum 12 lignes."""

    response = model.generate_content(prompt)
    return response.text


# ─────────────────────────────────────────
# MODULE COMMERÇANT
# ─────────────────────────────────────────

def analyser_ventes(ventes: list, stocks: list) -> str:
    if not ventes:
        return "Aucune vente enregistrée cette semaine."

    ca_total = sum(v["quantite"] * v["prix_unitaire"] for v in ventes)

    produits = {}
    for v in ventes:
        p = v["produit"]
        produits[p] = produits.get(p, 0) + v["quantite"] * v["prix_unitaire"]

    top_produits = sorted(produits.items(), key=lambda x: x[1], reverse=True)[:5]
    stocks_bas = [s for s in stocks if s["quantite"] <= s["seuil_alerte"]]

    prompt = f"""Tu es un conseiller commercial pour un petit commerçant en Afrique de l'Ouest.
Chiffre d'affaires de la semaine : {ca_total:,.0f} FCFA
Top produits vendus : {top_produits}
Stocks critiques (quantité ≤ seuil) : {[s['produit'] + ' (' + str(s['quantite']) + ' restants)' for s in stocks_bas]}

Génère un bilan structuré avec :
1. 📈 Performance de la semaine (CA, meilleurs produits)
2. ⚠️ Alertes stocks à réapprovisionner en priorité
3. 💡 2-3 stratégies concrètes pour améliorer les ventes la semaine prochaine
4. 🔄 Suggestion de réorganisation du stock si pertinent

Réponds en français simple et pratique. Maximum 15 lignes."""

    response = model.generate_content(prompt)
    return response.text
