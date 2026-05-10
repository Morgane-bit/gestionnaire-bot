from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from services.database import save_objectif, get_objectifs, supprimer_objectif, get_user

# États conversation
SAISIE_CATEGORIE, SAISIE_SEUIL, SAISIE_EPARGNE = range(10, 13)


# ─────────────────────────────────────────
# VOIR LES OBJECTIFS
# ─────────────────────────────────────────

async def cmd_objectifs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    objectifs = get_objectifs(user_id)

    if not objectifs:
        await update.message.reply_text(
            "🎯 *Aucun objectif défini.*\n\n"
            "Les objectifs te permettent de :\n"
            "  • Recevoir une alerte quand tu dépenses trop dans une catégorie\n"
            "  • Suivre ton épargne mensuelle\n\n"
            "Pour en créer un, tape : `/newobjectif`",
            parse_mode="Markdown"
        )
        return

    lignes = []
    for obj in objectifs:
        ligne = f"  • *{obj['categorie'].capitalize()}*\n"
        ligne += f"    ⚠️ Alerte si > *{float(obj['seuil_alerte']):,.0f} FCFA/jour*"
        if obj.get("objectif_epargne", 0) > 0:
            ligne += f"\n    🎯 Épargne visée : *{float(obj['objectif_epargne']):,.0f} FCFA/mois*"
        lignes.append(ligne)

    keyboard = [[InlineKeyboardButton("🗑 Supprimer un objectif", callback_data="suppr_objectif")]]

    await update.message.reply_text(
        f"🎯 *Tes objectifs*\n\n" + "\n\n".join(lignes),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─────────────────────────────────────────
# CRÉER UN OBJECTIF (conversation)
# ─────────────────────────────────────────

async def cmd_nouvel_objectif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 *Créer un objectif*\n\n"
        "Pour quelle catégorie de dépense ?\n\n"
        "Exemples : `repas`, `transport`, `loisirs`, `courses`",
        parse_mode="Markdown"
    )
    return SAISIE_CATEGORIE


async def saisir_categorie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    categorie = update.message.text.strip().lower()
    context.user_data["obj_categorie"] = categorie

    await update.message.reply_text(
        f"✅ Catégorie : *{categorie.capitalize()}*\n\n"
        f"Quel est le montant maximum par jour avant alerte ?\n"
        f"_(Exemple : 5000 pour être alerté si tu dépenses plus de 5 000 FCFA/jour en {categorie})_",
        parse_mode="Markdown"
    )
    return SAISIE_SEUIL


async def saisir_seuil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        seuil = float(update.message.text.strip().replace(",", ".").replace(" ", ""))
        context.user_data["obj_seuil"] = seuil
    except ValueError:
        await update.message.reply_text("❌ Tape un montant en FCFA. Exemple : `5000`", parse_mode="Markdown")
        return SAISIE_SEUIL

    await update.message.reply_text(
        f"✅ Alerte si > *{seuil:,.0f} FCFA/jour*\n\n"
        f"Quel est ton objectif d'épargne mensuel pour cette catégorie ?\n"
        f"_(Tape 0 si tu n'en as pas)_",
        parse_mode="Markdown"
    )
    return SAISIE_EPARGNE


async def saisir_epargne(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        epargne = float(update.message.text.strip().replace(",", ".").replace(" ", ""))
    except ValueError:
        await update.message.reply_text("❌ Tape un montant. Exemple : `20000` ou `0`", parse_mode="Markdown")
        return SAISIE_EPARGNE

    user_id = update.effective_user.id
    categorie = context.user_data["obj_categorie"]
    seuil = context.user_data["obj_seuil"]

    save_objectif(user_id, categorie, seuil, epargne)

    msg = (
        f"🎯 *Objectif créé !*\n\n"
        f"  • Catégorie : *{categorie.capitalize()}*\n"
        f"  • Alerte si > *{seuil:,.0f} FCFA/jour*\n"
    )
    if epargne > 0:
        msg += f"  • Épargne visée : *{epargne:,.0f} FCFA/mois*\n"

    msg += "\nTu seras alerté automatiquement dès que tu dépasses ce seuil."

    await update.message.reply_text(msg, parse_mode="Markdown")
    return ConversationHandler.END


# ─────────────────────────────────────────
# SUPPRIMER UN OBJECTIF
# ─────────────────────────────────────────

async def supprimer_objectif_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    objectifs = get_objectifs(user_id)

    if not objectifs:
        await query.edit_message_text("Aucun objectif à supprimer.")
        return

    keyboard = [
        [InlineKeyboardButton(f"🗑 {obj['categorie'].capitalize()}", callback_data=f"del_obj_{obj['categorie']}")]
        for obj in objectifs
    ]
    keyboard.append([InlineKeyboardButton("❌ Annuler", callback_data="annuler_suppr")])

    await query.edit_message_text(
        "Quel objectif veux-tu supprimer ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def confirmer_suppression(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "annuler_suppr":
        await query.edit_message_text("Annulé.")
        return

    categorie = query.data.replace("del_obj_", "")
    supprimer_objectif(query.from_user.id, categorie)
    await query.edit_message_text(f"✅ Objectif *{categorie.capitalize()}* supprimé.", parse_mode="Markdown")


# ─────────────────────────────────────────
# HANDLER DE CONVERSATION
# ─────────────────────────────────────────

def get_objectif_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("newobjectif", cmd_nouvel_objectif)],
        states={
            SAISIE_CATEGORIE: [MessageHandler(filters.TEXT & ~filters.COMMAND, saisir_categorie)],
            SAISIE_SEUIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, saisir_seuil)],
            SAISIE_EPARGNE: [MessageHandler(filters.TEXT & ~filters.COMMAND, saisir_epargne)],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
    )
