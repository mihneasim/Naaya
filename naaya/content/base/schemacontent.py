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

from zope import interface
from zope import component

from interfaces import INyContentObject
from interfaces import ISchemaContentObject

class SchemaContentAdapter(object):
    interface.implements(ISchemaContentObject)
    component.adapts(INyContentObject)

    def __init__(self, obj):
        self.obj = obj

    def get_schema(self):
        return self.obj._nsch_schema

    def get_schema_properties(self):
        data = {}
        names = set(n for n,w in self.get_schema().widgets)
        for name in names:
            data[name] = getattr(self.obj, name)
        return data

    def save_schema_properties(self, data):
        names = set(n for n,w in self.get_schema().widgets)
        assert set(data.iterkeys()) == names
        for name in names:
            setattr(self.obj, name, data[name])
        return data
