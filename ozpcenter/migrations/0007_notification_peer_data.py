# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ozpcenter', '0006_notification_peer'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='peer_data',
            field=models.CharField(null=True, blank=True, max_length=4096),
        ),
    ]
