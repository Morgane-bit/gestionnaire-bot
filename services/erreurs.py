import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import NetworkError, TimedOut, TelegramError

logger = logging.getLogger(__name__)


async def handler_erreur(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Gestionnaire global des erreurs — évite que le bot plante silencieusement"""

    erreur = context.error

    # Erreurs réseau — pas grave, le bot se reconnecte automatiquement
    if isinstance(erreur, (NetworkError, TimedOut)):
        logger.warning(f"Erreur réseau (temporaire) : {erreur}")
        return

    # Erreurs Telegram
    if isinstance(erreur, TelegramError):
        logger.error(f"Erreur Telegram : {erreur}")
        return

    # Autres erreurs — on log et on prévient l'utilisateur
    logger.error(f"Erreur inattendue : {erreur}", exc_info=context.error)

    if update and hasattr(update, "effective_message") and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Une erreur s'est produite. Réessaie dans quelques secondes.\n"
                "Si le problème persiste, tape /start pour redémarrer."
            )
        except Exception:
            pass
