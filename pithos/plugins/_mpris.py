# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2011 Rick Spencer <rick.spencer@canonical.com>
# Copyright (C) 2011-2012 Kevin Mehall <km@kevinmehall.net>
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

import math
import dbus
import dbus.service
from xml.etree import ElementTree

class PithosMprisService(dbus.service.Object):
    MEDIA_PLAYER2_IFACE = 'org.mpris.MediaPlayer2'
    MEDIA_PLAYER2_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'

    def __init__(self, window):
        name = dbus.service.BusName('org.mpris.MediaPlayer2.Pithos', dbus.SessionBus())
        dbus.service.Object.__init__(self, name, '/org/mpris/MediaPlayer2')

        self.window = window
        self._player_state = 'Stopped'
        self._volume = 0.0

        self.window.connect('mpris-metadata-changed', self._on_metadata_changed)
        self.window.connect('mpris-play-state-changed', self._on_playback_status_changed)
        self.window.connect('volume-changed', self._on_volume_changed)

        if self.window.current_song:
            self._on_metadata_changed(self.window, self.window.current_song)

    def _set_volume(self, new_volume):
        self.window.player.set_property('volume', new_volume)

    def _get_position(self):
        try:
            if self.window.query_position():
                position = self.window.query_position() // 1000
            else:
                position = 0
        except:
            position = 0
        return position

    def _get_duration(self):
        try:
            if self.window.query_duration():
                return self.window.query_duration() // 1000
            else:
                return None
        except:
            return None

    def _get_metadata(self, song=None):
        if not song:
            return {'mpris:trackid': '/org/mpris/MediaPlayer2/TrackList/NoTrack'}

        track_id = '/org/mpris/MediaPlayer2/TrackList/%s' %song.trackToken
        metadata = {'mpris:trackid': track_id}

        try:
            if self._get_duration():
                length = dbus.Int64(self._get_duration())
            else:
                length = dbus.Int64(song.trackLength * 1000000)     
            assert length is not None
            metadata['mpris:length'] = length
        except:
            pass

        try:
            if song.rating == 'love':
                userRating = 5
            else:
                userRating = 0
            if song.rating:
                pithos_rating = song.rating
            else:
                pithos_rating = ''
            assert userRating is not None
            assert pithos_rating is not None
            metadata['xesam:userRating'] = userRating
            metadata['pithos:rating'] = pithos_rating
        except:
            pass

        try:
            if song.title:
                title = song.title
            else:
                title = 'Title Unknown'
            assert title is not None
            metadata['xesam:title'] = title
        except:
            pass

        try:
            if song.album:
                album = song.album
            else:
                album = 'Unknown Album'
            assert album is not None
            metadata['xesam:album'] = album
        except:
            pass

        try:
            if song.artist:
                artist = song.artist
            else:
                artist = 'Unknown Artist'
            assert artist is not None
            metadata['xesam:artist'] = [artist]
        except:
            pass

        try:
            if song.artUrl:
                artUrl = song.artUrl
            else:
                if song.artRadio:
                   artUrl = song.artUrl
            assert artUrl is not None
            metadata['mpris:artUrl'] = artUrl
        except:
            pass

        return metadata

    def _on_metadata_changed(self, window, song):
        if song is self.window.current_song:
            self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
            {'Metadata': dbus.Dictionary(self._get_metadata(song=song),
            signature='sv'), }, [])

    def _on_playback_status_changed(self, window, state):
        if self._player_state != state:
            self._player_state = state 
            self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
            {'PlaybackStatus': self._player_state, }, [])

    def _on_volume_changed(self, window, volume):
        if self._volume != volume:
            self._volume = volume
            self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE,
            {'Volume': dbus.Double(self._volume),} , [])

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_IFACE)
    def Raise(self):
        self.window.bring_to_top()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_IFACE)
    def Quit(self):
        self.window.quit()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def LoveCurrentSong(self):
        self.window.love_song()
    
    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def BanCurrentSong(self):
        self.window.ban_song()
    
    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def TiredCurrentSong(self):
        self.window.tired_song()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def UnrateCurrentSong(self):
        self.window.unrate_song()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def Next(self):
        self.window.next_song()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def Previous(self):
        pass

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def Pause(self):
        self.window.pause()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def PlayPause(self):
        self.window.playpause()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def Stop(self):
        self.window.pause()

    @dbus.service.method(dbus_interface=MEDIA_PLAYER2_PLAYER_IFACE)
    def Play(self):
        self.window.play()

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ss', out_signature='v')
    def Get(self, interface_name, property_name):
        return self.GetAll(interface_name)[property_name]

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface_name):
        if interface_name == self.MEDIA_PLAYER2_IFACE:
            return {
                'CanQuit': True,
                'Fullscreen': False,
                'CanSetFullscreen': False,
                'CanRaise': True,
                'HasTrackList': False,
                'Identity': 'Pithos',
                'DesktopEntry': 'pithos',
                'SupportedUriSchemes': ['http', 'file'],
                'SupportedMimeTypes': ['audio/mpeg', 'audio/aac'],
            }
        elif interface_name == self.MEDIA_PLAYER2_PLAYER_IFACE:
            try:
                current_song = self.window.current_song
            except:
                current_song = None
            return {
                'PlaybackStatus': self._player_state,
                'LoopStatus': 'None',
                'Rate': dbus.Double(1.0),
                'Shuffle': False,
                'Metadata': dbus.Dictionary(self._get_metadata(song=current_song), signature='sv'),
                'Volume': dbus.Double(self._volume),
                'Position': dbus.Int64(self._get_position()),
                'MinimumRate': dbus.Double(1.0),
                'MaximumRate': dbus.Double(1.0),
                'CanGoNext': self.window.waiting_for_playlist is not True,
                'CanGoPrevious': False,
                'CanPlay': self.window.current_song is not None,
                'CanPause': self.window.current_song is not None,
                'CanSeek': False,
                'CanControl': True,
            }
        else:
            raise dbus.exceptions.DBusException(
                'org.mpris.MediaPlayer2.Pithos',
                'This object does not implement the %s interface'
                % interface_name)

    @dbus.service.method(dbus_interface=dbus.PROPERTIES_IFACE,
                         in_signature='ssv')
    def Set(self, interface_name, property_name, new_value):
        if interface_name == self.MEDIA_PLAYER2_IFACE:
            pass
        elif interface_name == self.MEDIA_PLAYER2_PLAYER_IFACE:
            if property_name == 'Volume':
                new_vol = math.pow(new_value, 3.0/1.0)
                self._set_volume(new_vol)

        else:
            raise dbus.exceptions.DBusException(
                'org.mpris.MediaPlayer2.Pithos',
                'This object does not implement the %s interface'
                % interface_name)

    @dbus.service.signal(dbus_interface=dbus.PROPERTIES_IFACE,
                         signature='sa{sv}as')
    def PropertiesChanged(self, interface_name, changed_properties,
                          invalidated_properties):
        pass

    # python-dbus does not have our properties for introspection, so we must manually add them
    @dbus.service.method(dbus.INTROSPECTABLE_IFACE, in_signature="", out_signature="s",
                         path_keyword="object_path", connection_keyword="connection")
    def Introspect(self, object_path, connection):
        data = dbus.service.Object.Introspect(self, object_path, connection)
        xml = ElementTree.fromstring(data)

        for iface in xml.findall("interface"):
            name = iface.attrib["name"]
            if name.startswith(self.MEDIA_PLAYER2_IFACE):
                for item, value in self.GetAll(name).items():
                    prop = {"name": item, "access": "read"}
                    if item == "Volume": # Hardcode the only writable property..
                        prop["access"] = "readwrite"
                    # Ugly mapping of types to signatures, is there a helper for this?
                    # KEEP IN SYNC!
                    if isinstance(value, str):
                        prop["type"] = "s"
                    elif isinstance(value, bool):
                        prop["type"] = "b"
                    elif isinstance(value, float):
                        prop["type"] = "d"
                    elif isinstance(value, int):
                        prop["type"] = "x"
                    elif isinstance(value, list):
                        prop["type"] = "as"
                    elif isinstance(value, dict):
                        prop["type"] = "a{sv}"
                    iface.append(ElementTree.Element("property", prop))
        return ElementTree.tostring(xml, encoding="UTF-8")
