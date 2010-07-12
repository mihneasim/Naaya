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
# The Original Code is Naaya version 1.0
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
import Acquisition
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import manage_users
from Globals import InitializeClass
from Products.PageTemplates.PageTemplateFile import PageTemplateFile
from persistent.dict import PersistentDict
from zope.event import notify

try:
    import ldap
    from Products.LDAPUserFolder.utils import GROUP_MEMBER_MAP
    from Products.LDAPUserFolder.LDAPDelegate import LDAPDelegate, filter_format
except:
    pass

#Product imports
from Products.NaayaCore.AuthenticationTool.plugBase import PlugBase
from Products.Naaya.NySite import NySite
from Products.NaayaBase.events import NyAddGroupRoleEvent, NyRemoveGroupRoleEvent

from naaya.core.utils import relative_object_path

plug_name = 'plugLDAPUserFolder'
plug_doc = 'Plugin for LDAPUserFolder'
plug_version = '1.0.0'
plug_object_type = 'LDAPUserFolder'


LDAP_ROOT_ID = 'ROOT'

class ldap_user:
    """Defines a ldap_user. """

    def __init__(self, id, dn, cn, description, parent, childs, cached):
        """Constructor"""
        self.id = id    #unique id, integer
        self.dn = dn    #cannonical name, string
        self.cn= cn     #distinguished name, string
        self.description = description  #string
        self.parent = parent    #parent's id, integer
        self.childs = childs    #a list with all childs nodes
        self.cached = cached    #if this node content is chached or not

    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")

InitializeClass(ldap_user)

