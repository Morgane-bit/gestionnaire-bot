from telegram import Update
from telegram.ext import ContextTypes
from services.database import (
    save_depense, get_depenses_aujourd_hui, get_depenses_semaine,
    get_depenses_mois, get_total_par_categorie, get_user, update_revenu,
    supprimer_derniere_depense
)
from services.claude_ai import analyser_depenses, estimer_budget_optimal

BOUTONS_PARTICULIER = {
    "📊 Bilan du jour": "bilan",
    "📅 Bilan semaine": "semaine",
    "💰 Budget optimal": "budget",
    "💵 Mon revenu": "revenu_info",
    "📅 Historique": "historique",
    "🎯 Mes objectifs": "objectifs",
    "🗑 Effacer dernière dépense": "effacer",
    "❓ Aide": "aide",
    "🔄 Changer de profil": "changer_profil",
}

async def handle_depense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if text in BOUTONS_PARTICULIER:
        action = BOUTONS_PARTICULIER[text]
        if action == "bilan": await cmd_bilan(update, context)
        elif action == "semaine": await cmd_semaine(update, context)
        elif action == "budget": await cmd_budget(update, context)
        elif action == "revenu_info": await cmd_revenu_info(update, context)
        elif action == "effacer": await cmd_effacer(update, context)
        elif action == "historique":
            from handlers.historique import cmd_historique
            await cmd_historique(update, context)
        elif action == "objectifs":
            from handlers.objectifs import cmd_objectifs
            await cmd_objectifs(update, context)
        elif action == "aide":
            from handlers.onboarding import cmd_aide
            await cmd_aide(update, context)
        elif action == "changer_profil":
            from handlers.onboarding import cmd_changer_profil
            await cmd_changer_profil(update, context)
        return

    parts = text.split()
    montant = None
    montant_index = -1
    for i, part in enumerate(parts):
        try:
            montant = float(part.replace(",", "."))
            montant_index = i
            break
        except ValueError:
            continue

    if montant is None or montant_index == 0:
        await update.message.reply_text(
            "❌ Je n'ai pas compris.\n\n"
            "💡 *Pour enregistrer une dépense, tape :*\n"
            "`repas 1500`\n"
            "`transport 500 taxi`\n"
            "`courses 3000 marché`\n\n"
            "Ou utilise les boutons du menu en bas.",
            parse_mode="Markdown"
        )
        return

    categorie = parts[0]
    description = " ".join(parts[montant_index + 1:]) if montant_index + 1 < len(parts) else ""
    save_depense(user_id, montant, categorie, description)

    depenses_jour = get_depenses_aujourd_hui(user_id)
    total_jour = sum(float(d["montant"]) for d in depenses_jour)
    desc_txt = f" _{description}_" if description else ""
    await update.message.reply_text(
        f"✅ *{categorie.capitalize()}*{desc_txt} : *{montant:,.0f} FCFA*\n\n"
        f"💸 Total aujourd'hui : *{total_jour:,.0f} FCFA*",
        parse_mode="Markdown"
    )

async def cmd_bilan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    depenses = get_depenses_aujourd_hui(user_id)
    if not depenses:
        await update.message.reply_text("📭 Aucune dépense aujourd'hui.\n\nTape : `repas 1500`", parse_mode="Markdown")
        return
    total = sum(float(d["montant"]) for d in depenses)
    lignes = "\n".join([
        f"  • {d['categorie'].capitalize()}"
        + (f" ({d['description']})" if d.get('description') else "")
        + f" : *{float(d['montant']):,.0f} FCFA*"
        for d in depenses
    ])
    await update.message.reply_text(
        f"📊 *Bilan du {depenses[0]['date']}*\n\n{lignes}\n\n💰 *Total : {total:,.0f} FCFA*",
        parse_mode="Markdown"
    )

async def cmd_semaine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text("⏳ Analyse en cours...")
    depenses = get_depenses_semaine(user_id)
    user = get_user(user_id)
    revenu = float(user.get("revenu_mensuel", 0)) if user else 0
    if not depenses:
        await update.message.reply_text("Aucune dépense cette semaine.")
        return
    total = sum(float(d["montant"]) for d in depenses)
    totaux_cat = get_total_par_categorie(user_id, "semaine")
    categs = "\n".join([f"  • {cat.capitalize()} : *{montant:,.0f} FCFA*" for cat, montant in list(totaux_cat.items())[:5]])
    analyse = analyser_depenses(depenses, revenu)
    await update.message.reply_text(
        f"📅 *Bilan de la semaine*\n\n💸 Total : *{total:,.0f} FCFA*\n\n*Par catégorie :*\n{categs}\n\n─────────────────\n🤖 *Analyse & conseils :*\n\n{analyse}",
        parse_mode="Markdown"
    )

async def cmd_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    revenu = float(user.get("revenu_mensuel", 0)) if user else 0
    if revenu <= 0:
        await update.message.reply_text("💵 Renseigne d'abord ton revenu.\n\nTape : `/revenu 150000`", parse_mode="Markdown")
        return
    await update.message.reply_text("⏳ Calcul en cours...")
    estimation = estimer_budget_optimal(get_depenses_mois(user_id), revenu)
    await update.message.reply_text(f"🎯 *Budget optimal pour le mois prochain*\n\n{estimation}", parse_mode="Markdown")

async def cmd_revenu_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    revenu = float(user.get("revenu_mensuel", 0)) if user else 0
    if revenu <= 0:
        await update.message.reply_text("💵 Aucun revenu renseigné.\n\nTape : `/revenu 150000`", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"💵 Ton revenu actuel : *{revenu:,.0f} FCFA*\n\nPour modifier : `/revenu nouveau_montant`", parse_mode="Markdown")

async def cmd_revenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("💵 Usage : `/revenu 150000`", parse_mode="Markdown")
        return
    try:
        revenu = float(args[0].replace(",", ".").replace(" ", ""))
        update_revenu(user_id, revenu)
        await update.message.reply_text(f"✅ Revenu mis à jour : *{revenu:,.0f} FCFA*", parse_mode="Markdown")
    except ValueError:
        await update.message.reply_text("❌ Exemple : `/revenu 150000`", parse_mode="Markdown")

async def cmd_effacer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    supprimee = supprimer_derniere_depense(user_id)
    if supprimee:
        await update.message.reply_text(
            f"🗑 Supprimée : *{supprimee['categorie'].capitalize()}* — *{float(supprimee['montant']):,.0f} FCFA*"
            + (f" ({supprimee['description']})" if supprimee.get('description') else ""),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Aucune dépense à supprimer aujourd'hui.")
