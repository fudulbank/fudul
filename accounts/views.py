from django.shortcuts import render
from userena import views as userena_views
from core import decorators
from .forms import CustomSignupForm
from .models import Institution


@decorators.ajax_only
def get_institution_details(request):
    name = request.GET['name']
    institution = Institution.objects.get(name=name)
    colleges = {}
    batches = {}

    for college in institution.college_set.all():
        colleges[college.pk] = college.name
        batches[college.pk] = []
        for batch in college.batch_set.all():
            batches[college.pk].append((batch.pk, batch.name))

    return {'colleges':  colleges,
            'batches': batches}

def signup(request):
    institutions = Institution.objects.all()
    extra_context = {'institutions': institutions} 
    return userena_views.signup(request, signup_form=CustomSignupForm,
                                template_name='accounts/signup.html',
                                extra_context=extra_context)
