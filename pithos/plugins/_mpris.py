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
import logging
import math
import codecs
from xml.etree import ElementTree
from gi.repository import (
    GLib,
    Gio,
    Gtk
)
from .dbus_util.DBusServiceObject import *

class PithosMprisService(DBusServiceObject):
    MEDIA_PLAYER2_IFACE = 'org.mpris.MediaPlayer2'
    MEDIA_PLAYER2_PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'
    MEDIA_PLAYER2_PLAYLISTS_IFACE = 'org.mpris.MediaPlayer2.Playlists'

    TRACK_OBJ_PATH = '/io/github/Pithos/TrackId/'
    PLAYLIST_OBJ_PATH = '/io/github/Pithos/PlaylistId/'

    def __init__(self, window, **kwargs):
        """
        Creates a PithosMprisService object.
        """
        super().__init__(object_path='/org/mpris/MediaPlayer2', **kwargs)
        self.window = window
        self._volume = math.pow(self.window.player.props.volume, 1.0/3.0)
        self._metadata = {"mpris:trackid": GLib.Variant('o', '/org/mpris/MediaPlayer2/TrackList/NoTrack'),
                          # Workaround for 
                          # https://github.com/eonpatapon/gnome-shell-extensions-mediaplayer/issues/247
                          "xesam:url": GLib.Variant('s', '')}
        self._playback_status = 'Stopped'
        self._playlists = [('/', '', ''),]
        self._current_playlist = False, ('/', '', '')

    def connect(self):
        self._connect_handlers()
        def on_name_acquired(connection, name):
            logging.info('Got bus name: %s' %name)
            self._update_handlers()
        self.bus_id = Gio.bus_own_name_on_connection(self.connection, 'org.mpris.MediaPlayer2.pithos',
                            Gio.BusNameOwnerFlags.NONE, on_name_acquired, None)

    def disconnect(self):
        self._disconnect_handlers()
        if self.bus_id:
            Gio.bus_unown_name(self.bus_id)
            self.bus_id = 0

    def _connect_handlers(self):
        self._metadatachange_handler_id = self.window.connect("metadata-changed", self._metadatachange_handler)
        self._playstate_handler_id = self.window.connect("play-state-changed", self._playstate_handler)
        self._volumechange_handler_id = self.window.player.connect("notify::volume", self._volumechange_handler)
        self._buffering_finished_handler_id = self.window.connect("buffering-finished", lambda window, position: self.Seeked(position // 1000))
        self._current_playlist_handler_id = self.window.connect("station-changed", self._current_playlist_handler)
        self._update_playlists_handler_id = self.window.connect("stations-processed", self._update_playlists_handler)
        self._stations_dlg_ready_handler_id = self.window.connect("stations-dlg-ready", self._stations_dlg_ready_handler)

    def _disconnect_handlers(self):
        self.window.disconnect(self._metadatachange_handler_id)
        self.window.disconnect(self._playstate_handler_id)
        self.window.player.disconnect(self._volumechange_handler_id)
        self.window.disconnect(self._buffering_finished_handler_id)
        self.window.disconnect(self._current_playlist_handler_id)
        self.window.disconnect(self._update_playlists_handler_id)
        self.window.disconnect(self._stations_dlg_ready_handler_id)
        if self.window.stations_dlg:
            self.window.stations_dlg.disconnect(self._rename_playlist_handler_id)
            self.window.stations_dlg.disconnect(self._add_playlist_handler_id)
            self.window.stations_dlg.disconnect(self._remove_playlist_handler_id)

    def _update_handlers(self):
        # update some of our dynamic props if mpris was enabled after a song has already started.
        if self.window.current_station:
            self._current_playlist_handler(self.window, self.window.current_station)
            self._update_playlists_handler(self.window, self.window.pandora.stations)
        if self.window.current_song:
            self._metadatachange_handler(self.window, self.window.current_song)
            self._playstate_handler(self.window, self.window.playing)
        if self.window.stations_dlg:
            # If stations_dlg exsists already we missed the ready signal and we should connect our handlers.
            self._rename_playlist_handler_id = self.window.stations_dlg.connect('station-renamed', self._rename_playlist_handler)
            self._add_playlist_handler_id = self.window.stations_dlg.connect('station-added', self._add_playlist_handler)
            self._remove_playlist_handler_id = self.window.stations_dlg.connect('station-removed', self._remove_playlist_handler)

    def _stations_dlg_ready_handler(self, *ignore):
        self._rename_playlist_handler_id = self.window.stations_dlg.connect('station-renamed', self._rename_playlist_handler)
        self._add_playlist_handler_id = self.window.stations_dlg.connect('station-added', self._add_playlist_handler)
        self._remove_playlist_handler_id = self.window.stations_dlg.connect('station-removed', self._remove_playlist_handler)

    def _playstate_handler(self, window, state):
        """Updates the playstate in the Sound Menu"""

        play_state = 'Playing' if state else 'Paused'

        if self._playback_status != play_state: # stops unneeded updates
            self._playback_status = play_state
            self._update_MEDIA_PLAYER2_PLAYER_IFACE('PlaybackStatus', 's', self._playback_status)

    def _volumechange_handler(self, player, spec):
        """Updates the volume in the Sound Menu"""
        volume = math.pow(player.props.volume, 1.0/3.0)

        if self._volume != volume: # stops unneeded updates
            self._volume = volume
            self._update_MEDIA_PLAYER2_PLAYER_IFACE('Volume', 'd', self._volume)

    def _update_playlists_handler(self, window, stations):
        self._playlists = [(self.PLAYLIST_OBJ_PATH + station.id, station.name, '') for station in stations]
        self._update_MEDIA_PLAYER2_PLAYLISTS_IFACE('PlaylistCount', 'u', len(self._playlists))

    def _remove_playlist_handler(self, window, station):
        for index, playlist in enumerate(self._playlists[:]):
            if playlist[0].strip(self.PLAYLIST_OBJ_PATH) == station.id:
                del self._playlists[index]
                self._update_MEDIA_PLAYER2_PLAYLISTS_IFACE('PlaylistCount', 'u', len(self._playlists))
                return

    def _rename_playlist_handler(self, stations_dlg, data):
        station_id, new_name = data
        for index, playlist in enumerate(self._playlists):
            if playlist[0].strip(self.PLAYLIST_OBJ_PATH) == station_id:
                self._playlists[index] = (self.PLAYLIST_OBJ_PATH + station_id, new_name, '')
                self.PlaylistChanged(self._playlists[index])
                # PlaylistChanged *should* be enough to tell applets a playlist name has changed.
                # But just in case, force applets to update the playlists list.
                self._update_MEDIA_PLAYER2_PLAYLISTS_IFACE('PlaylistCount', 'u', len(self._playlists))
                return
            
    def _add_playlist_handler(self, window, station):
        new_playlist = (self.PLAYLIST_OBJ_PATH + station.id, station.name, '')
        if not new_playlist in self._playlists:
            self._playlists.append(new_playlist)
            self._update_MEDIA_PLAYER2_PLAYLISTS_IFACE('PlaylistCount', 'u', len(self._playlists))
 
    def _current_playlist_handler(self, window, station):
        new_current_playlist = (self.PLAYLIST_OBJ_PATH + station.id, station.name, '')
        if self._current_playlist != (True, new_current_playlist):
            self._current_playlist = (True, new_current_playlist)
            self._update_MEDIA_PLAYER2_PLAYLISTS_IFACE('ActivePlaylist', '(b(oss))', self._current_playlist)

    def _metadatachange_handler(self, window, song):
        """Updates the song info in the Sound Menu"""

        if song is self.window.current_song: # we only care about the current song
            self._update_MEDIA_PLAYER2_PLAYER_IFACE('Metadata', 'a{sv}', self._update_metadata(song))

    def _update_metadata(self, song):
        """
        metadata changed - sets the info for the current song.

        This method is not typically overriden. It should be called
        by implementations of this class when the player has changed
        songs.

        named arguments:
            artists - a list of strings representing the artists"
            album - a string for the name of the album
            title - a string for the title of the song

        """
        # Map pithos ratings to something MPRIS understands
        if song.rating == 'love':
            userRating = 5
        else:
            userRating = 0

        # Try to use the generic audio MIME type icon from the user's current theme
        # for the cover image if we don't get one from Pandora
        # Workaround for:
        # https://github.com/eonpatapon/gnome-shell-extensions-mediaplayer/issues/248

        if song.artUrl is not None:
            artUrl = song.artUrl
        else:
            icon_sizes = Gtk.IconTheme.get_icon_sizes(Gtk.IconTheme.get_default(), 'audio-x-generic')
            if -1 in icon_sizes: # -1 is a scalable icon(svg)
                best_icon = -1
            else:
                icon_sizes = sorted(icon_sizes, key=int, reverse=True)
                best_icon = icon_sizes[0] 
            icon_info = Gtk.IconTheme.get_default().lookup_icon('audio-x-generic', best_icon, 0)
            artUrl = "file://%s" %icon_info.get_filename()

        # Ensure is a valid dbus path by converting to hex
        track_id = codecs.encode(bytes(song.trackToken, 'ascii'), 'hex').decode('ascii')
        self._metadata = {
            "mpris:trackid": GLib.Variant('o', self.TRACK_OBJ_PATH + track_id),
            "xesam:title": GLib.Variant('s', song.title or "Title Unknown"),
            "xesam:artist": GLib.Variant('as', [song.artist] or ["Artist Unknown"]),
            "xesam:album": GLib.Variant('s', song.album or "Album Unknown"),
            "xesam:userRating": GLib.Variant('i', userRating),
            "mpris:artUrl": GLib.Variant('s', artUrl),
            "xesam:url": GLib.Variant('s', song.audioUrl),
            "mpris:length": GLib.Variant('x', self._duration),
            "pithos:rating": GLib.Variant('s', song.rating or ""),
        }

        return self._metadata

    @property
    def _duration(self):
        # use the duration provided by Pandora
        # if Gstreamer hasn't figured out the duration yet
        duration = self.window.query_duration()
        if duration is not None:
            return duration // 1000
        else:
            return self.window.current_song.trackLength * 1000000

    @dbus_property(MEDIA_PLAYER2_IFACE, signature='b')
    def CanQuit(self):
        return True

    @dbus_property(MEDIA_PLAYER2_IFACE, signature='b')
    def CanRaise(self):
        return True

    @dbus_property(MEDIA_PLAYER2_IFACE, signature='b')
    def HasTrackList(self):
        return False

    @dbus_property(MEDIA_PLAYER2_IFACE, signature='s')
    def Identity(self):
        return 'Pithos'

    @dbus_property(MEDIA_PLAYER2_IFACE, signature='s')
    def DesktopEntry(self):
        return 'io.github.Pithos'

    @dbus_property(MEDIA_PLAYER2_IFACE, signature='as')
    def SupportedUriScheme(self):
        return ['',]

    @dbus_property(MEDIA_PLAYER2_IFACE, signature='as')
    def SupportedMimeTypes(self):
        return ['',]

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='s')
    def PlaybackStatus(self):
        """Current status "Playing", "Paused", or "Stopped"."""
        if not self.window.current_song:
            return "Stopped"
        if self.window.playing:
            return "Playing"
        else:
            return "Paused"

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='s')
    def LoopStatus(self):
        return 'None'

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='b')
    def Shuffle(self):
        return False

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='d')
    def Rate(self):
        return 1.0

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='a{sv}')
    def Metadata(self):
        """The info for the current song."""
        return self._metadata

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='d')
    def Volume(self):
        volume = self.window.player.get_property("volume")
        scaled_volume = math.pow(volume, 1.0/3.0)
        return scaled_volume

    @Volume.setter
    def Volume(self, new_volume):
        scaled_vol = math.pow(new_volume, 3.0/1.0)
        self.window.player.set_property('volume', scaled_vol)

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='x')
    def Position(self):
        if self.window.query_position() is not None:
            return self.window.query_position() // 1000
        else:
            return 0

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='d')
    def MinimumRate(self):
        return 1.0

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='d')
    def MaximumRate(self):
        return 1.0

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='b')
    def CanGoNext(self):
        return True

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='b')
    def CanGoPrevious(self):
        return False

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='b')
    def CanPlay(self):
        return True

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='b')
    def CanPause(self):
        return True

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='b')
    def CanSeek(self):
        # This a lie because some sound applets depend upon
        # this to show song position/duration info
        return True

    @dbus_property(MEDIA_PLAYER2_PLAYER_IFACE, signature='b')
    def CanControl(self):
        return True

    @dbus_property(MEDIA_PLAYER2_PLAYLISTS_IFACE, signature='(b(oss))')
    def ActivePlaylist(self):
        return self._current_playlist

    @dbus_property(MEDIA_PLAYER2_PLAYLISTS_IFACE, signature='u')
    def PlaylistCount(self):
        return len(self._playlists)

    @dbus_property(MEDIA_PLAYER2_PLAYLISTS_IFACE, signature='as')
    def Orderings(self):
        return ['CreationDate', 'Alphabetical']

    @dbus_method(MEDIA_PLAYER2_IFACE)
    def Raise(self):
        """Bring the media player to the front when selected by the sound menu"""

        self.window.bring_to_top()

    @dbus_method(MEDIA_PLAYER2_IFACE)
    def Quit(self):
        """Exit the player"""
        self.window.quit()

    @dbus_method(MEDIA_PLAYER2_PLAYER_IFACE)
    def Previous(self):
        """Play previous song, not implemented"""
        pass

    @dbus_method(MEDIA_PLAYER2_PLAYER_IFACE)
    def Next(self):
        """Play next song"""
        if not self.window.waiting_for_playlist:
            self.window.next_song()

    @dbus_method(MEDIA_PLAYER2_PLAYER_IFACE)
    def PlayPause(self):
        if self.window.current_song:
            self.window.playpause()

    @dbus_method(MEDIA_PLAYER2_PLAYER_IFACE)
    def Play(self):
        if self.window.current_song:
            self.window.play()

    @dbus_method(MEDIA_PLAYER2_PLAYER_IFACE)
    def Pause(self):
        if self.window.current_song:
            self.window.pause()

    @dbus_method(MEDIA_PLAYER2_PLAYER_IFACE)
    def Stop(self):
        """Stop is only used internally, mapping to pause instead"""
        self.window.pause()

    @dbus_method(MEDIA_PLAYER2_PLAYER_IFACE, in_signature='ox')
    def SetPosition(self, trackid, position):
        """
        We can't actually seek, we lie so gnome-shell-extensions-mediaplayer[1] will show the
        position slider. We send a Seeked signal with the current position to make sure applets
        update their postion.

        Under normal circumstances SetPosition would tell the player where to seek to and any
        seeking caused by either the MPRIS client or the player would cause a Seeked signal to
        be fired with current track position after the seek.

        (The MPRIS client tells the player that it wants to seek to a position >>>
         the player seeks to the disired position >>>
         the player tells the MPRIS client were it actually seeked too.)

        We're skipping the middleman(Pithos) because we can't seek. Some players do not send
        a Seeked signal and some clients workaround that[2] so this may not be necessary for
        all clients.

        [1] https://github.com/eonpatapon/gnome-shell-extensions-mediaplayer/issues/246
        [2] https://github.com/eonpatapon/gnome-shell-extensions-mediaplayer#known-bugs
        """

        self.Seeked(self.Position)

    @dbus_method(MEDIA_PLAYER2_PLAYLISTS_IFACE, in_signature='uusb', out_signature='a(oss)')
    def GetPlaylists(self, Index, MaxCount, Order, ReverseOrder):
        playlists = self._playlists[:]        
        quick_mix = playlists.pop(0)
        thumbprint_radio = None
        for i, playlist in enumerate(playlists):
            if playlist[1] == 'Thumbprint Radio':
                thumbprint_radio = playlists.pop(i)
                break              
        if Order == 'Alphabetical':
            playlists = sorted(playlists, key=lambda playlist: playlist[1])
        elif Order not in ('CreationDate', 'Alphabetical'):
            logging.warning('Unsupported Sort Order: {}, using CreationDate order.'.format(Order))
        if ReverseOrder:
            playlists.reverse()
        playlists = playlists[Index:MaxCount -2 if thumbprint_radio else MaxCount -1]
        if thumbprint_radio:
            playlists.insert(0, thumbprint_radio)
        playlists.insert(0, quick_mix)
        return playlists

    @dbus_method(MEDIA_PLAYER2_PLAYLISTS_IFACE, in_signature='o')
    def ActivatePlaylist(self, PlaylistId):
        stations = self.window.pandora.stations
        station_id = PlaylistId.strip(self.PLAYLIST_OBJ_PATH)
        for station in stations:
            if station.id == station_id:
                self.window.station_changed(station)
                break

    @dbus_signal(MEDIA_PLAYER2_PLAYER_IFACE, signature='x')
    def Seeked(self, position):
        '''Unsupported but some applets depend on this'''
        pass

    @dbus_signal(MEDIA_PLAYER2_PLAYLISTS_IFACE, signature='(oss)')
    def PlaylistChanged(self, playlist):
        pass

    def _update_MEDIA_PLAYER2_IFACE(self, prop, sig, value):
        self.PropertiesChanged(self.MEDIA_PLAYER2_IFACE, {
                prop: GLib.Variant(sig, value),
            }, [])

    def _update_MEDIA_PLAYER2_PLAYER_IFACE(self, prop, sig, value):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYER_IFACE, {
                prop: GLib.Variant(sig, value),
            }, [])

    def _update_MEDIA_PLAYER2_PLAYLISTS_IFACE(self, prop, sig, value):
        self.PropertiesChanged(self.MEDIA_PLAYER2_PLAYLISTS_IFACE, {
                prop: GLib.Variant(sig, value),
            }, [])

    def PropertiesChanged(self, interface, changed, invalidated):
        try:
            self.connection.emit_signal(None, '/org/mpris/MediaPlayer2',
                                        'org.freedesktop.DBus.Properties',
                                        'PropertiesChanged',
                                        GLib.Variant.new_tuple(
                                            GLib.Variant('s', interface),
                                            GLib.Variant('a{sv}', changed),
                                            GLib.Variant('as', invalidated)
                                        ))
        except GLib.Error as e:
            logging.warning(e)