class plugLDAPUserFolder(PlugBase):
    """ """

    meta_type = 'Plugin for user folder'
    default_encoding = 'latin-1' # TODO: this should be editable from ZMI
    group_to_roles_mapping = PersistentDict()

    def __init__(self):
        """ constructor """
        self._user_objs = {}
        self.delegate = None
        self.located = {}
        self.canonical_name = {}
        self.buffer = {}
        group_to_roles_mapping = PersistentDict()
        PlugBase.__dict__['__init__'](self)

    security = ClassSecurityInfo()

    def getUserLocation(self, user):
        return self.located.get(user, '-')

    def setUserLocation(self, user, user_location):
        self.located[user] = user_location
        self_p_changed = 1

    def delUserLocation(self, user):
        try:
            del self.located[user]
            self._p_changed = 1
        except:
            pass

    def getUserCanonicalName(self, user):
        value = self.canonical_name.get(user, '-')
        return self.decode_cn(value)

    def setUserCanonicalName(self, user, user_name):
        self.canonical_name[user] = user_name
        self_p_changed = 1

    def delUserCanonicalName(self, user):
        try:
            del self.canonical_name[user]
            self._p_changed = 1
        except:
            pass

    def sort_list(self, list, n, r):
        #returns a sorted list of messages - sort without case-sensitivity
        t = [(x[n].lower(), x) for x in list]
        t.sort()
        if r: t.reverse()
        return [val for (key, val) in t]

    def initializeCache(self, root_dn):
        """Init"""
        self._user_objs[LDAP_ROOT_ID] = ldap_user(LDAP_ROOT_ID, root_dn, LDAP_ROOT_ID, LDAP_ROOT_ID, '', [], 0)
        self._p_changed = 1

    def deleteCache(self, acl_folder):
        """Delete cache"""
        self.initializeCache(self.getRootDN(acl_folder))
        self._p_changed = 1

    def getLDAPServer(self, acl_folder):
        return acl_folder.getServers()[0].get('host', '')

    def getLDAPPort(self, acl_folder):
        return acl_folder.getServers()[0].get('port', '')

    def getRootDN(self, acl_folder):
        return acl_folder.groups_base

    def getGroupScope(self, acl_folder):
        return acl_folder.groups_scope

    def connectLDAP(self, acl_folder):
        """Open a connection to the server"""
        self.delegate = LDAPDelegate()
        self.delegate.addServer(self.getLDAPServer(acl_folder), use_ssl=0)
        self.delegate.connect()

    def getSortedUserRoles(self, skey='', rkey=''):
        """ sort users list """
        acl = self.getUserFolder()
        buf = []
        for user, value in self.getUsersRoles(acl).items():
            buf.append((user, self.getUserCanonicalName(user), self.getUserLocation(user), value))
        if skey == 'user':
            return self.sort_list(buf, 0, rkey)
        elif skey == 'cn':
            return self.sort_list(buf, 1, rkey)
        elif skey == 'group':
            return self.sort_list(buf, 2, rkey)

    def _parseRole(self, role):
        """Parse a structure like [('dn', {'cn':['value1'], 'description':['value2']})]
           and returns a tuple (dn, value1, value2)"""
        dn = role.get('dn', '')
        cn = role.get('cn', '')
        if cn:  cn = cn[0]
        description = role.get('description', '')
        if description: description = description[0]
        return (dn, cn, description)

    def _getRole(self, id):
        """Get an object"""
        try:
            return self._user_objs[id]
        except:
            return None

    def getRoleDescription(self, p_id):
        """Get title"""
        try:
            return self._getRole(p_id).description
        except:
            return ''

    def getRoles(self, expand=[LDAP_ROOT_ID], role_id=LDAP_ROOT_ID, depth=0):
        """Return a piece of roles tree"""
        role = self._user_objs[role_id]
        if role_id == LDAP_ROOT_ID:
            res = [(role, depth)]
            depth = depth + 1
        else:
            res = []
        if role_id in expand:
            #must expand this node
            if not role.cached:
                #must cache this node
                self._cacheRole(role)
            if role.cached:
                #this node is cached
                for child_role_id in role.childs:
                    res.append((self._user_objs[child_role_id], depth))
                    if self.isInList(expand, child_role_id):
                        res.extend(self.getRoles(expand, child_role_id, depth+1))
        return res

    def _searchRoles(self, dn):
        """Search roles in LDAP"""
        searchScope = ldap.SCOPE_ONELEVEL
        searchFilter = 'objectClass=*'
        ROLESretrieveAttributes = ('cn','description')
        roles = self.delegate.search(dn, searchScope, searchFilter, ROLESretrieveAttributes)
        return roles['results']

    def _cacheRole(self, role):
        """Cache a role"""
        #2. get all childs
        child_roles = self._searchRoles(role.dn)
        childs = []
        for child_role in child_roles:
            #3. parse
            child_role_dn, child_role_cn, child_role_description = self._parseRole(child_role)
            self._user_objs[child_role_cn] = ldap_user(child_role_cn, child_role_dn, child_role_cn, child_role_description, role.id, [], 0)
            childs.append(child_role_cn)
        #3. update current node
        role.childs = childs
        role.cached = 1
        self._p_changed = 1
        return 1

    def getLDAPSchema(self, acl_folder):
        """ returns the schema for a LDAPUserFolder """
        return acl_folder.getLDAPSchema()

    def getPluginPath(self):
        return self.absolute_url()

    def isList(self, l):
        return isinstance(l, list)

    def get_groups_roles_map(self):
        groups_roles_map = {}
        def add_roles_from_ob(ob):
            try:
                ob_roles = ob.acl_satellite.getAllLocalRoles()
            except AttributeError:
                return # looks like we found a broken object
            for group_id, group_roles in ob_roles.iteritems():
                all_group_roles = groups_roles_map.setdefault(group_id, [])
                for role in group_roles:
                    location = {
                        'ob': ob,
                        'path': relative_object_path(ob, site),
                        'is_site': ob == site,
                    }
                    all_group_roles.append( (role, location) )

        site = self.getSite()
        add_roles_from_ob(site)
        for b in site.getCatalogTool()(path='/'):
            try:
                ob = b.getObject()
            except:
                pass # broken brain?
            else:
                add_roles_from_ob(ob)

        return groups_roles_map

    security.declareProtected(manage_users, 'map_group_to_role')
    def map_group_to_role(self, group, roles=[], loc='', location='', REQUEST=None):
        """ """

        if loc == 'allsite':
            location = ''

        try:
            ob = self.getSite().unrestrictedTraverse(location)
        except KeyError:
            self.setSessionErrorsTrans('Invalid location path')
            return REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])
        ob.acl_satellite.add_group_roles(group, roles)

        if REQUEST is not None:
            return REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    security.declareProtected(manage_users, 'revoke_group_role')
    def revoke_group_role(self, roles, REQUEST=None):
        """ """

        for roledata in roles:
            group, role, location = roledata.split(';')
            ob = self.getSite().unrestrictedTraverse(location)
            ob.acl_satellite.remove_group_roles(group, [role])

        if REQUEST is not None:
            return REQUEST.RESPONSE.redirect(REQUEST['HTTP_REFERER'])

    def group_member_ids(self, group):
        if not hasattr(self, '_v_ldap_groups_cache'):
            cache = self._v_ldap_groups_cache = {}
        cache = self._v_ldap_groups_cache
        ldap_folder = self.getUserFolder()
        root_dn = self.getRootDN(ldap_folder)
        scope = self.getGroupScope(ldap_folder)
        if not cache.get(group, {}):
            result = self.delegate.search(root_dn, scope, filter_format('cn=%s', (group,)), ['uniqueMember'])
            cache[group] = result
        else:
            result = cache[group]
        if result['size'] > 0:
            group_users = [x.split(',')[0].split('=')[1] for x in result['results'][result['size']-1]['uniqueMember']]
            return group_users
        else:
            return []

    def user_in_group(self, user, group):
        return (str(user) in self.group_member_ids(group))

    def getUsersByRole(self, acl_folder, groups=None):
        """ Return all those users that are in a group """
        all_dns = {}
        res = []
        res_append = res.append
        member_attrs = GROUP_MEMBER_MAP.values()

        if groups is None:  return ()

        for group_id, group_dn in groups:
            dn = self.getRootDN(acl_folder)
            scope = self.getGroupScope(acl_folder)
            result = self.delegate.search(dn, scope, filter_format('(cn=%s)', (group_id,)), ['uniqueMember', 'member'])
            for val in result['results']:
                for dn in val['uniqueMember']:
                    info = self.delegate.search(base=dn, scope=ldap.SCOPE_BASE)
                    [ res_append(i) for i in info['results'] ]
            return res

    def findLDAPUsers(self, acl_folder, params='', term='', role='', dn=''):
        """ search for users in LDAP """
        if self.REQUEST.has_key('search_user'):
            if params and term:
                try:
                    self.buffer = {}
                    users = acl_folder.findUser(search_param=params, search_term=term)
                    [ self.buffer.setdefault(u['uid'], self.decode_cn(u['cn'])) for u in users ]
                    return users
                except: return ()
            else:   return ()
        elif self.REQUEST.has_key('search_role'):
            try:
                self.buffer = {}
                users = self.getUsersByRole(acl_folder, [(role, dn)])
                [ self.buffer.setdefault(u['uid'][0], self.decode_cn(u['cn'][0])) for u in users ]
                return users
            except: return ()
        else:
            return ()

    def _get_user_by_uid(self, uid, acl_folder):
        attrs = acl_folder.getSchemaConfig().keys()
        attrs.extend(['o', 'postalAddress'])
        users = acl_folder.findUser(search_param='uid', search_term=uid, attrs=attrs)
        for user in users:
            if user.get('uid', '') == uid:
                return user

    def _get_user_email(self, user):
        if user is not None:
            return unicode(user.get('mail', ''), 'iso-8859-1').encode('utf-8')
        else:
            return ''

    def getUserEmail(self, p_username, acl_folder):
        #return the email of the given user id
        user = self._get_user_by_uid(p_username, acl_folder)
        return self._get_user_email(user)

    def _get_user_full_name(self, user):
        if user is not None:
            return unicode(user.get('cn', ''), 'iso-8859-1').encode('utf-8')
        else:
            return ''

    def getUserFullName(self, p_username, acl_folder):
        #return the full name of the given user id
        user = self._get_user_by_uid(p_username, acl_folder)
        return self._get_user_full_name(user)

    def _get_user_organisation(self, user):
        if user is not None:
            return unicode(user.get('o', ''), 'iso-8859-1').encode('utf-8')
        else:
            return ''

    def _get_user_postal_address(self, user):
        if user is not None:
            return unicode(user.get('postalAddress', ''), 'iso-8859-1').encode('utf-8')
        else:
            return ''

    def getLDAPUserFirstName(self, dn):
        return unicode(dn.get('sn', ''), 'iso-8859-1').encode('utf-8')

    def getLDAPUserLastName(self, dn):
        return unicode(dn.get('givenName', ''), 'iso-8859-1').encode('utf-8')

    def getLDAPUserEmail(self, dn):
        return unicode(dn.get('mail', ''), 'iso-8859-1').encode('utf-8')

    def getLDAPUserPhone(self, dn):
        return unicode(dn.get('telephoneNumber', ''), 'iso-8859-1').encode('utf-8')

    def getLDAPUserAddress(self, dn):
        return unicode(dn.get('postalAddress', ''), 'iso-8859-1').encode('utf-8')

    def getLDAPUserDescription(self, dn):
        return unicode(dn.get('description', ''), 'iso-8859-1').encode('utf-8')

    def decode_cn(self, value):
        if isinstance(value, str):
            value = value.decode(self.default_encoding)
        return value

    def get_group_roles_in_site(self, user):
        """
        The user may have site-level roles because they are part of an
        LDAP group. If so, return them.
        """
        return self.getSite().acl_satellite.getAdditionalRoles(user)

    security.declarePublic('interface_html')
    interface_html = PageTemplateFile('plugLDAPUserFolder', globals())

    security.declarePublic('pickroles_html')
    pickroles_html = PageTemplateFile('pickRoles', globals())

    _group_members = PageTemplateFile('ldapGroupMembers', globals())
    security.declareProtected(manage_users, 'group_members')
    def group_members(self, REQUEST):
        """ Show members of a LDAP group """
        group_id = REQUEST.form['group_id']
        member_ids = self.group_member_ids(group_id)
        ldap_user_folder = self.getUserFolder()

        def user_data(user_id):
            user_ob = ldap_user_folder.getUser(user_id)
            if user_ob is None:
                name = "[not found]"
            else:
                name = user_ob.getProperty('cn').decode('latin-1')
            return {
                'user_id': user_id,
                'user_name': name,
            }

        options = {
            'group_id': group_id,
            'member_ids': member_ids,
            'members': map(user_data, member_ids),
        }
        return self._group_members(REQUEST, **options)


