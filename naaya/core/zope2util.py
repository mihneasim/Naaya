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

"""
naaya.core.zope2util - utilities to make Zope 2 a friendlier place
"""

import datetime

from AccessControl import ClassSecurityInfo
from Acquisition import Implicit
from OFS.SimpleItem import SimpleItem
from Globals import InitializeClass
from AccessControl.Permissions import view
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from DateTime import DateTime

def redirect_to(tmpl):
    """
    Generate a simple view that redirects to the specified URL.

    For example, this declaration:
    >>> the_old_page = redirect_to('%(self_url)s/the_new_page')

    is equivalent with:
    >>> def the_new_page(self, REQUEST):
    >>>     ''' perform redirect '''
    >>>     REQUEST.RESPONSE.redirect(self.absolute_url() + '/the_new_page')

    """
    def redirect(self, REQUEST):
        """ automatic redirect """
        url = tmpl % {
            'self_url': self.absolute_url(),
        }
        REQUEST.RESPONSE.redirect(url)
    return redirect

class RestrictedToolkit(SimpleItem):
    """
    RestrictedToolkit exposes some useful methods to RestrictedPython
    code (e.g. Scripts in ZODB, PageTemplates). You can get a hold of
    the RestrictedPython instance (it's a singleton) easily:

      >>> rstk = self.rstk

    It's pulled form the NySite object via acquisition.
    """
    security = ClassSecurityInfo()
    # by default, all methods are "public"

    _button_form = PageTemplateFile('zpt/button_form.zpt', globals())
    def button_form(self, **kwargs):
        """
        A simple one-button form, useful when a button that does POST
        is more appropriate than a link that does GET.

        It takes a few keyword arguments.
        `label`: what text should appear on the button;
        `button_title`: tooltip text for the button;
        `action`: what should the form do (e.g. ``"POST"``);
        `formdata`: dictionary of name/value pairs to be embedded as
        hidden inputs in the form.

        None of the fields are translated by default; it's your
        responsability to do that before calling ``button_form``.
        """
        return self._button_form(**kwargs)

    def parse_string_to_datetime(self, date_string):
        """
        Parse a date/time string to a Python ``datetime.datetime``
        object.
        """
        from dateutil.parser import parse
        return parse(date_string)

    def convert_datetime_to_DateTime(self, dt):
        """
        Convert a Python ``datetime.datetime`` object to a
        Zope2 ``DateTime``.
        """
        return dt2DT(dt)

    def convert_DateTime_to_datetime(self, DT):
        """
        Convert a Zope2 ``DateTime object`` to a Python
        ``datetime.datetime``.
        """
        return DT2dt(DT)

InitializeClass(RestrictedToolkit)


class CaptureTraverse(Implicit):
    """
    Capture any request path and invoke a callback.

    CaptureTraverse is useful when we need to capture arbitrary request
    paths. If our object is published at `http://example.com/my/object`,
    and we expect requests at `http://example.com/my/object/magic/a/b/c`,
    then we can use CaptureTraverse like so::

      >>> def handle_magic(context, path, REQUEST):
      ...     return ('the page! path=%r, url=%r' %
                      (path, context.absolute_url()))
      >>> class MyObject(SimpleItem):
      ...     # implementation of MyObject
      ...     # ...
      ...
      ...     magic = CaptureTraverse(handle_magic)

    GET requests for `http://example.com/my/object/magic/a/b/c` will
    receive the following response::

      the page! path=('a', 'b', 'c'), url='http://example.com/my/object'

    """

    security = ClassSecurityInfo()

    def __init__(self, callback, path=tuple(), context=None):
        self.callback = callback
        self.path = path
        self.context = context

    def __bobo_traverse__(self, REQUEST, name):
        new_path = self.path + (name,)
        context = self.context or (self.aq_parent,)
        return CaptureTraverse(self.callback, new_path, context).__of__(self)

    def __call__(self, REQUEST):
        assert self.path[-1] == 'index_html'
        return self.callback(self.context[0], self.path[:-1], REQUEST)


##################################################################
### `UnnamedTimeZone`, `dt2DT` and `DT2dt` come from Plone's
### Products.ATContentTypes.utils

class UnnamedTimeZone(datetime.tzinfo):
    """Unnamed timezone info"""

    def __init__(self, minutes):
        self.minutes = minutes

    def utcoffset(self, dt):
        return datetime.timedelta(minutes=self.minutes)

    def dst(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        aheadUTC = self.minutes > 0
        if aheadUTC:
            sign = '+'
            mins = self.minutes * -1
        else:
            sign = '-'
            mins = self.minutes
        wholehours = int(self.minutes / 60.)
        minutesleft = self.minutes % 60
        return """%s%0.2d%0.2d""" % (sign, wholehours, minutesleft)

def dt2DT(date):
    """ Convert Python's datetime to Zope's DateTime """
    args = (date.year, date.month, date.day, date.hour, date.minute, date.second, date.microsecond, date.tzinfo)
    timezone = args[7].utcoffset(date)
    secs = timezone.seconds
    days = timezone.days
    hours = secs/3600 + days*24
    mod = "+"
    if hours < 0:
        mod = ""
    timezone = "GMT%s%d" % (mod, hours)
    args = list(args[:6])
    args.append(timezone)
    return DateTime(*args)

def DT2dt(date):
    """ Convert Zope's DateTime to Pythons's datetime """
    # seconds (parts[6]) is a float, so we map to int
    args = map(int, date.parts()[:6])
    args.append(0)
    args.append(UnnamedTimeZone(int(date.tzoffset()/60)))
    return datetime.datetime(*args)
