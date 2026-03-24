from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from .models import Utilisateur
from .forms import *
from produits.models import *
from produits.forms import *
from django.db.models import Q  
from django.core.paginator import Paginator
from django.contrib import messages
import json
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required


User = get_user_model()

import random
from django.utils import timezone
from .tasks import envoyer_email_verification


#  Vue pour l'inscription
def inscription(request):
    if request.user.is_authenticated:
        return rediriger_utilisateur(request.user)
    
    if request.method == "POST":
        form = FormulaireInscription(request.POST)
        if form.is_valid():
            utilisateur = form.save(commit=False)
            # Génération du code de vérification
            code = str(random.randint(100000, 999999))
            utilisateur.verification_code = code
            utilisateur.is_verified = False
            utilisateur.code_generated_at = timezone.now()
            utilisateur.save()
            
            # Envoi du code par email via Celery
            envoyer_email_verification.delay(utilisateur.id, code)
            
            # On stocke l'ID utilisateur dans la session pour la vérification
            request.session['pending_user_id'] = utilisateur.id
            messages.info(request, "Un code de vérification a été envoyé à votre adresse email.")
            return redirect("verifier_compte")
    else:
        form = FormulaireInscription()
    
    return render(request, "users/inscription.html", {"form": form}  )

# Vue pour la vérification du compte
def verifier_compte(request):
    user_id = request.session.get('pending_user_id')
    if not user_id:
        return redirect("inscription")
    
    utilisateur = get_object_or_404(Utilisateur, id=user_id)
    
    if request.method == "POST":
        code_saisi = request.POST.get("code")
        if code_saisi == utilisateur.verification_code:
            utilisateur.is_verified = True
            utilisateur.save()
            login(request, utilisateur)
            del request.session['pending_user_id']
            messages.success(request, "Compte vérifié avec succès ! 🎉")
            return rediriger_utilisateur(utilisateur)
        else:
            messages.error(request, "Code de vérification incorrect.")
            
    return render(request, "users/verification.html", {"utilisateur": utilisateur})

# Vue pour renvoyer le code
def renvoyer_code(request):
    user_id = request.session.get('pending_user_id')
    if not user_id:
        return redirect("inscription")
    
    utilisateur = get_object_or_404(Utilisateur, id=user_id)
    
    # Vérification du cooldown de 2 minutes
    maintenant = timezone.now()
    if utilisateur.code_generated_at:
        difference = (maintenant - utilisateur.code_generated_at).total_seconds()
        if difference < 120:
            temps_restant = int(120 - difference)
            messages.warning(request, f"Veuillez attendre {temps_restant} secondes avant de demander un nouveau code.")
            return redirect("verifier_compte")
            
    # Régénération du code
    code = str(random.randint(100000, 999999))
    utilisateur.verification_code = code
    utilisateur.code_generated_at = timezone.now()
    utilisateur.save()
    
    envoyer_email_verification.delay(utilisateur.id, code)
    messages.success(request, "Un nouveau code a été envoyé.")
    return redirect("verifier_compte")

#  Vue pour la connexion
def connexion(request):
    if request.user.is_authenticated:
        return rediriger_utilisateur(request.user)
    
    if request.method == "POST":
        form = ConnexionForm(request=request, data=request.POST)
        if form.is_valid():
            utilisateur = form.get_user()
            if not utilisateur.is_verified:
                request.session['pending_user_id'] = utilisateur.id
                messages.warning(request, "Veuillez vérifier votre compte avant de vous connecter.")
                return redirect("verifier_compte")
            
            login(request, utilisateur)
            return rediriger_utilisateur(utilisateur)
        else:
            return render(request, "users/connexion.html", {"form": form, "erreur": "Identifiants invalides"})
    else:
        form = ConnexionForm()

    return render(request, "users/connexion.html", {"form": form})


#  Fonction de redirection selon le rôle
def rediriger_utilisateur(utilisateur):
    if utilisateur.role in [Utilisateur.ADMIN, Utilisateur.EMPLOYE]:
        return redirect("dashboard_admin")
    else:
        return redirect("dashboard_client")
    
@login_required(login_url='connexion')
def liste_utilisateurs(request):
    utilisateurs = Utilisateur.objects.all()

    # Vérifie si l'utilisateur connecté peut modifier
    peut_modifier = request.user.is_superuser

    return render(request, "users/liste_user.html", {
        "utilisateurs": utilisateurs,
        "peut_modifier": peut_modifier,
    })

