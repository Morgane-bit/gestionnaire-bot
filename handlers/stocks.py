from telegram import Update
from telegram.ext import ContextTypes
from services.database import (
    save_vente, get_ventes_aujourd_hui, get_ventes_semaine,
    get_chiffre_affaires_aujourd_hui, get_stocks, get_stocks_critiques,
    save_stock, supprimer_derniere_vente
)
from services.claude_ai import analyser_ventes

BOUTONS_COMMERCANT = {
    "📊 Bilan du jour": "bilan",
    "📅 Bilan semaine": "semaine",
    "📦 Mes stocks": "stock",
    "⚠️ Alertes stocks": "alertes",
    "👥 Mes clients": "clients",
    "💰 Dettes clients": "dettes",
    "📈 Top produits": "top_produits",
    "📊 Mes marges": "marges",
    "➕ Ajouter stock": "ajout_info",
    "❓ Aide": "aide",
    "🔄 Changer de profil": "changer_profil",
}

async def handle_vente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().lower()
    user_id = update.effective_user.id

    # Gérer les boutons du menu
    original_text = update.message.text.strip()
    if original_text in BOUTONS_COMMERCANT:
        action = BOUTONS_COMMERCANT[original_text]
        if action == "bilan": await cmd_bilan_commercant(update, context)
        elif action == "semaine": await cmd_semaine_commercant(update, context)
        elif action == "stock": await cmd_stock(update, context)
        elif action == "alertes": await cmd_alertes(update, context)
        elif action == "ajout_info": await cmd_ajout_info(update, context)
        elif action == "clients":
            from handlers.clients import cmd_clients
            await cmd_clients(update, context)
        elif action == "dettes":
            from handlers.clients import cmd_clients
            await cmd_clients(update, context)
        elif action == "top_produits":
            from handlers.marges import cmd_top_produits
            await cmd_top_produits(update, context)
        elif action == "marges":
            from handlers.marges import cmd_marges
            await cmd_marges(update, context)
        elif action == "aide":
            from handlers.onboarding import cmd_aide
            await cmd_aide(update, context)
        elif action == "changer_profil":
            from handlers.onboarding import cmd_changer_profil
            await cmd_changer_profil(update, context)
        return

    if not text.startswith("vendu "):
        await update.message.reply_text(
            "💡 *Pour enregistrer une vente, tape :*\n\n"
            "`vendu pagne 3 5000`\n"
            "`vendu savon 10 500`\n\n"
            "Format : `vendu [produit] [quantité] [prix unitaire]`\n\n"
            "Ou utilise les boutons du menu en bas.",
            parse_mode="Markdown"
        )
        return

    parts = text.replace("vendu ", "").split()
    if len(parts) < 3:
        await update.message.reply_text("❌ Format incomplet.\nExemple : `vendu pagne 3 5000`", parse_mode="Markdown")
        return

    try:
        prix = float(parts[-1].replace(",", "."))
        quantite = int(parts[-2])
        produit = " ".join(parts[:-2])
    except ValueError:
        await update.message.reply_text("❌ Vérifie le format.\nExemple : `vendu pagne 3 5000`", parse_mode="Markdown")
        return

    save_vente(user_id, produit, quantite, prix)
    total_vente = quantite * prix
    ca_jour = get_chiffre_affaires_aujourd_hui(user_id)

    await update.message.reply_text(
        f"✅ *{produit.capitalize()}* × {quantite} = *{total_vente:,.0f} FCFA*\n\n"
        f"💰 CA total aujourd'hui : *{ca_jour:,.0f} FCFA*",
        parse_mode="Markdown"
    )

    critiques = get_stocks_critiques(user_id)
    if any(s["produit"] == produit for s in critiques):
        stock = next(s for s in critiques if s["produit"] == produit)
        await update.message.reply_text(
            f"⚠️ *Alerte stock !*\nIl ne reste que *{stock['quantite']}* unité(s) de *{produit}*.",
            parse_mode="Markdown"
        )

