import os
import unittest

import transaction

def wrap_with_request(app):
    from StringIO import StringIO
    from ZPublisher.HTTPRequest import HTTPRequest
    from ZPublisher.HTTPResponse import HTTPResponse
    from Acquisition import Implicit

    class FakeRootObject(Implicit): pass

    fake_root = FakeRootObject()
    fake_root.app = app

    stdin = StringIO()
    environ = {'REQUEST_METHOD': 'GET',
               'SERVER_NAME': 'nohost',
               'SERVER_PORT': '80'}
    request = HTTPRequest(stdin, environ, HTTPResponse(), clean=1)

    anonymous_user = fake_root.app.acl_users._nobody
    request.AUTHENTICATED_USER = anonymous_user

    fake_root.REQUEST = request

    return fake_root

def portal_fixture(app):
    from Products.Naaya.NySite import manage_addNySite
    manage_addNySite(app, 'portal', 'Naaya Test Site')
    portal = app.portal

    portal.mail_address_from = 'from.zope@example.com'
    portal.administrator_email = 'site.admin@example.com'

    acl_users = portal.acl_users
    acl_users._doAddUser('test_user_1_', 'secret', ['Manager'], '', '', '', '')
    acl_users._doAddUser('contributor', 'contributor', ['Contributor'], '',
                         'Contributor', 'Test', 'contrib@example.com')
    acl_users._doAddUser('reviewer', 'reviewer', ['Reviewer'], '',
                         'Reviewer', 'Test', 'reviewer@example.com')
    acl_users._doAddUser('user1', 'user1', ['Contributor'], '',
                         'User', 'One', 'user1@example.com')
    acl_users._doAddUser('user2', 'user2', ['Contributor'], '',
                         'User', 'Two', 'user2@example.com')
    acl_users._doAddUser('user3', 'user3', ['Contributor'], '',
                         'User', 'Three', 'user3@example.com')


class NaayaTestCase(unittest.TestCase):
    def setUp(self):
        self.afterSetUp()

    def tearDown(self):
        self.beforeTearDown()

    def afterSetUp(self):
        # TODO: deprecate and remove
        pass

    def beforeTearDown(self):
        # TODO: deprecate and remove
        pass

    def login(self, name='test_user_1_'):
        # TODO: deprecate and remove
        acl_users = self.portal.acl_users
        user = acl_users.getUserById(name).__of__(acl_users)
        self.fake_request.AUTHENTICATED_USER = user
        from AccessControl.SecurityManagement import newSecurityManager
        newSecurityManager(None, user)

    def logout(self):
        # TODO: deprecate and remove
        self.fake_request.AUTHENTICATED_USER = self.app.acl_users._nobody
        from AccessControl.SecurityManagement import noSecurityManager
        noSecurityManager()

    def _portal(self):
        # TODO: deprecate and remove
        return self.portal

    def printLogErrors(self, min_severity=0):
        """Print out the log output on the console.
        """
        import zLOG
        if hasattr(zLOG, 'old_log_write'):
            return
        def log_write(subsystem, severity, summary, detail, error,
                      PROBLEM=zLOG.PROBLEM, min_severity=min_severity):
            if severity >= min_severity:
                print "%s(%s): %s %s" % (subsystem, severity, summary, detail)
        zLOG.old_log_write = zLOG.log_write
        zLOG.log_write = log_write

    def install_content_type(self, meta_type):
        content_type = self.portal.get_pluggable_item(meta_type)
        self.portal.manage_install_pluggableitem(meta_type)
        add_content_permissions = deepcopy(self.portal.acl_users.getPermission('Add content'))
        add_content_permissions['permissions'].append(content_type['permission'])
        self.portal.acl_users.editPermission('Add content', **add_content_permissions)

    def remove_content_type(self, meta_type):
        content_type = self.portal.get_pluggable_item(meta_type)
        add_content_permissions = deepcopy(self.portal.acl_users.getPermission('Add content'))
        add_content_permissions['permissions'].remove(content_type['permission'])
        self.portal.acl_users.editPermission('Add content', **add_content_permissions)
        self.portal.manage_uninstall_pluggableitem(meta_type)

FunctionalTestCase = NaayaTestCase # not really, but good enough for us

from nose.plugins import Plugin

class NaayaPortalTestPlugin(Plugin):
    """
    Nose plugin that prepares the environment for a NaayaTestCase to run
    """

    def __init__(self, tzope):
        Plugin.__init__(self)
        self.tzope = tzope
        self.cleanup_portal_layer = None
        self.cleanup_test_layer = None

    def options(self, parser, env):
        pass

    def configure(self, options, config):
        self.enabled = True

    def begin(self):
        from Products.ExtFile import ExtFile
        ExtFile.REPOSITORY_PATH = ['var', 'testing']

        cleanup, portal_db_layer = self.tzope.db_layer()

        app = portal_db_layer.open().root()['Application']
        app.acl_users._doAddUser('admin', '', ['Manager', 'Administrator'], [])
        transaction.commit()

        fake_root = wrap_with_request(app)
        wrapped_app = fake_root.app
        admin_user = wrapped_app.acl_users.getUserById('admin')
        fake_root.REQUEST.AUTHENTICATED_USER = admin_user
        portal_fixture(wrapped_app)

        transaction.commit()
        self.cleanup_portal_layer = cleanup

    def finalize(self, result):
        assert self.cleanup_test_layer is None
        self.cleanup_portal_layer()
        self.cleanup_portal_layer = None

        repository = os.path.join(INSTANCE_HOME, 'var', 'testing')
        if os.path.isdir(repository):
            import shutil
            shutil.rmtree(repository)

    def prepareTestCase(self, testCase):
        assert self.cleanup_test_layer is None
        the_test = testCase.test

        if isinstance(the_test, NaayaTestCase):
            cleanup, test_db_layer = self.tzope.db_layer()

            app = test_db_layer.open().root()['Application']
            fake_root = wrap_with_request(app)
            wrapped_app = fake_root.app

            the_test.wsgi_request = self.tzope.wsgi_app
            the_test.app = wrapped_app
            the_test.portal = wrapped_app['portal']
            the_test.fake_request = fake_root.REQUEST

            self.cleanup_test_layer = cleanup


    def afterTest(self, test):
        if self.cleanup_test_layer is not None:
            self.cleanup_test_layer()
            self.cleanup_test_layer = None
