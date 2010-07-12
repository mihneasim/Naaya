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

#constants
_SESSION_ERRORS = "site_errors"
_SESSION_INFO = "site_infos"

class session_manager:
    """This class has some methods to work with session variables"""

    def __init__(self):
        """Constructor"""
        pass

    def _sessionExists(self):
        """
        Check if a session has been created for this visitor
        """
        if 'SESSION' in self.REQUEST.other:
            # this occurs when testing
            return True
        elif self.session_data_manager.hasSessionData():
            return True
        else:
            return False

    def __isSession(self, key):
        """Test if exists a variable with the given key in SESSION"""
        if not self._sessionExists():
            return 0
        return self.REQUEST.SESSION.has_key(key)

    def __getSession(self, key, default):
        """Get a key value from SESSION; if that key doesn't exist then return default value"""
        if not self._sessionExists():
            return default
        try: return self.REQUEST.SESSION[key]
        except: return default

    def __setSession(self, key, value):
        """Add a value to SESSION"""
        try: self.REQUEST.SESSION.set(key, value)
        except: pass

    def __delSession(self, key):
        """Delete a value from SESSION"""
        if not self._sessionExists():
            return
        try: self.REQUEST.SESSION.delete(key)
        except: pass

    #Public methods
    def getSession(self, key, default):
        return self.__getSession(key, default)

    def setSession(self, key, value):
        return self.__setSession(key, value)

    def delSession(self, key):
        return self.__delSession(key)

    def delSessionKeys(self, keys):
        map(self.__delSession, keys)

    def isSession(self, key):
        return self.__isSession(key)

    #manage information
    def isSessionInfo(self):
        return self.__isSession(_SESSION_INFO)

    def getSessionInfo(self, default=None):
        return self.__getSession(_SESSION_INFO, default)

    def _translateSessionMessages(self, messages, lang=None, **kwargs):
        """
        Translates Session messages using interpolation like so:

        >>> self._translateSessionMessages(u"Hello world")
        [u'Hello world']

        >>> self._translateSessionMessages("Message ${a1} ${a2}", a1="aaaa", a2="bbbb")
        [u'Message aaaa bbbb']

        >>> self._translateSessionMessages([('First message ${arg1}', {'arg1': 'axxx'}), 'Second message', ])
        [u'First message axxx', 'Second message']

        >>> self._translateSessionMessages(['First message','Second message'])
        ['First message', 'Second message']
        """

        if lang is None:
            lang = self.gl_get_selected_language()

        def translate(msgid, mapping = {}):
            return self.getPortalTranslations().translate(domain = None,
                    msgid = msgid, mapping=mapping, target_language = lang)

        if isinstance(messages, (str, unicode)):
            return [translate(messages, kwargs), ]
        elif isinstance(messages, (list, tuple)): # This is the 3rd example
            translated_messages = []
            for message in messages:
                if isinstance(message, (list, tuple)):
                    message_str = message[0] #the message
                    try:
                        interpolation_params = message[1]
                    except IndexError:
                        interpolation_params = {}
                    trans_message = translate(message_str, interpolation_params)
                elif isinstance(message, (str, unicode)):
                    trans_message = translate(message)
                else:
                    trans_message = translate(str(message))

                if not trans_message: # There is no translation return unmodified
                    trans_message = message
                translated_messages.append(trans_message)
            return translated_messages
        else:
            raise ValueError("Invalid arguments")

    def setSessionInfoTrans(self, messages, lang=None, **kwargs):
        self.__setSession(_SESSION_INFO, self._translateSessionMessages(messages, lang, **kwargs))

    def setSessionInfo(self, value):
        self.__setSession(_SESSION_INFO, value)

    def delSessionInfo(self):
        self.__delSession(_SESSION_INFO)

    #manage errors
    def isSessionErrors(self):
        return self.__isSession(_SESSION_ERRORS)

    def getSessionErrors(self, default=None):
        return self.__getSession(_SESSION_ERRORS, default)

    def setSessionErrorsTrans(self, messages, lang=None, **kwargs):
        self.__setSession(_SESSION_ERRORS, self._translateSessionMessages(messages, lang=lang, **kwargs))

    def setSessionErrors(self, value):
        self.__setSession(_SESSION_ERRORS, value)

    def delSessionErrors(self):
        self.__delSession(_SESSION_ERRORS)

    #manage users
    def setUserSession(self, name, roles, domains, firstname, lastname, email, password):
        self.__setSession('user_name', name)
        self.__setSession('user_roles', roles)
        self.__setSession('user_domains', domains)  #not used for the moment
        self.__setSession('user_firstname', firstname)
        self.__setSession('user_lastname', lastname)
        self.__setSession('user_email', email)
        self.__setSession('user_password', password)

    def delUserSession(self):
        self.__delSession('user_name')
        self.__delSession('user_roles')
        self.__delSession('user_domains')
        self.__delSession('user_firstname')
        self.__delSession('user_lastname')
        self.__delSession('user_email')
        self.__delSession('user_password')

    def setRequestRoleSession(self, name, firstname, lastname, email, password,
        organisation, comments, location):
        self.setUserSession(name, '', '', firstname, lastname, email, password)
        self.__setSession('user_organisation', organisation)
        self.__setSession('user_comments', comments)
        self.__setSession('user_location', location)

    def delRequestRoleSession(self):
        self.delUserSession()
        self.__delSession('user_organisation')
        self.__delSession('user_comments')
        self.__delSession('user_location')

    def setCreateAccountSession(self, name, firstname, lastname, email, password):
        self.setUserSession(name, '', '', firstname, lastname, email, password)

    def delCreateAccountSession(self):
        self.delUserSession()

    def getSessionUserName(self, default=''):
        return self.__getSession('user_name', default)

    def getSessionUserRoles(self, default=''):
        return self.__getSession('user_roles', default)

    def getSessionUserDomains(self, default=''):
        return self.__getSession('user_domains', default)

    def getSessionUserFirstname(self, default=''):
        return self.__getSession('user_firstname', default)

    def getSessionUserLastname(self, default=''):
        return self.__getSession('user_lastname', default)

    def getSessionUserEmail(self, default=''):
        return self.__getSession('user_email', default)

    def getSessionUserPassword(self, default=''):
        return self.__getSession('user_password', default)

    def getSessionUserOrganisation(self, default=''):
        return self.__getSession('user_organisation', default)

    def getSessionUserComments(self, default=''):
        return self.__getSession('user_comments', default)

    def getSessionUserLocation(self, default=''):
        return self.__getSession('user_location', default)

    #feedback session
    def setFeedbackSession(self, name='', email='', comments='', who=0):
        self.__setSession('user_name', name)
        self.__setSession('user_email', email)
        self.__setSession('user_comments', comments)
        self.__setSession('user_who', who)

    def delFeedbackSession(self):
        self.__delSession('user_name')
        self.__delSession('user_email')
        self.__delSession('user_comments')
        self.__delSession('user_who')

    def getSessionFeedbackName(self, default=''):
        return self.__getSession('user_name', default)

    def getSessionFeedbackEmail(self, default=''):
        return self.__getSession('user_email', default)

    def getSessionFeedbackComments(self, default=''):
        return self.__getSession('user_comments', default)

    def getSessionFeedbackWho(self, default=''):
        return self.__getSession('user_who', default)

    #blog session
    def setBlogSession(self, title='', body='', author='', email=''):
        self.__setSession('blog_title', title)
        self.__setSession('blog_body', body)
        self.__setSession('blog_author', author)
        self.__setSession('blog_email', email)

    def delBlogSession(self):
        self.__delSession('blog_title')
        self.__delSession('blog_body')
        self.__delSession('blog_author')
        self.__delSession('blog_email')

    def getSessionBlogTitle(self, default=''):
        return self.__getSession('blog_title', default)

    def getSessionBlogBody(self, default=''):
        return self.__getSession('blog_body', default)

    def getSessionBlogAuthor(self, default=''):
        return self.__getSession('blog_author', default)

    def getSessionBlogEmail(self, default=''):
        return self.__getSession('blog_email', default)