async def cmd_bilan_commercant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ventes = get_ventes_aujourd_hui(user_id)
    if not ventes:
        await update.message.reply_text("📭 Aucune vente aujourd'hui.\n\nTape : `vendu pagne 3 5000`", parse_mode="Markdown")
        return
    ca = sum(v["quantite"] * v["prix_unitaire"] for v in ventes)
    lignes = "\n".join([f"  • {v['produit'].capitalize()} × {v['quantite']} = *{v['quantite'] * v['prix_unitaire']:,.0f} FCFA*" for v in ventes])
    await update.message.reply_text(f"📊 *Ventes du jour*\n\n{lignes}\n\n💰 *CA total : {ca:,.0f} FCFA*", parse_mode="Markdown")

async def cmd_semaine_commercant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("⏳ Analyse en cours...")
    ventes = get_ventes_semaine(user_id)
    stocks = get_stocks(user_id)
    if not ventes:
        await update.message.reply_text("Aucune vente cette semaine.")
        return
    ca = sum(v["quantite"] * v["prix_unitaire"] for v in ventes)
    analyse = analyser_ventes(ventes, stocks)
    await update.message.reply_text(
        f"📅 *Bilan hebdomadaire*\n\n💰 CA : *{ca:,.0f} FCFA*\n📦 Ventes : *{len(ventes)}*\n\n─────────────────\n🤖 *Analyse & stratégies :*\n\n{analyse}",
        parse_mode="Markdown"
    )

async def cmd_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stocks = get_stocks(user_id)
    if not stocks:
        await update.message.reply_text(
            "📭 Aucun stock enregistré.\n\n"
            "Pour ajouter : `/ajout pagne 50 5000`\n"
            "_(produit quantité prix_vente)_",
            parse_mode="Markdown"
        )
        return
    lignes = []
    for s in stocks:
        alerte = " ⚠️" if s["quantite"] <= s["seuil_alerte"] else ""
        lignes.append(f"  • *{s['produit'].capitalize()}*{alerte} : {s['quantite']} unités" + (f" ({s['prix_vente']:,.0f} FCFA/u)" if s.get("prix_vente") else ""))
    await update.message.reply_text(f"📦 *État des stocks*\n\n" + "\n".join(lignes) + "\n\n_⚠️ = stock critique_", parse_mode="Markdown")

async def cmd_ajout_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "➕ *Ajouter ou réapprovisionner un stock*\n\n"
        "Tape la commande :\n"
        "`/ajout pagne 50 5000`\n"
        "`/ajout savon 100`\n\n"
        "Format : `/ajout [produit] [quantité] [prix optionnel]`",
        parse_mode="Markdown"
    )

async def cmd_ajout_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args or len(args) < 2:
        await update.message.reply_text("📦 Usage : `/ajout pagne 50 5000`", parse_mode="Markdown")
        return
    try:
        quantite = int(args[-1] if len(args) == 2 else args[-2])
        prix = float(args[-1]) if len(args) >= 3 else 0
        produit = args[0] if len(args) <= 3 else " ".join(args[:-2])
        save_stock(user_id, produit, quantite, prix)
        await update.message.reply_text(
            f"✅ *{produit.capitalize()}* : {quantite} unités" + (f" à {prix:,.0f} FCFA/u" if prix > 0 else ""),
            parse_mode="Markdown"
        )
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Exemple : `/ajout pagne 50 5000`", parse_mode="Markdown")

async def cmd_alertes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    critiques = get_stocks_critiques(user_id)
    if not critiques:
        await update.message.reply_text("✅ Tous tes stocks sont au-dessus du seuil d'alerte !")
        return
    lignes = "\n".join([f"  ⚠️ *{s['produit'].capitalize()}* : {s['quantite']} restantes" for s in critiques])
    await update.message.reply_text(f"⚠️ *Stocks à réapprovisionner*\n\n{lignes}\n\nTape `/ajout produit quantité` pour mettre à jour.", parse_mode="Markdown")

async def cmd_effacer_vente(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    supprimee = supprimer_derniere_vente(user_id)
    if supprimee:
        await update.message.reply_text(
            f"🗑 Vente supprimée : *{supprimee['produit'].capitalize()}* × {supprimee['quantite']}",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Aucune vente à supprimer aujourd'hui.")
