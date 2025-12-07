from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AnomalyEvent
from .agent_module import generate_recommendation


@receiver(post_save, sender=AnomalyEvent)
def create_recommendation_on_anomaly(sender, instance: AnomalyEvent, created: bool, **kwargs):
    """Auto-generate an agent recommendation whenever a new anomaly is created."""
    if not created:
        return

    # Avoid duplicate creation if something already attached
    if hasattr(instance, "recommendation"):
        return

    # Run after transaction commit to ensure anomaly persists
    def _make_rec():
        try:
            generate_recommendation(instance)
        except Exception as exc:
            print(f"❌ Failed to generate recommendation for anomaly {instance.id}: {exc}")

    transaction.on_commit(_make_rec)
