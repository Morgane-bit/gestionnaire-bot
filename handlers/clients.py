from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from services.database import (
    save_client, get_clients, get_client_par_nom,
    save_dette, get_dettes_client, get_toutes_dettes,
    marquer_dette_payee, get_total_dettes
)

# États conversation
CLIENT_NOM, CLIENT_TEL, DETTE_CLIENT, DETTE_MONTANT, DETTE_DESC = range(20, 25)


# ─────────────────────────────────────────
# VOIR TOUS LES CLIENTS ET DETTES
# ─────────────────────────────────────────

async def cmd_clients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    dettes = get_toutes_dettes(user_id)
    clients = get_clients(user_id)

    if not clients:
        await update.message.reply_text(
            "👥 *Aucun client enregistré.*\n\n"
            "Pour ajouter un client :\n"
            "`/newclient Kofi 97000000`\n"
            "_(nom téléphone_optionnel)_\n\n"
            "Pour enregistrer une dette :\n"
            "`/dette Kofi 5000 3 pagnes`",
            parse_mode="Markdown"
        )
        return

    total_dettes = sum(float(d["montant"]) for d in dettes)

    # Grouper les dettes par client
    dettes_par_client = {}
    for d in dettes:
        nom = d["clients"]["nom"] if d.get("clients") else "inconnu"
        if nom not in dettes_par_client:
            dettes_par_client[nom] = 0
        dettes_par_client[nom] += float(d["montant"])

    lignes = []
    for client in clients:
        nom = client["nom"]
        tel = f" 📞 {client['telephone']}" if client.get("telephone") else ""
        dette = dettes_par_client.get(nom, 0)
        if dette > 0:
            lignes.append(f"  🔴 *{nom.capitalize()}*{tel}\n      Doit : *{dette:,.0f} FCFA*")
        else:
            lignes.append(f"  🟢 *{nom.capitalize()}*{tel} — À jour")

    keyboard = [
        [InlineKeyboardButton("💰 Voir toutes les dettes", callback_data="voir_dettes")],
        [InlineKeyboardButton("✅ Marquer une dette payée", callback_data="payer_dette")]
    ]

    await update.message.reply_text(
        f"👥 *Tes clients*\n\n"
        + "\n\n".join(lignes)
        + f"\n\n💰 Total impayé : *{total_dettes:,.0f} FCFA*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─────────────────────────────────────────
# AJOUTER UN CLIENT
# ─────────────────────────────────────────

async def cmd_nouveau_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id

    if not args:
        await update.message.reply_text(
            "👤 *Ajouter un client*\n\n"
            "Usage : `/newclient nom [téléphone]`\n\n"
            "Exemples :\n"
            "`/newclient Kofi`\n"
            "`/newclient Adjoua 97000000`",
            parse_mode="Markdown"
        )
        return

    nom = args[0]
    telephone = args[1] if len(args) > 1 else ""

    save_client(user_id, nom, telephone)
    await update.message.reply_text(
        f"✅ Client *{nom.capitalize()}* ajouté !"
        + (f"\n📞 {telephone}" if telephone else ""),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# ENREGISTRER UNE DETTE
# ─────────────────────────────────────────

async def cmd_nouvelle_dette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    user_id = update.effective_user.id

    # Format : /dette Kofi 5000 [description]
    if not args or len(args) < 2:
        await update.message.reply_text(
            "💰 *Enregistrer une dette*\n\n"
            "Usage : `/dette client montant [description]`\n\n"
            "Exemples :\n"
            "`/dette Kofi 5000`\n"
            "`/dette Adjoua 15000 3 pagnes`",
            parse_mode="Markdown"
        )
        return

    nom = args[0]
    try:
        montant = float(args[1].replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Montant invalide. Exemple : `/dette Kofi 5000`", parse_mode="Markdown")
        return

    description = " ".join(args[2:]) if len(args) > 2 else ""

    # Créer le client s'il n'existe pas
    client = get_client_par_nom(user_id, nom)
    if not client:
        save_client(user_id, nom)
        client = get_client_par_nom(user_id, nom)

    save_dette(user_id, client["id"], montant, description)

    await update.message.reply_text(
        f"💰 Dette enregistrée !\n\n"
        f"👤 Client : *{nom.capitalize()}*\n"
        f"💸 Montant : *{montant:,.0f} FCFA*"
        + (f"\n📝 {description}" if description else ""),
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# VOIR TOUTES LES DETTES
# ─────────────────────────────────────────

async def voir_toutes_dettes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    dettes = get_toutes_dettes(user_id)
    if not dettes:
        await query.edit_message_text("✅ Aucune dette impayée !")
        return

    lignes = []
    for d in dettes:
        nom = d["clients"]["nom"].capitalize() if d.get("clients") else "Inconnu"
        desc = f" — {d['description']}" if d.get("description") else ""
        lignes.append(
            f"  • *{nom}*{desc}\n"
            f"    *{float(d['montant']):,.0f} FCFA* — {d['date']}"
        )

    total = sum(float(d["montant"]) for d in dettes)
    await query.edit_message_text(
        f"💰 *Dettes impayées*\n\n"
        + "\n\n".join(lignes)
        + f"\n\n💸 *Total : {total:,.0f} FCFA*",
        parse_mode="Markdown"
    )


# ─────────────────────────────────────────
# MARQUER UNE DETTE PAYÉE
# ─────────────────────────────────────────

async def menu_payer_dette(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    dettes = get_toutes_dettes(user_id)
    if not dettes:
        await query.edit_message_text("✅ Aucune dette impayée !")
        return

    keyboard = []
    for d in dettes:
        nom = d["clients"]["nom"].capitalize() if d.get("clients") else "Inconnu"
        desc = f" — {d['description']}" if d.get("description") else ""
        label = f"✅ {nom} : {float(d['montant']):,.0f} FCFA{desc}"
        keyboard.append([InlineKeyboardButton(label, callback_data=f"payee_{d['id']}")])

    keyboard.append([InlineKeyboardButton("❌ Annuler", callback_data="annuler_paiement")])

    await query.edit_message_text(
        "Quelle dette a été remboursée ?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def confirmer_paiement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "annuler_paiement":
        await query.edit_message_text("Annulé.")
        return

    dette_id = query.data.replace("payee_", "")
    marquer_dette_payee(dette_id)
    await query.edit_message_text("✅ Dette marquée comme payée !")
