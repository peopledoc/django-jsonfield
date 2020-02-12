import uuid

from datetime import datetime, time, timedelta
from decimal import Decimal
from unittest import skipUnless

from django import forms
from django.core import serializers
from django.core.exceptions import ValidationError
from django.db import connection, models
from django.test import TestCase as DjangoTestCase
from django.utils.encoding import force_text
from django.utils.functional import Promise
from django.utils.timezone import make_aware, is_aware
from django.utils.translation import ugettext_lazy

from jsonfield.fields import JSONField
from jsonfield.tests.jsonfield_test_app.models import (
    JSONFieldTestModel, JSONFieldWithDefaultTestModel,
    BlankJSONFieldTestModel, CallableDefaultModel,
    CustomEncoderModel,
)
from jsonfield.utils import PY3

if PY3:
    from datetime import timezone


class JSONFieldTest(DjangoTestCase):
    def test_json_field(self):
        obj = JSONFieldTestModel(json={'spam': 'eggs'})
        self.assertEqual(obj.json, {'spam': 'eggs'})

    def test_json_field_empty(self):
        obj = JSONFieldTestModel(json='')
        self.assertEqual(obj.json, '')

    def test_json_field_null(self):
        obj = JSONFieldTestModel(json=None)
        self.assertEqual(obj.json, None)

    def test_db_prep_save(self):
        field = JSONField("test")
        field.set_attributes_from_name("json")
        self.assertEqual('null', field.get_db_prep_save(None, connection=None))
        self.assertEqual(
            '{"spam":"eggs"}',
            field.get_db_prep_save({"spam": "eggs"}, connection=None))

    def test_default_db_type(self):
        connection = type('connection', (object,), {})
        field = JSONField()
        connection.vendor = 'postgresql'
        self.assertEqual(field.default_db_type(connection), 'jsonb')
        connection.vendor = 'mysql'
        self.assertEqual(field.default_db_type(connection), 'longtext')
        connection.vendor = 'oracle'
        self.assertEqual(field.default_db_type(connection), 'long')
        connection.vendor = 'random'
        self.assertEqual(field.default_db_type(connection), 'text')

    def test_db_json_type(self):
        field = JSONField(db_json_type='bob')
        self.assertEqual(field.db_type(connection=None), 'bob')

    def test_formfield(self):
        from jsonfield.forms import JSONFormField
        from jsonfield.widgets import JSONWidget
        field = JSONField("test")
        field.set_attributes_from_name("json")
        formfield = field.formfield()
        self.assertEqual(type(formfield), JSONFormField)
        self.assertEqual(type(formfield.widget), JSONWidget)

    def test_formfield_clean_blank(self):
        field = JSONField("test")
        formfield = field.formfield()
        self.assertRaisesMessage(
            forms.ValidationError,
            force_text(formfield.error_messages['required']),
            formfield.clean,
            value='')

    def test_formfield_clean_none(self):
        field = JSONField("test")
        formfield = field.formfield()
        self.assertRaisesMessage(
            forms.ValidationError,
            force_text(formfield.error_messages['required']),
            formfield.clean,
            value=None)

    def test_formfield_null_and_blank_clean_blank(self):
        field = JSONField("test", null=True, blank=True)
        formfield = field.formfield()
        self.assertEqual(formfield.clean(value=''), '')

    def test_formfield_null_and_blank_clean_none(self):
        field = JSONField("test", null=True, blank=True)
        formfield = field.formfield()
        self.assertEqual(formfield.clean(value=None), None)

    def test_formfield_blank_clean_blank(self):
        field = JSONField("test", null=False, blank=True)
        formfield = field.formfield()
        self.assertEqual(formfield.clean(value=''), '')

    def test_formfield_blank_clean_none(self):
        # Hmm, I'm not sure how to do this. What happens if we pass a
        # None to a field that has null=False?
        field = JSONField("test", null=False, blank=True)
        formfield = field.formfield()
        self.assertEqual(formfield.clean(value=None), None)

    def test_default_value(self):
        obj = JSONFieldWithDefaultTestModel.objects.create()
        obj = JSONFieldWithDefaultTestModel.objects.get(id=obj.id)
        self.assertEqual(obj.json, {'sukasuka': 'YAAAAAZ'})

    def test_empty_strings_not_allowed(self):
        field = JSONField()
        self.assertEqual(field.get_default(), None)

    def test_query_equals(self):
        JSONFieldTestModel.objects.create(json={})
        JSONFieldTestModel.objects.create(json={'foo': 'bar'})
        self.assertEqual(2, JSONFieldTestModel.objects.all().count())
        self.assertEqual(
            1, JSONFieldTestModel.objects.exclude(json={}).count())
        self.assertEqual(
            1, JSONFieldTestModel.objects.filter(json={}).count())
        self.assertEqual(
            1, JSONFieldTestModel.objects.filter(json={'foo': 'bar'}).count())

    def test_query_contains(self):
        JSONFieldTestModel.objects.create(json={})
        JSONFieldTestModel.objects.create(json={'foo': 'bar'})
        JSONFieldTestModel.objects.create(json={'foo': ['bar', 'baz']})
        self.assertEqual(
            1, JSONFieldTestModel.objects.filter(
                json__contains={'foo': 'bar'}).count())
        JSONFieldTestModel.objects.create(json={'foo': 'bar', 'baz': 'bing'})
        self.assertEqual(
            2, JSONFieldTestModel.objects.filter(
                json__contains={'foo': 'bar'}).count())
        # This next one is a bit hard to do without proper lookups, which I'm
        # unlikely to implement.
        # self.assertEqual(
        #     1, JSONFieldTestModel.objects.filter(
        #         json__contains={'baz':'bing', 'foo':'bar'}).count())
        self.assertEqual(3, JSONFieldTestModel.objects.filter(
            json__contains='foo').count())

        self.assertEqual(1, JSONFieldTestModel.objects.filter(
            json__contains=['bar', 'baz']).count())

    def test_query_isnull(self):
        JSONFieldTestModel.objects.create(json=None)
        JSONFieldTestModel.objects.create(json={})
        JSONFieldTestModel.objects.create(json={'foo': 'bar'})

        self.assertEqual(
            1, JSONFieldTestModel.objects.filter(json=None).count())
        self.assertEqual(None, JSONFieldTestModel.objects.get(json=None).json)

    def test_jsonfield_blank(self):
        BlankJSONFieldTestModel.objects.create(blank_json='', null_json=None)
        obj = BlankJSONFieldTestModel.objects.get()
        self.assertEqual(None, obj.null_json)
        self.assertEqual("", obj.blank_json)
        obj.save()
        obj = BlankJSONFieldTestModel.objects.get()
        self.assertEqual(None, obj.null_json)
        self.assertEqual("", obj.blank_json)

    def test_callable_default(self):
        CallableDefaultModel.objects.create()
        obj = CallableDefaultModel.objects.get()
        self.assertEqual({'x': 2}, obj.json)

    def test_callable_default_overridden(self):
        CallableDefaultModel.objects.create(json={'x': 3})
        obj = CallableDefaultModel.objects.get()
        self.assertEqual({'x': 3}, obj.json)

    def test_mutable_default_checking(self):
        obj1 = JSONFieldWithDefaultTestModel()
        obj2 = JSONFieldWithDefaultTestModel()

        obj1.json['foo'] = 'bar'
        self.assertNotIn('foo', obj2.json)

    def test_indent(self):
        JSONField('test', indent=2)

    def test_string_is_not_json_decoded(self):
        JSONFieldTestModel.objects.create(json='"foo"')
        self.assertEqual('"foo"', JSONFieldTestModel.objects.get().json)

    def test_serializing(self):
        JSONFieldTestModel.objects.create(json='["foo"]')
        serialized = serializers.serialize(
            "json", JSONFieldTestModel.objects.all())
        self.assertIn('"json": "[\\"foo\\"]"', serialized)


