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

# Zope imports
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view
from OFS.Folder import Folder
from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from DateTime import DateTime

# Naaya imports
from Products.NaayaBase.constants import MESSAGE_SAVEDCHANGES, \
                                         PERMISSION_PUBLISH_OBJECTS
from Products.NaayaCore.managers.utils import genObjectId, genRandomId
from Products.NaayaCore.managers.utils import utils

from geo import Geo

WIDGET_ID_SUFFIX = '-property'

DATA_TYPES = {
    'int': int,
    'str': unicode,
    'float': float,
    'bool': bool,
    'date': DateTime,
    'geo': Geo,
    'list': list,
}


def propname_from_widgetid(widgetid):
    if not widgetid.endswith(WIDGET_ID_SUFFIX):
        raise ValueError('Widget ID does not end with '
            'WIDGET_ID_SUFFIX ("%s")' % WIDGET_ID_SUFFIX)
    return widgetid[:-len(WIDGET_ID_SUFFIX)]

def widgetid_from_propname(propname):
    """ construct a widget's id based on the property's name """
    # we avoid using "_" as a separator because Localizer will
    # recognise it as a separator and throw manage_addWidget in
    # an endless loop
    return propname + WIDGET_ID_SUFFIX


class WidgetError(Exception):
    """Widget error"""
    pass

def manage_addWidget(klass, container, id="", title=None, REQUEST=None, **kwargs):
    """Add widget"""
    if not title:
        title = str(klass)
    if not id:
        # prevent any name clashes by using the 'w_' prefix
        id = 'w_' + genObjectId(title)

    idSuffix = ''
    while (id+idSuffix in container.objectIds() or
           container._getOb(id+idSuffix, None) is not None):
        idSuffix = genRandomId(p_length=4)
    id = id + idSuffix

    # Get selected language
    lang = None
    if REQUEST is not None:
        lang = REQUEST.form.get('lang', None)
    if not lang:
        lang = kwargs.get('lang', container.gl_get_selected_language())
    widget = klass(id, title=title, lang=lang, **kwargs)

    container._setObject(id, widget)
    widget = container._getOb(id)
    if REQUEST is not None:
        REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)
    return id

class Widget(Folder):
    """ Abstract class for widget """
    meta_type = 'Naaya Schema Widget'
    meta_sortorder = 100 # used to sort the list of available widget types

    security = ClassSecurityInfo()

    # Subobjects
    all_meta_types = ()

    # ZMI Tabs
    manage_options=(
        {'label':'Properties', 'action':'manage_propertiesForm',
         'help':('OFSP','Properties.stx')},
        {'label':'Contents', 'action':'manage_main',
         'help':('OFSP','ObjectManager_Contents.stx')},
        )

    # Properties
    _properties=(
        {'id':'sortorder', 'type': 'int', 'mode':'w', 'label': 'Sort order'},
        {'id':'required', 'type': 'boolean', 'mode':'w', 'label': 'Required widget'},
        {'id':'default','mode':'w', 'type': 'string', 'label': 'Default value'},
        {'id':'localized', 'mode':'w', 'type': 'boolean'},
        {'id':'data_type', 'mode':'w', 'type': 'string'},
        {'id':'visible', 'mode':'w', 'type': 'boolean'},
    )

    multiple_form_values = False

    sortorder = 100
    required = False
    default = ''
    localized = False
    data_type = 'str'
    visible = True

    def __init__(self, id, title='', lang=None):
        Folder.__init__(self, id=id)
        self.title = title

    def _setProperty(self, id, value, *args, **kwargs):
        if id == 'default':
            self.default = self.convertValue(value)
        else:
            super(Widget, self)._setProperty(id, value, *args, **kwargs)

    def _setPropValue(self, id, value):
        if getattr(self, id) != value:
            super(Widget, self)._setPropValue(id, value)

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'saveProperties')
    def saveProperties(self, REQUEST=None, **kwargs):
        """ Update widget properties"""
        if REQUEST:
            kwargs.update(REQUEST.form)

        _lang = kwargs.get('lang', self.get_selected_language())
        _required = bool(kwargs.get('required'))

        if not _required and self.must_be_mandatory():
            raise ValueError('Can not make property "%s" non-mandatory'
                % self.prop_name())

        self.title = kwargs.get('title')
        self.required = _required
        self.sortorder = int(kwargs.get('sortorder'))
        self.visible = bool(kwargs.get('visible'))

        if REQUEST:
            self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
            return REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)

    def must_be_mandatory(self):
        return (self.get_default_definition() or {}).get('required', False)

    security.declarePrivate('get_default_definition')
    def get_default_definition(self):
        default_definition = self.getParentNode().getDefaultDefinition()
        if default_definition is not None:
            return default_definition.get(self.prop_name(), None)
        return None

    #
    # To be implemented or ovewritten (if needed) by widget concrete classes.
    #
    def isEmptyDatamodel(self, value):
        return not bool(value)

    def parseFormData(self, data):
        return data

    def validateDatamodel(self, value):
        """Validate datamodel"""
        if self.required and self.isEmptyDatamodel(value):
            raise WidgetError('Value required for "%s"' % self.title)

    security.declarePrivate('getPropertyType')
    def getDataType(self):
        return DATA_TYPES[self.data_type]

    security.declarePrivate('convertValue')
    def convertValue(self, value):
        convert = DATA_TYPES[self.data_type]
        try:
            if value in ('', None):
                # special cases for empty values
                if convert in (int, float):
                    return convert(0)
                elif convert is DateTime:
                    return None
            return convert(value)
        except ValueError:
            raise WidgetError('Conversion error: expected %s value '
                'for "%s"' % (self.data_type, self.prop_name()))

    def prop_name(self):
        return propname_from_widgetid(self.getId())

    def index_html(self, REQUEST):
        """ redirect to admin_html """
        return REQUEST.RESPONSE.redirect(self.absolute_url() + '/admin_html')

    def _convert_to_form_string(self, value):
        """ by default this does nothing; subclasses may override. """
        return value

    def render_html(self, value, context=None, errors=None):
        value = self._convert_to_form_string(value)
        if self.visible:
            return self.template(value=value, context=context, errors=errors)
        else:
            return self.hidden_template(value=value, context=context)

    def get_widget_type(self):
        classname = self.__class__.__name__
        if classname.endswith('Widget') and len(classname) > len('Widget'):
            return classname[:-len('Widget')]
        else:
            raise ValueError('Bad Widget class name: %s' % classname)

    def convert_from_user_string(self, value):
        """ Convert a user-readable string to a value that can be saved """
        return value

    def convert_to_user_string(self, value):
        """
        Convert a database value to a user-readable string
        this method must return a `unicode` value
        """
        return unicode(value)

    def convert_formvalue_to_pythonvalue(self, value):
        return value

    hidden_template = PageTemplateFile('../zpt/property_widget_hidden', globals())

    admin_html = PageTemplateFile('../zpt/admin_schema_property', globals())

InitializeClass(Widget)
