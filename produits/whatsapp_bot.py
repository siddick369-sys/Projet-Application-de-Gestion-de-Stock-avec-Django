"""
Bot WhatsApp pour les notifications automatiques de gestion de stock.

Supporte deux fournisseurs d'API :
1. Green API (green-api.com) - Recommandé, gratuit jusqu'à 50 messages/jour
2. CallMeBot (callmebot.com) - Alternative gratuite

Configuration dans settings.py :
    WHATSAPP_PROVIDER = 'green_api'  # ou 'callmebot'
    GREEN_API_ID_INSTANCE = 'votre_id'
    GREEN_API_TOKEN = 'votre_token'
    CALLMEBOT_API_KEY = 'votre_cle'
"""

import requests
import logging
import time
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppBot:
    """Bot WhatsApp unifié avec support multi-fournisseur."""

    def __init__(self):
        self.provider = getattr(settings, 'WHATSAPP_PROVIDER', 'green_api')
        self.default_number = getattr(settings, 'HUB_WHATSAPP_NUMBER', '')
        self.max_retries = 3
        self.retry_delay = 2  # secondes

    def send_message(self, to_number, message):
        """
        Envoie un message WhatsApp via le fournisseur configuré.
        Retourne True si le message a été envoyé avec succès.
        """
        if not to_number:
            logger.error("WhatsApp Bot: Aucun numéro de destinataire fourni.")
            return False

        clean_number = self._clean_number(to_number)

        for attempt in range(1, self.max_retries + 1):
            try:
                if self.provider == 'green_api':
                    success = self._send_via_green_api(clean_number, message)
                elif self.provider == 'callmebot':
                    success = self._send_via_callmebot(clean_number, message)
                else:
                    logger.error(f"WhatsApp Bot: Fournisseur inconnu '{self.provider}'")
                    return False

                if success:
                    logger.info(f"WhatsApp Bot: Message envoyé à {clean_number} (tentative {attempt})")
                    return True

                logger.warning(f"WhatsApp Bot: Échec tentative {attempt}/{self.max_retries}")
            except requests.exceptions.RequestException as e:
                logger.error(f"WhatsApp Bot: Erreur réseau tentative {attempt}: {e}")

            if attempt < self.max_retries:
                time.sleep(self.retry_delay * attempt)

        logger.error(f"WhatsApp Bot: Échec définitif après {self.max_retries} tentatives pour {clean_number}")
        return False

    def send_stock_alert(self, produits_bas):
        """Envoie une alerte de stock bas pour une liste de produits."""
        if not produits_bas:
            return False

        message = "📦 *ALERTE STOCK BAS*\n\n"
        for p in produits_bas:
            ref = p.reference or 'N/A'
            message += f"• *{p.nom}* (Réf: {ref})\n"
            message += f"  Stock actuel: {p.stock} {p.unite}\n"
            if p.stock == 0:
                message += "  ⛔ RUPTURE DE STOCK\n"
            else:
                message += "  ⚠️ Stock critique\n"
            message += "\n"

        message += f"_Total: {len(produits_bas)} produit(s) en alerte_\n"
        message += "Veuillez réapprovisionner rapidement."

        return self.send_message(self.default_number, message)

    def send_decharge_notification(self, commande):
        """Envoie une notification de soumission de demande de décharge."""
        message = "📋 *NOUVELLE DEMANDE DE DÉCHARGE*\n\n"
        message += f"👤 Demandeur: {commande.utilisateur.get_full_name() or commande.utilisateur.username}\n"
        message += f"📦 Produit: *{commande.produit.nom}*\n"
        message += f"🔢 Quantité: {commande.quantite} {commande.produit.unite}\n"
        message += f"📍 Site: {commande.nom_du_site or 'Non spécifié'}\n"
        message += f"📊 Stock disponible: {commande.produit.stock} {commande.produit.unite}\n"
        message += f"📅 Date: {commande.date_commande.strftime('%d/%m/%Y %H:%M')}\n\n"

        if commande.produit.stock < commande.quantite:
            message += "⚠️ *ATTENTION: Stock insuffisant pour cette demande!*\n"

        message += "Connectez-vous pour valider ou refuser cette demande."

        return self.send_message(self.default_number, message)

    def send_daily_report(self, produits_bas, date_str):
        """Envoie le rapport quotidien de stock."""
        message = f"📊 *RAPPORT QUOTIDIEN DE STOCK*\n"
        message += f"📅 {date_str}\n\n"

        if not produits_bas:
            message += "✅ Aucun produit en défaut de stock aujourd'hui."
            return self.send_message(self.default_number, message)

        rupture = [p for p in produits_bas if p.stock == 0]
        critique = [p for p in produits_bas if 0 < p.stock <= 5]

        if rupture:
            message += f"⛔ *RUPTURE DE STOCK ({len(rupture)}):*\n"
            for p in rupture:
                message += f"  • {p.nom} (Réf: {p.reference or 'N/A'})\n"
            message += "\n"

        if critique:
            message += f"⚠️ *STOCK CRITIQUE ({len(critique)}):*\n"
            for p in critique:
                message += f"  • {p.nom}: {p.stock} {p.unite} (Réf: {p.reference or 'N/A'})\n"
            message += "\n"

        message += f"_Total alertes: {len(produits_bas)}_\n"
        message += "Connectez-vous au dashboard pour plus de détails."

        return self.send_message(self.default_number, message)

    def send_stock_insuffisant_alert(self, produit, utilisateur_nom, quantite_demandee):
        """Envoie une alerte quand le stock est insuffisant pour une décharge."""
        message = "🚨 *ALERTE STOCK INSUFFISANT*\n\n"
        message += f"L'employé *{utilisateur_nom}* a demandé une décharge de:\n"
        message += f"📦 Produit: *{produit.nom}*\n"
        message += f"🔢 Quantité demandée: {quantite_demandee}\n"
        message += f"📊 Stock disponible: {produit.stock} {produit.unite}\n"
        message += f"❌ *Manque: {quantite_demandee - produit.stock} {produit.unite}*\n\n"
        message += "Veuillez réapprovisionner ce produit en urgence."

        return self.send_message(self.default_number, message)

    def _send_via_green_api(self, number, message):
        """Envoie via Green API (green-api.com)."""
        id_instance = getattr(settings, 'GREEN_API_ID_INSTANCE', '')
        api_token = getattr(settings, 'GREEN_API_TOKEN', '')

        if not id_instance or not api_token:
            logger.warning("WhatsApp Bot: Green API non configuré. Message logué uniquement.")
            self._log_message(number, message)
            return True

        url = f"https://api.green-api.com/waInstance{id_instance}/sendMessage/{api_token}"

        # Green API attend le format: 237678317658@c.us
        chat_id = f"{number}@c.us"

        payload = {
            "chatId": chat_id,
            "message": message
        }

        response = requests.post(url, json=payload, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if data.get('idMessage'):
                logger.info(f"WhatsApp Bot [Green API]: Message envoyé, ID: {data['idMessage']}")
                return True

        logger.error(f"WhatsApp Bot [Green API]: Erreur {response.status_code} - {response.text}")
        return False

    def _send_via_callmebot(self, number, message):
        """Envoie via CallMeBot API (callmebot.com)."""
        api_key = getattr(settings, 'CALLMEBOT_API_KEY', '')

        if not api_key:
            logger.warning("WhatsApp Bot: CallMeBot non configuré. Message logué uniquement.")
            self._log_message(number, message)
            return True

        url = "https://api.callmebot.com/whatsapp.php"
        params = {
            "phone": number,
            "text": message,
            "apikey": api_key
        }

        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            logger.info("WhatsApp Bot [CallMeBot]: Message envoyé avec succès")
            return True

        logger.error(f"WhatsApp Bot [CallMeBot]: Erreur {response.status_code} - {response.text}")
        return False

    def _clean_number(self, number):
        """Nettoie le numéro de téléphone (garde uniquement les chiffres)."""
        return "".join(filter(str.isdigit, str(number)))

    def _log_message(self, number, message):
        """Log le message quand aucune API n'est configurée (mode développement)."""
        logger.info("=" * 50)
        logger.info("WHATSAPP BOT - MESSAGE (MODE DEV)")
        logger.info(f"Destinataire: {number}")
        logger.info(f"Message:\n{message}")
        logger.info("=" * 50)


# Instance singleton du bot
whatsapp_bot = WhatsAppBot()
