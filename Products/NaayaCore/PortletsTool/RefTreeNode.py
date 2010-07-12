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
# Agency (EEA).  Portions created by Finsiel Romania are
# Copyright (C) European Environment Agency.  All
# Rights Reserved.
#
# Authors:
#
# Cornel Nitu, Finsiel Romania
# Dragos Chirila, Finsiel Romania

#Python imports

#Zope imports
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens, view
from OFS.SimpleItem import SimpleItem
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

#Product related imports
from Products.NaayaCore.constants import *
from Products.Localizer.LocalPropertyManager import LocalPropertyManager, LocalProperty
from Products.NaayaCore.managers.utils import make_id

manage_addRefTreeNodeForm = PageTemplateFile('zpt/reftreenode_manage_add', globals())
def manage_addRefTreeNode(self, id='', title='', parent=None, pickable='',
    lang=None, REQUEST=None):
    """ """
    id = make_id(self, id=id, title=title, prefix=PREFIX_SUFIX_REFTREE)
    if parent == '': parent = None
    if pickable: pickable = 1
    else: pickable = 0
    if lang is None: lang = self.gl_get_selected_language()
    ob = RefTreeNode(id, title, parent, pickable, lang)
    self.gl_add_languages(ob)
    self._setObject(id, ob)
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)
    return id

# localizer_patcher is a descriptor (getter/setter) that retrieves values
# from LocalProperty data. It's a patchy way of disabling localization,
# and eventually we need to run a proper update script.
def localizer_getter(self):
    # getter for title
    if 'title' in self.__dict__:
        return self.__dict__['title']
    else:
        return self.getLocalProperty('title', 'en')
def localizer_setter(self, value):
    self.__dict__['title'] = value
localizer_patcher = property(localizer_getter, localizer_setter)

class RefTreeNode(LocalPropertyManager, SimpleItem):
    """ """

    meta_type = METATYPE_REFTREENODE
    icon = 'misc_/NaayaCore/RefTreeNode.gif'

    manage_options = (
        (
            {'label': 'Properties', 'action': 'manage_edit_html'},
        )
        +
        SimpleItem.manage_options
    )

    security = ClassSecurityInfo()

    title = localizer_patcher

    def __init__(self, id, title, parent, pickable, lang):
        """ """
        self.id = id
        self.title = title
        self.parent = parent
        self.pickable = pickable
        self.weight = 0
    
    #zmi actions
    security.declareProtected(view_management_screens, 'manageProperties')
    def manageProperties(self, title='', parent='', pickable='',
        lang=None, REQUEST=None):
        """ """
        if parent == '': parent = None
        if pickable: pickable = 1
        else: pickable = 0
        if lang is None: lang = self.gl_get_selected_language()
        self.title = title
        self.parent = parent
        self.pickable = pickable
        self._p_changed = 1
        if REQUEST:
            REQUEST.RESPONSE.redirect('manage_edit_html')

    #zmi pages
    security.declareProtected(view_management_screens, 'manage_edit_html')
    manage_edit_html = PageTemplateFile('zpt/reftreenode_manage_edit', globals())

InitializeClass(RefTreeNode)
