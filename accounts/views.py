from django.shortcuts import render
from userena import views as userena_views
from core import decorators
from django.contrib.auth.models import User
from userena.utils import get_user_profile
from django.shortcuts import get_object_or_404,redirect
from userena.decorators import secure_required
from guardian.decorators import permission_required_or_403
from django.urls import reverse
from userena import signals as userena_signals
from userena.views import ExtraContextTemplateView
from userena.models import UserenaSignup
from userena import settings as userena_settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from userena.utils import signin_redirect
from django.utils.translation import ugettext_lazy as _

from .forms import CustomSignupForm,CustomEditProfileForm,ChangePersonalEmailForm
from .models import *


@decorators.ajax_only
def get_institution_details(request):
    name = request.GET['name']
    institution = Institution.objects.get(name=name)
    groups = {}
    levels = {}

    for group in institution.group_set.all():
        groups[group.pk] = group.name
        levels[group.pk] = []
        for level in group.level_set.all():
            levels[group.pk].append((level.pk, level.name))

    return {'groups':  groups,
            'levels': levels}

def signup(request):
    institutions = Institution.objects.all()
    primary_interests = PrimaryInterest.objects.all()
    extra_context = {'institutions': institutions,
                     'primary_interests': primary_interests} 
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
    context = {'form':form, 'profile':profile, 'institutions': institutions}


    if request.method == 'POST':
        form = CustomEditProfileForm(request.POST, request.FILES, instance=profile)

        if form.is_valid():
            profile = form.save()

            if userena_settings.USERENA_USE_MESSAGES:
                messages.success(request, _('Your profile has been updated.'),
                                 fail_silently=True)

            redirect_to = reverse('userena_profile_detail', kwargs={'username': username})
            return redirect(redirect_to)

    context['form'] = form
    context['profile'] = profile

    return render(request, 'accounts/profile_form.html', context)




@secure_required
@permission_required_or_403('change_user', (User, 'username', 'username'))
def personal_email_change(request, username, email_form=ChangePersonalEmailForm,
                          template_name='accounts/personal_email_form.html', success_url=None,
                          extra_context=None):
    """
    Change email address

    :param username:
        String of the username which specifies the current account.

    :param email_form:
        Form that will be used to change the email address. Defaults to
        :class:`ChangeEmailForm` supplied by userena.

    :param template_name:
        String containing the template to be used to display the email form.
        Defaults to ``userena/email_form.html``.

    :param success_url:
        Named URL where the user will get redirected to when successfully
        changing their email address.  When not supplied will redirect to
        ``userena_email_complete`` URL.

    :param extra_context:
        Dictionary containing extra variables that can be used to render the
        template. The ``form`` key is always the form supplied by the keyword
        argument ``form`` and the ``user`` key by the user whose email address
        is being changed.

    **Context**

    ``form``
        Form that is used to change the email address supplied by ``form``.

    ``account``
        Instance of the ``Account`` whose email address is about to be changed.

    **Todo**

    Need to have per-object permissions, which enables users with the correct
    permissions to alter the email address of others.

    """
    user = get_object_or_404(User, username__iexact=username)
    prev_email = user.profile.alternative_email
    form = email_form(user)

    if request.method == 'POST':
        form = email_form(user, request.POST, request.FILES)

        if form.is_valid():
            form.save()

            if success_url:
                # Send a signal that the email has changed
                userena_signals.email_change.send(sender=None,
                                                  user=user,
                                                  prev_email=prev_email,
                                                  new_email=user.profile.alternative_email)
                redirect_to = success_url
            else: redirect_to = reverse('userena_email_change_complete',
                                        kwargs={'username': user.username})
            return redirect(redirect_to)

    if not extra_context: extra_context = dict()
    extra_context['form'] = form
    extra_context['profile'] = get_user_profile(user=user)
    return ExtraContextTemplateView.as_view(template_name=template_name,
                                            extra_context=extra_context)(request)



@secure_required
def personal_email_confirm(request, confirmation_key,
                           template_name='userena/email_confirm_fail.html',
                           success_url=None, extra_context=None):
    """
    Confirms an email address with a confirmation key.

    Confirms a new email address by running :func:`User.objects.confirm_email`
    method. If the method returns an :class:`User` the user will have his new
    e-mail address set and redirected to ``success_url``. If no ``User`` is
    returned the user will be represented with a fail message from
    ``template_name``.

    :param confirmation_key:
        String with a SHA1 representing the confirmation key used to verify a
        new email address.

    :param template_name:
        String containing the template name which should be rendered when
        confirmation fails. When confirmation is successful, no template is
        needed because the user will be redirected to ``success_url``.

    :param success_url:
        String containing the URL which is redirected to after a successful
        confirmation.  Supplied argument must be able to be rendered by
        ``reverse`` function.

    :param extra_context:
        Dictionary of variables that are passed on to the template supplied by
        ``template_name``.

    """
    user = Profile.objects.confirm_personal_email(confirmation_key)
    if user:
        if userena_settings.USERENA_USE_MESSAGES:
            messages.success(request,'Your email address has been changed.',
                             fail_silently=True)

        if success_url: redirect_to = success_url
        else: redirect_to = reverse('userena_email_confirm_complete',
                                    kwargs={'username': user.username})
        return redirect(redirect_to)
    else:
        if not extra_context: extra_context = dict()
        return ExtraContextTemplateView.as_view(template_name=template_name,
                                                extra_context=extra_context)(request)

