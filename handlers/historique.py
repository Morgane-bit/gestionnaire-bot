from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from services.database import get_depenses_par_mois, get_mois_disponibles, get_total_par_categorie, get_user
from services.claude_ai import analyser_depenses
import io

NOMS_MOIS = {
    "01": "Janvier", "02": "Février", "03": "Mars", "04": "Avril",
    "05": "Mai", "06": "Juin", "07": "Juillet", "08": "Août",
    "09": "Septembre", "10": "Octobre", "11": "Novembre", "12": "Décembre"
}

# ─────────────────────────────────────────
# VOIR L'HISTORIQUE
# ─────────────────────────────────────────

async def cmd_historique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mois_dispo = get_mois_disponibles(user_id)

    if not mois_dispo:
        await update.message.reply_text(
            "📅 Aucun historique disponible.\n\n"
            "Commence à enregistrer tes dépenses pour construire ton historique."
        )
        return

    keyboard = []
    for m in mois_dispo[:6]:  # Max 6 mois affichés
        annee, mois = m.split("-")
        label = f"{NOMS_MOIS[mois]} {annee}"
        keyboard.append([InlineKeyboardButton(f"📅 {label}", callback_data=f"hist_{m}")])

    await update.message.reply_text(
        "📅 *Historique de tes dépenses*\n\nChoisis un mois :",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def afficher_mois(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mois_str = query.data.replace("hist_", "")
    annee, mois = mois_str.split("-")
    user_id = query.from_user.id

    depenses = get_depenses_par_mois(user_id, int(annee), int(mois))
    nom_mois = f"{NOMS_MOIS[mois]} {annee}"

    if not depenses:
        await query.edit_message_text(f"Aucune dépense en {nom_mois}.")
        return

    total = sum(float(d["montant"]) for d in depenses)

    # Regrouper par catégorie
    categories = {}
    for d in depenses:
        cat = d["categorie"]
        categories[cat] = categories.get(cat, 0) + float(d["montant"])
    categories = dict(sorted(categories.items(), key=lambda x: x[1], reverse=True))

    lignes = "\n".join([
        f"  • {cat.capitalize()} : *{montant:,.0f} FCFA*"
        for cat, montant in list(categories.items())[:8]
    ])

    keyboard = [
        [InlineKeyboardButton("📄 Exporter en PDF", callback_data=f"pdf_{mois_str}")],
        [InlineKeyboardButton("🔙 Retour", callback_data="retour_historique")]
    ]

    await query.edit_message_text(
        f"📅 *{nom_mois}*\n\n"
        f"*Par catégorie :*\n{lignes}\n\n"
        f"💰 *Total : {total:,.0f} FCFA*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def retour_historique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await cmd_historique(update, context)


# ─────────────────────────────────────────
# EXPORT PDF
# ─────────────────────────────────────────

async def exporter_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Génération du PDF en cours...")

    mois_str = query.data.replace("pdf_", "")
    annee, mois = mois_str.split("-")
    user_id = query.from_user.id
    nom_mois = f"{NOMS_MOIS[mois]} {annee}"

    depenses = get_depenses_par_mois(user_id, int(annee), int(mois))
    user = get_user(user_id)

    if not depenses:
        await query.edit_message_text("Aucune dépense à exporter.")
        return

    total = sum(float(d["montant"]) for d in depenses)
    categories = {}
    for d in depenses:
        cat = d["categorie"]
        categories[cat] = categories.get(cat, 0) + float(d["montant"])

    # Générer le contenu du rapport en texte
    lignes_detail = "\n".join([
        f"{d['date']} | {d['categorie'].capitalize():<15} | {float(d['montant']):>10,.0f} FCFA"
        + (f" | {d['description']}" if d.get('description') else "")
        for d in depenses
    ])

    lignes_categories = "\n".join([
        f"  {cat.capitalize():<20} {montant:>10,.0f} FCFA  ({montant/total*100:.1f}%)"
        for cat, montant in sorted(categories.items(), key=lambda x: x[1], reverse=True)
    ])

    revenu = float(user.get("revenu_mensuel", 0)) if user else 0
    revenu_ligne = f"Revenu mensuel déclaré : {revenu:,.0f} FCFA\n" if revenu > 0 else ""
    solde_ligne = f"Solde estimé            : {revenu - total:,.0f} FCFA\n" if revenu > 0 else ""

    rapport = f"""
╔══════════════════════════════════════════════════╗
║         RELEVÉ DE DÉPENSES — {nom_mois:<18} ║
╚══════════════════════════════════════════════════╝

Nom : {user['name'] if user else 'Utilisateur'}
{revenu_ligne}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÉSUMÉ PAR CATÉGORIE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{lignes_categories}

  TOTAL DÉPENSÉ          {total:>10,.0f} FCFA
{solde_ligne}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DÉTAIL DES DÉPENSES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATE       | CATÉGORIE       |      MONTANT
-----------+-----------------+------------------
{lignes_detail}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Généré par Gestionnaire Bot
"""

    # Envoyer comme fichier texte
    fichier = io.BytesIO(rapport.encode("utf-8"))
    fichier.name = f"releve_{mois_str}.txt"

    await context.bot.send_document(
        chat_id=user_id,
        document=fichier,
        filename=f"releve_{nom_mois.replace(' ', '_')}.txt",
        caption=f"📄 Ton relevé de *{nom_mois}* — Total : *{total:,.0f} FCFA*",
        parse_mode="Markdown"
    )
