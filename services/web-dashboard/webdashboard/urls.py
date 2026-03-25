"""
URL configuration for webdashboard project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from dashboard import views as dashboard_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/me/', dashboard_views.me, name='auth-me'),
    path('api/challenges/', dashboard_views.challenges, name='challenges'),
    path('api/activities/', dashboard_views.activities, name='activities'),
    path('api/players/', dashboard_views.players, name='players'),
    path('api/ranking/', dashboard_views.ranking, name='ranking'),
    path('api/stats/summary/', dashboard_views.stats_summary, name='stats-summary'),
    path('api/stats/weekly/', dashboard_views.stats_weekly, name='stats-weekly'),
    path('api/stats/distribution/', dashboard_views.stats_distribution, name='stats-distribution'),
    path('api/admin/events/', dashboard_views.admin_events, name='admin-events'),
    path('api/admin/events/<int:event_id>/', dashboard_views.admin_event_detail, name='admin-event-detail'),
    path('api/admin/challenges/', dashboard_views.admin_challenges, name='admin-challenges'),
    path('api/admin/challenges/<int:challenge_id>/', dashboard_views.admin_challenge_detail, name='admin-challenge-detail'),
    path('api/admin/missions/', dashboard_views.admin_missions, name='admin-missions'),
    path('api/admin/activities/', dashboard_views.admin_activities, name='admin-activities'),
    path('api/admin/activities/<int:activity_id>/', dashboard_views.admin_activity_detail, name='admin-activity-detail'),
    path('api/admin/activities/<int:activity_id>/bonus/', dashboard_views.admin_activity_bonus, name='admin-activity-bonus'),
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),  # React root
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)