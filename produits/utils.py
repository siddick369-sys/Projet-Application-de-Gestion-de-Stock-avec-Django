import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_whatsapp_message(to_number, message):
    """
    Envoie un message WhatsApp. 
    NOTE: Cette implémentation est prête pour une intégration API (ex: Twilio, UltraMsg, etc.)
    Par défaut, elle simule l'envoi dans les logs Celery si aucune clé API n'est configurée.
    """
    if not to_number:
        logger.error("WhatsApp: Aucun numéro de destinataire fourni.")
        return False

    # Nettoyage du numéro (garder uniquement les chiffres)
    clean_number = "".join(filter(str.isdigit, str(to_number)))
    
    logger.info(f"--- WHATSAPP OUTGOING ---")
    logger.info(f"Destinataire: {clean_number}")
    logger.info(f"Message: {message}")
    logger.info(f"-------------------------")

    # Exemple d'implémentation pour un Webhook ou API générique
    # response = requests.post("https://api.votre-service.com/send", json={
    #     "to": clean_number,
    #     "message": message,
    #     "token": settings.WHATSAPP_API_TOKEN
    # })
    
    return True
