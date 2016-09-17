# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
# Copyright (C) 2016 Jason Gray <jasonlevigray3@gmail.com> 
#This program is free software: you can redistribute it and/or modify it 
#under the terms of the GNU General Public License version 3, as published 
#by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful, but 
#WITHOUT ANY WARRANTY; without even the implied warranties of 
#MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
#PURPOSE.  See the GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along 
#with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE
import json
import logging
import html
from gettext import gettext as _

from gi.repository import GLib, Gtk, Gio

from pithos.plugin import PithosPlugin
from .dbus_util.GioNotify import GioNotify

class NotifyPlugin(PithosPlugin):
    preference = 'notify'
    description = 'Shows notifications on song change'
  
    def on_prepare(self):
        try:
            self.notification = GioNotify.sync_init('Pithos')
        except Exception as e:
            self.notification = None
            logging.warning('Notification server not found: {}'.format(e))
            return 'Notification server not found'

        self.show_actions = False

        caps = self.notification.capabilities
        server_info = self.notification.server_information

        if 'action-icons' or 'actions' or 'persistence' in caps:
            self.preferences_dialog = NotifyPrefs(self, self.settings, self.notification, caps)

        self.supports_actions = 'actions' in caps
        self.escape_markup = 'body-markup' in caps

        self.notification.set_hint('desktop-entry', GLib.Variant('s', 'io.github.Pithos'))
        self.notification.set_hint('category', GLib.Variant('s', 'x-gnome.music'))

        server_info = '\n'.join(('{}: {}'.format(k, v) for k, v in server_info.items()))
        logging.debug('\nNotification Server Information:\n{}'.format(server_info))

        caps = '\n'.join((cap for cap in caps))
        logging.debug('\nNotification Server Capabilities:\n{}'.format(caps))

    def on_enable(self):
        self.song_change_handler = self.window.connect('song-changed', self.send_notification)
        self.state_change_handler = self.window.connect('user-changed-play-state', self.send_notification)
        self.closed_handler = self.notification.connect('closed', self.on_notification_closed)
        self.action_invoked_handler = self.notification.connect('action-invoked', self.on_notification_action_invoked)

    def on_notification_closed(self, notification, reason):
        if reason is GioNotify.Closed.REASON_EXPIRED:
            logging.debug('The notification expired.')
        elif reason is GioNotify.Closed.REASON_DISMISSED:
            logging.debug('The notification was dismissed by the user.')
        elif reason is GioNotify.Closed.REASON_CLOSEMETHOD:
            logging.debug('The notification was closed by a call to CloseNotification.')
        elif reason is GioNotify.Closed.REASON_UNDEFINED:
            logging.debug('The notification was closed by undefined/reserved reasons.')

    def on_notification_action_invoked(self, notification, action_id):
        logging.debug('Notification action invoked: {}'.format(action_id))

    def send_notification(self, window, *ignore):
        if window.is_active():
            return
        if self.supports_actions:
            self.notification.clear_actions() 
            if self.show_actions:
                self.set_actions(window.playing != False)
        song = window.current_song
        summary = song.title
        body = '{} {} {} {}'.format(_('by'), song.artist, _('from'), song.album)
        if self.escape_markup:
            body = html.escape(body, quote=False)
        icon = song.artUrl or 'audio-x-generic'
        self.notification.show_new(summary, body, icon)

    def set_actions(self, playing):
        pause_action = 'media-playback-pause'
        play_action = 'media-playback-start'
        skip_action = 'media-skip-forward'
        if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL:
            play_action += '-rtl'
            skip_action += '-rtl'
        if playing:
            self.notification.add_action(pause_action, _('Pause'),
                                         self.window.playpause_notify)
        else:
            self.notification.add_action(play_action, _('Play'),
                                         self.window.playpause_notify)

        self.notification.add_action(skip_action, _('Skip'),
                                     self.window.next_song)

    def on_disable(self):
        if self.notification is None:
            return
        self.window.disconnect(self.song_change_handler)
        self.window.disconnect(self.state_change_handler)
        self.notification.disconnect(self.closed_handler)
        self.notification.disconnect(self.action_invoked_handler)

