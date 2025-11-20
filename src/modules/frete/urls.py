from django.urls import path, include

urlpatterns = [
    path('', include('modules.frete.application.web.urls')),
]

