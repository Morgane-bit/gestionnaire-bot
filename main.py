import logging
import os
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler
)

from handlers.onboarding import (
    get_onboarding_handler, cmd_aide, start,
    cmd_changer_profil, confirmer_changement_profil
)
from handlers.depenses import (
    handle_depense, cmd_bilan, cmd_semaine,
    cmd_budget, cmd_revenu
)
from handlers.stocks import (
    handle_vente, cmd_bilan_commercant, cmd_semaine_commercant,
    cmd_stock, cmd_ajout_stock, cmd_alertes
)
from handlers.objectifs import (
    cmd_objectifs, get_objectif_handler,
    supprimer_objectif_menu, confirmer_suppression
)
from handlers.historique import (
    cmd_historique, afficher_mois, exporter_pdf, retour_historique
)
from handlers.clients import (
    cmd_clients, cmd_nouveau_client, cmd_nouvelle_dette,
    voir_toutes_dettes, menu_payer_dette, confirmer_paiement
)
from handlers.marges import (
    cmd_marges, cmd_prix_achat, cmd_top_produits, cmd_historique_produit
)
from services.database import get_user, verifier_alertes_categories
from services.scheduler import start_scheduler
from services.erreurs import handler_erreur

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def router_message(update: Update, context):
    user_id = update.effective_user.id
    user = get_user(user_id)

    if not user:
        await update.message.reply_text("👋 Tape /start pour créer ton compte.")
        return

    if user["profile"] == "particulier":
        await handle_depense(update, context)
        alertes = verifier_alertes_categories(user_id)
        for alerte in alertes:
            await update.message.reply_text(
                f"⚠️ *Alerte budget !*\n\n"
                f"Tu as dépensé *{alerte['depense']:,.0f} FCFA* en *{alerte['categorie']}* aujourd'hui.\n"
                f"Ton seuil est de *{alerte['seuil']:,.0f} FCFA*.",
                parse_mode="Markdown"
            )
    elif user["profile"] == "commercant":
        await handle_vente(update, context)


async def router_bilan(update, context):
    user = get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Tape /start pour commencer.")
        return
    if user["profile"] == "particulier":
        await cmd_bilan(update, context)
    else:
        await cmd_bilan_commercant(update, context)


async def router_semaine(update, context):
    user = get_user(update.effective_user.id)
    if not user:
        await update.message.reply_text("Tape /start pour commencer.")
        return
    if user["profile"] == "particulier":
        await cmd_semaine(update, context)
    else:
        await cmd_semaine_commercant(update, context)


def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_TOKEN manquant dans le fichier .env")

    app = Application.builder().token(token).build()

    # Conversations
    app.add_handler(get_onboarding_handler())
    app.add_handler(get_objectif_handler())

    # Callbacks inline
    app.add_handler(CallbackQueryHandler(confirmer_changement_profil, pattern="^switch_"))
    app.add_handler(CallbackQueryHandler(supprimer_objectif_menu, pattern="^suppr_objectif$"))
    app.add_handler(CallbackQueryHandler(confirmer_suppression, pattern="^(del_obj_|annuler_suppr)"))
    app.add_handler(CallbackQueryHandler(afficher_mois, pattern="^hist_"))
    app.add_handler(CallbackQueryHandler(exporter_pdf, pattern="^pdf_"))
    app.add_handler(CallbackQueryHandler(retour_historique, pattern="^retour_historique$"))
    app.add_handler(CallbackQueryHandler(voir_toutes_dettes, pattern="^voir_dettes$"))
    app.add_handler(CallbackQueryHandler(menu_payer_dette, pattern="^payer_dette$"))
    app.add_handler(CallbackQueryHandler(confirmer_paiement, pattern="^(payee_|annuler_paiement)"))

    # Commandes partagées
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bilan", router_bilan))
    app.add_handler(CommandHandler("semaine", router_semaine))
    app.add_handler(CommandHandler("aide", cmd_aide))
    app.add_handler(CommandHandler("profil", cmd_changer_profil))

    # Commandes particuliers
    app.add_handler(CommandHandler("budget", cmd_budget))
    app.add_handler(CommandHandler("revenu", cmd_revenu))
    app.add_handler(CommandHandler("objectifs", cmd_objectifs))
    app.add_handler(CommandHandler("newobjectif", cmd_objectifs))
    app.add_handler(CommandHandler("historique", cmd_historique))

    # Commandes commerçants
    app.add_handler(CommandHandler("stock", cmd_stock))
    app.add_handler(CommandHandler("ajout", cmd_ajout_stock))
    app.add_handler(CommandHandler("alertes", cmd_alertes))
    app.add_handler(CommandHandler("clients", cmd_clients))
    app.add_handler(CommandHandler("newclient", cmd_nouveau_client))
    app.add_handler(CommandHandler("dette", cmd_nouvelle_dette))
    app.add_handler(CommandHandler("marges", cmd_marges))
    app.add_handler(CommandHandler("prixachat", cmd_prix_achat))
    app.add_handler(CommandHandler("topproduits", cmd_top_produits))
    app.add_handler(CommandHandler("hproduit", cmd_historique_produit))

    # Messages texte libres
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router_message))

    # Gestionnaire d'erreurs global
    app.add_error_handler(handler_erreur)

    start_scheduler(app)
    logger.info("🚀 Bot démarré avec succès !")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
