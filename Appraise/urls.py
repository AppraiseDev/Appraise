"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=unused-import,import-error
from django.conf.urls import url, handler404, handler500, include
from django.contrib import admin
from django.contrib.auth import views as auth_views

from Appraise.settings import BASE_CONTEXT, DEBUG
from Campaign import views as campaign_views
from Dashboard import views as dashboard_views
from EvalData import views as evaldata_views
from EvalView import views as evalview_views


# HTTP error handlers
# pylint: disable=invalid-name
handler404 = 'Dashboard.views._page_not_found'

handler500 = 'Dashboard.views._server_error'

urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(
        r'^admin/taskagenda/reset/(?P<agenda_id>[0-9]+)/$',
        evaldata_views.reset_taskagenda,
        name='reset-taskagenda'),

    url(r'^$', dashboard_views.frontpage, name='frontpage'),

    url(
        r'^dashboard/create-profile/$',
        dashboard_views.create_profile,
        name='create-profile'),

    url(
        r'^dashboard/sign-in/$',
        auth_views.LoginView.as_view(
            template_name='Dashboard/signin.html',
            extra_context=BASE_CONTEXT),
        name='sign-in'),

    url(
        (r'^dashboard/sso/(?P<username>[a-zA-Z0-9]{10,12})/'
         r'(?P<password>[a-fA-F0-9]{8})/$'),
        dashboard_views.sso_login),

    url(
        r'^dashboard/sign-out/$',
        auth_views.LogoutView.as_view(
            template_name='Dashboard/signout.html', # TODO: this does not exist!
            extra_context=BASE_CONTEXT),
        name='sign-out'),

    url(
        r'^dashboard/change-password/$',
        auth_views.PasswordChangeView.as_view(
            template_name='Dashboard/change-password.html',
            success_url='/dashboard/',
            extra_context=BASE_CONTEXT),
        name='change-password'),

    url(
        r'^dashboard/update-profile/$',
        dashboard_views.update_profile,
        name='update-profile'), # TODO: remove?

    url(
        r'^dashboard/$',
        dashboard_views.dashboard,
        name='dashboard'),

    url(
        r'^direct-assessment/$',
        evalview_views.direct_assessment,
        name='direct-assessment'),

    url(
        r'^direct-assessment/(?P<code>[a-z]{3})/$',
        evalview_views.direct_assessment,
        name='direct-assessment'),

    url(
        r'^direct-assessment/(?P<code>[a-z]{3})/'
        r'(?P<campaign_name>[a-zA-Z0-9]+)/$',
        evalview_views.direct_assessment,
        name='direct-assessment'),

    url(
        r'^direct-assessment-context/$',
        evalview_views.direct_assessment_context,
        name='direct-assessment-context'),

    url(
        r'^direct-assessment-context/(?P<code>[a-z]{3})/$',
        evalview_views.direct_assessment_context,
        name='direct-assessment-context'),

    url(
        r'^direct-assessment-context/(?P<code>[a-z]{3})/'
        r'(?P<campaign_name>[a-zA-Z0-9]+)/$',
        evalview_views.direct_assessment_context,
        name='direct-assessment-context'),

    url(
        r'^multimodal-assessment/$',
        evalview_views.multimodal_assessment,
        name='multimodal-assessment'),

    url(
        r'^multimodal-assessment/(?P<code>[a-z]{3})/$',
        evalview_views.multimodal_assessment,
        name='multimodal-assessment'),

    url(
        r'^multimodal-assessment/(?P<code>[a-z]{3})/'
        r'(?P<campaign_name>[a-zA-Z0-9]+)/$',
        evalview_views.multimodal_assessment,
        name='multimodal-assessment'),

    url(
        r'^campaign-status/(?P<campaign_name>[a-zA-Z0-9]+)/'
        r'(?P<sort_key>[0123456])?/?$',
        campaign_views.campaign_status,
        name='campaign_status'),
]

if DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns

    except ImportError:
        pass
