from django.urls import path
from modules.usuario.application.web.views import (
    RegisterView, 
    LoginView, 
    LogoutView, 
    RefreshTokenView, 
    UpdateUserView,
    ForgotPasswordView,
    ResetPasswordView
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='user-register'),
    path('login/', LoginView.as_view(), name='user-login'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
    path('refresh-token/', RefreshTokenView.as_view(), name='refresh-token'),
    path('update/', UpdateUserView.as_view(), name='user-update'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
]