@login_required
def changer_role_utilisateur(request, utilisateur_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Vous n'avez pas la permission.")

    utilisateur = get_object_or_404(Utilisateur, id=utilisateur_id)
    nouveau_role = request.POST.get("role")

    if nouveau_role in dict(Utilisateur.ROLES):
        utilisateur.role = nouveau_role
        utilisateur.save()

    return redirect("liste_utilisateurs")


@login_required
def supprimer_utilisateur(request, utilisateur_id):
    if not request.user.is_superuser:
        return HttpResponseForbidden("Vous n'avez pas la permission.")

    utilisateur = get_object_or_404(Utilisateur, id=utilisateur_id)
    if utilisateur != request.user:  # sécurité pour ne pas se supprimer soi-même
        utilisateur.delete()

    return redirect("liste_utilisateurs")


#  Vue pour la déconnexion
def deconnexion(request):
    logout(request)
    return redirect("connexion")

 
@login_required(login_url='connexion')
def dashboard_admin(request):
    produits = Produit.objects.all()
    categories = Categorie.objects.all()
    users = get_user_model().objects.all()
    form = ProduitForm()

    # Filtre stock faible
    stock = request.GET.get("stock")
    if stock == "faible":
        produits = produits.filter(stock__lte=5)

    # Filtres avancés
    query = request.GET.get("q")
    categorie_id = request.GET.get("categorie")
    tri = request.GET.get("tri")
    ref = request.GET.get("ref")
    unite_f = request.GET.get("unite")
    t_ajout = request.GET.get("type_ajout")

    if query:
        produits = produits.filter(Q(nom__icontains=query) | Q(description__icontains=query))
    if ref:
        produits = produits.filter(reference__icontains=ref)
    if unite_f:
        produits = produits.filter(unite__icontains=unite_f)
    if t_ajout:
        produits = produits.filter(type_ajout=t_ajout)
    if categorie_id:
        produits = produits.filter(categorie_id=categorie_id)
    
    # Tri
    if tri == "nom_asc":
        produits = produits.order_by("nom")
    elif tri == "nom_desc":
        produits = produits.order_by("-nom")
    elif tri == "prix_asc":
        produits = produits.order_by("prix")
    elif tri == "prix_desc":
        produits = produits.order_by("-prix")

    # Pagination
    paginator = Paginator(produits, 5)
    page = request.GET.get('page')
    produits_page = paginator.get_page(page)

    # Récupération des sites existants pour le datalist (lieu_implantation)
    sites_existants = Commande.objects.values_list('nom_du_site', flat=True).exclude(nom_du_site__isnull=True).exclude(nom_du_site="").distinct()

    # Alerte stock popup
    alerte_popup = AlerteStock.objects.exists() and stock != "faible"

    # Statistiques
    stats = {
        'nb_produits': produits.count(),
        'nb_commandes': Commande.objects.count(),
        'nb_users': users.count(),
        'nb_alertes': AlerteStock.objects.count()
    }

    # === GRAPH PRODUITS ===
    tous_les_produits = Produit.objects.all()
    labels = [p.nom for p in tous_les_produits]
    stocks = [p.stock for p in tous_les_produits]
    colors = [
        'rgba(255, 99, 132, 0.7)' if p.stock <= 5 else 'rgba(54, 162, 235, 0.7)'
        for p in tous_les_produits
    ]

    context = {
        'produits': produits_page,
        'categories': categories,
        'stats': stats,
        'form': form,
        'image_form': ImageProduitForm(),
        'alerte_popup': alerte_popup,
        'produits_tous': Produit.objects.all(),
        'labels': json.dumps(labels),
        'stocks': json.dumps(stocks),
        'colors': json.dumps(colors),
        'sites_existants': sites_existants,
        'users_list': Utilisateur.objects.all().order_by('username'),
    }

    return render(request, "users/dashboard_admin.html", context)


@login_required(login_url='connexion')
def dashboard_client(request):
    return render(request, "users/dashboard_client.html") 


@login_required(login_url='connexion')
def historique_actions(request):
    historique = HistoriqueProduit.objects.select_related('utilisateur', 'produit').order_by('-date_action')
    return render(request, "admin/historique_actions.html", {
        "historique": historique
    })