InitializeClass(plugLDAPUserFolder)

class LdapSatelliteProvider(Acquisition.Implicit):
    """
    This class behaves like LDAPUserFolder's LDAPSatellite class, and manages
    local roles for LDAP groups. It is a singleton that has no state but uses
    acquisition wrappers to figure out from which folder it was accessed.
    """

    def getAllLocalRoles(self):
        current_folder = self.aq_parent
        return getattr(current_folder, '__ny_ldap_group_roles__', {})

    def user_in_group_factory(self, user):
        """
        Returns a function that checks whether `user` is part of the
        specified group.

          >>> user_in_group = self.user_in_group_factory(user)
          >>> user_in_group('group1')
          ... False
          >>> user_in_group('group2')
          ... True

        This factory is especially useful in testing, where it gets replaced
        with a simplified mock factory.
        """
        for auth_plugin in self.getSite().getAuthenticationTool().getSources():
            user_of_plugin = auth_plugin.getUserFolder().getUser(user.getId())
            # ideally we'd check ``if user_of_plugin is user``
            # but LDAPUserFolder returns a different instance of the
            # user object, so that doesn't work. Instead we just make sure
            # a user with the same ID exists in the plugin.
            if user_of_plugin is not None:
                return lambda group: auth_plugin.user_in_group(user, group)
        else:
            return lambda group: False

    def getAdditionalRoles(self, user):
        roles = set()
        user_in_group = self.user_in_group_factory(user)
        mapped_roles = self.getAllLocalRoles()
        for group in mapped_roles:
            if user_in_group(group):
                roles.update(mapped_roles[group])

        current_folder = self.aq_parent
        next_folder = current_folder.aq_inner.aq_parent
        next_satellite = getattr(next_folder, 'acl_satellite', None)
        if next_satellite is not None:
            roles.update(next_satellite.getAdditionalRoles(user))

        return list(roles)

    def add_group_roles(self, group, roles):
        assert not isinstance(roles, basestring), "Roles must be a list or tuple, not string"
        if not roles:
            return

        current_folder = self.aq_parent

        try:
            local_roles = current_folder.__ny_ldap_group_roles__
        except AttributeError:
            local_roles = current_folder.__ny_ldap_group_roles__ = {}

        if group not in local_roles:
            assigned_roles = local_roles[group] = []
        else:
            assigned_roles = local_roles[group]

        roles_to_add = []
        for role in roles:
            if role not in assigned_roles:
                roles_to_add.append(role)
        assigned_roles += roles_to_add

        notify(NyAddGroupRoleEvent(current_folder, group, roles_to_add))

        current_folder._p_changed = True

    def remove_group_roles(self, group, roles):
        assert not isinstance(roles, basestring), "Roles must be a list or tuple, not string"

        current_folder = self.aq_parent
        local_roles = current_folder.__ny_ldap_group_roles__
        assigned_roles = local_roles[group]

        for role in roles:
            if role in assigned_roles:
                assigned_roles.remove(role)
            else:
                raise ValueError('Trying to remove non-existent role')
        if not assigned_roles:
            del local_roles[group]

        notify(NyRemoveGroupRoleEvent(current_folder, group, roles))

        current_folder._p_changed = True

NySite.acl_satellite = LdapSatelliteProvider()
