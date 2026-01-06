from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self) -> None:
        from .services.recommender_client import recommender_client

        try:
            recommender_client.warmup()
        except Exception:
            # Recommender may not be up yet (e.g. during migrations)
            pass
