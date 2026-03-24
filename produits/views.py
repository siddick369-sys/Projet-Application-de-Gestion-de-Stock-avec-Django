from django.shortcuts import render, redirect , get_object_or_404, HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import urllib.parse
from .forms import ProduitForm, ImageProduitForm, CommandeForm
from .models import *
from django.core.paginator import Paginator
from django.contrib import messages
import csv
import json
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.contrib.auth.decorators import login_required

 
def ajouter_produit(request):
    if not request.user.is_superuser:
        messages.error(request, "Accès non autorisé.")
        return redirect("")

    if request.method == "POST":
        form = ProduitForm(request.POST)
        image_form = ImageProduitForm(request.POST, request.FILES)

        if form.is_valid() and image_form.is_valid():
            produit = form.save()

            # Sauvegarde image
            image = image_form.save(commit=False)
            image.produit = produit
            image.save()

            # Ajout à l’historique
            HistoriqueProduit.objects.create(
                utilisateur=request.user,
                produit=produit,
                action=produit.type_ajout
            )

            # Vérifie le stock
            if produit.stock <= 5:
                AlerteStock.objects.create(
                    produit=produit,
                    stock_actuel=produit.stock
                )

            messages.success(request, "Produit ajouté avec succès ✅ .")
            return redirect("dashboard_admin")

        messages.error(request, "Erreur dans le formulaire.")

    else:
        form = ProduitForm()
        image_form = ImageProduitForm()

    return render(request, "produits/ajout.html", {
        "form": form,
        "image_form": image_form
    })


def modifier_produit(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)

    if request.method == "POST":
        form = ProduitForm(request.POST, instance=produit)
        if form.is_valid():
            form.save()

            if produit.stock <= 5:
                AlerteStock.objects.update_or_create(
                    produit=produit,
                    defaults={"stock_actuel": produit.stock}
                )
            else:
                AlerteStock.objects.filter(produit=produit).delete()

            # Ajout à l’historique
            HistoriqueProduit.objects.create(
                utilisateur=request.user,
                produit=produit,
                action="modification"
            )

            messages.success(request, "Produit modifié avec succès ✅.")
            return redirect('dashboard_admin')
        else:
            errors = ", ".join([f"{k}: {v[0]}" for k, v in form.errors.items()])
            messages.error(request, f"Erreur de modification : {errors}")
            return redirect('dashboard_admin')
    else:
        form = ProduitForm(instance=produit)

    # Note: On ne devrait normalement pas arriver ici en GET car le modal est inclus dans le dashboard.
    # Mais par sécurité, on redirige vers le dashboard si on tente d'accéder directement à l'URL.
    return redirect('dashboard_admin')

def supprimer_produit(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)
    if request.method == "POST":
        nom_produit = produit.nom 
        
        
        # Ajout à l’historique
        HistoriqueProduit.objects.create(
            utilisateur=request.user,
            produit=produit,
            action="suppression"
        )
#Apres la sauvegarde de l'historique, on supprime le produit
        produit.delete()
        
        messages.success(request, f"Le produit '{nom_produit}' a été supprimé avec succès ✅.")
        return redirect('dashboard_admin')
    return render(request, 'produits/supprimer.html', {'produit': produit})

def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="produits.csv"'

    writer = csv.writer(response)
    writer.writerow(['Nom', 'Prix', 'Stock'])  

    for produit in Produit.objects.all():
        writer.writerow([produit.nom, produit.prix, produit.stock])

    # Ajout à l’historique
    HistoriqueProduit.objects.create(
        utilisateur=request.user,
        produit=produit,
        action="exporter en CSV"
    )
    return response

def export_pdf(request):
    produits = Produit.objects.all().order_by('id') 
    template_path = 'produits/pdf_template.html'
    context = {'produits': produits}

    # Préparation de la réponse HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="produits.pdf"'

    # Chargement du template Django
    template = get_template(template_path)
    html = template.render(context)

    # Génération du PDF
    pisa_status = pisa.CreatePDF(html, dest=response)

    # Gestion des erreurs
    if pisa_status.err:
        return HttpResponse('Erreur lors de la génération du PDF', status=500)
    return response



