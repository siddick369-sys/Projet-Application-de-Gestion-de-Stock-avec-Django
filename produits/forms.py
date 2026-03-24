from django import forms
from .models import Produit, ImageProduit, Commande

# Formulaire pour la création/modification des produits
class ProduitForm(forms.ModelForm):
    class Meta:
        model = Produit
        fields = ['nom', 'description', 'prix', 'stock', 'categorie', 'reference', 'unite', 'type_ajout', 'nom_livreur', 'societe_livraison', 'demandeur', 'lieu_implantation']
        widgets = {
            'type_ajout': forms.Select(attrs={'class': 'form-select', 'onchange': 'toggleFields()'}),
            'unite': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: kg, unité, carton'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Référence produit'}),
            'nom_livreur': forms.TextInput(attrs={'class': 'form-control'}),
            'societe_livraison': forms.TextInput(attrs={'class': 'form-control'}),
            'lieu_implantation': forms.TextInput(attrs={'class': 'form-control', 'list': 'siteList'}),
            'demandeur': forms.Select(attrs={'class': 'form-select'}),
        }

# Formulaire pour l'ajout d'images associées à un produit
class ImageProduitForm(forms.ModelForm):
    class Meta:
        model = ImageProduit
        fields = ['image']

class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = ['produit', 'quantite', 'nom_du_site']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-control'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'nom_du_site': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du site'}),
        }
