import os
from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import joblib
from django.conf import settings
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import PredictionRecord
from .utils import extract_hashtags, is_explicit_debunk


@dataclass(frozen=True)
class PredictionResult:
    text: str
    label: str
    is_fake: bool
    confidence: float
    p_real: float
    p_fake: float
    threshold: float
    hashtags: list[str]
    overridden_by_debunk: bool = False

    @property
    def confidence_percent(self):
        return round(self.confidence * 100, 1)


def get_model_dir():
    configured = os.environ.get("ML_MODEL_DIR")
    if configured:
        return Path(configured)
    return settings.BASE_DIR.parent / "ml_models"


MODEL_DIR = get_model_dir()
MODEL_LOAD_ERROR = None

try:
    vectorizer = joblib.load(MODEL_DIR / "vectorizer.joblib")
    model = joblib.load(MODEL_DIR / "model.joblib")
    try:
        threshold = float(joblib.load(MODEL_DIR / "threshold.joblib"))
    except FileNotFoundError:
        threshold = 0.5
except Exception as exc:
    vectorizer = None
    model = None
    threshold = 0.5
    MODEL_LOAD_ERROR = str(exc)


def model_is_loaded():
    return model is not None and vectorizer is not None


def predict_text(text):
    cleaned_text = (text or "").strip()
    if not cleaned_text:
        raise ValueError("Text is required.")
    if len(cleaned_text) < 10:
        raise ValueError("Please enter a longer health claim or message.")
    if not model_is_loaded():
        detail = f" Model error: {MODEL_LOAD_ERROR}" if MODEL_LOAD_ERROR else ""
        raise RuntimeError(f"Prediction model is not loaded.{detail}")

    x_text = vectorizer.transform([cleaned_text])
    probs = model.predict_proba(x_text)[0]
    class_prob = dict(zip(model.classes_, probs))

    p_real = float(class_prob.get(False, class_prob.get(0, class_prob.get("real", 0.0))))
    p_fake = float(class_prob.get(True, class_prob.get(1, class_prob.get("fake", 0.0))))

    overridden_by_debunk = is_explicit_debunk(cleaned_text)
    if overridden_by_debunk:
        label = "real"
        is_fake = False
        confidence = max(p_real, 1 - p_fake)
    elif p_fake >= threshold:
        label = "fake"
        is_fake = True
        confidence = p_fake
    else:
        label = "real"
        is_fake = False
        confidence = p_real

    return PredictionResult(
        text=cleaned_text,
        label=label,
        is_fake=is_fake,
        confidence=confidence,
        p_real=p_real,
        p_fake=p_fake,
        threshold=threshold,
        hashtags=extract_hashtags(cleaned_text),
        overridden_by_debunk=overridden_by_debunk,
    )


def save_prediction(result, user=None):
    prediction_user = user if getattr(user, "is_authenticated", False) else None
    return PredictionRecord.objects.create(
        user=prediction_user,
        text=result.text,
        label=result.label,
        is_fake=result.is_fake,
        confidence=result.confidence,
        hashtags=",".join(result.hashtags),
    )


def predict_and_save(text, user=None):
    result = predict_text(text)
    record = save_prediction(result, user=user)
    return result, record


def prediction_queryset_for_user(user):
    qs = PredictionRecord.objects.all()
    if getattr(user, "is_authenticated", False):
        return qs.filter(user=user)
    return qs


def get_last_7_days_stats(user=None):
    end = timezone.now().date()
    start = end - timedelta(days=6)
    qs = prediction_queryset_for_user(user).filter(created_at__date__range=[start, end])

    stats = qs.annotate(date=TruncDate("created_at")).values("date").annotate(
        real=Count("id", filter=Q(label="real")),
        fake=Count("id", filter=Q(label="fake")),
    ).order_by("date")

    data = {}
    for i in range(7):
        d = (start + timedelta(days=i)).strftime("%b %d")
        data[d] = {"real": 0, "fake": 0}

    for row in stats:
        d = row["date"].strftime("%b %d")
        data[d]["real"] = row["real"]
        data[d]["fake"] = row["fake"]

    return {
        "labels": list(data.keys()),
        "real": [v["real"] for v in data.values()],
        "fake": [v["fake"] for v in data.values()],
    }


def get_top_fake_hashtags(user=None, limit=6, today_only=False):
    qs = prediction_queryset_for_user(user).filter(is_fake=True)
    if today_only:
        qs = qs.filter(created_at__date=timezone.now().date())

    counter = Counter()
    total = 0
    for tag_str in qs.values_list("hashtags", flat=True):
        if not tag_str:
            continue
        tags = [tag.strip().lstrip("#").lower() for tag in tag_str.split(",") if tag.strip()]
        counter.update(tags)
        total += len(tags)

    top = counter.most_common(limit)
    return {
        "labels": [f"#{tag}" for tag, _ in top],
        "data": [count for _, count in top],
        "total": total,
        "items": [{"hashtag": f"#{tag}", "count": count} for tag, count in top],
    }


def get_prediction_summary(user=None):
    qs = prediction_queryset_for_user(user)
    total = qs.count()
    fake = qs.filter(is_fake=True).count()
    real = qs.filter(is_fake=False).count()
    fake_percent = round((fake / total) * 100, 1) if total else 0
    return {
        "total": total,
        "fake": fake,
        "real": real,
        "fake_percent": fake_percent,
    }
