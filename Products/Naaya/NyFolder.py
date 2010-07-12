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
# Cornel Nitu, Eau de Web
# Dragos Chirila
# Alec Ghica, Eau de Web

#Python imports
from copy import copy, deepcopy
import operator

#Zope imports
from DateTime import DateTime
from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from Products.PageTemplates.ZopePageTemplate import manage_addPageTemplate
from AccessControl import ClassSecurityInfo, Unauthorized
from AccessControl.Permissions import view_management_screens, view, manage_users
import Products
from zope.interface import implements
from zope import event

#Product imports
from interfaces import INyFolder
from constants import *
from Products.NaayaBase.constants import *
from Products.NaayaCore.managers.utils import utils, batch_utils, make_id
from naaya.core.utils import force_to_unicode
from Products.NaayaBase.NyContainer import NyContainer
from Products.NaayaBase.NyImportExport import NyImportExport
from Products.NaayaBase.NyAttributes import NyAttributes
from Products.NaayaBase.NyProperties import NyProperties
from Products.Localizer.LocalPropertyManager import LocalProperty
from Products.NaayaBase.NyContentType import NyContentType, NyContentData
from Products.NaayaBase.NyContentType import NY_CONTENT_BASE_SCHEMA
from Products.NaayaCore.managers.csv_import_export import CSVImportTool, CSVExportTool
from Products.NaayaCore.NotificationTool.Subscriber import Subscriber
from NyFolderBase import NyFolderBase
from naaya.content.base.events import NyContentObjectAddEvent
from naaya.content.base.events import NyContentObjectEditEvent
from Products.NaayaBase.NyRoleManager import NyRoleManager
from Products.NaayaBase.NyItem import NyItem

manage_addNyFolder_html = PageTemplateFile('zpt/folder_manage_add', globals())
manage_addNyFolder_html.kind = METATYPE_FOLDER
manage_addNyFolder_html.action = 'addNyFolder'

DEFAULT_SCHEMA = deepcopy(NY_CONTENT_BASE_SCHEMA)
del DEFAULT_SCHEMA['geo_location']
del DEFAULT_SCHEMA['geo_type']
DEFAULT_SCHEMA['title']['required'] = False
DEFAULT_SCHEMA['maintainer_email'] = {
    'sortorder': 110,
    'widget_type': 'String',
    'label': 'Maintainer email',
}

def folder_add_html(self, REQUEST=None, RESPONSE=None):
    """ """
    from Products.NaayaBase.NyContentType import get_schema_helper_for_metatype
    form_helper = get_schema_helper_for_metatype(self, 'Naaya Folder')
    return self.getFormsTool().getContent({'here': self, 'kind': METATYPE_FOLDER, 'action': 'addNyFolder', 'form_helper': form_helper}, 'folder_add')

def _create_NyFolder_object(parent, id, contributor):
    make_id(parent, id=id, prefix=PREFIX_FOLDER)
    ob = NyFolder(id, contributor)
    parent.gl_add_languages(ob)
    parent._setObject(id, ob)
    ob = parent._getOb(id)
    ob.after_setObject()
    return ob

def addNyFolder(self, id='', REQUEST=None, contributor=None, callback=_create_NyFolder_object, **kwargs):
#def addNyFolder(self, id='', title='', description='', coverage='', keywords='', sortorder='',
#    publicinterface='', maintainer_email='', folder_meta_types='', contributor=None,
#    releasedate='', discussion='', lang=None, REQUEST=None, **kwargs):
    """
    Create a Folder type of object.
    Parameters:
        `callback`
            A function that returns an new instance of the NyFolder object-type
    """
    if REQUEST is not None:
        schema_raw_data = dict(REQUEST.form)
    else:
        schema_raw_data = kwargs
    _lang = schema_raw_data.pop('_lang', schema_raw_data.pop('lang', None))
    _releasedate = self.process_releasedate(schema_raw_data.pop('releasedate', ''))
    _publicinterface = int(bool(schema_raw_data.pop('publicinterface', None)))
    _folder_meta_types = schema_raw_data.pop('folder_meta_types', '')

    site = self.getSite()

    #process parameters
    id = make_id(self, id=id, title=schema_raw_data.get('title', ''), prefix=PREFIX_FOLDER)
    try: sortorder = abs(int(sortorder))
    except: sortorder = DEFAULT_SORTORDER
    if contributor is None: contributor = self.REQUEST.AUTHENTICATED_USER.getUserName()

    ob = callback(self, id, contributor)
    form_errors = ob.process_submitted_form(schema_raw_data, _lang, _override_releasedate=_releasedate)
    if form_errors:
        if REQUEST is None:
            raise ValueError(form_errors.popitem()[1]) # pick a random error
        else:
            import transaction; transaction.abort() # because we already called _crete_NyZzz_object
            ob._prepare_error_response(REQUEST, form_errors, schema_raw_data)
            REQUEST.RESPONSE.redirect('%s/folder_add_html' % self.absolute_url())
            return

    ob.createDynamicProperties(self.processDynamicProperties(METATYPE_FOLDER, REQUEST, kwargs), _lang)

    #extra settings
    if _folder_meta_types == '':
        #inherit allowd meta types from the parent
        if self.meta_type == site.meta_type:
            ob.folder_meta_types = self.adt_meta_types
        else:
            ob.folder_meta_types = self.folder_meta_types
    else:
        ob.folder_meta_types = self.utConvertToList(_folder_meta_types)

    if self.glCheckPermissionPublishObjects():
        approved, approved_by = 1, self.REQUEST.AUTHENTICATED_USER.getUserName()
    else:
        approved, approved_by = 0, None
    ob.approveThis(approved, approved_by)
    ob.submitThis()

    ob.publicinterface = _publicinterface
    ob.createPublicInterface()

    if ob.discussion: ob.open_for_comments()
    self.recatalogNyObject(ob)
    event.notify(NyContentObjectAddEvent(ob, contributor, schema_raw_data))
    #log post date
    auth_tool = self.getAuthenticationTool()
    auth_tool.changeLastPost(contributor)
    #redirect if case
    if REQUEST is not None:
        referer = REQUEST['HTTP_REFERER'].split('/')[-1]
        if referer == 'folder_manage_add' or referer.find('folder_manage_add') != -1:
            return self.manage_main(self, REQUEST, update_menu=1)
        elif referer == 'folder_add_html':
            self.setSession('referer', self.absolute_url())
            return ob.object_submitted_message(REQUEST)
            REQUEST.RESPONSE.redirect('%s/messages_html' % self.absolute_url())

    return ob.getId()

def importNyFolder(self, param, id, attrs, content, properties, discussion, objects):
    #this method is called during the import process
    try: param = abs(int(param))
    except: param = 0
    if param == 3:
        #just try to delete the object
        try: self.manage_delObjects([id])
        except: pass
    else:
        ob = self._getOb(id, None)
        if param in [0, 1] or (param==2 and ob is None):
            if param == 1:
                #delete the object if exists
                try: self.manage_delObjects([id])
                except: pass
            publicinterface = abs(int(attrs['publicinterface'].encode('utf-8')))
            meta_types = attrs['folder_meta_types'].encode('utf-8')
            if meta_types == '': meta_types = ''
            else: meta_types = meta_types.split(',')
            #create the object
            addNyFolder(self, id=id,
                sortorder=attrs['sortorder'].encode('utf-8'),
                publicinterface=publicinterface,
                maintainer_email=attrs['maintainer_email'].encode('utf-8'),
                folder_meta_types=meta_types,
                contributor=self.utEmptyToNone(attrs['contributor'].encode('utf-8')),
                discussion=abs(int(attrs['discussion'].encode('utf-8'))))
            ob = self._getOb(id)
            for property, langs in properties.items():
                for lang in langs:
                    ob._setLocalPropValue(property, lang, langs[lang])
            ob.approveThis(approved=abs(int(attrs['approved'].encode('utf-8'))),
                approved_by=self.utEmptyToNone(attrs['approved_by'].encode('utf-8')))
            if attrs['releasedate'].encode('utf-8') != '':
                ob.setReleaseDate(attrs['releasedate'].encode('utf-8'))
            if publicinterface:
                l_index = ob._getOb('index', None)
                if l_index is not None:
                    l_index.pt_edit(text=content, content_type='')
            ob.import_comments(discussion)
            self.recatalogNyObject(ob)
        #go on and import sub objects
        for object in objects:
            ob.import_data(object)

