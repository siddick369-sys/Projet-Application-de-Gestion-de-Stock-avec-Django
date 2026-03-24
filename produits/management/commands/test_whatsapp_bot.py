"""
Commande de management pour tester et diagnostiquer le bot WhatsApp.

Usage:
    python manage.py test_whatsapp_bot                  # Diagnostic + test simple
    python manage.py test_whatsapp_bot --stock           # Test rapport stock
    python manage.py test_whatsapp_bot --decharge        # Test notification décharge
    python manage.py test_whatsapp_bot --daily           # Test rapport quotidien
    python manage.py test_whatsapp_bot --all             # Tous les tests
    python manage.py test_whatsapp_bot --diagnose        # Diagnostic uniquement
"""

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = "Teste et diagnostique le bot WhatsApp"

    def add_arguments(self, parser):
        parser.add_argument('--stock', action='store_true', help='Teste alerte stock critique')
        parser.add_argument('--decharge', action='store_true', help='Teste notification décharge')
        parser.add_argument('--daily', action='store_true', help='Teste rapport quotidien')
        parser.add_argument('--all', action='store_true', help='Exécute tous les tests')
        parser.add_argument('--diagnose', action='store_true', help='Diagnostic uniquement')
        parser.add_argument('--number', type=str, help='Numéro WhatsApp de test (override)')

    def handle(self, *args, **options):
        from produits.whatsapp_bot import whatsapp_bot

        if options['number']:
            whatsapp_bot.default_number = options['number']

        # Toujours afficher le diagnostic
        self._run_diagnostic(whatsapp_bot)

        if options['diagnose']:
            return

        run_all = options['all'] or not any([options['stock'], options['decharge'], options['daily']])

        if not whatsapp_bot.is_configured():
            self.stdout.write(self.style.ERROR(
                "\n⛔ Le bot n'est pas configuré. Les messages ne seront PAS envoyés."
                "\n   Corrigez la configuration ci-dessus avant de lancer les tests."
                "\n   Utilisez --diagnose pour revoir le diagnostic.\n"
            ))
            return

        self.stdout.write(self.style.SUCCESS("\n✓ Configuration OK - Lancement des tests...\n"))

        if run_all or options.get('stock'):
            self._test_message_simple(whatsapp_bot)
            self._test_stock_alert(whatsapp_bot)

        if run_all or options.get('decharge'):
            self._test_decharge_notification(whatsapp_bot)

        if run_all or options.get('daily'):
            self._test_daily_report(whatsapp_bot)

        self.stdout.write(self.style.SUCCESS("\nTests terminés."))

    def _run_diagnostic(self, bot):
        self.stdout.write(self.style.WARNING("\n" + "=" * 55))
        self.stdout.write(self.style.WARNING("  DIAGNOSTIC WHATSAPP BOT"))
        self.stdout.write(self.style.WARNING("=" * 55))

        # Fournisseur
        provider = bot.provider
        self.stdout.write(f"\n  Fournisseur:       {provider}")
        self.stdout.write(f"  Numéro cible:      {bot.default_number or 'NON DÉFINI'}")

        # Vérification Celery/Redis
        self.stdout.write(f"\n  --- Infrastructure ---")
        celery_url = getattr(settings, 'CELERY_BROKER_URL', '')
        self.stdout.write(f"  Celery Broker:     {celery_url or 'NON CONFIGURÉ'}")

        try:
            import redis
            r = redis.from_url(celery_url)
            r.ping()
            self.stdout.write(self.style.SUCCESS("  Redis:             ✓ Connecté"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Redis:             ✗ Non accessible ({e})"))
            self.stdout.write(self.style.ERROR("                     → Les tâches Celery ne s'exécuteront pas!"))
            self.stdout.write(self.style.ERROR("                     → Lancez: redis-server"))

        # Vérification API
        self.stdout.write(f"\n  --- Configuration API ---")

        if provider == 'green_api':
            id_inst = getattr(settings, 'GREEN_API_ID_INSTANCE', '')
            token = getattr(settings, 'GREEN_API_TOKEN', '')
            self._check_setting("GREEN_API_ID_INSTANCE", id_inst)
            self._check_setting("GREEN_API_TOKEN", token)
            if not id_inst or not token:
                self.stdout.write(self.style.ERROR(
                    "\n  → SOLUTION: Inscrivez-vous sur https://green-api.com (gratuit)"
                    "\n    1. Créez un compte"
                    "\n    2. Créez une instance WhatsApp"
                    "\n    3. Scannez le QR code avec WhatsApp sur votre téléphone (678317658)"
                    "\n    4. Copiez idInstance et apiTokenInstance"
                    "\n    5. Ajoutez dans settings.py ou variables d'environnement:"
                    "\n       export GREEN_API_ID_INSTANCE='votre_id'"
                    "\n       export GREEN_API_TOKEN='votre_token'"
                ))

        elif provider == 'callmebot':
            api_key = getattr(settings, 'CALLMEBOT_API_KEY', '')
            self._check_setting("CALLMEBOT_API_KEY", api_key)
            if not api_key:
                self.stdout.write(self.style.ERROR(
                    "\n  → SOLUTION:"
                    "\n    1. Envoyez 'I allow callmebot to send me messages'"
                    "\n       au numéro WhatsApp +34 644 59 71 67"
                    "\n    2. Récupérez la clé API reçue par message"
                    "\n    3. Ajoutez: export CALLMEBOT_API_KEY='votre_cle'"
                ))

        elif provider == 'pywhatkit':
            try:
                import pywhatkit  # noqa: F401
                self.stdout.write(self.style.SUCCESS("  pywhatkit:         ✓ Installé"))
            except ImportError:
                self.stdout.write(self.style.ERROR("  pywhatkit:         ✗ Non installé"))
                self.stdout.write(self.style.ERROR("  → SOLUTION: pip install pywhatkit"))

        # Vérification configuration globale
        config_error = bot._check_configuration()
        self.stdout.write(f"\n  --- Statut ---")
        if config_error:
            self.stdout.write(self.style.ERROR(f"  ✗ NON OPÉRATIONNEL: {config_error.splitlines()[0]}"))
        else:
            self.stdout.write(self.style.SUCCESS("  ✓ OPÉRATIONNEL - Prêt à envoyer des messages"))

        self.stdout.write("")

    def _check_setting(self, name, value):
        if value:
            masked = value[:4] + "***" + value[-4:] if len(value) > 8 else "***"
            self.stdout.write(self.style.SUCCESS(f"  {name:25s}✓ Configuré ({masked})"))
        else:
            self.stdout.write(self.style.ERROR(f"  {name:25s}✗ MANQUANT"))

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