class NotifyPrefs(Gtk.Dialog):
    def __init__(self, parent, settings, notification, caps, *args, **kwargs):
        super().__init__(*args, use_header_bar=1, **kwargs)
        self.set_default_size(300, -1)
        self.set_resizable(False)
        self.parent = parent
        self.settings = settings
        self.notification = notification
        self.active_settings = []
        self.default_settings = json.dumps({'actions': True,
                                            'action-icons': True,
                                            'persistence': True})
        if not self.settings['data']:
           self.reset_prefs()

        caps_map = {
            'action-icons': (# settings key
            _('Action Icons'), # SettingBox title
            _('Icons in Notification Action Buttons'), # SettingBox subtitle
            ),

            'actions': (
            _('Action Buttons'),
            _('Action Buttons in Notifications'),
            ),

            'persistence': (
            _('Persistent Notifications'),
            _('Notifications will be retained until closed'),
            ),
        }

        header_bar = self.get_header_bar()
        header_bar.set_show_close_button(False)
        header_bar.set_title(_('Notify'))
        header_bar.set_subtitle(_('Preferences'))
        reset_button = Gtk.Button.new_with_label(_('Reset'))
        reset_button.set_halign(Gtk.Align.START)
        reset_button.set_valign(Gtk.Align.CENTER)
        reset_button.set_tooltip_text(_('Reset to Defaults'))
        reset_button.connect('clicked', self.reset_prefs)
        header_bar.pack_start(reset_button)
        close_button = Gtk.Button.new_with_label(_('Close'))
        close_button.set_can_default(True)
        close_button.set_halign(Gtk.Align.END)
        close_button.set_valign(Gtk.Align.CENTER)
        close_button.connect('clicked', lambda *ignore: self.hide())
        header_bar.pack_end(close_button)

        add_separator = False 
        box = self.get_content_area()
        for key, val in caps_map.items():
            # Only "build" boxes for supported settings
            if key in caps:
                if add_separator: # Don't put a separator on the top of the 1st settings box
                    box.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), True, True, 0)
                add_separator = True
                settingbox = SettingBox(self, key, val)
                box.pack_start(settingbox, True, True, 0)
                self.active_settings.append(settingbox)

    def reset_prefs(self, *ignore):
        self.settings['data'] = self.default_settings
        active_settings = self.active_settings
        if active_settings:
            for setting in active_settings:
                setting.switch.set_active(True)

    def get_value(self, key):
        return json.loads(self.settings['data'])[key]

    def set_value(self, key, value):
        settings = json.loads(self.settings['data'])
        if key in settings:
            settings[key] = value
            self.settings['data'] = json.dumps(settings)
            if key == 'actions':
                self.parent.show_actions = value
            elif key == 'action-icons':
                if value is False:
                    self.notification.set_hint(key, None)
                elif value is True:
                    self.notification.set_hint(key, GLib.Variant('b', True))
            elif key == 'persistence':
                # If persistence is in notification server's capabilities
                # it means by default notifications are persistent.
                # Persistence can be overridden with the transient hint.
                # persistence True = no transient hint
                # persistence False = transient hint True                
                if value is False:
                    self.notification.set_hint('transient', GLib.Variant('b', True))
                elif value is True:
                    self.notification.set_hint('transient', None) 

class SettingBox(Gtk.Box):
    def __init__(self, parent, setting_key, caps_map_tuple):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        title, subtitle = caps_map_tuple
        label = Gtk.Label(valign=Gtk.Align.CENTER, halign=Gtk.Align.START)
        label.set_markup('<b>{}</b>\n<small>{}</small>'.format(title, subtitle))
        self.pack_start(label, True, True, 4)
        self.switch = Gtk.Switch(active=not parent.get_value(setting_key), valign=Gtk.Align.CENTER, halign=Gtk.Align.END)
        self.switch.connect('notify::active', lambda s, p: parent.set_value(setting_key, s.get_active()))
        self.switch.set_active(parent.get_value(setting_key))            
        self.pack_end(self.switch, False, False, 2)

