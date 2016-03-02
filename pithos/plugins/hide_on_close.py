from gi.repository import Gio
from pithos.plugin import PithosPlugin
from gettext import gettext as _

WHITE_LIST = ['mediaplayer@patapon.info', 'laine@knasher.gmail.com']

class HideOnClose(PithosPlugin):    
    preference = 'hide_on_close'
    description = _('Hide to GNOME shell Media extension.')

    def on_prepare(self):
        self.destroy_handler = self.window.connect('delete-event',self.window.on_destroy)
        self.destroy_handler_connected = True
        self.hide_handler_connected = False
        if not self.compatible_extension_enabled:
            return _('No compatible or enabled extension found')

    @property
    def compatible_extension_enabled(self):
        schema = Gio.SettingsSchemaSource.get_default()
        valid_schema = schema.lookup('org.gnome.shell', True)
        if not valid_schema:
            return False
        self.gnome_shell = Gio.Settings.new('org.gnome.shell')
        enabled_extensions = self.gnome_shell.get_value('enabled-extensions')
        compatible_extensions = set(WHITE_LIST).intersection(enabled_extensions)
        if compatible_extensions:
            return True
        else:
            return False

    def on_gsettings_change(self, *ignore):
        if not self.compatible_extension_enabled:
            self.disconnect_window()
            if not self.window.get_visible():
                self.window.set_visible(True)
                self.window.bring_to_top()
        else:
            self.connect_window()             
            
        self.connect_gsettings()
            

    def connect_gsettings(self):
        self.gsettings_connection = self.gnome_shell.connect('changed::enabled-extensions', self.on_gsettings_change)

    def disconnect_gsettings(self):
        self.gnome_shell.disconnect(self.gsettings_connection)

    def connect_window(self):
        if self.destroy_handler_connected:
            self.window.disconnect(self.destroy_handler)
            self.destroy_handler_connected = False
        if not self.hide_handler_connected:
            self.hide_handle = self.window.connect('delete-event', lambda w, e: w.set_visible(False) or True)
            self.hide_handler_connected = True

    def disconnect_window(self):
        if self.hide_handler_connected:   
            self.window.disconnect(self.hide_handle)
            self.hide_handler_connected = False
        if not self.destroy_handler_connected:
            self.destroy_handler = self.window.connect('delete-event',self.window.on_destroy)
            self.destroy_handler_connected = True

    def on_enable(self):
        self.connect_window()
        self.connect_gsettings()

    def on_disable(self):
        self.disconnect_window()
        self.disconnect_gsettings()
