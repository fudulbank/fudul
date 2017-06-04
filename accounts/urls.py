from django.conf.urls import url, include
from userena import views as userena_views
from .forms import CustomSignupForm

urlpatterns = [
    url(r'^signup/$', userena_views.signup, {'signup_form': CustomSignupForm, 'template_name': 'accounts/signup.html'}, name="signup"),
    url(r'', include('userena.urls')),
]