class JSONFieldSaveTest(DjangoTestCase):
    def test_string(self):
        """Test saving an ordinary Python string in our JSONField"""
        json_obj = 'blah blah'
        obj = JSONFieldTestModel.objects.create(json=json_obj)
        new_obj = JSONFieldTestModel.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_float(self):
        """Test saving a Python float in our JSONField"""
        json_obj = 1.23
        obj = JSONFieldTestModel.objects.create(json=json_obj)
        new_obj = JSONFieldTestModel.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_int(self):
        """Test saving a Python integer in our JSONField"""
        json_obj = 1234567
        obj = JSONFieldTestModel.objects.create(json=json_obj)
        new_obj = JSONFieldTestModel.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_decimal(self):
        """Test saving a Python Decimal in our JSONField"""
        json_obj = Decimal(12.34)
        obj = JSONFieldTestModel.objects.create(json=json_obj)
        new_obj = JSONFieldTestModel.objects.get(id=obj.id)

        # here we must know to convert the returned string back to Decimal,
        # since json does not support that format
        self.assertEqual(Decimal(new_obj.json), json_obj)

    def test_uuid(self):
        """Test saving a Python uuid in our JSONField"""
        json_obj = uuid.uuid4()
        obj = JSONFieldTestModel.objects.create(json=json_obj)
        new_obj = JSONFieldTestModel.objects.get(id=obj.id)

        # here we must know to convert the returned string back to Decimal,
        # since json does not support that format
        self.assertEqual(force_text(new_obj.json), force_text(json_obj))

    def test_unserializable(self):
        def unserializable():
            pass

        with self.assertRaises(ValidationError):
            JSONFieldTestModel.objects.create(json=unserializable)

    def test_dict(self):
        json_obj = {'spam': 'eggs'}
        obj = JSONFieldTestModel.objects.create(json=json_obj)
        new_obj = JSONFieldTestModel.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, json_obj)

    def test_list(self):
        """Test storing a JSON list"""
        json_obj = ["my", "list", "of", 1, "objs", {"hello": "there"}]

        obj = JSONFieldTestModel.objects.create(json=json_obj)
        new_obj = JSONFieldTestModel.objects.get(id=obj.id)
        self.assertEqual(new_obj.json, json_obj)

    def test_aware_datetime(self):
        json_obj = make_aware(datetime.now())

        obj = JSONFieldTestModel.objects.create(json=json_obj)
        new_obj = JSONFieldTestModel.objects.get(id=obj.id)
        self.assertEqual(new_obj.json,
                         json_obj.isoformat()[:23] + json_obj.isoformat()[26:])

    @skipUnless(PY3, 'Only works with python 3.x')
    def test_aware_time(self):
        tz = timezone(timedelta(hours=-5), 'EST')
        json_obj = time(tzinfo=tz)

        self.assertTrue(is_aware(json_obj))

        with self.assertRaises(ValidationError):
            JSONFieldTestModel.objects.create(json=json_obj)

    def test_promise(self):
        json_obj = ugettext_lazy('This is a test')
        self.assertTrue(isinstance(json_obj, Promise))

        obj = JSONFieldTestModel.objects.create(json=json_obj)
        new_obj = JSONFieldTestModel.objects.get(id=obj.id)

        self.assertEqual(new_obj.json, force_text(json_obj))

    def test_empty_string(self):
        JSONFieldTestModel.objects.create(id=10, json='')
        obj2 = JSONFieldTestModel.objects.get(id=10)
        self.assertEqual(obj2.json, '')

    def test_null(self):
        JSONFieldTestModel.objects.create(id=10, json=None)
        obj2 = JSONFieldTestModel.objects.get(id=10)
        self.assertEqual(obj2.json, None)

    def test_saving_null(self):
        obj = BlankJSONFieldTestModel.objects.create(
            blank_json='', null_json=None)
        self.assertEqual('', obj.blank_json)
        self.assertEqual(None, obj.null_json)

    def test_custom_encoder(self):
        CustomEncoderModel.objects.create(json=10)
        CustomEncoderModel.objects.create(json_from_path=10)

        with self.assertRaises(Exception) as e:
            CustomEncoderModel.objects.create(json=Decimal(10))

        self.assertEqual(str(e.exception), 'Decimal are not allowed !')

        with self.assertRaises(Exception) as e:
            CustomEncoderModel.objects.create(json_from_path=Decimal(10))

        self.assertEqual(str(e.exception), 'Decimal are not allowed !')

    def test_custom_encoder_from_invalid_path(self):
        with self.assertRaises(ImportError):
            class InvalidModuleEncoderFieldTestModel(models.Model):
                json = JSONField(
                    encoder_class='unknown_module.UnknownJSONEncoder'
                )

        with self.assertRaises(ImportError):
            class InvalidEncoderFieldTestModel(models.Model):
                json = JSONField(
                    encoder_class='jsonfield.encoder.UnknownJSONEncoder'
                )


