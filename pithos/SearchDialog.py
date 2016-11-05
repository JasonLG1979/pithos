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

import html
from gi.repository import GObject, Gtk, Gdk

from .gi_composites import GtkTemplate

@GtkTemplate(ui='/io/github/Pithos/ui/SearchDialog.ui')
class SearchDialog(Gtk.Dialog):
    __gtype_name__ = "SearchDialog"
    __gsignals__ = {
        "add-station": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    entry = GtkTemplate.Child()
    search_results_model = GtkTemplate.Child()
    add_btn = GtkTemplate.Child()

    def __init__(self, worker_run, **kwargs):
        super().__init__(**kwargs)
        self.init_template()
        self.worker_run = worker_run
        self.query = ''

    @GtkTemplate.Callback
    def on_cancel_btn_clicked(self, *ignore):
        self.query = ''
        # Reset everything.
        text_in_search_entry = self.entry.get_text()
        if text_in_search_entry:
            self.entry.set_text('')
        self.add_btn.set_sensitive(False)
        self.search_results_model.clear()
        self.hide()

    @GtkTemplate.Callback
    def on_add_btn_clicked(self, btn, treeview):
        musicId = self.get_musicId(treeview)
        if musicId:
            self.on_cancel_btn_clicked()
            self.emit("add-station", musicId)

    @GtkTemplate.Callback
    def on_entry_search_changed(self, entry, model):
        self.add_btn.set_sensitive(False)
        model.clear()
        self.query = entry.get_text()
        if not self.query: return
        def callback(results):
            model.clear()
            # If there is no current query(the searchbox is empty)
            # we don't want to populate the model with irrelevant results.
            if not self.query: return
            for i in results:
                if i.resultType is 'song':
                    mk = "<b>%s</b> by %s"%(html.escape(i.title), html.escape(i.artist))
                elif i.resultType is 'artist':
                    mk = "<b>%s</b> (artist)"%(html.escape(i.name))
                model.append((i.musicId, mk))
        self.worker_run('search', (self.query,), callback, "Searching...")

    @GtkTemplate.Callback
    def on_treeview_button_press_event(self, treeview, event):
        pthinfo = treeview.get_path_at_pos(int(event.x), int(event.y))
        if pthinfo is not None:
            path, col, cellx, celly = pthinfo
            treeview.grab_focus()
            treeview.set_cursor(path, col, 0)
        musicId = self.get_musicId(treeview)
        self.add_btn.set_sensitive(not not musicId)
        if event.button == 1 and event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS and musicId:
            self.on_cancel_btn_clicked()
            self.emit("add-station", musicId)

    def get_musicId(self, treeview):
        selected = treeview.get_selection().get_selected()[1]
        if selected:
            return treeview.get_model().get_value(selected, 0)

