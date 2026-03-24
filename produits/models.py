from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
 

# Modèle représentant une catégorie de produits
class Categorie(models.Model):
    nom = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nom

# Modèle représentant un produit
class Produit(models.Model):
    nom = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()  # Correction: "quantite" remplacé par "stock"
    categorie = models.ForeignKey(Categorie, on_delete=models.CASCADE, related_name='produits')
    date_ajout = models.DateTimeField(auto_now_add=True)

    # Nouveaux champs pour le suivi détaillé
    reference = models.CharField(max_length=100, blank=True, null=True)
    unite = models.CharField(max_length=50, blank=True, null=True, default="Unité")
    
    TYPE_AJOUT_CHOICES = [
        ('livraison', 'Livraison'),
        ('retour_magasin', 'Retour de magasin'),
    ]
    type_ajout = models.CharField(max_length=20, choices=TYPE_AJOUT_CHOICES, default='livraison')
    
    # Champs pour 'livraison'
    nom_livreur = models.CharField(max_length=255, blank=True, null=True)
    societe_livraison = models.CharField(max_length=255, blank=True, null=True)
    
    # Champs pour 'retour_magasin'
    demandeur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='retours')
    lieu_implantation = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.nom

# Modèle représentant les images d'un produit
class ImageProduit(models.Model):
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='produits/')
    date_ajout = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"Image de {self.produit.nom}"
    

# Historique des actions sur un produit
class HistoriqueProduit(models.Model):
    ACTIONS = (
        ('ajout', 'Ajout'),
        ('livraison', 'Livraison'),
        ('retour_magasin', 'Retour de magasin'),
        ('modification', 'Modification'),
        ('suppression', 'Suppression'),
        ('exporter en CSV', 'Exporter en CSV'),
        ('exporter en PDF', 'Exporter en PDF'),
    )

    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=ACTIONS)
    date_action = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.utilisateur.username} - {self.action} - {self.produit.nom}"

# Alerte automatique si stock bas
class AlerteStock(models.Model):
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE)
    stock_actuel = models.PositiveIntegerField()
    date_alerte = models.DateTimeField(auto_now_add=True)
    seuil = models.PositiveIntegerField(default=5)  # Personnalisable si besoin

    def __str__(self):
        return f"Alerte: {self.produit.nom} stock bas ({self.stock_actuel})"
    

User = get_user_model()

class Commande(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('acseptee', 'Acceptée'),
        ('refusee', 'Refusée'),
    ]

    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField()
    nom_du_site = models.CharField(max_length=255, verbose_name="Nom du site", blank=True, null=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_commande = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utilisateur} - {self.produit.nom} x {self.quantite} ({self.statut})"

# Signaux pour les alertes automatiques
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Produit)
def verifier_stock_bas(sender, instance, **kwargs):
    if instance.stock <= 5:
        # On évite les alertes multiples pour le même produit sur de petites modifications
        # si une alerte récente a déjà été créée
        from .tasks import alerte_stock_automatique_task
        alerte_stock_automatique_task.delay(instance.id)

