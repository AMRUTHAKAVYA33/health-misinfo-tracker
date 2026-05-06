from django.urls import path
from .views import (
    PredictFakeNewsView,
    DailyStatsView,
    TopHashtagsView,
    home_view,
    register_view,
    login_view,
    logout_view,
    predict_page_view,
)

urlpatterns = [
    # pages
    path("", home_view, name="home"),
    path("register/", register_view, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("predict-page/", predict_page_view, name="predict-page"),

    # APIs
    path("api/predict/", PredictFakeNewsView.as_view(), name="predict-fake-news"),
    path("api/stats/daily/", DailyStatsView.as_view(), name="daily-stats"),
    path("api/stats/top-hashtags/", TopHashtagsView.as_view(), name="top-hashtags"),
]
