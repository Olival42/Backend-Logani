from django.urls import path
from modules.email.application.web.views import ContactMessageView

app_name = "email"

urlpatterns = [
    path("contact/", ContactMessageView.as_view(), name="contact-message"),
]

