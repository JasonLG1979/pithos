# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: nil; -*-
### BEGIN LICENSE
# Copyright (C) 2010-2012 Kevin Mehall <km@kevinmehall.net>
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

from gi.repository import GLib, Gtk, Pango
import logging


class StationsPopover(Gtk.Popover):
    __gtype_name__ = "StationsPopover"

    def __init__(self):
        Gtk.Popover.__init__(self)

        box2 = Gtk.Box()
        self.search = Gtk.SearchEntry()
        self.sorted = False
        sort = Gtk.ToggleButton.new()
        sort.add(Gtk.Image.new_from_icon_name("view-sort-ascending", Gtk.IconSize.SMALL_TOOLBAR))
        sort.connect("toggled", self.sort_changed)
        box2.pack_start(self.search, True, True, 0)
        box2.add(sort)
        
        self.listbox = Gtk.ListBox()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_size_request(-1, 200)
        sw.add(self.listbox)

        self.search.connect("search-changed", self.search_changed)
        self.listbox.set_filter_func(self.listbox_filter, self.search)

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        box.add(box2)
        box.pack_start(sw, True, True, 3)

        box.show_all()
        self.add (box)

    def sort_changed(self, widget):
        self.sorted = widget.get_active()
        # This crashes on passing None
        self.listbox.set_sort_func(self.listbox_sort) #if widget.get_active() else None)

    def search_changed(self, entry):
        self.listbox.invalidate_filter()

    def listbox_filter(self, row, entry):
        search_text = entry.get_text().lower()
        if not search_text or search_text in row.station.name.lower():
            return True
        else:
            return False

    def listbox_sort(self, row1, row2):
        if not self.sorted:
            return -1 # This is just to work around the python bindings being broken..
        else:
            if row1.station.isQuickMix:
                return -1

            return GLib.ascii_strcasecmp(row1.name, row2.name)

    def insert_row(self, model, path, iter):
        station, name = model.get(iter, 0, 1)
        row = StationListBoxRow(station, name)
        row.show_all()
        self.listbox.add(row)
        #model.foreach(self.insert_row_real)

    def set_model(self, model):
        model.connect('row-inserted', self.insert_row)


class StationListBoxRow(Gtk.ListBoxRow):

    def __init__(self, station, name):
        Gtk.ListBoxRow.__init__(self)
        self.station = station
        self.name = name
        
        box = Gtk.Box()
        label = Gtk.Label()
        label.set_alignment(0, .5)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_max_width_chars(15)
        label.set_text(name)
        box.pack_start(label, True, True, 0)

        if not station.isQuickMix:
            button = Gtk.CheckButton()
            button.set_active(station.useQuickMix)
            button.set_sensitive(False) # TODO
            box.pack_end(button, False, False, 0)     

        self.add(box)

