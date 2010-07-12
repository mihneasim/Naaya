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

#Product imports

class channeltype_item:
    """ """

    def __init__(self, id, title):
        """ """
        self.id = id
        self.title = title

    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")

InitializeClass(channeltype_item)

class channeltypes_manager:
    """ """

    def __init__(self):
        """ """
        self.__channeltypes_collection = {}

    def __add_channeltype_item(self, id, title):
        #create a new item
        item = channeltype_item(id, title)
        self.__channeltypes_collection[id] = item

    def __edit_channeltype_item(self, id, title):
        #modify an item
        try:
            item = self.__channeltypes_collection[id]
        except:
            pass
        else:
            item.title = title

    def __delete_channeltype_item(self, id):
        #delete an item
        try: del(self.__channeltypes_collection[id])
        except: pass

    #api
    def get_channeltypes_collection(self):
        #get the collection
        return self.__channeltypes_collection

    def get_channeltypes_list(self):
        #get a list with all items
        return self.__channeltypes_collection.values()

    def get_channeltype_item(self, id):
        #get an item
        try: return self.__channeltypes_collection[id]
        except: return None

    def get_channeltype_title(self, id):
        #get the title of an item
        try: return self.__channeltypes_collection[id].title
        except: return ''

    def get_channeltype_item_data(self, id):
        #get an item data
        item = self.get_channeltype_item(id)
        if item is not None: 
            return ['edit', item.id, item.title]
        else:
            return ['add', '', '']

    def add_channeltype_item(self, id, title):
        #create a new item
        self.__add_channeltype_item(id, title)
        self._p_changed = 1

    def edit_channeltype_item(self, id, title):
        #modify an item
        self.__edit_channeltype_item(id, title)
        self._p_changed = 1

    def delete_channeltype_item(self, ids):
        #delete 1 or more items
        map(self.__delete_channeltype_item, ids)
        self._p_changed = 1
