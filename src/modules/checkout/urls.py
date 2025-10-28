from django.urls import path, include

urlpatterns = [
    path('', include('modules.checkout.application.web.urls')),
]
