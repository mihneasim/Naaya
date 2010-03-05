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

from StringIO import StringIO

from persistent.list import PersistentList
from persistent import Persistent

from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

import basic

class PersistentSchema(basic.Schema, Persistent):
    widget_list_factory = PersistentList

class PersistentWidget(basic.Widget, Persistent):
    pass

class ZMISchema(SimpleItem, PersistentSchema):
    meta_type = 'Naaya New Schema'
    manage_options = (
        ({'label': "Widgets", 'action': 'manage_main'},) +
        SimpleItem.manage_options)
    def __init__(self, id):
        super(ZMISchema, self).__init__()
        self.id = id

    def manage_create_widget(self, REQUEST, name):
        """ create a new widget with the given name """

        self.add(name, PersistentWidget(
            label=name,
            validator='unicode',
            initial='unicode:',
            zmi_fields="label template validator initial",
            template='portal_forms/naaya.core.schema.text_field'))

        REQUEST.RESPONSE.redirect(self.absolute_url() + '/manage_main')

    _manage_edit_widget = PageTemplateFile('zpt/manage_edit_widget', globals())
    def manage_edit_widget(self, REQUEST, name):
        """ edit a widget """
        obj = dict(self.widgets)[name]

        widget_schema = basic.Schema()
        form_data = {}
        field_names = ['zmi_fields'] + obj.zmi_fields.split()
        for field_name in field_names:
            w = basic.Widget(label=field_name, validator='unicode')
            widget_schema.add(field_name, w)

        tmpl_options = {'name': name, 'schema': widget_schema, 'messages': []}

        if REQUEST.REQUEST_METHOD == 'POST':
            raise NotImplementedError
            #try:
            #    py_data = widget_schema.to_python(REQUEST.form)
            #except formencode.Invalid, e:
            #    tmpl_options['errors'] = e.error_dict
            #else:
            #    save_form_data(py_data, self)
            #    tmpl_options['message'].append('Properties saved')
        else:
            for field_name in field_names:
                form_data[field_name] = getattr(obj, field_name)
            tmpl_options['form_data'] = form_data

        tmpl_options['render_fields'] = lambda: \
            render_fields(self, widget_schema, form_data)

        return self._manage_edit_widget(REQUEST, **tmpl_options)

    manage_main = PageTemplateFile('zpt/manage_main', globals())

InitializeClass(ZMISchema)

text_field = PageTemplateFile('zpt/text_field', globals())

def render_fields(context, schema, form_data):
    tmpl = text_field.__of__(context)
    output = StringIO()
    for name, widget in schema.widgets:
        output.write(tmpl(name=name, widget=widget, form_data=form_data))
    return output.getvalue()

def manage_addZMISchema(context, id):
    context._setObject(id, ZMISchema(id))
    title = property(lambda self: "Schema for %s" % self.id)
#from naaya.core.schema.zopeobj import manage_addZMISchema; manage_addZMISchema(self, 'story')