@login_required(login_url='connexion')
def passer_commande(request):
    if request.method == 'POST':
        form = CommandeForm(request.POST)
        if form.is_valid():
            # Enregistrement de la demande de décharge sans réduction de stock immédiate
            commande = form.save(commit=False)
            commande.utilisateur = request.user
            commande.statut = 'en_attente'
            commande.save()

            messages.success(request, f"✅ Demande de décharge pour {commande.quantite} x {commande.produit.nom} enregistrée. En attente de validation.")
            return redirect('liste_commandes')
    else:
        form = CommandeForm()

    return render(request, 'commandes/passer_commande.html', {'form': form})


@login_required(login_url='connexion') 
def liste_commandes(request):
    if request.user.role == 'admin':
        # Les administrateurs voient toutes les demandes
        commandes = Commande.objects.all().order_by('-date_commande')
    else:
        # Les autres utilisateurs voient seulement leurs propres demandes
        commandes = Commande.objects.filter(utilisateur=request.user).order_by('-date_commande')
    
    return render(request, 'commandes/liste_commande.html', {'commandes': commandes})


@login_required(login_url='connexion')
def valider_decharge(request, decharge_id):
    if request.user.role != 'admin':
        messages.error(request, "Accès non autorisé.")
        return redirect('liste_commandes')

    decharge = get_object_or_404(Commande, id=decharge_id)
    produit = decharge.produit

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accepter':
            if produit.stock >= decharge.quantite:
                # Réduction du stock
                produit.stock -= decharge.quantite
                produit.save()

                # Mise à jour du statut
                decharge.statut = 'acseptee'
                decharge.save()

                # Ajout à l’historique
                HistoriqueProduit.objects.create(
                    utilisateur=request.user,
                    produit=produit,
                    action="modification"
                )

                messages.success(request, f"✅ Décharge pour {decharge.produit.nom} acceptée et stock mis à jour.")
            else:
                # Stock insuffisant : Envoi email via Celery
                from .tasks import envoyer_email_alerte_stock
                envoyer_email_alerte_stock.delay(produit.id, decharge.utilisateur.username, decharge.quantite)
                
                messages.error(request, f"❌ Stock insuffisant ({produit.stock} disponibles). Une alerte a été envoyée aux administrateurs.")
        
        elif action == 'refuser':
            decharge.statut = 'refusee'
            decharge.save()
            messages.info(request, "❌ Demande de décharge refusée.")

    return redirect('liste_commandes')


from django.http import JsonResponse
from .tasks import envoyer_email_alerte_stock, envoyer_alerte_hub_task


@login_required(login_url='connexion')
def alerter_hub(request):
    if request.method == 'POST':
        produit_ids = request.POST.getlist('produit_ids')
        if not produit_ids:
            return JsonResponse({'success': False, 'error': "Veuillez sélectionner au moins un produit."}, status=400)

        produits = Produit.objects.filter(id__in=produit_ids)
        date_jour = timezone.now().strftime('%d/%m/%Y')
        
        # 1. Trigger Celery Task (Background Email)
        envoyer_alerte_hub_task.delay(produit_ids, date_jour)

        # 2. Prepare WhatsApp URL (returned for frontend redirection)
        noms_produits = ", ".join([p.nom for p in produits])
        wa_message = f"Le {noms_produits} qui a été sélectionné est déclaré défectueux nous l'avons envoyé le {date_jour} au HUB"
        encoded_message = urllib.parse.quote(wa_message)
        wa_url = f"https://wa.me/{settings.HUB_WHATSAPP_NUMBER}?text={encoded_message}"
        
        return JsonResponse({
            'success': True,
            'wa_url': wa_url,
            'message': "L'email est en cours d'envoi et vous allez être redirigé vers WhatsApp ✅."
        })

    return redirect('dashboard_admin')
