from django.contrib import admin
from django.urls import path, include

from compliance.tokens import AuditraTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from compliance.views import LogoutView


urlpatterns = [

    # Django admin
    path('admin/', admin.site.urls),

    # All compliance APIs
    path('api/', include('compliance.urls')),

    # JWT Login
    path(
        'api/auth/login/',
        AuditraTokenObtainPairView.as_view(),
        name='token_obtain_pair'
    ),

    # JWT Refresh
    path(
        'api/auth/refresh/',
        TokenRefreshView.as_view(),
        name='token_refresh'
    ),

    # JWT Logout
    path(
        'api/auth/logout/',
        LogoutView.as_view(),
        name='logout'
    ),
]