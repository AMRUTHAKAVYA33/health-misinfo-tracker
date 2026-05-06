import json
import warnings

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import HttpResponseRedirect
from django.shortcuts import render

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PredictionRecord
from .services import (
    MODEL_LOAD_ERROR,
    get_last_7_days_stats,
    get_prediction_summary,
    get_top_fake_hashtags,
    model_is_loaded,
    predict_and_save,
    prediction_queryset_for_user,
)

warnings.filterwarnings("ignore")


class PredictFakeNewsView(APIView):
    def post(self, request):
        try:
            result, _record = predict_and_save(request.data.get("text", ""), user=request.user)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "label": result.label.upper(),
                "is_fake": result.is_fake,
                "confidence_percent": result.confidence_percent,
                "probabilities": {
                    "real": round(result.p_real * 100, 1),
                    "fake": round(result.p_fake * 100, 1),
                },
                "threshold": round(result.threshold, 3),
                "hashtags": result.hashtags,
                "overridden_by_debunk": result.overridden_by_debunk,
                "text_preview": result.text[:120] + "..." if len(result.text) > 120 else result.text,
            },
            status=status.HTTP_200_OK,
        )


class DailyStatsView(APIView):
    def get(self, request):
        qs = (
            prediction_queryset_for_user(request.user)
            .annotate(day=TruncDate("created_at"))
            .values("day", "label")
            .annotate(count=Count("id"))
            .order_by("day", "label")
        )

        data = {}
        for row in qs:
            day = row["day"].isoformat()
            label = row["label"]
            count = row["count"]

            data.setdefault(day, {"real": 0, "fake": 0})
            data[day][label] = count

        return Response(data)


class TopHashtagsView(APIView):
    def get(self, request):
        limit = int(request.GET.get("limit", 20))
        top = get_top_fake_hashtags(request.user, limit=limit)
        return Response(top["items"])


def home_view(request):
    return render(request, "home.html")


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("uname")
        email = request.POST.get("email")
        password = request.POST.get("pwd")
        confirm_password = request.POST.get("cpwd")

        if password == confirm_password:
            if User.objects.filter(email=email).exists():
                messages.info(request, "Email already exists")
            elif User.objects.filter(username=username).exists():
                messages.info(request, "Username already exists")
            else:
                User.objects.create_user(username=username, email=email, password=confirm_password)
                messages.info(request, "Account created. Please login.")
                return HttpResponseRedirect("/login/")
        else:
            messages.info(request, "Passwords do not match")

    return render(request, "register.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("uname")
        password = request.POST.get("pwd")
        user = authenticate(username=username, password=password)
        if user:
            auth_login(request, user)
            return HttpResponseRedirect("/")
        messages.info(request, "Invalid credentials")

    return render(request, "login.html")


def logout_view(request):
    auth_logout(request)
    return HttpResponseRedirect("/")


@login_required(login_url="/login/")
def predict_page_view(request):
    result = None
    error = None

    if request.method == "POST":
        try:
            prediction, _record = predict_and_save(request.POST.get("text", ""), user=request.user)
            result = {
                "text": prediction.text,
                "label": prediction.label,
                "is_fake": prediction.is_fake,
                "confidence": round(prediction.confidence, 4),
                "confidence_percent": prediction.confidence_percent,
                "p_real": round(prediction.p_real * 100, 1),
                "p_fake": round(prediction.p_fake * 100, 1),
                "threshold": prediction.threshold,
                "hashtags": prediction.hashtags,
                "overridden_by_debunk": prediction.overridden_by_debunk,
            }
        except (ValueError, RuntimeError) as exc:
            error = str(exc)
            messages.info(request, error)

    daily_stats = get_last_7_days_stats(request.user)
    today_fake_hashtags = get_top_fake_hashtags(request.user, today_only=True)
    recent_predictions = PredictionRecord.objects.filter(user=request.user).order_by("-created_at")[:10]
    daily_stats_rows = zip(
        daily_stats["labels"],
        daily_stats["real"],
        daily_stats["fake"],
    )

    context = {
        "result": result,
        "error": error,
        "summary": get_prediction_summary(request.user),
        "recent_predictions": recent_predictions,
        "daily_stats_rows": daily_stats_rows,
        "daily_stats_json": json.dumps(daily_stats),
        "today_fake_hashtags_json": json.dumps(today_fake_hashtags),
        "model_loaded": model_is_loaded(),
        "model_load_error": MODEL_LOAD_ERROR,
    }

    return render(request, "predict.html", context)
