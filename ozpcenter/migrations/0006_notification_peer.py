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
            name='peer',
            field=models.ForeignKey(blank=True, to='ozpcenter.Profile', related_name='peer_notifications', null=True),
        ),
    ]
