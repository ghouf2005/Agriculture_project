from django.apps import AppConfig


class AgricultureAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agriculture_app'

    def ready(self):
        # Import signal handlers
        from . import signals  # noqa: F401
