from django.urls import path, include

urlpatterns = [
    path('', include('modules.webhook.application.web.urls')),
]

