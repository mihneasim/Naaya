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
# Andrei Laza, Eau de Web

from unittest import TestSuite, makeSuite
import random

from Products.Naaya.tests import NaayaTestCase
from Products.Naaya.tests import NaayaFunctionalTestCase

from Products.Naaya.NyFolder import addNyFolder

class RequestStub(object):
    #simulates HTTP Request with filled form-data
    form = {'lon_min': '24.62327117919922', 'lat_max': '44.43549691351629',
    'address': u'', 'geo_types': [],
    'lon_max': '26.16495895403205', 'geo_query': [u'', ''],
    'path': '', 'lat_min': '43.07123237879009'}

class GeoClustersTestCase(NaayaFunctionalTestCase.NaayaFunctionalTestCase):
    symbol_ids = ['symbol1', 'symbol2']
    howmany = 100
    ob_dicts = []
    cluster_count=20
    cluster_pos = (44.43549691351628, 26.16495895403204)

    def afterSetUp(self):
        self.portal.manage_install_pluggableitem('Naaya GeoPoint')
        self.portal.setDefaultSearchableContent()

        for id in self.symbol_ids:
            self.portal.portal_map.addSymbol(id, id, '', '', '', '')

        addNyFolder(self.portal, 'geo_clusters_test', contributor='contributor',
                submited=1)

    def beforeTearDown(self):
        self.portal.portal_map.admin_set_contenttypes([gt['id'] for gt in self.old_geotagged if gt['geo_enabled']])

        ids = [ob_dict['id'] for ob_dict in self.ob_dicts]
        self.portal.geo_clusters_test.manage_delObjects(ids)

        self.portal.manage_delObjects(['geo_clusters_test'])

        for id in self.symbol_ids:
            self.portal.portal_map.deleteSymbol(id)

        self.portal.manage_uninstall_pluggableitem('Naaya GeoPoint')
        self.portal.setDefaultSearchableContent()

    def test_clusters_function(self):
        #scene setup
        self.ob_dicts=[]
        folder = self.portal.geo_clusters_test
        for i in range(self.howmany):
            ob_dict = dict()
            ob_dict['id'] = 'id_%s' % i
            ob_dict['title'] = 'Title for point %s' % i
            ob_dict['description'] = 'Description for point %s' % i
            ob_dict['geo_location.lat'] = str(random.uniform(-90, 90))
            ob_dict['geo_location.lon'] = str(random.uniform(-180, 180))
            ob_dict['geo_location.address'] = 'Address for point %s' % i
            ob_dict['latitude'] = str(random.uniform(-90, 90))
            ob_dict['longitude'] = str(random.uniform(-180, 180))
            ob_dict['geo_type'] = random.choice(self.symbol_ids)
            ob_dict['URL'] = 'URL for point %s' % i
            ob_dict['id'] = folder.addNyGeoPoint(**ob_dict)
            self.ob_dicts.append(ob_dict)
            ob = folder._getOb(ob_dict['id'])
            ob.approveThis()
            self.portal.portal_map.catalogNyObject(ob)
        self.old_geotagged = self.portal.portal_map.list_geotaggable_types()
        schemas = self.portal.portal_schemas.objectValues()
        self.portal.portal_map.admin_set_contenttypes([schema.id for schema in schemas])

        cl, sg = self.portal.portal_map.search_geo_clusters()

    def test_clusters_close_to_map_bounds(self):
        #scene setup
        folder = self.portal.geo_clusters_test
        self.ob_dicts=[]
        for i in range(self.cluster_count):
            ob_dict=dict()
            ob_dict['id'] = 'id2_%s' % i
            ob_dict['title'] = 'Title for point in cluster %s' % i
            ob_dict['description'] = 'Description for point in cluster %s' % i
            #add radial points to the chosen cluster center in self.cluster_pos
            ob_dict['geo_location.lat'] = str(self.cluster_pos[0] + ((-1)**(i%2)) * (i*0.0001))
            ob_dict['geo_location.lon'] = str(self.cluster_pos[1] + ((-1)**(i%2)) * (i*0.0001))
            ob_dict['geo_location.address'] = 'Address for point in cluster %s' % i
            ob_dict['latitude'] = ob_dict['geo_location.lat']
            ob_dict['longitude'] = ob_dict['geo_location.lon']
            ob_dict['geo_type'] = self.symbol_ids[0]
            ob_dict['URL'] = 'URL for point in cluster %s' % i
            ob_dict['id'] = folder.addNyGeoPoint(**ob_dict)
            self.ob_dicts.append(ob_dict)
            ob = folder._getOb(ob_dict['id'])
            ob.approveThis()
            self.portal.portal_map.catalogNyObject(ob)
        self.old_geotagged = self.portal.portal_map.list_geotaggable_types()
        schemas = self.portal.portal_schemas.objectValues()
        self.portal.portal_map.admin_set_contenttypes([schema.id for schema in schemas])

        r = RequestStub()
        r.form['geo_types'].extend(self.symbol_ids)
        #perform search with frame border slicing cluster in half
        #expecting to get one cluster containing all 20 points
        cluster_obs, single_obs = self.portal.portal_map.search_geo_clusters(REQUEST=r)
        #some random points may fall into our cluster
        #greaterequal is best to evaluate for assertion
        self.assertTrue(cluster_obs[0][1]>=self.cluster_count)


def test_suite():
    suite = TestSuite()
    suite.addTest(makeSuite(GeoClustersTestCase))
    return suite
