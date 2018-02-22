# -*- coding: utf-8 -*-
# Generated by Django 1.9.13 on 2017-11-28 14:51
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0009_filefield'),
        ('testrun', '0002_filefield'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestRunConfigForInstance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('test_runs_limit', models.IntegerField(default=10, verbose_name='test runs limit')),
                ('problem_instance', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='test_run_config', to='contests.ProblemInstance', verbose_name='problem instance')),
            ],
            options={
                'verbose_name': 'test run configuration for instance',
                'verbose_name_plural': 'test run configuration for instances',
            },
        ),
    ]