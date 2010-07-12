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

import re
from unittest import TestSuite, makeSuite
from copy import deepcopy
from BeautifulSoup import BeautifulSoup

from Products.Naaya.tests.NaayaFunctionalTestCase import NaayaFunctionalTestCase


class NyContactFunctionalTestCase(NaayaFunctionalTestCase):
    """ TestCase for NaayaContent object """

    def afterSetUp(self):
        self.portal.manage_install_pluggableitem('Naaya Contact')
        from Products.Naaya.NyFolder import addNyFolder
        from naaya.content.contact.contact_item import addNyContact
        addNyFolder(self.portal, 'myfolder', contributor='contributor', submitted=1)
        addNyContact(self.portal.myfolder, id='mycontact', title='My contact', submitted=1, contributor='contributor')
        import transaction; transaction.commit()

    def beforeTearDown(self):
        self.portal.manage_delObjects(['myfolder'])
        self.portal.manage_uninstall_pluggableitem('Naaya Contact')
        import transaction; transaction.commit()

    def test_add(self):
        self.browser_do_login('contributor', 'contributor')
        self.browser.go('http://localhost/portal/info/contact_add_html')
        self.failUnless('<h1>Submit Contact</h1>' in self.browser.get_html())
        form = self.browser.get_form('frmAdd')
        expected_controls = set([
            'lang', 'title:utf8:ustring', 'description:utf8:ustring', 'coverage:utf8:ustring',
            'keywords:utf8:ustring', 'releasedate', 'discussion:boolean',
        ])
        found_controls = set(c.name for c in form.controls)
        self.failUnless(expected_controls.issubset(found_controls),
            'Missing form controls: %s' % repr(expected_controls - found_controls))

        self.browser.clicked(form, self.browser.get_form_field(form, 'title'))
        form['title:utf8:ustring'] = 'test_contact'
        form['description:utf8:ustring'] = 'test_contact_description'
        form['coverage:utf8:ustring'] = 'test_contact_coverage'
        form['keywords:utf8:ustring'] = 'keyw1, keyw2'

        self.browser.submit()
        html = self.browser.get_html()
        self.failUnless('The administrator will analyze your request and you will be notified about the result shortly.' in html)

        self.portal.info.testcontact.approveThis()

        self.browser.go('http://localhost/portal/info/testcontact')
        html = self.browser.get_html()
        self.failUnless(re.search(r'<h1>.*test_contact.*</h1>', html, re.DOTALL))
        self.failUnless('test_contact_description' in html)
        self.failUnless('test_contact_coverage' in html)

        self.browser_do_logout()

    def test_add_error(self):
        self.browser_do_login('contributor', 'contributor')
        self.browser.go('http://localhost/portal/myfolder/contact_add_html')

        form = self.browser.get_form('frmAdd')
        self.browser.clicked(form, self.browser.get_form_field(form, 'title'))
        # enter no values in the fields
        self.browser.submit()

        html = self.browser.get_html()
        self.failUnless('The form contains errors' in html)
        self.failUnless('Value required for "Title"' in html)

    def test_edit(self):
        self.browser_do_login('admin', '')

        self.browser.go('http://localhost/portal/myfolder/mycontact/edit_html')
        form = self.browser.get_form('frmEdit')

        self.failUnlessEqual(form['title:utf8:ustring'], 'My contact')

        form['title:utf8:ustring'] = 'new_contact_title'
        self.browser.clicked(form, self.browser.get_form_field(form, 'title:utf8:ustring'))
        self.browser.submit()

        self.failUnlessEqual(self.portal.myfolder.mycontact.title, 'new_contact_title')

        self.browser.go('http://localhost/portal/myfolder/mycontact/edit_html?lang=fr')
        form = self.browser.get_form('frmEdit')
        form['title:utf8:ustring'] = 'french_title'
        self.browser.clicked(form, self.browser.get_form_field(form, 'title:utf8:ustring'))
        self.browser.submit()

        self.failUnlessEqual(self.portal.myfolder.mycontact.title, 'new_contact_title')
        self.failUnlessEqual(self.portal.myfolder.mycontact.getLocalProperty('title', 'fr'), 'french_title')

        self.browser_do_logout()

    def test_edit_error(self):
        self.browser_do_login('admin', '')
        self.browser.go('http://localhost/portal/myfolder/mycontact/edit_html')

        form = self.browser.get_form('frmEdit')
        self.browser.clicked(form, self.browser.get_form_field(form, 'title:utf8:ustring'))
        form['title:utf8:ustring'] = ''
        self.browser.submit()

        html = self.browser.get_html()
        self.failUnless('The form contains errors' in html)
        self.failUnless('Value required for "Title"' in html)

        self.browser_do_logout()

    def test_manage(self):
        self.browser_do_login('admin', '')

        self.browser.go('http://localhost/portal/myfolder/mycontact/manage_edit_html')
        form = self.browser.get_form('frmEdit')
        self.failUnlessEqual(form['title:utf8:ustring'], 'My contact')
        form['title:utf8:ustring'] = 'new_contact_title'
        self.browser.clicked(form, self.browser.get_form_field(form, 'title:utf8:ustring'))
        self.browser.submit()

        self.failUnlessEqual(self.portal.myfolder.mycontact.title, 'new_contact_title')

        self.browser_do_logout()

    def test_view_in_folder(self):
        self.browser_do_login('admin', '')

        self.browser.go('http://localhost/portal/myfolder')
        html = self.browser.get_html()
        soup = BeautifulSoup(html)

        tables = soup.findAll('table', id='folderfile_list')
        self.assertTrue(len(tables) == 1)

        links_to_contact = tables[0].findAll('a', attrs={'href': 'http://localhost/portal/myfolder/mycontact'})
        self.assertTrue(len(links_to_contact) == 1)
        self.assertTrue(links_to_contact[0].string == 'My contact')

        self.browser_do_logout()

