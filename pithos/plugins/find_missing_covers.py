### BEGIN LICENSE
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

import logging
import json
import urllib.error
import urllib.parse
import urllib.request

from enum import Enum

from pithos.gobject_worker import GObjectWorker
from pithos.plugin import PithosPlugin

class LastfmErrorCode(Enum):
    INVALID_SERVICE = 2 # This service does not exist
    INVALID_METHOD = 3 # No method with that name in this package
    AUTH_FAILED = 4 # You do not have permissions to access the service
    INVALID_FORMAT = 5 # This service doesn't exist in that format
    INVALID_PARMAS = 6 # Your request is missing a required parameter
    INVALID_RESOURCES = 7 # Invalid resource specified
    OPERATION_FAILED = 8 # Something else went wrong
    INVALID_SESSION_KEY = 9 # Please re-authenticate
    INVALID_API_KEY = 10 # You must be granted a valid key by last.fm
    SERVICE_OFFLINE = 11 # This service is temporarily offline. Try again later.
    INVALID_METHOD_SIG = 13 # Invalid method signature supplied.
    TEMPORARY_ERROR = 16 # There was a temporary error processing your request. Please try again
    SUSPENDED_API_KEY = 26 # Access for your account has been suspended, please contact Last.fm
    RATE_LIMIT_EXCEEDED = 29 # Your IP has made too many requests in a short period

class LastfmError(IOError):
    def __init__(self, message, status=None, submsg=None):
        self.status = status
        self.message = message
        self.submsg = submsg

class LastfmNetError(LastfmError): pass
class LastfmTimeout(LastfmError): pass

class LastfmArtScraperPlugin(PithosPlugin):
    preference = 'enable_lastfm_art_scraper'
    description = 'Find missing covers with Last.fm'

    LASTFM_ROOT = 'http://ws.audioscrobbler.com/2.0/?'
    LASTFM_KEY = '&api_key=997f635176130d5d6fe3a7387de601a8'
    ALBUM_M = 'method=album.getinfo'
    ARTIST_M = 'method=artist.getinfo'
    FORMAT = '&format=json'
    BRACKETS = '([{'
    SUFFIXES_TO_STRIP = [' EP', ' - EP', ' ep', ' - ep', ' Ep', ' - Ep',
                         ' LP', ' - LP', ' lp', ' - lp', ' Lp', ' - Lp']


    def on_prepare(self):
        self.worker = GObjectWorker()

    def on_enable(self):
        self.art_handler = self.window.connect('no-art-url', self.get_lastfm_art)    

    def on_disable(self):
        self.window.disconnect(self.art_handler)

    def get_lastfm_art(self, window, data):
        song, get_album_art, art_callback = data
        def last_fm_api_call(api_call, key):
            try:
                with urllib.request.urlopen(api_call, timeout=30) as response:
                    lastfm_response = json.loads(response.read().decode('utf-8'))
                # Last.fm image sizes are not set sizes by pixel
                # they are relative sizes:
                # 'small', 'medium', 'large', 'extralarge', 'mega' and ''.
                # Sizes may not have an image url associated
                # with them. They may be an empty string.
                # We prefer the named sizes from 'mega' to 'large'
                # and then the unnamed '' size, so we slice the list,
                # reverse the order, and pop the '' size to the end.
                # The 'small' and 'medium' sizes are usually unusably small.
                images = lastfm_response.get(key,{}).get('image')
                if images is not None:
                    images = images[2:] 
                    images.reverse()
                    images += [images.pop(0)]            
                    for image in images:
                        art_url = image['#text']
                        if art_url:
                            return art_url

                error = lastfm_response.get('error')
                if error is not None:
                    error = LastfmErrorCode(int(error))
                    message = lastfm_response.get('message', 'No Message')
                    logging.debug('{}: {}'.format(error, message))

            except urllib.error.HTTPError as e:
                logging.error('HTTP error: {}'.format(e))
                raise LastfmNetError(str(e))
            except urllib.error.URLError as e:
                logging.error('Network error: {}'.format(e))
                if e.reason.strerror == 'timed out':
                    raise LastfmTimeout('Network error', submsg='Timeout')
                else:
                    raise LastfmNetError('Network error', submsg=e.reason.strerror)

            return None

        def get_art_url_from_lastfm():
            artist = '&artist={}'.format(self.clean_text_for_lastfm(song.artist))
            album = '&album={}'.format(self.clean_text_for_lastfm(song.album, album=True))
            get_album_info = ''.join((self.LASTFM_ROOT, self.ALBUM_M, self.LASTFM_KEY, artist, album, self.FORMAT))
            get_artist_info = ''.join((self.LASTFM_ROOT, self.ARTIST_M, self.LASTFM_KEY, artist, self.FORMAT))
            call_key_pairs = [(get_album_info, 'album'), (get_artist_info, 'artist')]
            for val in call_key_pairs:
                art_url = last_fm_api_call(val[0], val[1])
                if art_url is not None:
                    logging.info('got {} image from Last.fm for {}'.format(val[1], song.index))
                    return art_url
                     
            return None

        def set_art(art_url):
            if art_url is not None:
                self.worker.send(get_album_art, (art_url, window.tempdir, song, song.index), art_callback)
            else:
                logging.info('No match for {} by {} for {} found with Last.fm.'.format(song.title, song.artist, song.index))
     
        self.worker.send(get_art_url_from_lastfm, (), set_art)

    def clean_text_for_lastfm(self, text, album=False):
        # Format artist names and album titles for use with Last.fm.
        # Remove all text after the actual name/title.
        for bracket in self.BRACKETS:
            bracket = text.find(bracket)
            if bracket != -1:
                text = text[:bracket].strip()
        if album: # Last.fm doesn't like album titles that end with any variation EP or LP.
            for suffix in self.SUFFIXES_TO_STRIP:                    
                if text.endswith(suffix):
                    text = text[:len(text) - len(suffix)].strip()
        return urllib.parse.quote(text)
