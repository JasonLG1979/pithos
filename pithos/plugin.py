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
import glob
import os
import sys
from gi.repository import Gio, GLib

THIRD_PARTY_PLUGINS = 'pithos/third-party-plugins'


class PithosPlugin:
    _PITHOS_PLUGIN = True # used to find the plugin class in a module
    preference = None
    description = ""

    def __init__(self, name, window):
        self.name = name
        self.window = window
        self.preferences_dialog = None
        self.prepared = False
        self.enabled = False

    def enable(self):
        if not self.prepared:
            self.error = self.on_prepare()
            self.prepared = True
        if not self.error and not self.enabled:
            logging.info('Enabling module {}'.format(self.name))
            self.on_enable()
            self.enabled = True

    def disable(self):
        if self.enabled:
            logging.info('Disabling module {}'.format(self.name))
            self.on_disable()
            self.enabled = False

    def on_prepare(self):
        pass

    def on_enable(self):
        pass

    def on_disable(self):
        pass


class ErrorPlugin(PithosPlugin):
    def __init__(self, name, error):
        logging.error('Error loading plugin {}: {}'.format(name, error))
        self.prepared = True
        self.error = error
        self.name = name
        self.enabled = False


def load_plugin(name, window, path):
    try:
        if path:
            sys.path.append(os.path.dirname('{}/{}.py'.format(path, name)))
            module = __import__(name)
        else:
            module = __import__('pithos.plugins.' + name)
            module = getattr(module.plugins, name)

    except ImportError as e:
        return ErrorPlugin(name, e.msg)

    # find the class object for the actual plugin
    for key, item in module.__dict__.items():
        if hasattr(item, '_PITHOS_PLUGIN') and key != "PithosPlugin":
            plugin_class = item
            break
    else:
        return ErrorPlugin(name, "Could not find module class")

    return plugin_class(name, window)


def _maybe_migrate_setting(new_setting, name):
    if name != 'notification_icon':
        return

    old_setting = Gio.Settings.new_with_path('io.github.Pithos.plugin', '/io/github/Pithos/{}/'.format(name))
    if old_setting['enabled']:
        new_setting['enabled'] = True
        old_setting.reset('enabled')

def discover_plugins(path):
    return [fname[:-3] for fname in glob.glob1(path, "*.py") if not fname.startswith("_")]

def load_plugins(window):
    plugins = window.plugins

    settings = window.settings
    in_tree_plugins = settings.props.settings_schema.list_children()
    default_plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins")
    discovered_plugins = discover_plugins(default_plugins_dir)
    try:
        third_party_plugins_dir = os.path.join(
            GLib.get_user_config_dir(),
            THIRD_PARTY_PLUGINS,
        )

        if not os.path.exists(third_party_plugins_dir):
            os.makedirs(third_party_plugins_dir)

        third_party_plugins = discover_plugins(third_party_plugins_dir)

    except (IOError, GLib.Error) as e:
        logging.warning('Error finding 3rd party plugins: {}'.format(e))
        third_party_plugins_dir = None
        third_party_plugins = None

    if third_party_plugins:
        discovered_plugins = discovered_plugins + third_party_plugins

    for name in discovered_plugins:
        path = None
        settings_name = name.replace('_', '-')
        if settings_name not in in_tree_plugins:
            path = third_party_plugins_dir     
        if name not in plugins:                
            plugin = plugins[name] = load_plugin(name, window, path)
        else:
            plugin = plugins[name]

        if settings_name in in_tree_plugins:
            plugin.settings = settings.get_child(settings_name)
            _maybe_migrate_setting(plugin.settings, name)
        else:
            # Out of tree plugin
            plugin.settings = Gio.Settings.new_with_path('io.github.Pithos.plugin',
                                                         '/io/github/Pithos/{}/'.format(settings_name))

        if plugin.settings['enabled']:
            plugin.enable()
        else:
            plugin.disable()
