from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.database import get_tous_utilisateurs, get_depenses_semaine, get_ventes_semaine, get_stocks
from services.claude_ai import analyser_depenses, analyser_ventes
import logging

logger = logging.getLogger(__name__)


def start_scheduler(app):
    scheduler = AsyncIOScheduler()

    # Rapport hebdomadaire chaque dimanche à 20h
    scheduler.add_job(
        envoyer_bilans_hebdo,
        'cron',
        day_of_week='sun',
        hour=20,
        minute=0,
        args=[app]
    )

    # Alertes stocks critiques chaque matin à 8h (commerçants)
    scheduler.add_job(
        envoyer_alertes_stocks,
        'cron',
        hour=8,
        minute=0,
        args=[app]
    )

    scheduler.start()
    logger.info("✅ Scheduler démarré — rapports hebdo activés")


async def envoyer_bilans_hebdo(app):
    logger.info("📊 Envoi des bilans hebdomadaires...")

    # Bilans particuliers
    particuliers = get_tous_utilisateurs(profile="particulier")
    for user in particuliers:
        try:
            depenses = get_depenses_semaine(user["id"])
            if not depenses:
                continue
            analyse = analyser_depenses(depenses, float(user.get("revenu_mensuel", 0)))
            total = sum(float(d["montant"]) for d in depenses)
            await app.bot.send_message(
                chat_id=user["id"],
                text=f"📅 *Ton bilan de la semaine*\n\n"
                     f"💸 Total dépensé : *{total:,.0f} FCFA*\n\n"
                     f"─────────────────\n"
                     f"🤖 *Analyse :*\n\n{analyse}\n\n"
                     f"Tape /budget pour ton plan de la semaine prochaine.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Erreur bilan particulier {user['id']}: {e}")

    # Bilans commerçants
    commercants = get_tous_utilisateurs(profile="commercant")
    for user in commercants:
        try:
            ventes = get_ventes_semaine(user["id"])
            if not ventes:
                continue
            stocks = get_stocks(user["id"])
            analyse = analyser_ventes(ventes, stocks)
            ca = sum(v["quantite"] * v["prix_unitaire"] for v in ventes)
            await app.bot.send_message(
                chat_id=user["id"],
                text=f"📅 *Bilan hebdomadaire de ton commerce*\n\n"
                     f"💰 CA de la semaine : *{ca:,.0f} FCFA*\n\n"
                     f"─────────────────\n"
                     f"🤖 *Analyse & stratégies :*\n\n{analyse}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Erreur bilan commerçant {user['id']}: {e}")


async def envoyer_alertes_stocks(app):
    from services.database import get_stocks_critiques
    commercants = get_tous_utilisateurs(profile="commercant")
    for user in commercants:
        try:
            critiques = get_stocks_critiques(user["id"])
            if not critiques:
                continue
            lignes = "\n".join([
                f"  ⚠️ *{s['produit'].capitalize()}* : {s['quantite']} restantes"
                for s in critiques
            ])
            await app.bot.send_message(
                chat_id=user["id"],
                text=f"🌅 *Bonjour ! Alerte stocks du matin*\n\n"
                     f"Ces produits sont à réapprovisionner :\n\n"
                     f"{lignes}\n\n"
                     f"Tape `/ajout produit quantité` pour mettre à jour.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Erreur alertes stocks {user['id']}: {e}")
