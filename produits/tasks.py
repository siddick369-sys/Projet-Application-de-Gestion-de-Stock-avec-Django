from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Produit, Commande
from django.contrib.auth import get_user_model
from .utils import (
    send_whatsapp_message,
    send_whatsapp_decharge_notification,
    send_whatsapp_daily_report,
    send_whatsapp_stock_insuffisant,
)


@shared_task
def envoyer_email_alerte_stock(produit_id, utilisateur_nom, quantite_demandee):
    try:
        produit = Produit.objects.get(id=produit_id)
        User = get_user_model()
        admins = User.objects.filter(role='admin')
        admin_emails = [admin.email for admin in admins if admin.email]

        if not admin_emails:
            return "Aucun email d'administrateur trouvé."

        sujet = f"🚨 Alerte Stock Insuffisant : {produit.nom}"
        message = (
            f"Bonjour,\n\n"
            f"L'employé {utilisateur_nom} a demandé une décharge de {quantite_demandee} "
            f"unités de '{produit.nom}', mais il n'en reste que {produit.stock} en stock.\n\n"
            f"Merci de vérifier le stock."
        )

        send_mail(
            sujet,
            message,
            settings.DEFAULT_FROM_EMAIL,
            admin_emails,
            fail_silently=False,
        )

        # Notification WhatsApp enrichie
        send_whatsapp_stock_insuffisant(produit, utilisateur_nom, quantite_demandee)

        return f"Email et WhatsApp envoyés pour {produit.nom}."
    except Produit.DoesNotExist:
        return f"Produit avec id {produit_id} non trouvé."
    except Exception as e:
        return f"Erreur lors de l'envoi : {str(e)}"


@shared_task
def envoyer_alerte_hub_task(produit_ids, date_jour):
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags

        produits = Produit.objects.filter(id__in=produit_ids)
        if not produits:
            return "Aucun produit trouvé."

        subject = "Alerte Produit Défectueux - Envoi au HUB"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [settings.HUB_EMAIL]

        html_content = render_to_string('produits/alerte_hub_email.html', {
            'produits': produits,
            'date_jour': date_jour,
        })
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        email.attach_alternative(html_content, "text/html")
        email.send()

        # Notification WhatsApp
        wa_message = (
            f"📢 *ALERTE HUB* ({date_jour})\n\n"
            f"{len(produits)} produit(s) défectueux signalé(s):\n"
        )
        for p in produits:
            wa_message += f"• {p.nom} (Réf: {p.reference or 'N/A'})\n"
        wa_message += "\nMerci de vérifier vos emails pour plus de détails."

        send_whatsapp_message(settings.HUB_WHATSAPP_NUMBER, wa_message)

        return f"Alerte HUB envoyée pour {len(produits)} produits."
    except Exception as e:
        return f"Erreur alerte HUB : {str(e)}"


@shared_task
def notification_quotidienne_stock():
    """
    Notification quotidienne à 8h00 - Rapport des produits en défaut de stock.
    Envoie un email + message WhatsApp aux administrateurs.
    """
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.utils import timezone

        produits_bas = list(Produit.objects.filter(stock__lte=5).order_by('stock'))
        date_str = timezone.now().strftime('%d/%m/%Y')

        if not produits_bas:
            # Envoyer quand même un message de confirmation
            send_whatsapp_message(
                settings.HUB_WHATSAPP_NUMBER,
                f"✅ *RAPPORT STOCK {date_str}*\n\nAucun produit en défaut de stock aujourd'hui. Tout est en ordre!"
            )
            return "Aucun produit en manque de stock aujourd'hui."

        # Email
        subject = f"Résumé Journalier : {len(produits_bas)} produits en rupture ou stock bas"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = settings.ADMIN_EMAILS

        html_content = render_to_string('produits/daily_stock_report.html', {
            'produits': produits_bas,
            'nb_alertes': len(produits_bas),
            'date_jour': date_str,
        })
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        email.attach_alternative(html_content, "text/html")
        email.send()

        # WhatsApp - Rapport quotidien détaillé
        send_whatsapp_daily_report(produits_bas, date_str)

        return f"Notifications quotidiennes envoyées pour {len(produits_bas)} produits."
    except Exception as e:
        return f"Erreur notification quotidienne : {str(e)}"


@shared_task
def alerte_stock_automatique_task(produit_id):
    try:
        produit = Produit.objects.get(id=produit_id)
        if produit.stock > 5:
            return "Stock remonté, pas d'alerte."

        # Email
        subject = f"⚠️ STOCK CRITIQUE : {produit.nom}"
        message = (
            f"Le stock de '{produit.nom}' est descendu à {produit.stock} unités.\n"
            f"Référence: {produit.reference or 'N/A'}\n\n"
            f"Merci de réapprovisionner rapidement."
        )

        User = get_user_model()
        admin_emails = [admin.email for admin in User.objects.filter(role='admin') if admin.email]

        if admin_emails:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, admin_emails)

        # WhatsApp
        wa_message = (
            f"⚠️ *STOCK CRITIQUE*\n\n"
            f"📦 Produit: *{produit.nom}*\n"
            f"🔢 Stock actuel: {produit.stock} {produit.unite}\n"
            f"🏷️ Référence: {produit.reference or 'N/A'}\n\n"
            f"Veuillez réapprovisionner en urgence."
        )
        send_whatsapp_message(settings.HUB_WHATSAPP_NUMBER, wa_message)

        return f"Alertes automatiques envoyées pour {produit.nom}."
    except Exception as e:
        return f"Erreur alerte automatique : {str(e)}"


@shared_task
def notifier_nouvelle_decharge(commande_id):
    """
    Envoie une notification WhatsApp + Email quand une nouvelle demande de décharge
    est soumise par un employé/utilisateur.
    """
    try:
        from django.utils import timezone

        commande = Commande.objects.select_related('utilisateur', 'produit').get(id=commande_id)

        # 1. Notification WhatsApp
        send_whatsapp_decharge_notification(commande)

        # 2. Notification Email aux admins
        User = get_user_model()
        admin_emails = [admin.email for admin in User.objects.filter(role='admin') if admin.email]

        if admin_emails:
            demandeur = commande.utilisateur.get_full_name() or commande.utilisateur.username
            subject = f"📋 Nouvelle demande de décharge - {commande.produit.nom}"
            message = (
                f"Bonjour,\n\n"
                f"Une nouvelle demande de décharge a été soumise:\n\n"
                f"Demandeur: {demandeur}\n"
                f"Produit: {commande.produit.nom}\n"
                f"Quantité: {commande.quantite} {commande.produit.unite}\n"
                f"Site: {commande.nom_du_site or 'Non spécifié'}\n"
                f"Stock disponible: {commande.produit.stock} {commande.produit.unite}\n"
                f"Date: {commande.date_commande.strftime('%d/%m/%Y %H:%M')}\n\n"
                f"Connectez-vous au dashboard pour valider ou refuser cette demande.\n"
                f"{settings.FRONTEND_URL}/produit/commandes/"
            )

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=True,
            )

        return f"Notification décharge envoyée pour commande #{commande_id}."
    except Commande.DoesNotExist:
        return f"Commande #{commande_id} non trouvée."
    except Exception as e:
        return f"Erreur notification décharge : {str(e)}"
