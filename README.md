# 🇧🇫 IFOAD STORE 2025 (batisé par le groupe )

> **Projet de fin de module "Gestion de données avec Python" – réalisé sous la supervision du Dr Arthur**

---

## 📘 Présentation

IFOAD STORE 2025 est une application web complète développée avec **Django**. Ce projet a été conçu pour permettre la **gestion intelligente de stock**, en intégrant des **fonctionnalités avancées** comme les graphiques, les alertes de stock, la gestion des utilisateurs, des commandes et bien plus encore.

L’objectif principal est de démontrer la maîtrise des outils de gestion de données avec Python tout en répondant à des **besoins concrets d’entreprise**.

---
## 🎯 Objectifs du Projet

- Implémenter un **CRUD complet** sur les produits.
- Créer une **interface utilisateur moderne** avec Bootstrap 5.
- Gérer les utilisateurs avec un **système d'authentification sécurisé**.
- Ajouter des **fonctionnalités avancées** : filtres, tri, alertes de stock, export CSV, dashboard dynamique.
- Utiliser **Chart.js** pour la visualisation des données.
- Notifier les utilisateurs en cas de **stock critique**.

---

## ⚙️ Fonctionnalités principales

- ✅ Gestion des utilisateurs (inscription, **vérification par email**, connexion, accès restreint)
- ✅ Gestion des produits (Référence, Unité, Catégorie, Image, **Type d'entrée**)
- ✅ Gestion des décharges et commandes
- ✅ **Alerte HUB** : Notification immédiate (Email + WhatsApp) pour les produits défectueux
- ✅ **Notifications en temps réel** : Alerte automatique si stock ≤ 5 (Email + WhatsApp) via Celery
- ✅ **Rapport journalier** : Résumé automatique envoyé chaque matin à 8h00
- ✅ Filtrage et recherche avancée (par Référence, Type, Unité)
- ✅ Dashboard Administrateur complet avec graphiques **Chart.js**
- ✅ Exportation des données en CSV et PDF
- ✅ Historique des actions utilisateur (Ajout, Modification, Suppression)

---

- **Backend** : Python 3.11/3.12, Django 5.1.7
- **Tâches de fond** : Celery, Redis (Broker)
- **Frontend** : HTML5, CSS3, Bootstrap 5, Chart.js
- **Base de données** : SQLite
- **Notifications** : Brevo (SMTP/Email), API WhatsApp ready
- **Outils** : Django ORM, Widget Tweaks, xhtml2pdf, Paginator

---

## 🚀 Lancement local (Dernière mise à jour : 24 Mars 2026)

1. **Cloner le projet** :
   ```bash
   git clone https://github.com/siddick369-sys/Projet-Application-de-Gestion-de-Stock-avec-Django.git
   cd Projet-Application-de-Gestion-de-Stock-avec-Django

2.**Créer un environnement virtuel** :

  ```bash
    python -m venv env
    env\Scripts\activate  # Sous Windows


3. **Installer les dépendances** :
    ```bash
    pip install -r requirements.txt
    ```

4. **Lancer Redis** (nécessaire pour Celery) :
    - Sur Windows : Utilisez WSL ou téléchargez le `.msi` de Redis.
    - `redis-server`

5. **Lancer le Worker Celery** (dans un nouveau terminal) :
    ```bash
    celery -A Projet worker -l info --pool=solo
    ```

6. **Lancer Celery Beat** (pour le rapport journalier de 8h - optionnel en test) :
    ```bash
    celery -A Projet beat -l info
    ```

7. **Lancer le serveur Django** :
    ```bash
    python manage.py runserver
    ```

8. **Accéder à l'application** :
    http://127.0.0.1:8000/

💾 ** Base de données **
La base de données db.sqlite3 est intégrée au projet pour permettre une exécution immédiate sans configuration supplémentaire (usage conseillé uniquement pour test ou démonstration).
 
## 👥 Que peut-on faire dans l'application ?

L'application propose un **parcours adapté à chaque type d'utilisateur** selon son rôle : Client, Employé ou Administrateur.

---

###  1. Inscription (Accessible à tous)

Toute personne peut créer un compte via la page d’inscription.

> 📌 Une fois inscrit, l'utilisateur est automatiquement connecté et redirigé selon son rôle :
- Client → vers le tableau de bord client
- Employé ou Admin → vers le tableau de bord administrateur

---

### 🧑‍💼 2. Parcours d’un **Client**

- ✅ Peut **consulter tous les produits disponibles** (pas encore implementer)
- ❌ Ne peut **pas modifier**, **ajouter** ou **supprimer** de produits
- ❌ Ne voit **aucune statistique** ni graphique
- ✅ Interface propre, simple, adaptée à la consultation

> Le client ne voit que les produits. Il n’a **aucun pouvoir de gestion**.

---

### 👷 3. Parcours d’un **Employé**

- ✅ Accès au **tableau de bord admin**
- ✅ Peut **ajouter**, **modifier**  des produits
- ✅ Peut voir les **statistiques**, **alertes de stock**, et **graphiques**
- ❌ Ne peut **pas gérer les utilisateurs**
 

> L’employé est un **gestionnaire opérationnel**, limité à l'inventaire.

---

### 🧑‍💼 4. Parcours d’un **Administrateur**

- ✅ Dispose de **toutes les permissions**
- ✅ Peut **gérer tous les produits** et leurs images
- ✅ Peut **exporter les produits** en CSV ou PDF
- ✅ Peut **voir les alertes de stock**
- ✅ Accède aux **statistiques dynamiques** et **graphiques**
- ✅ Peut **créer des employés via l’administration Django**
- ✅ Peut accéder à l'interface d'administration complète (`/admin`)

> L’administrateur est **le chef de la plateforme** : tout passe par lui.

---

📌 **Résumé comparatif**

| Fonctionnalité                     | Client | Employé | Admin |
|-----------------------------------|--------|---------|-------|
| Voir les produits                 | ✅     | ✅      | ✅    |
| Ajouter un produit                | ❌     | ✅      | ✅    |
| Modifier un produit               | ❌     | ✅      | ✅    |
| Supprimer un produit              | ❌     | ❌      | ✅    |
| Voir les statistiques             | ❌     | ✅      | ✅    |
| Voir les graphiques               | ❌     | ✅      | ✅    |
| Voir les alertes de stock         | ❌     | ✅      | ✅    |
| Exporter CSV / PDF                | ❌     | ✅      | ✅    |
| Gérer les utilisateurs            | ❌     | ❌      | ✅    |

---

Ce système de rôles garantit une **utilisation sécurisée et ciblée** de l'application selon le profil de l'utilisateur.


 ===========🧑‍🤝‍🧑 Équipe de développement================================

Joseph BAGA	(Chef de groupe ) josephbaga45@gmail.com

Ilboudo Vanessa	(Membre)	..........................

Yaméogo Micael	(Membre)	..........................

 
🙏 Remerciements
Merci au Dr Arthur pour l'encadrement et les conseils lors de la réalisation de son cours. Ce travail reflète l'implication de notre groupe et notre volonté de faire de l'informatique notre metier. 




=============================CAPTURE DES PAGES ============================================

## dans le dossier Capturepage