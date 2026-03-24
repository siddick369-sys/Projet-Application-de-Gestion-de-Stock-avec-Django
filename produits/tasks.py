from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Produit
from django.contrib.auth import get_user_model
from .utils import send_whatsapp_message

@shared_task
def envoyer_email_alerte_stock(produit_id, utilisateur_nom, quantite_demandee):
    try:
        produit = Produit.objects.get(id=produit_id)
        User = get_user_model()
        # On envoie l'email à tous les administrateurs
        admins = User.objects.filter(role='admin')
        admin_emails = [admin.email for admin in admins if admin.email]
        
        if not admin_emails:
            return "Aucun email d'administrateur trouvé."

        sujet = f"🚨 Alerte Stock Insuffisant : {produit.nom}"
        message = f"Bonjour,\n\nL'employé {utilisateur_nom} a demandé une décharge de {quantite_demandee} unités de '{produit.nom}', mais il n'en reste que {produit.stock} en stock.\n\nMerci de vérifier le stock."
        
        send_mail(
            sujet,
            message,
            settings.DEFAULT_FROM_EMAIL,
            admin_emails,
            fail_silently=False,
        )

        # Ajout de la notification WhatsApp
        wa_message = f"🚨 ALERTE STOCK BAS : {produit.nom}\nDemande de {quantite_demandee} unités par {utilisateur_nom}. Stock actuel : {produit.stock}."
        send_whatsapp_message(settings.HUB_WHATSAPP_NUMBER, wa_message)

        return f"Email envoyé et WhatsApp envoyé pour {produit.nom}."
    except Produit.DoesNotExist:
        return f"Produit avec id {produit_id} non trouvé."
    except Exception as e:
        return f"Erreur lors de l'envoi de l'email : {str(e)}"


@shared_task
def envoyer_alerte_hub_task(produit_ids, date_jour):
    try:
        from .models import Produit
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.conf import settings

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
        
        # Ajout de la notification WhatsApp
        wa_message = f"📢 ALERTE HUB ({date_jour}): {len(produits)} produits défectueux signalés. Merci de vérifier vos emails."
        send_whatsapp_message(settings.HUB_WHATSAPP_NUMBER, wa_message)
        
        return f"Alerte HUB envoyée via Email et WhatsApp pour {len(produits)} produits."
    except Exception as e:
        return f"Erreur lors de l'envoi de l'alerte HUB : {str(e)}"


@shared_task
def notification_quotidienne_stock():
    try:
        from .models import Produit
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.conf import settings
        from django.utils import timezone
        import logging

        logger = logging.getLogger(__name__)

        # 1. Identifier les produits en manque (stock <= 5 ou selon seuil spécifique)
        produits_bas = Produit.objects.filter(stock__lte=5)
        if not produits_bas.exists():
            return "Aucun produit en manque de stock aujourd'hui."

        # 2. Préparer l'Email de Résumé
        subject = f"Résumé Journalier : {produits_bas.count()} produits en rupture ou stock bas"
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = settings.ADMIN_EMAILS  # Liste d'admins définie dans settings

        html_content = render_to_string('produits/daily_stock_report.html', {
            'produits': produits_bas,
            'nb_alertes': produits_bas.count(),
            'date_jour': timezone.now().strftime('%d/%m/%Y'),
        })
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        email.attach_alternative(html_content, "text/html")
        email.send()

        # 3. Notification WhatsApp (Simulation)
        noms = ", ".join([p.nom for p in produits_bas[:5]])
        if produits_bas.count() > 5:
            noms += "..."
        
        wa_message = f"📢 RÉSUMÉ STOCK BAS ({timezone.now().strftime('%d/%m/%Y')})\n"
        wa_message += f"Sont en manque : {noms}\nTotal: {produits_bas.count()} alertes."
        
        send_whatsapp_message(settings.HUB_WHATSAPP_NUMBER, wa_message)
        
        return f"Notifications envoyées pour {produits_bas.count()} produits."
    except Exception as e:
        return f"Erreur lors de la notification quotidienne : {str(e)}"


@shared_task
def alerte_stock_automatique_task(produit_id):
    try:
        produit = Produit.objects.get(id=produit_id)
        if produit.stock > 5:
            return "Stock remonté, pas d'alerte."

        # Email
        subject = f"⚠️ STOCK CRITIQUE : {produit.nom}"
        message = f"Le stock de '{produit.nom}' est descendu à {produit.stock} unités.\nRéférence: {produit.reference or 'N/A'}\n\nMerci de réapprovisionner rapidement."
        
        # On récupère les emails des admins
        User = get_user_model()
        admin_emails = [admin.email for admin in User.objects.filter(role='admin') if admin.email]
        
        if admin_emails:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, admin_emails)

        # WhatsApp
        wa_message = f"⚠️ STOCK CRITIQUE : {produit.nom} ({produit.stock} restants).\nRéférence: {produit.reference or 'N/A'}."
        send_whatsapp_message(settings.HUB_WHATSAPP_NUMBER, wa_message)

        return f"Alertes automatiques envoyées pour {produit.nom}."
    except Exception as e:
        return f"Erreur alerte automatique : {str(e)}"
