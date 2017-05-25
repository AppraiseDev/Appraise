# pylint: disable=C0330
from hashlib import md5
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.views import password_change
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.shortcuts import render, reverse, redirect

from Appraise.settings import STATIC_URL, BASE_CONTEXT
from .models import UserInviteToken

def frontpage(request, extra_context=None):
    """
    Appraise front page.
    """
    context = {
      'active_page': 'frontpage'
    }
    context.update(BASE_CONTEXT)
    if extra_context:
        context.update(extra_context)

    return render(request, 'Dashboard/frontpage.html', context)

def create_profile(request):
    """
    Renders the create profile view.
    """
    errors = None
    username = None
    email = None
    token = None
    languages = []

    focus_input = 'id_username'

    if request.method == "POST":
        username = request.POST.get('username', None)
        email = request.POST.get('email', None)
        token = request.POST.get('token', None)
        languages = request.POST.getlist('languages', None)

        if username and email and token and languages:
            try:
                # Check if given invite token is still active.
                invite = UserInviteToken.objects.filter(token=token)
                if not invite.exists() or not invite[0].active:
                    raise ValueError('invalid_token')

                # We now have a valid invite token...
                invite = invite[0]

                # Check if desired username is already in use.
                current_user = User.objects.filter(username=username)
                if current_user.exists():
                    raise ValueError('invalid_username')

                # Compute set of evaluation languages for this user.
                eval_groups = []

                if False:
                    for eval_language in ('2ces', '2deu', '2eng', '2fin', '2fra', '2hin', '2rus'):
                        if eval_language in languages:
                            eng2xyz = Group.objects.filter(name__endswith=eval_language)
                            if eng2xyz.exists():
                                eval_groups.extend(eng2xyz)

                    # Also, add user to WMT15 group.
                    wmt15_group = Group.objects.filter(name='WMT15')
                    if wmt15_group.exists():
                        eval_groups.append(wmt15_group[0])

                # Create new user account and add to group.
                password = '{0}{1}'.format(
                  invite.group.name[:2].upper(),
                  md5(invite.group.name).hexdigest()[:8]
                )
                user = User.objects.create_user(username, email, password)

                # Update group settings for the new user account.
                user.groups.add(invite.group)
                for eval_group in eval_groups:
                    user.groups.add(eval_group)

                user.save()

                # Disable invite token.
                invite.active = False
                invite.save()

                # Login user and redirect to WMT15 overview page.
                user = authenticate(username=username, password=password)
                login(request, user)
                return redirect('dashboard')

            # For validation errors, invalidate the respective value.
            except ValueError as issue:
                if issue.message == 'invalid_username':
                    username = None

                elif issue.message == 'invalid_token':
                    token = None

                else:
                    username = None
                    email = None
                    token = None
                    languages = None

            # For any other exception, clean up and ask user to retry.
            except:
                username = None
                email = None
                token = None
                languages = None

        # Detect which input should get focus for next page rendering.
        if not username:
            focus_input = 'id_username'
            errors = ['invalid_username']

        elif not email:
            focus_input = 'id_email'
            errors = ['invalid_email']

        elif not token:
            focus_input = 'id_token'
            errors = ['invalid_token']

        elif not languages:
            focus_input = 'id_languages'
            errors = ['invalid_languages']
    
    context = {
      'active_page': "OVERVIEW",
      'errors': errors,
      'focus_input': focus_input,
      'username': username,
      'email': email,
      'token': token,
      'languages': languages,
      'title': 'Create profile',
    }
    context.update(BASE_CONTEXT)
    
    return render(request, 'Dashboard/create-profile.html', context)

@login_required
def dashboard(request):
    """
    Appraise dashboard page.
    """
    context = {
      'active_page': 'dashboard'
    }
    context.update(BASE_CONTEXT)

    return render(request, 'Dashboard/dashboard.html', context)

def NOT_NEEDED_reset_password(request, template_name):
    """
    Renders password change view by connecting to django.contrib.auth.views.
    """
    # Verify that user session is active.  Otherwise, redirect to front page.
    if not request.user.username:
        context = {
          'message': 'You need to sign in to change your password.',
        }
        return frontpage(request, extra_context=context)

    # For increased security Verify that old password was correct.
    if request.method == 'POST':
        old_password = request.POST.get('old_password', None)
        if not request.user.check_password(old_password):
            context = {
              'message': 'Authentication failed, password unchanged.',
            }
            return frontpage(request, extra_context=context)

        password1 = request.POST.get('password1', None)
        password2 = request.POST.get('password2', None)
        if password1 != password2:
            context = {
              'message': 'New passwords did not match, password unchanged.',
            }
            return frontpage(request, extra_context=context)

    post_change_redirect = reverse('Dashboard.frontpage')
    context = {
      'admin_url': reverse('admin:index') if request.user.is_superuser else None,
    }
    context.update(BASE_CONTEXT)

    return password_change(request, template_name,
      post_change_redirect=post_change_redirect,
      password_change_form=AdminPasswordChangeForm,
      extra_context=context
    )

def profile(request):
    pass