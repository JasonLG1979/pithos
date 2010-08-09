# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010 Kevin Mehall <km@kevinmehall.net>
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

import time
import logging

RATE_BAN = 'ban'
RATE_LOVE = 'love'

counter = 0
def count():
    global counter
    counter +=1
    return counter

import gtk      
window = gtk.Window()
window.set_size_request(200, 100)
window.set_title("Pithos failure tester")
window.set_opacity(0.7)
auth_check = gtk.CheckButton("Authenticated")
time_check = gtk.CheckButton("Be really slow")
vbox = gtk.VBox()
window.add(vbox)
vbox.pack_start(auth_check)
vbox.pack_start(time_check)
window.show_all()

    
def maybe_fail():
    if time_check.get_active():
        logging.info("fakepiano: Going to sleep for 10s")
        time.sleep(10)
    if not auth_check.get_active():
        logging.info("fakepiano: We're deauthenticated...")
        raise PandoraAuthTokenInvalid(123, "Auth token invalid")

def set_authenticated():
    auth_check.set_active(True)


class PandoraError(IOError):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        
class PandoraAuthTokenInvalid(PandoraError): pass

class Pandora(object):
    def __init__(self):
        self.stations = [
            Station("Fake 1"),
            Station("Fake 2"),
            Station("Fake 3"),
            Station("Errors"),
            Station("QuickMix", 1),
        ]
        self.test_failing = False
        
    def set_proxy(self, proxy):
        if proxy:
            logging.info("fakepiano: using proxy %s"%proxy)
        
    def connect(self, user, password):
        set_authenticated()
        logging.info("fakepiano: logging in")
        time.sleep(1)    
        
    def save_quick_mix(self):
        time.sleep(1)
        logging.info("fakepiano: Saving QuickMix")
        
    def search(self, query):
        time.sleep(1)
        logging.info("fakepiano: search")
        return [
            Artist("Test Artist"),
            Artist("Another Result"),
            Song("Test Song", "Song Artist", '', None),
            Song(query, "Songwriter", '', None),
         ]
         
    def add_station_by_music_id(self, musicid):
        time.sleep(1)
        logging.info("fakepiano: add station by music id %s"%musicid)
        s = Station(musicid)
        self.stations.append(s)
        return s
        
        
class Station(object):
    def __init__(self, name, qm=False):
        self.id = str(hash(name))
        self.isCreator = True
        self.isQuickMix = qm
        self.name = name
        self.useQuickMix = (name != "Errors")
        self.info_url = 'http://launchpad.net/pithos'
        
        self.authError = False
        
    def get_playlist(self):
        global failmode
        failmode = (self.name == "Errors")
        maybe_fail()
        r = [Song("Test  &song %i"%count(), "Test Artist", "The really really really really really really long Album %s"%self.name, i%3-1) for i in range(4)]        
        time.sleep(1)
        return r
        
    def rename(self, new_name):
        self.name = new_name
        logging.info("fakepiano: Rename station")
        time.sleep(1)
        
    def delete(self):
        logging.info("fakepiano: Delete station")
        time.sleep(1)

        
class Song(object):
    def __init__(self, title, artist, album, rating):
        self.musicId=id(self)
        self.album = album
        self.artist = artist
        self.audioUrl = 'file:///home/km/Downloads/download'
        self.title = title
        self.rating = rating
        self.tired=False
        self.songDetailURL = 'http://launchpad.net/pithos'
        self.artRadio = 'http://i.imgur.com/H3Z8x.jpg'
        self.message = ''
        self.resultType = 'song'
        self.start_time = None
        
    def rate(self, rating):
        time.sleep(1)
        maybe_fail()
        logging.info("rating song %s %s"%(self.title, rating))
        self.rating = rating
            
    def set_tired(self):
        time.sleep(1)
        maybe_fail()
        logging.info("tired %s"%self.title)
        self.tired = True
        
    @property
    def rating_str(self):
        return self.rating
        
class Artist(object):
    def __init__(self, name):
        self.name = name
        self.musicId = id(self)
        self.resultType = 'artist'
        
        
        
    


