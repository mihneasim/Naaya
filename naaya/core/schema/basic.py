# The contents of this file are subject to the Mozilla Public
# License Version 1.1 (the "License"); you may not use this file
# except in compliance with the License. You may obtain a copy of
# the License at http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS
# IS" basis, WITHOUT WARRANTY OF ANY KIND, either express or
# implied. See the License for the specific language governing
# rights and limitations under the License.
#
# The Initial Owner of the Original Code is European Environment
# Agency (EEA).  Portions created by Eau de Web are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Authors:
#
# Alex Morega, Eau de Web

import formencode
import formencode.schema
import formencode.validators

from Products.NaayaCore.backport import namedtuple

SchemaEntry = namedtuple('SchemaEntry', 'name widget')

class Widget(object):
    required = False
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        kws = ', '.join('%s=%r' % kv for kv in self.__dict__.iteritems())
        return 'Widget(%s)' % kws

class Schema(object):
    """
    Naaya Schema class. It's basically a container for Widgets, along
    with some wrapper code over the ``formencode`` library, which does
    most of the work.

      >>> schema = Schema()
      >>> schema.add('title', Widget(label='Title', validator='unicode',
      ...                            required=True))
      >>> schema.add('sortorder', Widget(label='Sort order', validator='int',
      ...                                initial='int:100'))
      >>> py_data = schema.to_python({'title': 'My New Object'})
      >>> sorted(py_data.items())
      [('sortorder', 100), ('title', u'My New Object')]

    """

    widget_list_factory = list

    def __init__(self):
        self.widgets = self.widget_list_factory()

    def add(self, name, widget):
        assert name not in dict(self.widgets)
        self.widgets.append(SchemaEntry(name, widget))

    def to_python(self, str_data):
        """ Shorthand for ``schema.get_validator().to_python(str_data)`` """
        return self.get_validator().to_python(str_data)

    def from_python(self, py_data):
        """ Shorthand for ``schema.get_validator().from_python(py_data)`` """
        return self.get_validator().from_python(py_data)

    def get_validator(self):
        """
        Construct and return a ``formencode.Schema`` object from
        this schema's widgets.
        """
        validators = {}
        for entry in self.widgets:
            validators[entry.name] = self.get_widget_validator(entry.widget)
        return formencode.schema.Schema(allow_extra_fields=True,
                                        filter_extra_fields=True,
                                        **validators)

    def get_widget_validator(self, widget):
        return get_validator_by_name(widget.validator)(widget)


def parse_initial_value(in_value):
    """
    Parse a string to a Python value.

      >>> parse_initial_value('int:13')
      13
      >>> parse_initial_value('str:asdf')
      'asdf'
      >>> parse_initial_value('unicode:')
      u''
      >>> parse_initial_value('bool:True')
      True
      >>> parse_initial_value('None')
      >>> print parse_initial_value('None')
      None
      >>> parse_initial_value('borked')
      Traceback (most recent call last):
          ...
      ValueError: Can't parse value: 'borked'
    """

    cant_parse = lambda: ValueError("Can't parse value: %r" % in_value)

    if in_value == 'None':
        return None
    elif in_value.startswith('str:'):
        return in_value[len('str:'):]
    elif in_value.startswith('unicode:'):
        return unicode(in_value[len('unicode:'):])
    elif in_value.startswith('int:'):
        return int(in_value[len('int:'):])
    elif in_value.startswith('bool:'):
        if in_value in ('bool:', 'bool:False'):
            return False
        elif in_value == 'bool:True':
            return True
        else:
            raise cant_parse()
    else:
        raise cant_parse()


validators_library = {}

def get_validator_by_name(name):
    return validators_library[name]

def default_config(widget, validator):
    validator.not_empty = widget.required
    if hasattr(widget, 'initial'):
        validator.if_missing = parse_initial_value(widget.initial)
    return validator

def unicode_validator(widget):
    return default_config(widget, formencode.validators.UnicodeString())
validators_library['unicode'] = unicode_validator

def check_ascii(value, state):
    if type(value) is not str:
        raise formencode.Invalid('Expected `str` value', value, state)

    try:
        value.decode('ascii')
    except UnicodeDecodeError:
        msg = 'Value must contain only ascii characters'
        raise formencode.Invalid(msg, value, state)

def ascii_validator(widget):
    v = default_config(widget, formencode.validators.String(
                encoding='ascii'))
    v.validate_python = check_ascii
    return v
validators_library['ascii'] = ascii_validator

def int_validator(widget):
    return default_config(widget, formencode.validators.Int())
validators_library['int'] = int_validator