@skipUnless(connection.vendor == 'postgresql', 'PostgreSQL-specific test')
class PosgresJSONFieldTest(DjangoTestCase):
    def test_dict(self):
        from .jsonfield_test_app.models import PostgresJSONFieldTestModel

        data = {'foo': 'bar'}

        PostgresJSONFieldTestModel.objects.create(
            json_as_jsonb=data,
            json_as_text=data,
            json_as_json=data,
            django_json=data,
        )

        obj = PostgresJSONFieldTestModel.objects.get()
        self.assertEqual(data, obj.json_as_jsonb)
        self.assertEqual(data, obj.json_as_text)
        self.assertEqual(data, obj.json_as_json)
        self.assertEqual(data, obj.django_json)

    def test_none(self):
        from .jsonfield_test_app.models import PostgresJSONFieldTestModel

        PostgresJSONFieldTestModel.objects.create(
            json_as_jsonb=None,
            json_as_text=None,
            json_as_json=None,
            # django contrib jsonfield null=False behave correctly
            django_json={},
        )

        obj = PostgresJSONFieldTestModel.objects.get()
        self.assertIsNone(obj.json_as_jsonb)
        self.assertIsNone(obj.json_as_text)
        self.assertIsNone(obj.json_as_json)
        self.assertEqual({}, obj.django_json)

    def test_none_not_nullable(self):
        from .jsonfield_test_app.models import BlankPostgresJSONFieldTestModel

        BlankPostgresJSONFieldTestModel.objects.create(
            json_as_jsonb=None,
            json_as_text=None,
            json_as_json=None,
            django_json=None,
        )

        obj = BlankPostgresJSONFieldTestModel.objects.get()
        self.assertIsNone(obj.json_as_jsonb)
        self.assertIsNone(obj.json_as_text)
        self.assertIsNone(obj.json_as_json)
        self.assertIsNone(obj.django_json)

    def test_query_contains(self):
        from .jsonfield_test_app.models import PostgresJSONFieldTestModel

        PostgresJSONFieldTestModel.objects.create(
            json_as_jsonb={},
            json_as_text={},
            json_as_json={},
            django_json={},
        )
        PostgresJSONFieldTestModel.objects.create(
            json_as_jsonb={'foo': 'bar'},
            json_as_text={'foo': 'bar'},
            json_as_json={'foo': 'bar'},
            django_json={},
        )
        PostgresJSONFieldTestModel.objects.create(
            json_as_jsonb={'foo': ['bar', 'baz']},
            json_as_text={'foo': ['bar', 'baz']},
            json_as_json={'foo': ['bar', 'baz']},
            django_json={},
        )

        self.assertEqual(
            1, PostgresJSONFieldTestModel.objects.filter(
                json_as_jsonb__contains={'foo': 'bar'}).count())
        self.assertEqual(
            1, PostgresJSONFieldTestModel.objects.filter(
                json_as_text__contains={'foo': 'bar'}).count())
        self.assertEqual(
            1, PostgresJSONFieldTestModel.objects.filter(
                json_as_json__contains={'foo': 'bar'}).count())

        PostgresJSONFieldTestModel.objects.create(
            json_as_jsonb={'foo': 'bar', 'baz': 'bing'},
            json_as_text={'foo': 'bar', 'baz': 'bing'},
            json_as_json={'foo': 'bar', 'baz': 'bing'},
            django_json={},
        )

        self.assertEqual(
            2, PostgresJSONFieldTestModel.objects.filter(
                json_as_jsonb__contains={'foo': 'bar'}).count())
        self.assertEqual(
            2, PostgresJSONFieldTestModel.objects.filter(
                json_as_text__contains={'foo': 'bar'}).count())
        self.assertEqual(
            2, PostgresJSONFieldTestModel.objects.filter(
                json_as_json__contains={'foo': 'bar'}).count())

        self.assertEqual(
            3, PostgresJSONFieldTestModel.objects.filter(
                json_as_jsonb__contains='foo').count())
        self.assertEqual(
            3, PostgresJSONFieldTestModel.objects.filter(
                json_as_text__contains='foo').count())
        self.assertEqual(
            3, PostgresJSONFieldTestModel.objects.filter(
                json_as_json__contains='foo').count())

        self.assertEqual(
            1, PostgresJSONFieldTestModel.objects.filter(
                json_as_jsonb__contains=['bar', 'baz']).count())
        self.assertEqual(
            1, PostgresJSONFieldTestModel.objects.filter(
                json_as_text__contains=['bar', 'baz']).count())
        self.assertEqual(
            1, PostgresJSONFieldTestModel.objects.filter(
                json_as_json__contains=['bar', 'baz']).count())