class NyFolder(NyRoleManager, NyAttributes, NyProperties, NyImportExport, NyContainer, utils, NyContentType, NyContentData, NyFolderBase):
    """ """

    implements(INyFolder)

    meta_type = METATYPE_FOLDER
    meta_label = LABEL_NYFOLDER
    icon = 'misc_/Naaya/NyFolder.gif'
    icon_marked = 'misc_/Naaya/NyFolder_marked.gif'

    manage_options = (
        NyContainer.manage_options[0:2]
        +
        (
            {'label': 'Properties', 'action': 'manage_edit_html'},
            {'label': 'Subobjects', 'action': 'manage_folder_subobjects_html'},
        )
        +
        NyProperties.manage_options
        +
        NyImportExport.manage_options
        +
        NyContainer.manage_options[3:8]
    )

    security = ClassSecurityInfo()

    #constructors
    security.declareProtected(PERMISSION_ADD_FOLDER, 'folder_add_html')
    folder_add_html = folder_add_html
    security.declareProtected(PERMISSION_ADD_FOLDER, 'addNyFolder')
    addNyFolder = addNyFolder

    title = LocalProperty('title')
    description = LocalProperty('description')
    coverage = LocalProperty('coverage')
    keywords = LocalProperty('keywords')

    def all_meta_types(self, interfaces=None):
        """ What can you put inside me? """
        if len(self.folder_meta_types) > 0:
            #filter meta types
            l = list(filter(lambda x: x['name'] in self.folder_meta_types, Products.meta_types))
            #handle uninstalled pluggable meta_types
            pluggable_meta_types = self.get_pluggable_metatypes()
            pluggable_installed_meta_types = self.get_pluggable_installed_meta_types()
            t = copy(l)
            for x in t:
                if (x['name'] in pluggable_meta_types) and (x['name'] not in pluggable_installed_meta_types):
                    l.remove(x)
            return l
        else:
            return self.meta_types

    def __init__(self, id, contributor):
        """ """
        self.id = id
        NyContainer.__dict__['__init__'](self)
        NyProperties.__dict__['__init__'](self)
        self.contributor = contributor

    def hasVersion(self):
        return False

    def write_import(self, REQUEST=None):
        """ """
        from os.path import join
        file_id = REQUEST.get('id', None)
        file_path = join(CLIENT_HOME, '%s.nyexp' % file_id)
        if file_id is not None:
            self.manage_import(source='', file=open(file_path).read(), url='')
        return 'done import'

    # image container for this folder
    def getUploadedImages(self): return self.objectValues(['Image'])

    #import/export
    def exportdata_custom(self, all_levels):
        #exports all the Naaya content in XML format from this folder
        return self.export_this(all_levels=all_levels)

    security.declarePublic('export_this')
    def export_this(self, folderish=0, all_levels=1):
        r = []
        ra = r.append
        ra(self.export_this_tag())
        ra(self.export_this_body())
        if self.publicinterface:
            l_index = self._getOb('index', None)
            if l_index is not None:
                ra('<![CDATA[%s]]>' % l_index.document_src())
        if not folderish:
            for x in self.getObjects():
                ra(x.export_this())
        if all_levels:
            for x in self.getFolders():
                ra(x.export_this(folderish))
        ra('</ob>')
        return ''.join(force_to_unicode(ln) for ln in r)

    security.declarePublic('export_this_withoutcontent')
    def export_this_withoutcontent(self):
        r = []
        ra = r.append
        ra(self.export_this_tag())
        ra(self.export_this_body())
        if self.publicinterface:
            l_index = self._getOb('index', None)
            if l_index is not None:
                ra('<![CDATA[%s]]>' % l_index.document_src())
        return ''.join(r)

    security.declarePrivate('export_this_tag_custom')
    def export_this_tag_custom(self):
        return 'publicinterface="%s" maintainer_email="%s" folder_meta_types="%s"' % \
            (self.utXmlEncode(self.publicinterface),
                self.utXmlEncode(self.maintainer_email),
                self.utXmlEncode(','.join(self.folder_meta_types)))

    security.declarePrivate('export_this_body_custom')
    def export_this_body_custom(self):
        r = []
        ra = r.append
        for i in self.getUploadedImages():
            ra('<img param="0" id="%s" content="%s" />' % \
                (self.utXmlEncode(i.id()), self.utXmlEncode(self.utBase64Encode(str(i.data)))))
        return ''.join(r)

    security.declarePrivate('createPublicInterface')
    def createPublicInterface(self):
        pt_id = 'index'
        if self.publicinterface and self._getOb(pt_id, None) is None:
            pt_content = self.getFormsTool().getForm('folder_index').document_src()
            manage_addPageTemplate(self, id=pt_id, title='Custom index for this folder', text='')
            pt_obj = self._getOb(pt_id)
            pt_obj.pt_edit(text=pt_content, content_type='text/html')

    security.declarePrivate('modifyPublicInterface')
    def modifyPublicInterface(self, pt_content):
        pt_id = 'index'
        if self.publicinterface and self._getOb(pt_id, None) is not None:
            try: self._getOb(pt_id).pt_edit(text=pt_content, content_type='')
            except: pass

    def import_data(self, object):
        #import an object
        if object.meta_type == METATYPE_FOLDER:
            importNyFolder(self, object.param, object.id, object.attrs,
                object.content, object.properties, object.discussion,
                object.objects)
        elif object.meta_type in self.get_pluggable_installed_meta_types():
            item = self.get_pluggable_item(object.meta_type)
            if not item.has_key('import_string'):
                import_method = getattr(self, 'import_%s' % item['module'])
            else:
                import_method = getattr(self, item['import_string'])
            import_method(object.param, object.id, object.attrs, object.content,
                          object.properties, object.discussion, object.objects)
        else:
            self.import_data_custom(self, object)

    security.declareProtected(view, 'checkPermissionManageObjects')
    def checkPermissionManageObjects(self, sort_on='title', sort_order=0):
        """ Deprecated: This function was moved in NyFolderBase as folder_listing_info
            This function is called on the folder index and it checkes whether or not
            to display the various buttons on that form
        """
        results_folders = []
        results_objects = []
        btn_select, btn_delete, btn_copy, btn_cut, btn_paste, can_operate = 0, 0, 0, 0, 0, 0
        # btn_select - if there is at least one permisson to delete or copy an object
        # btn_delete - if there is at least one permisson to delete an object
        # btn_copy - if there is at least one permisson to copy an object
        # btn_cut - if there is at least one permisson to delete AND copy an object
        # btn_paste - if there is the add permission and there's some copyed data
        btn_paste = self.cb_dataValid() and self.checkPermissionPasteObjects()
        # Naaya folders
        sorted_folders = self.utSortObjsListByAttr(self.getFolders(), sort_on, sort_order)
        for x in self.utSortObjsListByAttr(sorted_folders, 'sortorder', 0):
            del_permission = x.checkPermissionDeleteObject()
            copy_permission = x.checkPermissionCopyObject()
            edit_permission = x.checkPermissionEditObject()
            if del_permission or copy_permission: btn_select = 1
            if del_permission and copy_permission: btn_cut = 1
            if del_permission: btn_delete = 1
            if copy_permission: btn_copy = 1
            if edit_permission: can_operate = 1
            version_status = 0
            if ((del_permission or edit_permission) and not x.approved) or x.approved:
                results_folders.append((del_permission, edit_permission, version_status, copy_permission, x))
        # Naaya objects
        sorted_objects = self.utSortObjsListByAttr(self.getObjects(), sort_on, sort_order)
        for x in self.utSortObjsListByAttr(sorted_objects, 'sortorder', 0):
            del_permission = x.checkPermissionDeleteObject()
            copy_permission = x.checkPermissionCopyObject()
            edit_permission = x.checkPermissionEditObject()
            if del_permission or copy_permission: btn_select = 1
            if del_permission and copy_permission: btn_cut = 1
            if del_permission: btn_delete = 1
            if copy_permission: btn_copy = 1
            if edit_permission: can_operate = 1
            #TODO: remove version_status -- moved to NaayaBase.NyContentType.version_status
            # version_status:  0 - cannot check out for some reason
            #                  1 - can check in
            #                  2 - can check out
            if not edit_permission or not x.isVersionable():
                version_status = 0
            elif x.hasVersion():
                if x.isVersionAuthor(): version_status = 1
                else: version_status = 0
            else:
                version_status = 2
            if ((del_permission or edit_permission) and not x.approved) or x.approved:
                results_objects.append((del_permission, edit_permission, version_status, copy_permission, x))
        can_operate = can_operate or btn_select
        return (btn_select, btn_delete, btn_copy, btn_cut, btn_paste, can_operate, results_folders, results_objects)

    security.declareProtected(view, 'checkPermissionManageObjectsMixed')
    def checkPermissionManageObjectsMixed(self):
        """ This function is called on the folder index, returns a mixed list of folders and objects and it checkes whether or not
            to display the various buttons on that form
        """
        result_mixed_objects = []
        btn_select, btn_delete, btn_copy, btn_cut, btn_paste, can_operate = 0, 0, 0, 0, 0, 0
        # btn_select - if there is at least one permisson to delete or copy an object
        # btn_delete - if there is at least one permisson to delete an object
        # btn_copy - if there is at least one permisson to copy an object
        # btn_cut - if there is at least one permisson to delete AND copy an object
        # btn_paste - if there is the add permission and there's some copyed data
        btn_paste = self.cb_dataValid() and self.checkPermissionPasteObjects()
        mixed_list = self.getFolders() + self.getObjects()
        for x in self.utSortObjsListByAttr(mixed_list, 'sortorder', 0):
            del_permission = x.checkPermissionDeleteObject()
            copy_permission = x.checkPermissionCopyObject()
            edit_permission = x.checkPermissionEditObject()
            if del_permission or copy_permission: btn_select = 1
            if del_permission and copy_permission: btn_cut = 1
            if del_permission: btn_delete = 1
            if copy_permission: btn_copy = 1
            if edit_permission: can_operate = 1
            if x.meta_type == METATYPE_FOLDER:
                version_status = 0
            else:
                if not edit_permission or not x.isVersionable():
                    version_status = 0
                elif x.hasVersion():
                    if x.isVersionAuthor(): version_status = 1
                    else: version_status = 0
                else:
                    version_status = 2
            if ((del_permission or edit_permission) and not x.approved) or x.approved:
                result_mixed_objects.append((del_permission, edit_permission, version_status, copy_permission, x))
        can_operate = can_operate or btn_select
        return (btn_select, btn_delete, btn_copy, btn_cut, btn_paste, can_operate, result_mixed_objects)

    def getObjects(self):
        """ Deprecated: This function was moved in NyFolderBase as contained_objects """
        return [x for x in self.objectValues(self.get_meta_types()) if x.submitted==1]

    def getFolders(self):
        """ Deprecated: This function was moved in NyFolderBase as contained_folders """
        return [x for x in self.objectValues(METATYPE_FOLDER) if x.submitted==1]

    def hasContent(self): return (len(self.getObjects()) > 0) or (len(self.objectValues(METATYPE_FOLDER)) > 0)

    def getPublishedFolders(self):
        folders = []
        for obj in self.objectValues(self.get_naaya_containers_metatypes()):
            if not getattr(obj, 'approved', False):
                continue
            if not getattr(obj, 'submitted', False):
                continue
            folders.append(obj)
        folders.sort(key=operator.attrgetter('sortorder'))
        return folders

    def getPublishedObjects(self, items=0):
        doc_metatypes = [m for m in self.get_meta_types()
                         if m not in self.get_naaya_containers_metatypes()]
        result = []
        for obj in self.objectValues(doc_metatypes):
            if not getattr(obj, 'approved', False):
                continue
            if not getattr(obj, 'submitted', False):
                continue
            result.append(obj)

        if items:
            result = result[:items]

        return result

    def getPublishedContent(self):
        r = self.getPublishedFolders()
        r.extend(self.getPublishedObjects())
        return r

    def getPendingFolders(self): return [x for x in self.objectValues(METATYPE_FOLDER) if x.approved==0 and x.submitted==1]
    def getPendingObjects(self): return [x for x in self.getObjects() if x.approved==0 and x.submitted==1]
    def getPendingContent(self):
        r = self.getPendingFolders()
        r.extend(self.getPendingObjects())
        return r

    def getTranslatableFolders(self, lang): return [x for x in self.objectValues(METATYPE_FOLDER) if not x.getLocalProperty('title', lang)]
    def getTranslatableObjects(self, lang): return [x for x in self.getObjects() if not x.getLocalProperty('title', lang)]
    def getTranslatableContent(self, lang):
        r = self.getTranslatableFolders(lang)
        r.extend(self.getTranslatableObjects(lang))
        return r

    def countPendingContent(self):  return len(self.getPendingContent())
    def hasPendingContent(self):    return len(self.getPendingContent()) > 0
    def getSubfoldersWithPendingItems(self):
        #returns a list with all subfolders that contains pending(draft) objects
        return filter(lambda x: x.hasPendingContent(), self.getCatalogedObjects([METATYPE_FOLDER], 0, path='/'.join(self.getPhysicalPath())))

    security.declareProtected(manage_users, 'admin_getusers')
    def admin_getusers(self):
        """ """
        return self.getAuthenticationTool().getUserNames()

    def getUsersRoles(self):
        """
        Returns information about the user's roles inside this folder
        and its subfolders.
        """
        return self.getAuthenticationTool().getUsersRolesRestricted('/'.join(self.getPhysicalPath()))

    def getObjectsForValidation(self): return [x for x in self.objectValues(self.get_pluggable_metatypes_validation()) if x.submitted==1]
    def count_notok_objects(self): return len([x for x in self.getObjectsForValidation() if x.validation_status==-1 and x.submitted==1])
    def count_notchecked_objects(self): return len([x for x in self.getObjectsForValidation() if x.validation_status==0 and x.submitted==1])

    def getSortedFolders(self): return self.utSortObjsListByAttr(self.getFolders(), 'sortorder', 0)
    def getSortedObjects(self): return self.utSortObjsListByAttr(self.getObjects(), 'sortorder', 0)

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'isFeedbackCustomized')
    def isFeedbackCustomized(self):
        """
        Test if the feedback form for the current folder is customized.
        """
        return self.getSite().folder_customized_feedback.has_key('/'.join(self.getPhysicalPath()))

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'getAdministratorsEmails')
    def getAdministratorsEmails(self, roles=['Administrator']):
        """
        Returns a list with administrator emails. Administrator is the user
        that has at least one o the given roles on this folder.
        """
        r = []
        ra = r.append
        for k, v in self.get_local_roles():
            if len(self.utListIntersection(roles, v)): ra(k)
        return self.getAuthenticationTool().getUsersEmails(r)

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'getFeedbackCustomizedEmail')
    def getFeedbackCustomizedEmail(self):
        """
        Returns the email addresses.
        """
        buf = self.getSite().folder_customized_feedback.get('/'.join(self.getPhysicalPath()), None)
        if isinstance(buf, tuple):
            return buf[0]

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'getFeedbackCustomizedPostal')
    def getFeedbackCustomizedPostal(self):
        """
        Returns the postal addresses.
        """
        buf = self.getSite().folder_customized_feedback.get('/'.join(self.getPhysicalPath()), None)
        if isinstance(buf, tuple):
            return buf[1]

    security.declareProtected(view, 'getParentFeedbackCustomized')
    def getParentFeedbackCustomized(self):
        """
        Test if the feedback form has been customized for this
        folder or for one of his parents. It returns the folder
        with feedback customized.
        """
        node = self
        while node.meta_type == METATYPE_FOLDER:
            if node.isFeedbackCustomized():
                return node, node.absolute_url()
            else:
                node = node.getParentNode()
        return None, self.absolute_url()

    security.declareProtected(view, 'admin_folder_feedback_form')
    def admin_folder_feedback_form(self, who=0, username='', email='', comments='', contact_word='', REQUEST=None):
        """ """
        err = []

        try: who = abs(int(who))
        except: who = 0
        if not self.checkPermissionPublishDirect():
            if contact_word=='' or contact_word!=self.getSession('captcha', None):
                err.append('The word you typed does not match with the one shown in the image. Please try again.')
        if username.strip() == '':
            err.append('The full name is required')
        if email.strip() == '':
            err.append('The email is required')
        if comments.strip() == '':
            err.append('The comments are required')

        if who == 1:
            l_to = self.getFeedbackCustomizedEmail()
            if l_to is None:
                l_to = self.administrator_email
        elif who==0:
            l_to = self.administrator_email
        if err:
            if REQUEST:
                self.setSessionErrorsTrans(err)
                self.setFeedbackSession(username, email, comments, who)
                return REQUEST.RESPONSE.redirect(REQUEST.HTTP_REFERER)
        else:
            self.getEmailTool().sendFeedbackEmail(l_to, username, email, comments)
        if REQUEST:
            self.setSession('title', 'Thank you for your feedback')
            self.setSession('body', 'The administrator will process your comments and get back to you.')
            return REQUEST.RESPONSE.redirect('%s/messages_html' % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'admin_folder_feedback')
    def admin_folder_feedback(self, status='0', emails='', postal='', REQUEST=None):
        """ """
        #process data
        try: status = abs(int(status))
        except: status = 0
        site = self.getSite()
        if status == 1:
            #customized
            site.folder_customized_feedback['/'.join(self.getPhysicalPath())] = (self.utConvertLinesToList(emails), postal)
        elif status == 0:
            #not customized
            try: del site.folder_customized_feedback['/'.join(self.getPhysicalPath())]
            except: pass
        site._p_changed = 1
        #save data
        if REQUEST:
            self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
            REQUEST.RESPONSE.redirect('%s/administration_feedback_html' % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'admin_folder_revokeroles')
    def admin_folder_revokeroles(self, roles=[], REQUEST=None):
        """ """
        self.getAuthenticationTool().manage_revokeUsersRoles(roles)
        if REQUEST:
            self.setSessionInfoTrans(MESSAGE_ROLEREVOKED)
            REQUEST.RESPONSE.redirect('%s/administration_users_html' % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'admin_adduser')
    def admin_adduser(self, firstname='', lastname='', email='', name='', password='', confirm='', REQUEST=None, RESPONSE=None):
        """ """
        self.setUserSession(name, '', '', firstname, lastname, email, '')
        _err = []
        try:
            self.getAuthenticationTool().manage_addUser(name, password, confirm, [], [],
                                                            firstname, lastname, email)
        except Exception, error:
            self.setSessionErrorsTrans(error)
            return RESPONSE.redirect("%s/administration_users_html?mode=add" % self.absolute_url())
        self.delUserSession()
        self.setSessionInfoTrans(MESSAGE_USERADDED)
        return RESPONSE.redirect("%s/administration_users_html" % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'admin_getuser')
    def admin_getuser(self, username):
        """ """
        auth_tool = self.getAuthenticationTool()
        user_obj = auth_tool.getUser(username)
        if user_obj:
            fn = auth_tool.getUserFirstName(user_obj)
            ln = auth_tool.getUserLastName(user_obj)
            em = auth_tool.getUserEmail(user_obj)
            acc = auth_tool.getUserAccount(user_obj)
            pwd = auth_tool.getUserPassword(user_obj)
            roles = auth_tool.getUserRoles(user_obj)
            created = auth_tool.getUserCreatedDate(user_obj)
            updated = auth_tool.getUserLastUpdated(user_obj)
            return fn, ln, em, acc, pwd, roles, created, updated

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'admin_saveuser_credentials')
    def admin_saveuser_credentials(self, name='', password='', confirm='', roles=[], domains=[], firstname='',
        lastname='', email='', lastupdated='', REQUEST=None, RESPONSE=None):
        """ """
        self.setUserSession(name, '', '', firstname, lastname, email, '')
        _err = []
        try:
            self.getAuthenticationTool().manage_changeUser(name, password, confirm, roles, domains, firstname, lastname, email, lastupdated)
        except Exception, error:
            self.setSessionErrorsTrans(error)
            return RESPONSE.redirect("%s/administration_users_html?mode=edit&name=%s" % (self.absolute_url(), name))

        self.delUserSession()
        self.setSessionInfoTrans(MESSAGE_USERMODIFIED)
        return RESPONSE.redirect("%s/administration_users_html" % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'admin_folder_portlets')
    def admin_folder_portlets(self, portlets=[], folder='', mode='', REQUEST=None):
        """ """
        #right portlets
        if mode == 'delete':
            for pair in self.utConvertToList(portlets):
                location, id = pair.split('||')
                self.delete_right_portlets_locations(location, id)
        else:
            if folder == '':
                #this is the current folder actually
                folder = self.absolute_url(1)
            self.set_right_portlets_locations(folder, self.utConvertToList(portlets))
        if REQUEST:
            self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
            REQUEST.RESPONSE.redirect('%s/administration_portlets_html' % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'admin_folder_addroles')
    def admin_folder_addroles(self, name='', roles=[], location='', REQUEST=None):
        """ """
        if location == '':
                #this is the current folder actually
                location = self.absolute_url(1)
        msg = err = ''
        success = False
        #test that the location is under the current folder
        if location.startswith(self.absolute_url(1)):
            try:
                self.getAuthenticationTool().manage_addUsersRoles(name, roles, 'other', location)
            except Exception, error:
                err = str(error)
            else:
                success = True
        else:
            err = 'Invalid location specified.'
        if REQUEST:
            if err != '': self.setSessionErrorsTrans(err)
            if success: self.setSessionInfoTrans(MESSAGE_ROLEADDED, user=name)
            if not err:
                try: #backwards compatibility
                    auth_tool = self.getAuthenticationTool()
                    user_ob = auth_tool.getUser(name)
                    self.sendAccountCreatedEmail('%s %s' % (user_ob.firstname, user_ob.lastname), user_ob.email, user_ob.name, REQUEST)
                except:
                    pass
            REQUEST.RESPONSE.redirect('%s/administration_users_html' % self.absolute_url())

    def getFolderLogo(self):
        """
        Returns the logo for this folder. The logo is an object
        with the B{logo.gif} id.
        """
        return self._getOb('logo.gif', None)

    def setLogo(self, source, file, url):
        """
        Upload the logo.
        """
        logo = self.getFolderLogo()
        if logo is None:
            self.manage_addImage(id='logo.gif', file='')
            logo = self.getFolderLogo()
        if source=='file':
            if file != '':
                if hasattr(file, 'filename'):
                    if file.filename != '':
                        data, size = logo._read_data(file)
                        content_type = logo._get_content_type(file, data, logo.__name__, 'application/octet-stream')
                        logo.update_data(data, content_type, size)
                else:
                    logo.update_data(file)
        elif source=='url':
            if url != '':
                l_data, l_ctype = self.grabFromUrl(url)
                if l_data is not None:
                    logo.update_data(l_data, l_ctype)
                    logo.content_type = l_ctype
        logo._p_changed = 1

    def delLogo(self):
        """
        Delete the folder logo.
        """
        try: self.manage_delObjects('logo.gif')
        except: pass

    security.declareProtected(view_management_screens, 'manage_edit_properties')
    def manage_edit_properties(self, title='', description='', coverage='', keywords='', sortorder=''):
        """ Changes just the properties provided as parameters """
        lang = self.gl_get_selected_language()
        if not self.checkPermissionEditObject():
            raise EXCEPTION_NOTAUTHORIZED, EXCEPTION_NOTAUTHORIZED_MSG
        if title:
            self._setLocalPropValue('title', lang, title)
        if description:
            self._setLocalPropValue('description', lang, description)
        if coverage:
            self._setLocalPropValue('coverage', lang, coverage)
        if keywords:
            self._setLocalPropValue('keywords', lang, keywords)
        if sortorder:
            try: sortorder = abs(int(sortorder))
            except: sortorder = DEFAULT_SORTORDER
            self.sortorder = sortorder
        self.recatalogNyObject(self)

    #zmi actions
    security.declareProtected(view_management_screens, 'manageProperties')
    def manageProperties(self, title='', description='', coverage='',
        keywords='', sortorder='', publicinterface='', maintainer_email='', approved='',
        releasedate='', discussion='', REQUEST=None, **kwargs):
        """ """
        if not self.checkPermissionEditObject():
            raise EXCEPTION_NOTAUTHORIZED, EXCEPTION_NOTAUTHORIZED_MSG
        try: sortorder = abs(int(sortorder))
        except: sortorder = DEFAULT_SORTORDER
        if publicinterface: publicinterface = 1
        else: publicinterface = 0
        if approved: approved = 1
        else: approved = 0
        releasedate = self.process_releasedate(releasedate, self.releasedate)
        lang = kwargs.get('lang', self.gl_get_selected_language())
        self._setLocalPropValue('title', lang, title)
        self._setLocalPropValue('description', lang, description)
        self._setLocalPropValue('coverage', lang, coverage)
        self._setLocalPropValue('keywords', lang, keywords)
        self.sortorder = sortorder
        self.publicinterface = publicinterface
        self.maintainer_email = maintainer_email
        self.approved = approved
        self.releasedate = releasedate
        self.updatePropertiesFromGlossary(lang)
        self.updateDynamicProperties(self.processDynamicProperties(METATYPE_FOLDER, REQUEST, kwargs), lang)
        if approved != self.approved:
            if approved == 0: approved_by = None
            else: approved_by = self.REQUEST.AUTHENTICATED_USER.getUserName()
            self.approveThis(approved, approved_by)
        self._p_changed = 1
        if discussion: self.open_for_comments()
        else: self.close_for_comments()
        self.recatalogNyObject(self)
        self.createPublicInterface()
        if REQUEST: REQUEST.RESPONSE.redirect('manage_edit_html?save=ok')

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'manageSubobjects')
    def manageSubobjects(self, REQUEST=None, **kwargs):
        """ """
        if REQUEST:
            kwargs.update(REQUEST.form)

        if kwargs.get('default', ''):
            self.folder_meta_types = self.adt_meta_types
        else:
            self.folder_meta_types = self.utConvertToList(kwargs.get('subobjects', []))
            self.folder_meta_types.extend(self.utConvertToList(kwargs.get('ny_subobjects', [])))
        self._p_changed = 1
        if REQUEST:
            self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
            redirect = REQUEST.get('redirect_url', 'manage_folder_subobjects_html')
            redirect += '?save=ok'
            REQUEST.RESPONSE.redirect(redirect)

    security.declareProtected(view_management_screens, 'setMaintainer')
    def setMaintainer(self, maintainer_email):
        """ """
        self.maintainer_email = maintainer_email
        self._p_changed = 1

    #site actions
    security.declareProtected(PERMISSION_EDIT_OBJECTS, 'saveProperties')
    def saveProperties(self, REQUEST=None, **kwargs):
        """ """
        if not self.checkPermissionEditObject():
            raise EXCEPTION_NOTAUTHORIZED, EXCEPTION_NOTAUTHORIZED_MSG

        if REQUEST is not None:
            schema_raw_data = dict(REQUEST.form)
        else:
            schema_raw_data = kwargs
        _lang = schema_raw_data.pop('_lang', schema_raw_data.pop('lang', None))
        _releasedate = self.process_releasedate(schema_raw_data.pop('releasedate', ''), self.releasedate)

        form_errors = self.process_submitted_form(schema_raw_data, _lang, _override_releasedate=_releasedate)

        if not form_errors:
            if self.discussion: self.open_for_comments()
            else: self.close_for_comments()
            self._p_changed = 1
            self.recatalogNyObject(self)
            #log date
            contributor = self.REQUEST.AUTHENTICATED_USER.getUserName()
            auth_tool = self.getAuthenticationTool()
            auth_tool.changeLastPost(contributor)
            event.notify(NyContentObjectEditEvent(self, contributor))
            if REQUEST:
                self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
                REQUEST.RESPONSE.redirect('%s/edit_html?lang=%s' % (self.absolute_url(), _lang))
        else:
            if REQUEST is not None:
                self._prepare_error_response(REQUEST, form_errors, schema_raw_data)
                REQUEST.RESPONSE.redirect('%s/edit_html?lang=%s' % (self.absolute_url(), _lang))
            else:
                raise ValueError(form_errors.popitem()[1]) # pick a random error

    security.declareProtected(PERMISSION_EDIT_OBJECTS, 'saveLogo')
    def saveLogo(self, source='file', file='', url='', del_logo='', REQUEST=None, **kwargs):
        """ """
        if not self.checkPermissionEditObject():
            raise EXCEPTION_NOTAUTHORIZED, EXCEPTION_NOTAUTHORIZED_MSG
        if del_logo != '': self.delLogo()
        else: self.setLogo(source, file, url)
        if REQUEST:
            self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
            REQUEST.RESPONSE.redirect('editlogo_html')

    security.declareProtected(PERMISSION_EDIT_OBJECTS, 'setTopStoryObjects')
    def setTopStoryObjects(self, REQUEST=None):
        """ """
        #ids_list = self.utConvertToList(REQUEST.get('id_topstory', []))
        try:
            for item in self.objectValues():
                if not isinstance(item, NyItem):
                    continue
                if hasattr(item, 'topitem'): item.topitem = 0
                if REQUEST.has_key('topstory_' + item.id):
                    item.topitem = 1
                item._p_changed = 1
                self.recatalogNyObject(item)
        except: self.setSessionErrorsTrans('Error while updating data.')
        else: self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
        if REQUEST: REQUEST.RESPONSE.redirect('index_html')

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'processPendingContent')
    def processPendingContent(self, appids=[], delids=[], REQUEST=None):
        """
        Process the pending content inside this folder.

        Objects with ids in appids list will be approved.

        Objects with ids in delids will be deleted.
        """
        for id in self.utConvertToList(appids):
            ob = self._getOb(id, None)
            if not ob:
                continue
            if hasattr(ob, 'approveThis'):
                ob.approveThis()
            if hasattr(ob, 'takeEditRights'):
                ob.takeEditRights()
            ob.releasedate = self.utGetTodayDate()
            self.recatalogNyObject(ob)

        for id in self.utConvertToList(delids):
            try: self._delObject(id)
            except: pass
        if REQUEST:
            self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
            REQUEST.RESPONSE.redirect('%s/basketofapprovals_html' % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'processPublishedContent')
    def processPublishedContent(self, appids=[], delids=[], REQUEST=None):
        """
        Process the published content inside this folder.

        Objects with ids in appids list will be unapproved.

        Objects with ids in delids will be deleted.
        """
        for id in self.utConvertToList(appids):
            ob = self._getOb(id, None)
            if not ob:
                continue
            if hasattr(ob, 'approveThis'):
                ob.approveThis(0, None)
            if hasattr(ob, 'giveEditRights'):
                ob.giveEditRights()
            self.recatalogNyObject(ob)
        for id in self.utConvertToList(delids):
            try: self._delObject(id)
            except: pass
        if REQUEST:
            self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
            REQUEST.RESPONSE.redirect('%s/basketofapprovals_html' % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'setSortOrder')
    def setSortOrder(self, ids, REQUEST):
        """ """
        for id in self.utConvertToList(ids):
            try: sortorder = abs(int(REQUEST.get('%s__sortorder' % id, 0)))
            except: sortorder = DEFAULT_SORTORDER
            try:
                ob = self._getOb(id)
                ob.sortorder = sortorder
                ob._p_changed = 1
            except:
                pass
        if REQUEST:
            self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
            REQUEST.RESPONSE.redirect('sortorder_html')

    security.declareProtected(view_management_screens, 'set_default_sortorder')
    def set_default_sortorder(self, sortorder = DEFAULT_SORTORDER, REQUEST=None):
        """ Set sortorder attribute to default of all folder items """
        for item in self.objectValues():
            if hasattr(item, 'sortorder'):
                item.sortorder = sortorder
        if REQUEST: REQUEST.RESPONSE.redirect(self.absolute_url() + '/manage_workspace')

    security.declareProtected(PERMISSION_VALIDATE_OBJECTS, 'validateObject')
    def validateObject(self, id='', status='', comment='', REQUEST=None):
        """ """
        err = ''
        success = False
        try:
            status = int(status)
            if status == -1 and len(comment)<=0:
                raise Exception, self.getPortalTranslations().translate('', 'You must insert a comment explaining why the items is not ok')
            ob = self._getOb(id)
            ob.checkThis(int(status), comment, self.REQUEST.AUTHENTICATED_USER.getUserName())
            self.recatalogNyObject(ob)
        except Exception, error:
            err = error
        else:
            success = True
        if REQUEST:
            if err != '': self.setSessionErrorsTrans(err)
            if success: self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
            REQUEST.RESPONSE.redirect('%s/basketofvalidation_html' % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'setRestrictions')
    def setRestrictions(self, access='all', roles=[], REQUEST=None):
        """
        Restrict access to current folder for given roles.
        """
        err = ''
        success = False
        if access == 'all':
            #remove restrictions
            try:
                self.manage_permission(view, roles=[], acquire=1)
            except Exception, error:
                err = error
            else:
                success = True
        else:
            #restrict for given roles
            try:
                roles = self.utConvertToList(roles)
                roles.extend(['Manager', 'Administrator'])
                self.manage_permission(view, roles=roles, acquire=0)
            except Exception, error:
                err = error
            else:
                success = True
        if REQUEST:
            if err != '': self.setSessionErrorsTrans(err)
            if success: self.setSessionInfoTrans(MESSAGE_SAVEDCHANGES, date=self.utGetTodayDate())
            REQUEST.RESPONSE.redirect('%s/restrict_html' % self.absolute_url())

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'renameObjectsIds')
    def renameObjectsIds(self, old_ids, new_ids, REQUEST):
        """renames objects ids for this folder's selected items."""
        r = []
        old_ids = self.utConvertToList(old_ids)
        new_ids = self.utConvertToList(new_ids)
        for i in range(len(old_ids)):
            if self.getObjectById(old_ids[i]).meta_type not in ['Naaya File', 'Naaya ExFile', 'Naaya MediaFile']:
                try:
                    self.manage_renameObject(old_ids[i], new_ids[i])
                    if self.getObjectById(new_ids[i]).meta_type in ['Naaya Document', 'Naaya Story']:
                        new_body = self.getObjectById(new_ids[i]).body.replace(old_ids[i], new_ids[i])
                        self.getObjectById(new_ids[i]).body = new_body
                        self.getObjectById(new_ids[i])._p_changed = 1
                    r.append((MESSAGE_SAVEDCHANGES, {'date': self.utGetTodayDate()}))
                except: r.append(("The ${id} object could not be renamed.", {'id': old_ids[i]}))
            else: r.append("Files can not be renamed.")
        self.setSessionInfoTrans(r)
        return REQUEST.RESPONSE.redirect('%s/index_html' % self.absolute_url())

    security.declareProtected(view_management_screens, 'set_subobject')
    def set_subobject(self, subobject, operation):
        """
        adds or substracts a subobject metatype in a folder
        """
        if subobject in self.getProductsMetaTypes() or subobject in self.get_meta_types(1):
            if operation in ['a', 'add']:
                self.folder_meta_types.append(subobject)
                self._p_changed=1
            elif operation in ['d', 'del', 'delete']:
                self.folder_meta_types.remove(subobject)
                self.p_changed=1

    #blog functionalities
    security.declareProtected(view, 'checkPermissionManageEntries')
    def checkPermissionManageEntries(self, author='', howmany=-1, tag=''):
        """ This function is called on the folder index and it checkes whether or not
            to display the various buttons on that form
        """
        results_objects = []
        btn_select, btn_delete, btn_copy, btn_cut, btn_paste, can_operate = 0, 0, 0, 0, 0, 0
        # btn_select - if there is at least one permisson to delete or copy an object
        # btn_delete - if there is at least one permisson to delete an object
        # btn_copy - if there is at least one permisson to copy an object
        # btn_cut - if there is at least one permisson to delete AND copy an object
        # btn_paste - if there is the add permission and there's some copyed data
        btn_paste = self.cb_dataValid() and self.checkPermissionPasteObjects()
        # Naaya objects
        objects = self.getCatalogedObjects(meta_type=['Naaya Blog Entry'], contributor=author, howmany=howmany, tags_en=tag, path='/%s' % self.absolute_url(1))
        sorted_objects = self.utSortObjsListByAttr(objects, 'releasedate', 1)
        for x in self.utSortObjsListByAttr(sorted_objects, 'sortorder', 0):
            del_permission = x.checkPermissionDeleteObject()
            copy_permission = x.checkPermissionCopyObject()
            edit_permission = x.checkPermissionEditObject()
            if del_permission or copy_permission: btn_select = 1
            if del_permission and copy_permission: btn_cut = 1
            if del_permission: btn_delete = 1
            if copy_permission: btn_copy = 1
            if edit_permission: can_operate = 1
            # version_status:  0 - cannot check out for some reason
            #                  1 - can check in
            #                  2 - can check out
            if not edit_permission or not x.isVersionable():
                version_status = 0
            elif x.hasVersion():
                if x.isVersionAuthor(): version_status = 1
                else: version_status = 0
            else:
                version_status = 2
            if ((del_permission or edit_permission) and not x.approved) or x.approved:
                results_objects.append((del_permission, edit_permission, version_status, copy_permission, x))
        can_operate = can_operate or btn_select
        return (btn_select, btn_delete, btn_copy, btn_cut, btn_paste, can_operate, results_objects)


    security.declareProtected(view, 'getTagCloud')
    def getTagCloud(self, tagCount=1):
        """ """
        import string, copy
        chars = list(string.ascii_lowercase)
        catalog_tool = self.getCatalogTool()
        tag_index = [index for index in catalog_tool.getIndexObjects() if index.id == 'tags_en']
        if tag_index:
            index_obj = tag_index[0]
            lexicon = index_obj.getLexicon()
            words_score = []
            for c in chars:
                words = [word.encode('utf-8') for word in lexicon.getWordsForRightTruncation(unicode(c, 'utf-8'))]
                words_score.extend([(len(index_obj.getDocumentsForWord(w)), w)for w in words if len(index_obj.getDocumentsForWord(w)) >= tagCount])
            buf = copy.copy(words_score)
            buf.sort()
            #Find the difference between max and min, and the distribution
            results = []
            if buf:
                max = buf[-1][0]
                min = buf[0][0]
                diff = max - min
                distribution = diff / 3
                for score, word in words_score:
                    if score == min:
                        tag = 4
                    elif score == max:
                        tag = 1
                    elif score > (min + (distribution*2)):
                        tag = 2
                    elif score > (min + distribution):
                        tag = 3
                    else:
                        tag = 4
                    results.append((tag, word))
            return results

    security.declareProtected(view, 'getLatestComments')
    def getLatestComments(self, folder=None, number=None, date=None):
        """ get the latest comments """
        folder_comments = {}
        if folder is None:  folder = self
        for obj in folder.getObjects():
            folder_comments.update(obj.get_comments_collection())
        if number and date is None:
            t = [(x.date, x) for x in folder_comments.values()][:number]
        elif number is None and date:
            t = [(x.date, x) for x in folder_comments.values() if x.date.isCurrentDay()]
        elif number and date:
            t = [(x.date, x) for x in folder_comments.values() if x.date.isCurrentDay()][:number]
        else:
            t = [(x.date, x) for x in folder_comments.values()]
        t.sort()
        t.reverse()
        return [val for (key, val) in t]

    def _page_result(self, p_result, p_start):
        #Returns results with paging information
        NUMBER_OF_RESULTS_PER_PAGE = 5
        l_paging_information = (0, 0, 0, -1, -1, 0, NUMBER_OF_RESULTS_PER_PAGE, [0])
        try: p_start = abs(int(p_start))
        except: p_start = 0
        batch_obj = batch_utils(NUMBER_OF_RESULTS_PER_PAGE, len(p_result[6]), p_start)
        if len(p_result[6]):
            paging_informations = batch_obj.butGetPagingInformations()
        else:
            paging_informations = (-1, 0, 0, -1, -1, 0, NUMBER_OF_RESULTS_PER_PAGE, [0])
        return (paging_informations, p_result[:6], p_result[6][paging_informations[0]:paging_informations[1]])

    security.declareProtected(view, 'getEntries')
    def getEntries(self, author='', tag='', p_start=0, howmany=-1):
        """ get blog entries """
        return self._page_result(self.checkPermissionManageEntries(author, howmany, tag), p_start)

    def getWeekObjects(self): return [x for x in self.objectValues(self.get_meta_types()) if x.submitted==1 and x.releasedate > (self.utGetTodayDate() - 7)]

    security.declareProtected(view, 'entries_rdf')
    def entries_rdf(self, REQUEST=None, RESPONSE=None):
        """ """
        entries = self.getWeekObjects()
        s = self.getSite()
        lang = self.gl_get_selected_language()
        r = []
        ra = r.append
        ra('<?xml version="1.0" encoding="utf-8"?>')
        ra('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="http://purl.org/rss/1.0/">')
        ra('<channel rdf:about="%s">' % self.utXmlEncode(s.absolute_url()))
        ra('<title>%s</title>' % s.utXmlEncode(s.title))
        ra('<link>%s</link>' % self.utXmlEncode(s.portal_url))
        ra('<description><![CDATA[%s]]></description>' % self.utXmlEncode(s.description))
        ra('<dc:identifier>%s</dc:identifier>' % self.utXmlEncode(s.portal_url))
        ra('<dc:date>%s</dc:date>' % self.utShowFullDateTimeHTML(self.utGetTodayDate()))
        ra('<dc:publisher>%s</dc:publisher>' % self.utXmlEncode(s.publisher))
        ra('<dc:subject>%s</dc:subject>' % self.utXmlEncode(s.title))
        ra('<dc:language>%s</dc:language>' % self.utXmlEncode(lang))
        ra('</channel>')
        for entry in entries:
            ra('<item rdf:about="%s">' % self.utXmlEncode(entry.absolute_url()))
            ra('<title>%s</title>' % self.utXmlEncode(entry.title))
            ra('<url>%s</url>' % self.utXmlEncode(entry.absolute_url()))
            ra('<description><![CDATA[%s]]></description>' % self.utXmlEncode(entry.content[:255]))
            ra('<dc:date>%s</dc:date>' % self.utShowFullDateTimeHTML(entry.releasedate))
            ra('<dc:subject>%s</dc:subject>' % self.utXmlEncode(entry.title))
            ra('<dc:creator>%s</dc:creator>' % self.utXmlEncode(entry.contributor))
            ra('</item>')
        ra("</rdf:RDF>")
        self.REQUEST.RESPONSE.setHeader('content-type', 'application/xhtml+xml')
        return '\n'.join(r)


    security.declareProtected(view, 'comments_rdf')
    def comments_rdf(self, REQUEST=None, RESPONSE=None):
        """ """
        comments = self.getLatestComments(date=self.utGetTodayDate())
        s = self.getSite()
        lang = self.gl_get_selected_language()
        r = []
        ra = r.append
        ra('<?xml version="1.0" encoding="utf-8"?>')
        ra('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns="http://purl.org/rss/1.0/">')
        ra('<channel rdf:about="%s">' % self.utXmlEncode(s.absolute_url()))
        ra('<title>%s</title>' % s.utXmlEncode(s.title))
        ra('<link>%s</link>' % self.utXmlEncode(s.portal_url))
        ra('<description><![CDATA[%s]]></description>' % self.utXmlEncode(s.description))
        ra('<dc:identifier>%s</dc:identifier>' % self.utXmlEncode(s.portal_url))
        ra('<dc:date>%s</dc:date>' % self.utShowFullDateTimeHTML(self.utGetTodayDate()))
        ra('<dc:publisher>%s</dc:publisher>' % self.utXmlEncode(s.publisher))
        ra('<dc:subject>%s</dc:subject>' % self.utXmlEncode(s.title))
        ra('<dc:language>%s</dc:language>' % self.utXmlEncode(lang))
        ra('</channel>')
        for comm in comments:
            ra('<item rdf:about="%s">' % self.utXmlEncode('%s#%s' % (comm.entry, comm.id)))
            ra('<title>%s</title>' % self.utXmlEncode(comm.title))
            ra('<url>%s</url>' % self.utXmlEncode('%s#%s' % (comm.entry, comm.id)))
            ra('<description><![CDATA[%s]]></description>' % self.utXmlEncode(comm.body))
            ra('<dc:date>%s</dc:date>' % self.utShowFullDateTimeHTML(comm.date))
            ra('<dc:subject>%s</dc:subject>' % self.utXmlEncode(comm.title))
            ra('<dc:creator>%s</dc:creator>' % self.utXmlEncode(comm.author))
            ra('</item>')
        ra("</rdf:RDF>")
        self.REQUEST.RESPONSE.setHeader('content-type', 'application/xhtml+xml')
        return '\n'.join(r)

    security.declareProtected(view, 'check_item_title')
    def check_item_title(self, object, obj_title=''):
        """
        Deprecated: This function was moved in NyFolderBase as item_has_title
        Checks if the object has no display title and if it
        has a title in at least one of the portal languages
        """

        if isinstance(object, str): return 0

        if obj_title == '':
            for lang in self.gl_get_languages():
                if object.getLocalProperty('title', lang):
                    return 1


    #zmi pages
    security.declareProtected(view_management_screens, 'manage_edit_html')
    manage_edit_html = PageTemplateFile('zpt/folder_manage_edit', globals())

    security.declareProtected(view_management_screens, 'manage_folder_subobjects_html')
    manage_folder_subobjects_html = PageTemplateFile('zpt/folder_manage_subobjects', globals())

    #site pages
    security.declareProtected(view, 'standard_html_header')
    def standard_html_header(self, REQUEST=None, RESPONSE=None, **args):
        """ """
        context = self.REQUEST.PARENTS[0]
        pt = self._getOb('header', None)
        if pt is None:
            return self.getParentNode().standard_html_header(REQUEST, RESPONSE)
        else:
            if not args.has_key('show_edit'): args['show_edit'] = 0
            args['here'] = context
            args['skin_files_path'] = self.getLayoutTool().getSkinFilesPath()
            return pt.pt_render(extra_context=args).split('<!--SITE_HEADERFOOTER_MARKER-->')[0]

    security.declareProtected(view, 'standard_html_header')
    def standard_html_footer(self, REQUEST=None, RESPONSE=None):
        """ """
        context = self.REQUEST.PARENTS[0]
        pt = self._getOb('footer', None)
        if pt is None:
            return self.getParentNode().standard_html_footer(REQUEST, RESPONSE)
        else:
            pt_context = {'here': context}
            pt_context['skin_files_path'] = self.getLayoutTool().getSkinFilesPath()
            return pt.pt_render(extra_context=pt_context).split('<!--SITE_HEADERFOOTER_MARKER-->')[1]

    security.declareProtected(view, 'index_html')
    def index_html(self, REQUEST=None, RESPONSE=None):
        """ """
        if self.publicinterface:
            l_index = self._getOb('index', None)
            if l_index is not None: return l_index()
        return self.getFormsTool().getContent({'here': self}, 'folder_index')

    security.declareProtected(view, 'index_rdf')
    def index_rdf(self, REQUEST=None, RESPONSE=None):
        """ RDF feed """
        items = REQUEST.get('items', 0)
        rdf_max_items = getattr(self.getSite(), 'rdf_max_items', 0)
        items = items or rdf_max_items
        try:
            items = int(items)
        except TypeError, ValueError:
            items = 0
        return self.getSyndicationTool().syndicateSomething(
            self.absolute_url(), self.getPublishedObjects(items=items))

    security.declareProtected(view, 'index_rdf')
    def index_atom(self, REQUEST=None, RESPONSE=None):
        """ Atom feed """
        items = REQUEST.get('items', 0)
        lang = REQUEST.get('lang', None)
        rdf_max_items = getattr(self.getSite(), 'rdf_max_items', 0)
        items = items or rdf_max_items
        try:
            items = int(items)
        except TypeError, ValueError:
            items = 0
        return self.getSyndicationTool().syndicateAtom(
            context=self, items=self.getPublishedObjects(items=items), lang=lang, REQUEST=REQUEST)

    security.declarePrivate('_getSwitchToLangDenyArgs')
    def _getSwitchToLangDenyArgs(self, meta_type=""):
        """ Return a list of keys to deny according with given meta_type
        """
        deny_args = ('switch_to', 'from_lang', 'switchToLanguage',
                     'file', 'source', 'subtitle_file', 'url',
                 )
        if meta_type in ('Naaya GeoPoint',):
            deny_args = tuple([x for x in deny_args if x != 'url'])
        if meta_type in ('Naaya Story', 'Naaya News'):
            deny_args = tuple([x for x in deny_args if x != 'source'])

        # Custom filter by site
        site = self.getSite()
        custom_meth = getattr(site, '_getCustomSwitchToLangDenyArgs', None)
        if custom_meth:
            deny_args = custom_meth(meta_type, deny_args)
        return deny_args

    security.declareProtected(PERMISSION_EDIT_OBJECTS, 'switchToLanguage')
    def switchToLanguage(self, REQUEST=None, **kwargs):
        """Update session from a given language"""
        # Update kwargs from request
        if not REQUEST:
            return
        parents = REQUEST.get('PARENTS', None)
        if not parents:
            return
        doc = parents[0]
        form = getattr(REQUEST, 'form', {})
        kwargs.update(form)
        kwargs['approved'] = 1
        lang = kwargs.get('lang', None)
        new_lang = kwargs.get('switch_to', None)

        if hasattr(doc, 'switch_content_to_language'):
            # this is a Schema-based content type
            doc.switch_content_to_language(lang, new_lang)
            return

        # TODO: after all relevant content types are ported to Schema, remove
        # the following.

        # Reset current translation
        doc.manageProperties(lang=lang, approved=1)

        # Update attached files
        if doc.meta_type in ('Naaya Extended File',):
            files = doc.getFileItems()
            files[new_lang] = doc.getFileItem(lang)
            files = dict([(key, value) for key, value in files.items() if key != lang])
            doc.setFileItems(files)

        # Create new translation
        kwargs['lang'] = new_lang
        deny_args = self._getSwitchToLangDenyArgs(doc.meta_type)
        kwargs = dict([(key, value) for key, value in kwargs.items()
                       if key not in deny_args])

        doc.manageProperties(**kwargs)

        # Return
        REQUEST.RESPONSE.redirect('%s/edit_html?lang=%s' % (doc.absolute_url(), new_lang))

    security.declareProtected(PERMISSION_EDIT_OBJECTS, 'updateSessionFrom')
    def updateSessionFrom(self, REQUEST=None, **kwargs):
        """Update session from a given language"""
        # Update kwargs from request
        if not REQUEST:
            return
        parents = REQUEST.get('PARENTS', None)
        if not parents:
            return

        doc = parents[0]
        form = getattr(REQUEST, 'form', {})
        kwargs.update(form)
        # Update session info
        from_lang = kwargs.get('from_lang', None)
        lang = kwargs.get('lang', None)

        version = getattr(doc, 'hasVersion', None) and doc.hasVersion()
        context = version and doc.version or doc
        for key, value in kwargs.items():
            value = context.getPropertyValue(key, from_lang)
            if not value:
                continue
            self.setSession(key, value)
        # Return
        REQUEST.RESPONSE.redirect('%s/edit_html?lang=%s' % (doc.absolute_url(), lang))

    def sort_folderIndex(self, obj_list=[], skey='', rkey=0):
        """
        This function, recieves as argument a list generated by checkPermissionManageObjects
        and sorts the objects by skey
        """

        sortable = [ob[4] for ob in obj_list]
        print sortable





    security.declareProtected(PERMISSION_EDIT_OBJECTS, 'subobjects_html')
    def subobjects_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_subobjects')

    security.declareProtected(PERMISSION_EDIT_OBJECTS, 'edit_html')
    def edit_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_edit')

    security.declareProtected(PERMISSION_EDIT_OBJECTS, 'editlogo_html')
    def editlogo_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_editlogo')

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'basketofapprovals_html')
    def basketofapprovals_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_basketofapprovals')

    security.declareProtected(PERMISSION_VALIDATE_OBJECTS, 'basketofvalidation_html')
    def basketofvalidation_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_basketofvalidation')

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'sortorder_html')
    def sortorder_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_sortorder')

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'restrict_html')
    def restrict_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_restrict')

    security.declareProtected(view, 'menusubmissions')
    def menusubmissions(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_menusubmissions')

    security.declareProtected(view, 'renameobject_html')
    def renameobject_html(self, REQUEST=None, RESPONSE=None, **kwargs):
        """ """
        kwargs['here'] = self
        return self.getFormsTool().getContent(kwargs, 'folder_renameid')

    #administration pages
    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'administration_basket_html')
    def administration_basket_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_administration_basket')

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'administration_logo_html')
    def administration_logo_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_administration_logo')

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'administration_users_html')
    def administration_users_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_administration_users')

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'administration_source_html')
    def administration_source_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_administration_source')

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'administration_portlets_html')
    def administration_portlets_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_administration_portlets')

    security.declareProtected(PERMISSION_PUBLISH_OBJECTS, 'administration_feedback_html')
    def administration_feedback_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'folder_administration_feedback')

    security.declareProtected(view, 'feedback_html')
    def feedback_html(self, REQUEST=None, RESPONSE=None):
        """ """
        return self.getFormsTool().getContent({'here': self}, 'site_feedback')

    csv_import = CSVImportTool('csv_import')
    notifications_subscribe = Subscriber('notifications_subscribe')

InitializeClass(NyFolder)
