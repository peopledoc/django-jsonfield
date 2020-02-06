from django.db import models, connection

from jsonfield.fields import JSONField


class JSONFieldTestModel(models.Model):
    json = JSONField("test", null=True, blank=True)

    class Meta:
        app_label = 'jsonfield'


class JSONFieldWithDefaultTestModel(models.Model):
    json = JSONField(default={"sukasuka": "YAAAAAZ"})

    class Meta:
        app_label = 'jsonfield'


class BlankJSONFieldTestModel(models.Model):
    null_json = JSONField(null=True)
    blank_json = JSONField(blank=True)

    class Meta:
        app_label = 'jsonfield'


class CallableDefaultModel(models.Model):
    json = JSONField(default=lambda: {'x': 2})

    class Meta:
        app_label = 'jsonfield'


if connection.vendor == 'postgresql':
    from django.contrib.postgres.fields import JSONField as PostgresJSONField

    class PostgresParallelModel(models.Model):
        library_json = JSONField()
        postgres_text_json = JSONField(db_json_type='text')
        postgres_json = PostgresJSONField()

        class Meta:
            app_label = 'jsonfield'
