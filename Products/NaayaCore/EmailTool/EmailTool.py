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
import time
import smtplib
import cStringIO
from urlparse import urlparse
import logging
import email.MIMEText, email.Utils, email.Charset, email.Header

#Zope imports
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl.Permissions import view_management_screens, view
from OFS.Folder import Folder
from Products.PageTemplates.PageTemplateFile import PageTemplateFile

#Product imports
from Products.NaayaCore.constants import *
import EmailTemplate
from EmailSender import build_email
from naaya.core.permissions import naaya_admin
from naaya.core.utils import force_to_unicode

mail_logger = logging.getLogger('naaya.core.email')

def manage_addEmailTool(self, REQUEST=None):
    """ """
    ob = EmailTool(ID_EMAILTOOL, TITLE_EMAILTOOL)
    self._setObject(ID_EMAILTOOL, ob)
    self._getOb(ID_EMAILTOOL).loadDefaultData()
    if REQUEST is not None:
        return self.manage_main(self, REQUEST, update_menu=1)

class EmailTool(Folder):
    """ """

    meta_type = METATYPE_EMAILTOOL
    icon = 'misc_/NaayaCore/EmailTool.gif'

    manage_options = (
        Folder.manage_options[:1]
        +
        (
            {'label': 'Settings', 'action': 'manage_settings_html'},
        )
        +
        Folder.manage_options[3:]
    )

    meta_types = (
        {'name': METATYPE_EMAILTEMPLATE, 'action': 'manage_addEmailTemplateForm', 'permission': PERMISSION_ADD_NAAYACORE_TOOL},
    )
    all_meta_types = meta_types

    manage_addEmailTemplateForm = EmailTemplate.manage_addEmailTemplateForm
    manage_addEmailTemplate = EmailTemplate.manage_addEmailTemplate

    security = ClassSecurityInfo()

    def __init__(self, id, title):
        """ """
        self.id = id
        self.title = title

    security.declarePrivate('loadDefaultData')
    def loadDefaultData(self):
        #load default stuff
        pass

    def _guess_from_address(self):
        if self.portal_url != '':
            return 'notifications@%s' % urlparse(self.getSite().get_portal_domain())[1]
        else:
            return 'notifications@%s' % self.REQUEST.SERVER_NAME

    def _get_from_address(self):
        addr_from = self.getSite().mail_address_from
        return addr_from or self._guess_from_address()

    _errors_report = PageTemplateFile('zpt/configuration_errors_report', globals())
    security.declareProtected(naaya_admin, 'configuration_errors_report')
    def configuration_errors_report(self):
        errors = []
        if not (self.mail_server_name and self.mail_server_port):
            errors.append('Mail server address/port not configured')
        if not self._get_from_address():
            errors.append('"From" address not configured')
        return self._errors_report(errors=errors)

    #api
    security.declareProtected(view, 'sendEmail')
    def sendEmail(self, p_content, p_to, p_from, p_subject):
        #sends a generic email
        if not isinstance(p_to, list):
            p_to = [e.strip() for e in p_to.split(',')]

        p_to = filter(None, p_to) # filter out blank recipients

        try:
            site = self.getSite()
            site_path = '/'.join(site.getPhysicalPath())
        except:
            site = None
            site_path = '[no site]'

        try:
            if diverted_mail is not None: # we're inside a unit test
                diverted_mail.append([p_content, p_to, p_from, p_subject])
                return 1
            elif not (self.mail_server_name and self.mail_server_port):
                mail_logger.info('Not sending email from %r because mail '
                                 'server is not configured',
                                 site_path)
                return 0
            elif not p_to:
                mail_logger.info('Not sending email from %r - no recipients',
                                 site_path)
                return 0
            else:
                mail_logger.info('Sending email from site: %r '
                                 'to: %r subject: %r',
                                 site_path, p_to, p_subject)
                l_message = create_message(p_content, p_to, p_from, p_subject)
                server = smtplib.SMTP(self.mail_server_name,
                                      self.mail_server_port)
                server.sendmail(p_from, p_to, l_message)
                server.quit()
                return 1
        except:
            mail_logger.error('Did not send email from site: %r to: %r '
                              'because an error occurred',
                              site_path, p_to)
            if site is not None:
                self.getSite().log_current_error()
            return 0

    #zmi actions
    security.declareProtected(view_management_screens, 'manageSettings')
    def manageSettings(self, mail_server_name='', mail_server_port='', administrator_email='', mail_address_from='', notify_on_errors='', REQUEST=None):
        """ """
        site = self.getSite()
        try: mail_server_port = int(mail_server_port)
        except: mail_server_port = site.mail_server_port
        if notify_on_errors: notify_on_errors = 1
        else: notify_on_errors = 0
        site.mail_server_name = mail_server_name
        site.mail_server_port = mail_server_port
        site.mail_address_from = mail_address_from
        site.administrator_email = administrator_email
        site.notify_on_errors = notify_on_errors
        self._p_changed = 1
        if REQUEST:
            REQUEST.RESPONSE.redirect('manage_settings_html?save=ok')

    #zmi pages
    security.declareProtected(view_management_screens, 'manage_settings_html')
    manage_settings_html = PageTemplateFile('zpt/email_settings', globals())

InitializeClass(EmailTool)

diverted_mail = None
def divert_mail(enabled=True):
    global diverted_mail
    if enabled:
        diverted_mail = []
        return diverted_mail
    else:
        diverted_mail = None

def safe_header(value):
    """ prevent header injection attacks (the email library doesn't) """
    if '\n' in value:
        return email.Header.Header(value.encode('utf-8'), 'utf-8')
    else:
        return value

def hack_to_use_quopri(message):
    """
    force message payload to be encoded using quoted-printable
    http://mail.python.org/pipermail/baypiggies/2008-September/003984.html
    """

    charset = email.Charset.Charset('utf-8')
    charset.header_encoding = email.Charset.QP
    charset.body_encoding = email.Charset.QP

    del message['Content-Transfer-Encoding']
    message.set_charset(charset)

def create_message(text, addr_to, addr_from, subject):
    if isinstance(addr_to, basestring):
        addr_to = (addr_to,)
    addr_to = ', '.join(addr_to)
    subject = force_to_unicode(subject)
    text = force_to_unicode(text)

    message = email.MIMEText.MIMEText(text.encode('utf-8'), 'plain')
    hack_to_use_quopri(message)
    message['To'] = safe_header(addr_to)
    message['From'] = safe_header(addr_from)
    message['Subject'] = safe_header(subject)
    message['Date'] = email.Utils.formatdate()

    return message.as_string()