class NyContactVersioningFunctionalTestCase(NaayaFunctionalTestCase):
    """ TestCase for NaayaContent object """
    def afterSetUp(self):
        self.portal.manage_install_pluggableitem('Naaya Contact')
        from naaya.content.contact.contact_item import addNyContact
        addNyContact(self.portal.info, id='ver_contact', title='ver_contact', submitted=1)
        import transaction; transaction.commit()

    def beforeTearDown(self):
        self.portal.info.manage_delObjects(['ver_contact'])
        self.portal.manage_uninstall_pluggableitem('Naaya Contact')
        import transaction; transaction.commit()

    def test_start_version(self):
        from naaya.content.contact.contact_item import contact_item
        self.browser_do_login('admin', '')
        self.failUnlessEqual(self.portal.info.ver_contact.version, None)
        self.browser.go('http://localhost/portal/info/ver_contact/startVersion')
        self.failUnless(isinstance(self.portal.info.ver_contact.version, contact_item))
        self.browser_do_logout()

    def test_edit_version(self):
        self.browser_do_login('admin', '')
        self.browser.go('http://localhost/portal/info/ver_contact/startVersion')

        form = self.browser.get_form('frmEdit')
        form['title:utf8:ustring'] = 'ver_contact_newtitle'
        self.browser.clicked(form, self.browser.get_form_field(form, 'title:utf8:ustring'))
        self.browser.submit()

        ver_contact = self.portal.info.ver_contact
        self.failUnlessEqual(ver_contact.title, 'ver_contact')
        # we can't do ver_contact.version.title because version objects don't have the _languages property
        self.failUnlessEqual(ver_contact.version.getLocalProperty('title', 'en'), 'ver_contact_newtitle')

        self.browser_do_logout()

def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(NyContactFunctionalTestCase))
    suite.addTest(makeSuite(NyContactVersioningFunctionalTestCase))
    return suite
