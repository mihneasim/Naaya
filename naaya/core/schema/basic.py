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

import formencode.schema

from Products.NaayaCore.backport import namedtuple
from validators import get_validator_by_name

SchemaEntry = namedtuple('SchemaEntry', 'name widget')

class Widget(object):
    required = False
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

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

    def __init__(self):
        self.widgets = []

    def add(self, name, widget):
        self.widgets.append(SchemaEntry(name, widget))

    def to_python(self, str_data):
        """ Shorthand for ``schema.get_validator().to_python(str_data)`` """
        return self.get_validator().to_python(str_data)

#    def from_python(self, py_data):
#        """ Shorthand for ``schema.get_validator().from_python(py_data)`` """
#        return self.get_validator().from_python(py_data)

    def get_validator(self):
        """
        Construct and return a ``formencode.Schema`` object from
        this schema's widgets.
        """
        validators = {}
        for entry in self.widgets:
            validators[entry.name] = self.get_widget_validator(entry.widget)
        return formencode.schema.Schema(**validators)

    def get_widget_validator(self, widget):
        return get_validator_by_name(widget.validator)(widget)
