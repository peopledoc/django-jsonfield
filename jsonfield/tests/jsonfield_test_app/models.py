from decimal import Decimal

from django.db import models, connection
from jsonfield.encoder import JSONEncoder
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


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            raise Exception('Decimal are not allowed !')


class CustomEncoderModel(models.Model):
    json = JSONField(encoder_class=CustomJSONEncoder)
    json_from_path = JSONField(
        encoder_class='jsonfield.tests.jsonfield_test_app.models.CustomJSONEncoder'  # noqa
    )


if connection.vendor == 'postgresql':
    from django.contrib.postgres.fields import JSONField as DjangoJSONField

    class PostgresJSONFieldTestModel(models.Model):
        json_as_jsonb = JSONField()
        json_as_text = JSONField(db_json_type='text')
        json_as_json = JSONField(db_json_type='json')
        django_json = DjangoJSONField()

        class Meta:
            app_label = 'jsonfield'

    class BlankPostgresJSONFieldTestModel(models.Model):
        json_as_jsonb = JSONField(null=True)
        json_as_text = JSONField(null=True, db_json_type='text')
        json_as_json = JSONField(null=True, db_json_type='json')
        django_json = DjangoJSONField(null=True)

        class Meta:
            app_label = 'jsonfield'
