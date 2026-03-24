import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_whatsapp_message(to_number, message):
    """
    Envoie un message WhatsApp via le bot configuré.
    Utilise le WhatsAppBot avec support Green API / CallMeBot.
    """
    from .whatsapp_bot import whatsapp_bot
    return whatsapp_bot.send_message(to_number, message)


def send_whatsapp_decharge_notification(commande):
    """Envoie une notification WhatsApp pour une nouvelle demande de décharge."""
    from .whatsapp_bot import whatsapp_bot
    return whatsapp_bot.send_decharge_notification(commande)


def send_whatsapp_daily_report(produits_bas, date_str):
    """Envoie le rapport quotidien de stock via WhatsApp."""
    from .whatsapp_bot import whatsapp_bot
    return whatsapp_bot.send_daily_report(produits_bas, date_str)


def send_whatsapp_stock_insuffisant(produit, utilisateur_nom, quantite_demandee):
    """Envoie une alerte WhatsApp de stock insuffisant."""
    from .whatsapp_bot import whatsapp_bot
    return whatsapp_bot.send_stock_insuffisant_alert(produit, utilisateur_nom, quantite_demandee)
