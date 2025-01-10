#!/bin/bash
set -x
echo "import Campaign.models; print(max(Campaign.models.Campaign.objects.values_list('id', flat=True)))" | python3 manage.py shell 2>/dev/null
