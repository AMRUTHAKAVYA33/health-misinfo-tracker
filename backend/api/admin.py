from django.contrib import admin
from .models import PredictionRecord

@admin.register(PredictionRecord)
class PredictionRecordAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "label", "is_fake", "confidence", "hashtags")
    list_filter = ("label", "is_fake", "created_at")
    search_fields = ("text", "hashtags", "user__username", "user__email")
