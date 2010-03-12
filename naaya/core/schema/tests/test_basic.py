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

import unittest
import doctest

import formencode

from naaya.core.schema import basic

def make_schema(*args):
    s = basic.Schema()
    for widget_spec in args:
        s.add(widget_spec['label'], basic.Widget(**widget_spec))
    return s

def test_parse_initial_value():
    expected_valid = {
        'None': None,
        'str:': '',
        'str:asdf': 'asdf',
        'unicode:': u'',
        'unicode:qwer': u'qwer',
        'int:0': 0,
        'int:84721': 84721,
        'int:-5243': -5243,
        'bool:': False,
        'bool:False': False,
        'bool:True': True,
    }
    expected_invalid = ('', 'xzzx', 'xy:',
                        'unicode:asdf\xc9qwer',
                        'int:', 'int:asdf',
                        'bool:1', 'bool:true')

    for in_value, expected_value in expected_valid.iteritems():
        out_value = basic.parse_initial_value(in_value)
        assert type(out_value) is type(expected_value)
        assert out_value == expected_value

    for in_value in expected_invalid:
        try:
            basic.parse_initial_value(in_value)
        except ValueError:
            pass
        except Exception, e:
            assert False, "Unexpected exception: %r" % e
        else:
            assert False, "ValueError not raised for input %r" % in_value

class BasicSchemaTest(unittest.TestCase):
    def test_to_python(self):
        schema = make_schema(
            {'label': "num", 'validator': 'int'},
            {'label': "uni", 'validator': 'unicode'})
        py_value = schema.to_python({'num': '13', 'uni': 'asdf'})
        self.assertEqual(py_value, {'num': 13, 'uni': u'asdf'})
        self.assertTrue(type(py_value['uni']) is unicode)

        self.assertRaises(formencode.Invalid,
                          schema.to_python, {'num': 'qwer', 'uni': 'asdf'})
        self.assertRaises(formencode.Invalid,
                          schema.to_python, {'uni': 'asdf'})
        self.assertRaises(formencode.Invalid,
                          schema.to_python, {'num': '13'})

    def test_to_python_with_defaults(self):
        schema = make_schema(
            {'label': "num", 'validator': 'int', 'initial': 'int:50'},
            {'label': "uni", 'validator': 'unicode', 'initial': 'unicode:x'})
        py_value = schema.to_python({})
        self.assertEqual(py_value, {'num': 50, 'uni': u'x'})
        self.assertTrue(type(py_value['uni']) is unicode)

    def test_from_python(self):
        schema = make_schema(
            {'label': "num", 'validator': 'int'},
            {'label': "uni", 'validator': 'unicode'})
        str_value = schema.from_python({'num': 13, 'uni': u'hello world'})
        self.assertTrue(type(str_value['uni']) is str)
        # strangely enough, type(str_value['num']) is int. formencode is weird.

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(BasicSchemaTest))
    suite.addTest(unittest.FunctionTestCase(test_parse_initial_value))
    suite.addTest(doctest.DocTestSuite('naaya.core.schema.basic'))
    return suite
