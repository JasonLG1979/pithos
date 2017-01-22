# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
from urllib.parse import splittype, splituser, splitpasswd

import gi
gi.require_version('Secret', '1')
from gi.repository import (
    GLib,
    Secret,
    Gtk
)

class _SecretService:
    __account_schema = None
    __service = None
    __default_collection = None
    _current_collection = Secret.COLLECTION_DEFAULT

    @property
    def _account_schema(self):
        if self.__account_schema is None:
            self.__account_schema = Secret.Schema.new(
                'io.github.Pithos.Account',
                Secret.SchemaFlags.NONE,
                {'email': Secret.SchemaAttributeType.STRING},
            )

        return self.__account_schema

    @property
    def _service(self): 
        if self.__service is None:
            self.__service = Secret.Service.get_sync(
                Secret.ServiceFlags.NONE,
                None,
            )

        return self.__service

    @property
    def _default_collection(self):
        if self.__default_collection is None:
            self.__default_collection = Secret.Collection.for_alias_sync(
                self._service,
                Secret.COLLECTION_DEFAULT,
                Secret.CollectionFlags.NONE,
                None,
            )

        return self.__default_collection

    def try_unlock(self, dont_unlock_keyring):
        if not self._default_collection.get_locked():
            logging.debug('The default keyring is unlocked.')
            return True
        else:
            if dont_unlock_keyring:
                self._current_collection = Secret.COLLECTION_SESSION
                logging.debug('The default keyring is locked. Using session collection.')
                return True
            else:
                num_items, unlocked = self._service.unlock_sync(
                    [self._default_collection],
                    None,
                )

                if not num_items or self._default_collection not in unlocked:
                    self._current_collection = Secret.COLLECTION_SESSION
                    logging.debug('The default keyring is locked. Using session collection.')

                return not self._default_collection.get_locked()

    def get_account_password(self, email):
        return Secret.password_lookup_sync(
            self._account_schema,
            {"email": email},
            None,
        ) or ''

    def _clear_account_password(self, email):
        return Secret.password_clear_sync(
            self._account_schema,
            {"email": email},
            None,
        )

    def set_account_password(self, email, password, previous_email=None):
        if previous_email and previous_email != email:
            if not self._clear_account_password(previous_email):
                logging.warning('Failed to clear previous account')

        if not password:
            return self._clear_account_password(email)

        if password == self.get_account_password(email):
            logging.debug('Password unchanged')
            return False

        Secret.password_store_sync(
            self._account_schema,
            {'email': email},
            self._current_collection,
            'Pandora Account',
            password,
            None,
        )

        return True

    def get_account_password_async(self, email, callback, user_data=None):
        def on_password_lookup_finish(source, result, data):
            callback, user_data = data
            password = Secret.password_lookup_finish(result) or ''
            if user_data:
                callback(password, user_data)
            else:
                callback(password)

        Secret.password_lookup(
            self._account_schema,
            {"email": email},
            None,
            on_password_lookup_finish,
            (callback, user_data),
            )

    def set_account_password_async(self, email, password, previous_email=None, callback=None):
        def on_previous_email_password_clear_finish(source, result, callback):
            if not Secret.password_clear_finish(result):
                logging.warning('Failed to clear previous account')

        def on_current_email_password_clear_finish(source, result, callback):
            result = Secret.password_clear_finish(result)
            if callback:
                callback(result)

        def on_password_lookup_finish(source, result, data):
            callback, password = data
            if password == Secret.password_lookup_finish(result) or '':
                logging.debug('Password unchanged')
                if callback:
                    callback(False)
            else:
                Secret.password_store(
                    self._account_schema,
                    {'email': email},
                    self._current_collection,
                    'Pandora Account',
                    password,
                    None,
                    on_password_store_finish,
                    callback,
                )

        def on_password_store_finish(source, result, callback):
            result = Secret.password_store_finish(result)
            if not result:
                logging.warning('Failed to save password')
            if callback:
                callback(result)

        if previous_email and previous_email != email:
            Secret.password_clear(
                self._account_schema,
                {"email": previous_email},
                None,
                on_previous_email_password_clear_finish,
                callback,
            )

        if not password:
            Secret.password_clear(
                self._account_schema,
                {"email": email},
                None,
                on_current_email_password_clear_finish,
                callback,
            )

        else:
            Secret.password_lookup(
                self._account_schema,
                {"email": email},
                None,
                on_password_lookup_finish,
                (callback, password),
            )

SecretService = _SecretService()

def parse_proxy(proxy):
    """ _parse_proxy from urllib """
    scheme, r_scheme = splittype(proxy)
    if not r_scheme.startswith("/"):
        # authority
        scheme = None
        authority = proxy
    else:
        # URL
        if not r_scheme.startswith("//"):
            raise ValueError("proxy URL with no authority: %r" % proxy)
        # We have an authority, so for RFC 3986-compliant URLs (by ss 3.
        # and 3.3.), path is empty or starts with '/'
        end = r_scheme.find("/", 2)
        if end == -1:
            end = None
        authority = r_scheme[2:end]
    userinfo, hostport = splituser(authority)
    if userinfo is not None:
        user, password = splitpasswd(userinfo)
    else:
        user = password = None
    return scheme, user, password, hostport


def open_browser(url, parent=None, timestamp=0):
    logging.info("Opening URL {}".format(url))
    if not timestamp:
        timestamp = Gtk.get_current_event_time()
    try:
        if hasattr(Gtk, 'show_uri_on_window'):
            Gtk.show_uri_on_window(parent, url, timestamp)
        else: # Gtk <= 3.20
            screen = None
            if parent:
                screen = parent.get_screen()
            Gtk.show_uri(screen, url, timestamp)
    except GLib.Error as e:
        logging.warning('Failed to open URL: {}'.format(e.message))

if hasattr(Gtk.Menu, 'popup_at_pointer'):
    popup_at_pointer = Gtk.Menu.popup_at_pointer
else:
    popup_at_pointer = lambda menu, event: menu.popup(None, None, None, None, event.button, event.time)
