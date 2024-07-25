"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=unused-import,import-error
from django.conf.urls import handler404
from django.conf.urls import handler500
from django.conf.urls import include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import re_path

from Appraise.settings import BASE_CONTEXT
from Appraise.settings import DEBUG
from Campaign import views as campaign_views
from Dashboard import views as dashboard_views
from EvalData import views as evaldata_views
from EvalView import views as evalview_views


# HTTP error handlers
# pylint: disable=invalid-name
handler404 = 'Dashboard.views._page_not_found'

handler500 = 'Dashboard.views._server_error'

urlpatterns = [
    re_path(
        r'^admin/taskagenda/reset/(?P<agenda_id>[0-9]+)/$',
        evaldata_views.reset_taskagenda,
        name='reset-taskagenda',
    ),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^$', dashboard_views.frontpage, name='frontpage'),
    re_path(
        r'^dashboard/create-profile/$',
        dashboard_views.create_profile,
        name='create-profile',
    ),
    re_path(
        r'^dashboard/sign-in/$',
        auth_views.LoginView.as_view(
            template_name='Dashboard/signin.html',
            extra_context=BASE_CONTEXT,
        ),
        name='sign-in',
    ),
    re_path(
        (
            r'^dashboard/sso/(?P<username>[a-zA-Z0-9]{10,20})/'
            r'(?P<password>[a-fA-F0-9]{8})/$'
        ),
        dashboard_views.sso_login,
    ),
    re_path(
        r'^dashboard/sign-out/$',
        auth_views.LogoutView.as_view(
            template_name='Dashboard/signout.html',  # TODO: this does not exist!
            extra_context=BASE_CONTEXT,
        ),
        name='sign-out',
    ),
    re_path(
        r'^dashboard/change-password/$',
        auth_views.PasswordChangeView.as_view(
            template_name='Dashboard/change-password.html',
            success_url='/dashboard/',
            extra_context=BASE_CONTEXT,
        ),
        name='change-password',
    ),
    re_path(
        r'^dashboard/update-profile/$',
        dashboard_views.update_profile,
        name='update-profile',
    ),  # TODO: remove?
    re_path(r'^dashboard/$', dashboard_views.dashboard, name='dashboard'),
    re_path(
        r'^data-assessment/$',
        evalview_views.data_assessment,
        name='data-assessment',
    ),
    re_path(
        r'^data-assessment/(?P<code>[a-z]{3})/$',
        evalview_views.data_assessment,
        name='data-assessment',
    ),
    re_path(
        r'^data-assessment/(?P<code>[a-z]{3})/' r'(?P<campaign_name>[a-zA-Z0-9]+)/$',
        evalview_views.data_assessment,
        name='data-assessment',
    ),
    re_path(
        r'^direct-assessment/$',
        evalview_views.direct_assessment,
        name='direct-assessment',
    ),
    re_path(
        r'^direct-assessment/(?P<code>[a-z]{3})/$',
        evalview_views.direct_assessment,
        name='direct-assessment',
    ),
    re_path(
        r'^direct-assessment/(?P<code>[a-z]{3})/' r'(?P<campaign_name>[a-zA-Z0-9]+)/$',
        evalview_views.direct_assessment,
        name='direct-assessment',
    ),
    re_path(
        r'^direct-assessment-context/$',
        evalview_views.direct_assessment_context,
        name='direct-assessment-context',
    ),
    re_path(
        r'^direct-assessment-context/(?P<code>[a-z]{3})/$',
        evalview_views.direct_assessment_context,
        name='direct-assessment-context',
    ),
    re_path(
        r'^direct-assessment-context/(?P<code>[a-z]{3})/'
        r'(?P<campaign_name>[a-zA-Z0-9]+)/$',
        evalview_views.direct_assessment_context,
        name='direct-assessment-context',
    ),
    re_path(
        r'^direct-assessment-document/$',
        evalview_views.direct_assessment_document,
        name='direct-assessment-document',
    ),
    re_path(
        r'^direct-assessment-document/(?P<code>[a-z]{3})/$',
        evalview_views.direct_assessment_document,
        name='direct-assessment-document',
    ),
    re_path(
        r'^direct-assessment-document/(?P<code>[a-z]{3})/'
        r'(?P<campaign_name>[a-zA-Z0-9]+)/$',
        evalview_views.direct_assessment_document,
        name='direct-assessment-document',
    ),
    re_path(
        r'^multimodal-assessment/$',
        evalview_views.multimodal_assessment,
        name='multimodal-assessment',
    ),
    re_path(
        r'^multimodal-assessment/(?P<code>[a-z]{3})/$',
        evalview_views.multimodal_assessment,
        name='multimodal-assessment',
    ),
    re_path(
        r'^multimodal-assessment/(?P<code>[a-z]{3})/'
        r'(?P<campaign_name>[a-zA-Z0-9]+)/$',
        evalview_views.multimodal_assessment,
        name='multimodal-assessment',
    ),
    re_path(
        r'^pairwise-assessment/$',
        evalview_views.pairwise_assessment,
        name='pairwise-assessment',
    ),
    re_path(
        r'^pairwise-assessment/(?P<code>[a-z]{3})/$',
        evalview_views.pairwise_assessment,
        name='pairwise-assessment',
    ),
    re_path(
        r'^pairwise-assessment/(?P<code>[a-z]{3})/'
        r'(?P<campaign_name>[a-zA-Z0-9]+)/$',
        evalview_views.pairwise_assessment,
        name='pairwise-assessment',
    ),
    re_path(
        r'^pairwise-assessment-document/$',
        evalview_views.pairwise_assessment_document,
        name='pairwise-assessment-document',
    ),
    re_path(
        r'^pairwise-assessment-document/(?P<code>[a-z]{3})/$',
        evalview_views.pairwise_assessment_document,
        name='pairwise-assessment-document',
    ),
    re_path(
        r'^pairwise-assessment-document/(?P<code>[a-z]{3})/'
        r'(?P<campaign_name>[a-zA-Z0-9]+)/$',
        evalview_views.pairwise_assessment_document,
        name='pairwise-assessment-document',
    ),
    re_path(
        r'^campaign-status/(?P<campaign_name>[a-zA-Z0-9]+)/'
        r'(?P<sort_key>[0123456])?/?$',
        campaign_views.campaign_status,
        name='campaign_status',
    ),
]

if DEBUG:
    try:
        import debug_toolbar  # type: ignore

        urlpatterns = [
            re_path(r'^__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns  # type: ignore

    except ImportError:
        pass
