from django.apps import AppConfig
from django.db.models.signals import post_save
from django.dispatch import receiver

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Import inside ready() to avoid circular imports
        try:
            from core.models import Bid
            from core.services.recommender_client import recommender_client
        except ImportError:
            return

        # ---------------------------------------------------------------
        # MOVED: The startup sync logic was removed.
        # Why? It crashes 'migrate' because the table doesn't exist yet.
        # The RecommenderClient now handles syncing automatically.
        # ---------------------------------------------------------------

        # Signal: Automatically push new bids to Recommender in real-time
        @receiver(post_save, sender=Bid)
        def push_new_bid(sender, instance, **kwargs):
            try:
                # Only push if we have a valid amount
                if not instance.amount:
                    return

                interaction = {
                    "user_id": instance.buyer.id,
                    "item_id": instance.item.id,
                    "rating": float(instance.amount)
                }
                # Send as a list, as expected by the server
                recommender_client.load_interactions([interaction])
                print(f"[DEBUG] Pushed new bid to Recommender: {interaction}")
            except Exception as e:
                # Fail silently to keep Auction Service robust
                print(f"[ERROR] Failed to push new bid to Recommender: {e}")