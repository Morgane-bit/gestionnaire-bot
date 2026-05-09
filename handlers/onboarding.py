from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from services.database import get_user, create_user, update_revenu, supabase

# États de la conversation
CHOIX_PROFIL, SAISIE_REVENU = range(2)


def menu_particulier():
    """Clavier permanent pour les particuliers"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 Bilan du jour"), KeyboardButton("📅 Bilan semaine")],
        [KeyboardButton("💰 Budget optimal"), KeyboardButton("💵 Mon revenu")],
        [KeyboardButton("📅 Historique"), KeyboardButton("🎯 Mes objectifs")],
        [KeyboardButton("🗑 Effacer dernière dépense"), KeyboardButton("❓ Aide")],
        [KeyboardButton("🔄 Changer de profil")]
    ], resize_keyboard=True)


def menu_commercant():
    """Clavier permanent pour les commerçants"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 Bilan du jour"), KeyboardButton("📅 Bilan semaine")],
        [KeyboardButton("📦 Mes stocks"), KeyboardButton("⚠️ Alertes stocks")],
        [KeyboardButton("👥 Mes clients"), KeyboardButton("💰 Dettes clients")],
        [KeyboardButton("📈 Top produits"), KeyboardButton("📊 Mes marges")],
        [KeyboardButton("➕ Ajouter stock"), KeyboardButton("❓ Aide")],
        [KeyboardButton("🔄 Changer de profil")]
    ], resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = get_user(user.id)

    if existing:
        profil = existing["profile"]
        emoji = "🏪" if profil == "commercant" else "👤"
        clavier = menu_commercant() if profil == "commercant" else menu_particulier()
        await update.message.reply_text(
            f"Bon retour, *{existing['name']}* {emoji}\n\n"
            f"Le menu est affiché en bas de ton écran.\n"
            f"Tu peux aussi taper directement une dépense ou une vente.",
            parse_mode="Markdown",
            reply_markup=clavier
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"👋 Bonjour *{user.first_name}* !\n\n"
        f"Je suis ton assistant de gestion financière.\n\n"
        f"Qui es-tu ?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏪 Commerçant / Vendeur", callback_data="commercant")],
            [InlineKeyboardButton("👤 Particulier / Salarié", callback_data="particulier")]
        ])
    )
    return CHOIX_PROFIL


async def choisir_profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    profil = query.data
    user = query.from_user
    context.user_data["profil"] = profil

    if profil == "particulier":
        await query.edit_message_text(
            f"Parfait 👤\n\n"
            f"Quel est ton revenu mensuel en FCFA ?\n"
            f"_(Tape 0 si tu préfères ne pas le renseigner)_",
            parse_mode="Markdown"
        )
        return SAISIE_REVENU
    else:
        create_user(user.id, user.first_name, profil)
        await query.edit_message_text(
            f"Parfait 🏪 Compte commerçant créé !\n\n"
            f"Pour enregistrer une vente, tape :\n"
            f"`vendu pagne 3 5000`\n\n"
            f"Le menu apparaît en bas de ton écran.",
            parse_mode="Markdown"
        )
        await context.bot.send_message(
            chat_id=user.id,
            text="Menu chargé ✅",
            reply_markup=menu_commercant()
        )
        return ConversationHandler.END


async def saisir_revenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip().replace(" ", "").replace(",", ".")

    try:
        revenu = float(text)
    except ValueError:
        await update.message.reply_text(
            "❌ Tape un nombre en FCFA.\nExemple : *150000* ou *0*",
            parse_mode="Markdown"
        )
        return SAISIE_REVENU

    profil = context.user_data.get("profil", "particulier")
    create_user(user.id, user.first_name, profil)
    if revenu > 0:
        update_revenu(user.id, revenu)

    await update.message.reply_text(
        f"✅ Compte créé ! Bienvenue *{user.first_name}* 🎉\n\n"
        f"Pour enregistrer une dépense, tape par exemple :\n"
        f"`repas 1500` ou `transport 500 taxi`\n\n"
        f"Le menu est affiché en bas de ton écran.",
        parse_mode="Markdown",
        reply_markup=menu_particulier()
    )
    return ConversationHandler.END


async def cmd_aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("Tape /start pour créer ton compte.")
        return

    if user["profile"] == "particulier":
        await update.message.reply_text(
            "❓ *Aide — Mode Particulier*\n\n"
            "*Enregistrer une dépense (tape directement) :*\n"
            "`repas 1500`\n"
            "`transport 500 taxi moto`\n"
            "`courses 3000 marché dantokpa`\n\n"
            "*Boutons du menu :*\n"
            "📊 Bilan du jour — tes dépenses d'aujourd'hui\n"
            "📅 Bilan semaine — analyse + conseils IA\n"
            "💰 Budget optimal — répartition recommandée\n"
            "💵 Mon revenu — mettre à jour ton revenu\n"
            "🗑 Effacer — supprime la dernière dépense",
            parse_mode="Markdown",
            reply_markup=menu_particulier()
        )
    else:
        await update.message.reply_text(
            "❓ *Aide — Mode Commerçant*\n\n"
            "*Enregistrer une vente (tape directement) :*\n"
            "`vendu pagne 3 5000`\n"
            "`vendu savon 10 500`\n\n"
            "*Boutons du menu :*\n"
            "📊 Bilan du jour — CA d'aujourd'hui\n"
            "📅 Bilan semaine — analyse + stratégies IA\n"
            "📦 Mes stocks — état de tous les stocks\n"
            "⚠️ Alertes stocks — produits à réapprovisionner\n"
            "➕ Ajouter stock — ajouter ou réapprovisionner",
            parse_mode="Markdown",
            reply_markup=menu_commercant()
        )


def get_onboarding_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOIX_PROFIL: [CallbackQueryHandler(choisir_profil)],
            SAISIE_REVENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, saisir_revenu),
                CommandHandler("start", start)
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )


# ─────────────────────────────────────────
# CHANGER DE PROFIL
# ─────────────────────────────────────────

async def cmd_changer_profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("Tape /start pour créer ton compte.")
        return

    profil_actuel = user["profile"]
    nouveau_profil = "particulier" if profil_actuel == "commercant" else "commercant"
    emoji_actuel = "🏪" if profil_actuel == "commercant" else "👤"
    emoji_nouveau = "👤" if profil_actuel == "commercant" else "🏪"

    await update.message.reply_text(
        f"Tu es actuellement en mode {emoji_actuel} *{profil_actuel.capitalize()}*.\n\nVeux-tu passer en mode {emoji_nouveau} *{nouveau_profil.capitalize()}* ?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ Oui, passer en {nouveau_profil}", callback_data=f"switch_{nouveau_profil}")],
            [InlineKeyboardButton("❌ Non, rester en " + profil_actuel, callback_data="switch_annuler")]
        ])
    )


async def confirmer_changement_profil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "switch_annuler":
        await query.edit_message_text("✅ Profil inchangé.")
        return

    nouveau_profil = query.data.replace("switch_", "")
    supabase.table("users").update({"profile": nouveau_profil}).eq("id", user_id).execute()

    clavier = menu_commercant() if nouveau_profil == "commercant" else menu_particulier()
    emoji = "🏪" if nouveau_profil == "commercant" else "👤"

    await query.edit_message_text(
        f"✅ Profil changé en {emoji} *{nouveau_profil.capitalize()}* !",
        parse_mode="Markdown"
    )
    await context.bot.send_message(
        chat_id=user_id,
        text="Voici ton nouveau menu 👇",
        reply_markup=clavier
    )
