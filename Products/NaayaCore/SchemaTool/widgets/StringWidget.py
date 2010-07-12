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
# Alin Voinea, Eau de Web
# Alex Morega, Eau de Web

from AccessControl import ClassSecurityInfo
from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

from Widget import Widget, WidgetError, manage_addWidget

def addStringWidget(container, id="", title="String Widget", REQUEST=None, **kwargs):
    """ Contructor for String widget"""
    return manage_addWidget(StringWidget, container, id, title, REQUEST, **kwargs)

class StringWidget(Widget):
    """ String Widget """

    meta_type = "Naaya Schema String Widget"
    meta_label = "Single line text"
    meta_description = "Free text input box"
    meta_sortorder = 150

    _properties = Widget._properties + (
        {'id': 'width', 'type': 'int', 'mode': 'w',
         'label': 'Display width'},
        {'id': 'size_max', 'type': 'int', 'mode': 'w',
         'label': 'Maximum input width'},
        )

    # Constructor
    _constructors = (addStringWidget,)

    width = 50
    size_max = 0

    def _convert_to_form_string(self, value):
        if isinstance(value, int):
            value = str(value)
        return value

    template = PageTemplateFile('../zpt/property_widget_string', globals())

InitializeClass(StringWidget)
