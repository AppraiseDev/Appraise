"""
Appraise evaluation framework

See LICENSE for usage details
"""
# pylint: disable=import-error
from django.contrib import admin

from Dashboard.models import TimedKeyValueData
from Dashboard.models import UserInviteToken

admin.site.register(UserInviteToken)
admin.site.register(TimedKeyValueData)
