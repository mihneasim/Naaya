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

from Products.NaayaCore.FormsTool.NaayaTemplate import NaayaPageTemplateFile
import basic

class PersistentSchema(basic.Schema, Persistent):
    widget_list_factory = PersistentList

class PersistentWidget(basic.Widget, Persistent):
    def __repr__(self):
        self._p_activate()
        return super(PersistentWidget, self).__repr__()

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
            w = basic.Widget(label=field_name, validator='ascii')
            widget_schema.add(field_name, w)

        form_errors = {}
        tmpl_options = {'input_name': name, 'messages': [], 'errors': []}

        if REQUEST.REQUEST_METHOD == 'POST':
            try:
                form_data = dict(REQUEST.form)
                py_data = widget_schema.to_python(form_data)

            except basic.ConversionError, e:
                tmpl_options['errors'].append(e.msg)
                form_errors.update(e.field_errors)

            else:
                for key, value in py_data.iteritems():
                    setattr(obj, key, value)
                tmpl_options['messages'].append('Properties saved')

        else:
            for field_name in field_names:
                form_data[field_name] = getattr(obj, field_name)

        tmpl_options['form_data'] = form_data
        tmpl_options['form_errors'] = form_errors
        tmpl_options['form_widgets'] = widget_schema.widgets

        return self._manage_edit_widget(REQUEST, **tmpl_options)

    manage_main = PageTemplateFile('zpt/manage_main', globals())

InitializeClass(ZMISchema)

def manage_addZMISchema(context, id):
    context._setObject(id, ZMISchema(id))
    title = property(lambda self: "Schema for %s" % self.id)
#from naaya.core.schema.zopeobj import manage_addZMISchema; manage_addZMISchema(self, 'story')

from Products.Naaya.NySite import NySite
#NySite.nsch_text_field = PageTemplateFile('zpt/text_field', globals())
#NySite.nsch_form = PageTemplateFile('zpt/form', globals())

NaayaPageTemplateFile('zpt/form', globals(),
                      'naaya.core.schema.form')

NaayaPageTemplateFile('zpt/textfield', globals(),
                      'naaya.core.schema.textfield')

NaayaPageTemplateFile('zpt/textarea', globals(),
                      'naaya.core.schema.textarea')

#NaayaPageTemplateFile('zpt/geolocation', globals(),
#                      'naaya.core.schema.geolocation')

#NaayaPageTemplateFile('zpt/geotype', globals(),
#                      'naaya.core.schema.geotype')

NaayaPageTemplateFile('zpt/glossary', globals(),
                      'naaya.core.schema.glossary')

#NaayaPageTemplateFile('zpt/date', globals(),
#                      'naaya.core.schema.date')

#NaayaPageTemplateFile('zpt/checkbox', globals(),
#                      'naaya.core.schema.checkbox')
