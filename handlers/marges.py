from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from services.database import (
    get_stocks, get_top_produits, get_historique_produit,
    save_prix_achat, get_ventes_semaine
)


# ─────────────────────────────────────────
# MARGES PAR PRODUIT
# ─────────────────────────────────────────

async def cmd_marges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    stocks = get_stocks(user_id)

    if not stocks:
        await update.message.reply_text(
            "📊 Aucun stock enregistré.\n\n"
            "Ajoute d'abord tes produits avec `/ajout`\n"
            "Puis définis le prix d'achat avec `/prixachat pagne 3000`",
            parse_mode="Markdown"
        )
        return

    lignes = []
    for s in stocks:
        prix_vente = float(s.get("prix_vente", 0))
        prix_achat = float(s.get("prix_achat", 0))

        if prix_vente > 0 and prix_achat > 0:
            marge = prix_vente - prix_achat
            pct = (marge / prix_vente) * 100
            emoji = "🟢" if pct >= 20 else "🟡" if pct >= 10 else "🔴"
            lignes.append(
                f"  {emoji} *{s['produit'].capitalize()}*\n"
                f"    Achat : {prix_achat:,.0f} | Vente : {prix_vente:,.0f} | "
                f"Marge : *{marge:,.0f} FCFA ({pct:.0f}%)*"
            )
        elif prix_vente > 0:
            lignes.append(
                f"  ⚪ *{s['produit'].capitalize()}*\n"
                f"    Vente : {prix_vente:,.0f} FCFA — _prix d'achat non renseigné_"
            )
        else:
            lignes.append(f"  ⚪ *{s['produit'].capitalize()}* — _prix non renseigné_")

    await update.message.reply_text(
        f"📊 *Marges par produit*\n\n"
        + "\n\n".join(lignes)
        + "\n\n_🟢 Bonne marge (≥20%) | 🟡 Moyenne | 🔴 Faible_\n\n"
        + "Pour définir un prix d'achat : `/prixachat produit montant`",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# DÉFINIR LE PRIX D'ACHAT
# ─────────────────────────────────────────

async def cmd_prix_achat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if not args or len(args) < 2:
        await update.message.reply_text(
            "💰 *Définir le prix d'achat*\n\n"
            "Usage : `/prixachat produit montant`\n\n"
            "Exemples :\n"
            "`/prixachat pagne 3000`\n"
            "`/prixachat savon 200`",
            parse_mode="Markdown"
        )
        return

    try:
        prix = float(args[-1].replace(",", "."))
        produit = " ".join(args[:-1])
        save_prix_achat(user_id, produit, prix)
        await update.message.reply_text(
            f"✅ Prix d'achat de *{produit.capitalize()}* : *{prix:,.0f} FCFA*\n\n"
            f"Tape /marges pour voir tes marges.",
            parse_mode="Markdown"
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Format invalide.\nExemple : `/prixachat pagne 3000`",
            parse_mode="Markdown"
        )


# ─────────────────────────────────────────
# TOP PRODUITS DE LA SEMAINE
# ─────────────────────────────────────────

async def cmd_top_produits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    top = get_top_produits(user_id)

    if not top:
        await update.message.reply_text(
            "📈 Aucune vente cette semaine.\n\n"
            "Enregistre tes ventes avec `vendu produit quantité prix`"
        )
        return

    lignes = []
    for i, (produit, stats) in enumerate(top, 1):
        medal = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"][i-1]
        lignes.append(
            f"  {medal} *{produit.capitalize()}*\n"
            f"    {stats['quantite']} vendus — *{stats['ca']:,.0f} FCFA*"
        )

    await update.message.reply_text(
        f"📈 *Top produits cette semaine*\n\n" + "\n\n".join(lignes),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# HISTORIQUE D'UN PRODUIT
# ─────────────────────────────────────────

async def cmd_historique_produit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text(
            "📦 Usage : `/hproduit nom_produit`\n\nExemple : `/hproduit pagne`",
            parse_mode="Markdown"
        )
        return

    produit = " ".join(args)
    ventes = get_historique_produit(user_id, produit)

    if not ventes:
        await update.message.reply_text(
            f"Aucune vente enregistrée pour *{produit}*.",
            parse_mode="Markdown"
        )
        return

    total_qte = sum(v["quantite"] for v in ventes)
    total_ca = sum(v["quantite"] * v["prix_unitaire"] for v in ventes)

    lignes = "\n".join([
        f"  • {v['date']} — {v['quantite']} unités × {float(v['prix_unitaire']):,.0f} = *{v['quantite']*v['prix_unitaire']:,.0f} FCFA*"
        for v in ventes[:10]
    ])

    await update.message.reply_text(
        f"📦 *Historique : {produit.capitalize()}*\n\n"
        f"{lignes}\n\n"
        f"📊 Total : *{total_qte} unités* — *{total_ca:,.0f} FCFA*",
        parse_mode="Markdown"
    )
