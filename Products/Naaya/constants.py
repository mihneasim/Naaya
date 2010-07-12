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

"""
This module contains global constants.
"""

#Python imports

#Zope imports
import Globals

#Product imports

NAAYA_PRODUCT_NAME = 'Naaya'
NAAYA_PRODUCT_PATH = Globals.package_home(globals())

PERMISSION_ADD_SITE = 'Naaya - Add Naaya Site objects'
PERMISSION_ADD_FOLDER = 'Naaya - Add Naaya Folder objects'

METATYPE_NYSITE = 'Naaya Site'
METATYPE_FOLDER = 'Naaya Folder'

LABEL_NYFOLDER = 'Folder'

DEFAULT_PORTAL_LANGUAGE_CODE = 'en' #English language is assumed to be the default language
DEFAULT_SORTORDER = 100
DEFAULT_MAILSERVERNAME = 'localhost'
DEFAULT_MAILSERVERPORT = 25

PREFIX_SITE = 'portal'
PREFIX_FOLDER = 'fol'

ID_IMAGESFOLDER = 'images'
WRONG_PASSWORD = 'Current password is not correct. Changes NOT saved.'

MESSAGE_ROLEADDED = 'Role(s) successfully granted to user ${user}'
MESSAGE_ROLEREVOKED = 'Role(s) successfully revoked to selected user(s)'
MESSAGE_USERADDED = 'User successfully added. Now you can assign a role to this account.'
MESSAGE_USERMODIFIED = 'User\'s credentials saved'

NYEXP_SCHEMA_LOCATION = 'http://svn.eionet.eu.int/repositories/Zope/trunk/Naaya/NaayaDocuments/schemas/naaya/naaya-nyexp-1.0.0.xsd'

JS_MESSAGES = [
# datetime_js
    'Today',
    'Yesterday',
    'Tomorrow',
    'Calendar',
    'Cancel',
# calendar_js
    ('January February March April May June July '
     'August September October November December'),
    'S M T W T F S',
# portal_map
    'Check All',
    'Uncheck All',
    'Type location address',
    'Type keywords',
    'close',
# folder_listing.zpt error messages
    'Please select one or more items to copy.',
    'Please select one or more items to cut.',
    'Please select one or more items to delete.',
    'Please select one or more items to rename.',
]
