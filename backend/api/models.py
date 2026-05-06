from django.db import models
from django.conf import settings

class PredictionRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="prediction_records",
    )
    text = models.TextField()
    label = models.CharField(max_length=10)         # "real" or "fake"
    is_fake = models.BooleanField()
    confidence = models.FloatField(null=True, blank=True)
    hashtags = models.TextField(blank=True)          # store as comma-separated string
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.created_at} - {self.label}"
