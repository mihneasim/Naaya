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

from naaya.core.schema.zopeobj import ZMISchema, PersistentWidget
from interfaces import INyContentObject
from interfaces import ISchemaContentObject

class SchemaContentAdapter(object):
    interface.implements(ISchemaContentObject)
    component.adapts(INyContentObject)

    def __init__(self, obj):
        self.obj = obj
        self.schema = obj._nsch_schema

    def get_schema_properties(self, lang):
        data = {}
        widgets = dict(self.schema.widgets)
        for name, widget in widgets.iteritems():
            localized = getattr(widget, 'localized', False)
            if localized:
                data[name] = self.obj.getLocalProperty(name, lang)
            else:
                data[name] = getattr(self.obj, name)
        return data

    def save_schema_properties(self, data, lang):
        widgets = dict(self.schema.widgets)
        assert set(data.iterkeys()) == set(widgets.iterkeys())
        for name, widget in widgets.iteritems():
            localized = getattr(widget, 'localized', False)
            if localized:
                self.obj._setLocalPropValue(name, lang, data[name])
            else:
                setattr(self.obj, name, data[name])
        return data

def create_default_zmi_schema(schema_id):
    schema = ZMISchema(schema_id)

    schema.add('title', PersistentWidget(
                        label="Title",
                        validator='unicode',
                        template='naaya.core.schema.textfield',
                        required=True,
                        localized=True))

    schema.add('description', PersistentWidget(
                        label="Description",
                        validator='unicode',
                        template='naaya.core.schema.textarea',
                        localized=True,
                        tinymce=True))

#    schema.add('geo_location', PersistentWidget(
#                        label="Geographical location",
#                        validator='geo',
#                        template='naaya.core.schema.geolocation',
#                        visible=False))

#    schema.add('geo_type', PersistentWidget(
#                        label="Geographical location type",
#                        validator='ascii',
#                        template='naaya.core.schema.geotype',
#                        visible=False))

    schema.add('coverage', PersistentWidget(
                        label="Geographical coverage",
                        validator='unicode',
                        template='naaya.core.schema.glossary',
                        glossary_id='coverage',
                        localized=True))

    schema.add('keywords', PersistentWidget(
                        label="Keywords",
                        validator='unicode',
                        template='naaya.core.schema.glossary',
                        glossary_id='keywords',
                        localized=True))

    schema.add('sortorder', PersistentWidget(
                        label="Sort order",
                        validator='int',
                        template='naaya.core.schema.textfield',
                        initial='int:100',
                        required=True))

#    schema.add('releasedate', PersistentWidget(
#                        label="Release date",
#                        validator='zopedate',
#                        template='naaya.core.schema.date',
#                        required=True))

#    schema.add('discussion', PersistentWidget(
#                        label="Open for comments",
#                        validator='intbool',
#                        template='naaya.core.schema.checkbox'))

    return schema

