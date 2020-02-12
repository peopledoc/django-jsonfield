from __future__ import unicode_literals

import copy
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.lookups import Exact, IExact, In, Contains, IContains
from django.utils.translation import ugettext_lazy as _

from .encoder import JSONEncoder
from .forms import JSONFormField
from .utils import resolve_object_from_path
from .widgets import JSONWidget


class JSONField(models.Field):
    """
    A field that will ensure the data entered into it is valid JSON.
    """
    empty_strings_allowed = False
    default_error_messages = {
        'invalid': _("Value must be valid JSON."),
    }
    description = "JSON object"

    def __init__(self, *args, **kwargs):
        self.db_json_type = kwargs.pop('db_json_type', None)

        self.encoder_kwargs = self._encoder_kwargs(
            indent=kwargs.pop('indent', None),
            encoder_class=kwargs.pop('encoder_class', None)
        )
        self.decoder_kwargs = self._decoder_kwargs(
            decoder_kwargs=kwargs.pop('decoder_kwargs', None)
        )

        super(JSONField, self).__init__(*args, **kwargs)

    def _decoder_kwargs(self, decoder_kwargs=None):
        kwargs = dict(getattr(settings, 'JSONFIELD_DECODER_KWARGS', {}))

        if decoder_kwargs:
            kwargs.update(decoder_kwargs)

        return kwargs

    def _encoder_kwargs(self, indent=None, encoder_class=None):
        kwargs = {
            'cls': getattr(settings, 'JSONFIELD_ENCODER_CLASS', JSONEncoder),
            'indent': getattr(settings, 'JSONFIELD_INDENT', None),
            'separators': (',', ':')
        }

        if indent:
            kwargs['indent'] = indent

        # This can be an object (probably a class), or a path which can be
        # imported, resulting in an object.
        if encoder_class:
            kwargs['cls'] = resolve_object_from_path(encoder_class)

        return kwargs

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
        if value is None or self.db_type(connection) in ('json', 'jsonb'):
            return value
        return json.loads(value, **self.decoder_kwargs)

    def get_db_prep_value(self, value, connection=None, prepared=None):
        return self.get_prep_value(value)

    def get_prep_value(self, value):
        if self.null and value is None:
            return None

        try:
            return json.dumps(value, **self.encoder_kwargs)
        except (TypeError, ValueError):
            raise ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value}
            )

    def value_to_string(self, obj):
        return self.value_from_object(obj)

    def validate(self, value, model_instance):
        if not self.null and value is None:
            raise ValidationError(
                self.error_messages['null'],
                code='invalid',
                params={'value': value}
            )

        return super(JSONField, self).validate(value, model_instance)


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
    def get_db_prep_lookup(self, value, connection):
        # jsonb field uses ', ' & ': ' separators natively. So we need to
        # conform to this when serializing the argument.
        if self.lhs.output_field.db_type(connection) == 'jsonb':
            value = json.dumps(value, **dict(
                self.lhs.output_field.encoder_kwargs,
                separators=(', ', ': ')
            ))
        else:
            value = self.lhs.output_field.get_db_prep_value(value)

        return ('%s', [value.strip('{}')])


class JSONFieldContainsLookup(ContainsLookupMixin, Contains):
    pass


class JSONFieldIContainsLookup(ContainsLookupMixin, IContains):
    pass


JSONField.register_lookup(JSONFieldExactLookup)
JSONField.register_lookup(JSONFieldIExactLookup)
JSONField.register_lookup(JSONFieldInLookup)
JSONField.register_lookup(JSONFieldContainsLookup)
JSONField.register_lookup(JSONFieldIContainsLookup)
