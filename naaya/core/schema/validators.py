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

import formencode.validators

validators_library = {}

def register(func):
    assert func.__name__.endswith('_validator')
    validator_name = func.__name__[:-len('_validator')]
    validators_library[validator_name] = func

def get_validator_by_name(name):
    return validators_library[name]

def default_config(widget, validator):
    validator.not_empty = widget.required
    if hasattr(widget, 'initial'):
        validator.if_missing = parse_initial_value(widget.initial)
    return validator

@register
def unicode_validator(widget):
    return default_config(widget, formencode.validators.UnicodeString())

@register
def int_validator(widget):
    return default_config(widget, formencode.validators.Int())

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
