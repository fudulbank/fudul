from django.shortcuts import render
from userena import views as userena_views
from core import decorators
from .forms import CustomSignupForm,CustomEditProfileForm
from .models import Institution,Profile
from django.contrib.auth.models import User
from userena.utils import get_user_profile
from django.shortcuts import get_object_or_404, render



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

def edit_profile(request,username):
    institutions = Institution.objects.all()
    user = get_object_or_404(User, username__iexact=username)
    profile = get_object_or_404(Profile, user=user)
    user_initial = {'first_name': user.profile.first_name,
                    'last_name': user.profile.last_name}
    form = CustomEditProfileForm(instance=profile,initial=user_initial)
    extra_context = {'form':form, 'profile':profile, 'institutions': institutions}

    return userena_views.profile_edit(request=request,username=username,edit_profile_form=CustomEditProfileForm,
                                      template_name='accounts/profile_form.html',
                                      extra_context=extra_context)

