# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ozpcenter', '0005_notification_agency'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='_peer',
            field=models.CharField(max_length=4096, null=True, db_column='peer', blank=True),
        ),
    ]
