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

from unittest import TestSuite, makeSuite

from Products.Naaya.tests.NaayaTestCase import NaayaTestCase
from Products.NaayaCore.NotificationTool.interfaces import ISubscriptionTarget
from Products.NaayaCore.NotificationTool.interfaces import \
    ISubscriptionContainer
from Products.NaayaCore.NotificationTool.NotificationTool import \
    fetch_subscriptions
from Products.NaayaCore.NotificationTool.NotificationTool import \
    walk_subscriptions
from Products.NaayaCore.NotificationTool.NotificationTool import \
    AccountSubscription
from Products.Naaya.NyFolder import NyFolder
from Products.Naaya.NyFolder import addNyFolder
from naaya.core.utils import path_in_site

class SubscriptionTest(NaayaTestCase):
    # this is not a real NaayaTestCase, just a unit test, but we need
    # to have the SubscriptionContainer annotation registered

    def afterSetUp(self):
        self.root = NyFolder('root', 'contributor')

    def beforeTearDown(self):
        del self.root

    def test_add(self):
        sc = ISubscriptionContainer(self.root)
        self.assertEqual(sc._next_id, 1)

        sub1 = AccountSubscription('gigel', 'instant', 'en')
        sub2 = AccountSubscription('user2', 'instant', 'en')
        sc.add(sub1)
        sc.add(sub2)

        subs = list(sc)
        self.assertEqual(len(subs), 2)
        self.assertTrue(subs[0] is sub1)
        self.assertTrue(subs[1] is sub2)

        enum = dict(sc.list_with_keys())
        self.assertEqual(enum.keys(), [1, 2])
        self.assertTrue(enum[1] is sub1)
        self.assertTrue(enum[2] is sub2)
        self.assertEqual(sc._next_id, 3)

    def test_remove(self):
        sc = ISubscriptionContainer(self.root)
        sub1 = AccountSubscription('user1', 'instant', 'en')
        sub2 = AccountSubscription('user2', 'instant', 'en')
        sc.add(sub1)
        sc.add(sub2)
        self.assertEqual(len(list(sc)), 2)

        enum = dict(sc.list_with_keys())
        self.assertTrue(enum[1] is sub1)

        sc.remove(1)
        self.assertEqual(len(list(sc)), 1)
        self.assertTrue(list(sc)[0] is sub2)

    def test_marker_interface(self):
        """
        make sure the marker interface ISubscriptionTarget is
        properly set on various classes
        """

        from Products.Naaya.NySite import NySite
        from naaya.content.document.document_item import NyDocument
        from naaya.content.url.url_item import NyURL

        for cls in (NySite, NyFolder, NyDocument, NyURL):
            self.assertTrue(ISubscriptionTarget.implementedBy(cls),
                            "class %r does not accept subscriptions" % cls)

class SubscriptionListingTest(NaayaTestCase):
    def afterSetUp(self):
        addNyFolder(self.portal, id='f1', contributor='contributor')
        addNyFolder(self.portal['f1'], id='a', contributor='contributor')
        addNyFolder(self.portal['f1'], id='b', contributor='contributor')
        addNyFolder(self.portal['f1']['b'], id='2', contributor='contributor')

        f1 = self.portal['f1']
        f1_b_sc = ISubscriptionContainer(f1['b'])
        f1_b_2_sc = ISubscriptionContainer(f1['b']['2'])

        self.user1_sub = AccountSubscription('user1', 'instant', 'en')
        f1_b_sc.add(self.user1_sub)

        self.user2_sub = AccountSubscription('user2', 'instant', 'en')
        f1_b_2_sc.add(self.user2_sub)

    def beforeTearDown(self):
        self.portal.manage_delObjects(['f1'])

    def test_fetch_subscriptions(self):
        f1 = self.portal['f1']
        subs1 = list(fetch_subscriptions(f1['b']['2'], inherit=False))
        self.assertEqual(len(subs1), 1)
        self.assertTrue(self.user2_sub in subs1)

        subs2 = list(fetch_subscriptions(f1['b']['2'], inherit=True))
        self.assertEqual(len(subs2), 2)
        self.assertTrue(self.user1_sub in subs2)
        self.assertTrue(self.user2_sub in subs2)

    def test_walk_subscriptions(self):
        subs1 = list((path_in_site(obj), sub) for
                     obj, n, sub in walk_subscriptions(self.portal))
        self.assertEqual(len(subs1), 2)
        self.assertTrue(('f1/b/2', self.user2_sub) in subs1)
        self.assertTrue(('f1/b', self.user1_sub) in subs1)

        subs2 = list((path_in_site(obj), sub) for
                     obj, n, sub in
                     walk_subscriptions(self.portal['f1']['b']['2']))
        self.assertEqual(len(subs2), 1)
        self.assertTrue(('f1/b/2', self.user2_sub) in subs1)

        subs3 = list(walk_subscriptions(self.portal['f1']['a']))
        self.assertEqual(len(subs3), 0)

def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(SubscriptionTest))
    suite.addTest(makeSuite(SubscriptionListingTest))
    return suite
