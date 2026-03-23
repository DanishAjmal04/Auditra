from django.urls import path
from . import views

urlpatterns = [
    path('violations/', views.get_violations),
    path('violations/<int:pk>/status/', views.update_violation_status),
    path('stats/', views.get_stats),
    path('logs/', views.get_logs),
]




from django.urls import path
from . import views

urlpatterns = [
    path('violations/', views.get_violations),
    path('violations/<int:pk>/status/', views.update_violation_status),
    path('stats/', views.get_stats),
    path('logs/', views.get_logs),
    path('simulate/', views.simulate_action),
]