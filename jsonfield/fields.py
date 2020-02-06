from __future__ import unicode_literals
import copy
import json

from django.conf import settings
from django.db import models
from django.db.models.lookups import Exact, IExact, In, Contains, IContains
from django.utils.translation import ugettext_lazy as _

from .utils import _resolve_object_path
from .widgets import JSONWidget
from .forms import JSONFormField


class JSONField(models.Field):
    """
    A field that will ensure the data entered into it is valid JSON.
    """
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("'%s' is not a valid JSON string.")
    }
    description = "JSON object"

    def __init__(self, *args, **kwargs):
        self.encoder_kwargs = {
            'indent': kwargs.pop(
                'indent', getattr(settings, 'JSONFIELD_INDENT', None)),
        }
        self.db_json_type = kwargs.pop('db_json_type', None)
        # This can be an object (probably a class), or a path which can be
        # imported, resulting in an object.
        encoder_class = kwargs.pop(
            'encoder_class',
            getattr(settings, 'JSONFIELD_ENCODER_CLASS', None))
        if encoder_class:
            self.encoder_kwargs['cls'] = _resolve_object_path(encoder_class)

        self.decoder_kwargs = dict(kwargs.pop(
            'decoder_kwargs',
            getattr(settings, 'JSONFIELD_DECODER_KWARGS', {})))
        super(JSONField, self).__init__(*args, **kwargs)

    def default_db_type(self, connection):
        if connection.vendor == 'postgresql':
            return 'jsonb'
        if connection.vendor == 'mysql':
            return 'longtext'
        if connection.vendor == 'oracle':
            return 'long'
        return 'text'

    def get_default(self):
        if self.has_default():
            if callable(self.default):
                return self.default()
            return copy.deepcopy(self.default)

        return super(JSONField, self).get_default()

    def formfield(self, **kwargs):
        defaults = {
            'form_class': JSONFormField,
            'widget': JSONWidget
        }
        defaults.update(**kwargs)
        return super(JSONField, self).formfield(**defaults)

    def get_internal_type(self):
        return 'TextField'

    def db_type(self, connection):
        return self.db_json_type or self.default_db_type(connection)

    def from_db_value(self, value, expression, connection, context=None):
        if value is None or self.db_type(connection) == 'jsonb':
            return value
        return json.loads(value, **self.decoder_kwargs)

    def get_db_prep_value(self, value, connection=None, prepared=None):
        return self.get_prep_value(value)

    def get_prep_value(self, value):
        if value is None:
            if not self.null and self.blank:
                return ""
            return None
        return json.dumps(value, **self.encoder_kwargs)

    def value_to_string(self, obj):
        return self.value_from_object(obj)


class NoPrepareMixin(object):
    def get_prep_lookup(self):
        return self.rhs


class JSONFieldExactLookup(NoPrepareMixin, Exact):
    pass


class JSONFieldIExactLookup(NoPrepareMixin, IExact):
    pass


class JSONFieldInLookup(NoPrepareMixin, In):
    pass


class ContainsLookupMixin(object):
    def get_prep_lookup(self):
        if isinstance(self.rhs, (list, tuple)):
            raise TypeError("Lookup type %r not supported with %s argument" % (
                self.lookup_name, type(self.rhs).__name__
            ))
        if isinstance(self.rhs, dict):
            return self.lhs.output_field.get_prep_value(self.rhs)[1:-1]
        return self.lhs.output_field.get_prep_value(self.rhs)


class JSONFieldContainsLookup(ContainsLookupMixin, Contains):
    pass


class JSONFieldIContainsLookup(ContainsLookupMixin, IContains):
    pass


JSONField.register_lookup(JSONFieldExactLookup)
JSONField.register_lookup(JSONFieldIExactLookup)
JSONField.register_lookup(JSONFieldInLookup)
JSONField.register_lookup(JSONFieldContainsLookup)
JSONField.register_lookup(JSONFieldIContainsLookup)


class TypedJSONField(JSONField):
    """

    """
    def __init__(self, *args, **kwargs):
        self.json_required_fields = kwargs.pop('required_fields', {})
        self.json_validators = kwargs.pop('validators', [])

        super(TypedJSONField, self).__init__(*args, **kwargs)

    def cast_required_fields(self, obj):
        if not obj:
            return
        for field_name, field_type in self.json_required_fields.items():
            obj[field_name] = field_type.to_python(obj[field_name])

    def to_python(self, value):
        value = super(TypedJSONField, self).to_python(value)

        if isinstance(value, list):
            for item in value:
                self.cast_required_fields(item)
        else:
            self.cast_required_fields(value)

        return value

    def validate(self, value, model_instance):
        super(TypedJSONField, self).validate(value, model_instance)

        for v in self.json_validators:
            if isinstance(value, list):
                for item in value:
                    v(item)
            else:
                v(value)
