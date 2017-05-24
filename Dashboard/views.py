# pylint: disable=C0330
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib.auth.views import password_change
from django.contrib import messages
from django.shortcuts import render, reverse, redirect

from Appraise.settings import STATIC_URL, BASE_CONTEXT

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

def register(request):
    pass

@login_required
def dashboard(request):
    pass

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