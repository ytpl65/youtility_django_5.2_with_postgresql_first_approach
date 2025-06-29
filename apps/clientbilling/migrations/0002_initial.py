# Generated by Django 5.2.1 on 2025-05-17 07:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clientbilling', '0001_initial'),
        ('onboarding', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='approvedfeature',
            name='cuser',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='%(class)s_cusers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='approvedfeature',
            name='muser',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='%(class)s_musers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='billing',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to='onboarding.bt', verbose_name='Client'),
        ),
        migrations.AddField(
            model_name='billing',
            name='cuser',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='%(class)s_cusers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='billing',
            name='muser',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='%(class)s_musers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='discounts',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to='onboarding.bt', verbose_name='Client'),
        ),
        migrations.AddField(
            model_name='discounts',
            name='cuser',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='%(class)s_cusers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='discounts',
            name='muser',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='%(class)s_musers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='features',
            name='cuser',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='%(class)s_cusers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='features',
            name='muser',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, related_name='%(class)s_musers', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='billing',
            name='feature',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.RESTRICT, to='clientbilling.features', verbose_name='Feature'),
        ),
        migrations.AddField(
            model_name='approvedfeature',
            name='feature',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.RESTRICT, to='clientbilling.features', verbose_name='Feature'),
        ),
        migrations.AddConstraint(
            model_name='discounts',
            constraint=models.UniqueConstraint(fields=('client', 'discount'), name='unique_client_discount'),
        ),
        migrations.AddConstraint(
            model_name='features',
            constraint=models.UniqueConstraint(fields=('name',), name='unique_feature_name'),
        ),
        migrations.AddConstraint(
            model_name='billing',
            constraint=models.UniqueConstraint(fields=('client', 'feature'), name='unique_client_feature'),
        ),
    ]
