from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

@shared_task
def envoyer_email_verification(user_id, code):
    User = get_user_model()
    try:
        user = User.objects.get(id=user_id)
        subject = "Code de vérification - IFOAD STORE"
        message = f"Bonjour {user.username},\n\nVotre code de vérification est : {code}\nCe code est valable pour finaliser votre inscription.\n\nCordialement,\nL'équipe IFOAD STORE."
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return f"Email de vérification envoyé à {user.email}"
    except User.DoesNotExist:
        return f"Utilisateur avec id {user_id} non trouvé."
    except Exception as e:
        return f"Erreur lors de l'envoi de l'email : {str(e)}"
