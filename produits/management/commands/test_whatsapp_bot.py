"""
Commande de management pour tester le bot WhatsApp.

Usage:
    python manage.py test_whatsapp_bot                  # Test simple
    python manage.py test_whatsapp_bot --stock           # Test rapport stock
    python manage.py test_whatsapp_bot --decharge        # Test notification décharge
    python manage.py test_whatsapp_bot --daily           # Test rapport quotidien
    python manage.py test_whatsapp_bot --all             # Tous les tests
"""

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Teste le bot WhatsApp avec différents types de notifications"

    def add_arguments(self, parser):
        parser.add_argument('--stock', action='store_true', help='Teste alerte stock critique')
        parser.add_argument('--decharge', action='store_true', help='Teste notification décharge')
        parser.add_argument('--daily', action='store_true', help='Teste rapport quotidien')
        parser.add_argument('--all', action='store_true', help='Exécute tous les tests')
        parser.add_argument('--number', type=str, help='Numéro WhatsApp de test (override)')

    def handle(self, *args, **options):
        from produits.whatsapp_bot import whatsapp_bot

        if options['number']:
            whatsapp_bot.default_number = options['number']

        self.stdout.write(self.style.WARNING(
            f"\nConfiguration WhatsApp Bot:"
            f"\n  Fournisseur: {whatsapp_bot.provider}"
            f"\n  Numéro: {whatsapp_bot.default_number}"
            f"\n  Green API ID: {'Configuré' if getattr(settings, 'GREEN_API_ID_INSTANCE', '') else 'Non configuré'}"
            f"\n  Green API Token: {'Configuré' if getattr(settings, 'GREEN_API_TOKEN', '') else 'Non configuré'}"
            f"\n  CallMeBot Key: {'Configuré' if getattr(settings, 'CALLMEBOT_API_KEY', '') else 'Non configuré'}"
            f"\n"
        ))

        run_all = options['all'] or not any([options['stock'], options['decharge'], options['daily']])

        if run_all or options.get('stock'):
            self._test_message_simple(whatsapp_bot)

        if run_all or options.get('stock'):
            self._test_stock_alert(whatsapp_bot)

        if run_all or options.get('decharge'):
            self._test_decharge_notification(whatsapp_bot)

        if run_all or options.get('daily'):
            self._test_daily_report(whatsapp_bot)

        self.stdout.write(self.style.SUCCESS("\nTests terminés."))

    def _test_message_simple(self, bot):
        self.stdout.write("\n[1/4] Test message simple...")
        result = bot.send_message(
            bot.default_number,
            "🤖 *TEST BOT WHATSAPP*\n\nCeci est un message de test du bot de gestion de stock.\nSi vous recevez ce message, le bot fonctionne correctement!"
        )
        self._print_result(result)

    def _test_stock_alert(self, bot):
        self.stdout.write("\n[2/4] Test alerte stock critique...")
        from produits.models import Produit
        produits_bas = list(Produit.objects.filter(stock__lte=5)[:5])

        if produits_bas:
            result = bot.send_stock_alert(produits_bas)
        else:
            self.stdout.write(self.style.WARNING("  Aucun produit avec stock <= 5. Envoi d'un message de test."))
            result = bot.send_message(
                bot.default_number,
                "📦 *TEST ALERTE STOCK*\n\nAucun produit en défaut de stock actuellement.\nCe message confirme que le bot fonctionne."
            )
        self._print_result(result)

    def _test_decharge_notification(self, bot):
        self.stdout.write("\n[3/4] Test notification décharge...")
        from produits.models import Commande
        derniere_commande = Commande.objects.select_related('utilisateur', 'produit').last()

        if derniere_commande:
            result = bot.send_decharge_notification(derniere_commande)
        else:
            self.stdout.write(self.style.WARNING("  Aucune commande trouvée. Envoi d'un message de test."))
            result = bot.send_message(
                bot.default_number,
                "📋 *TEST NOTIFICATION DÉCHARGE*\n\nAucune demande de décharge trouvée.\nCe message confirme que le bot fonctionne."
            )
        self._print_result(result)

    def _test_daily_report(self, bot):
        self.stdout.write("\n[4/4] Test rapport quotidien...")
        from produits.models import Produit
        from django.utils import timezone

        produits_bas = list(Produit.objects.filter(stock__lte=5).order_by('stock'))
        date_str = timezone.now().strftime('%d/%m/%Y')
        result = bot.send_daily_report(produits_bas, date_str)
        self._print_result(result)

    def _print_result(self, success):
        if success:
            self.stdout.write(self.style.SUCCESS("  ✓ Envoyé avec succès"))
        else:
            self.stdout.write(self.style.ERROR("  ✗ Échec de l'envoi"))
