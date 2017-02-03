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

import html
from gi.repository import GObject, Gtk, GLib

from .gi_composites import GtkTemplate


@GtkTemplate(ui='/io/github/Pithos/ui/SearchDialog.ui')
class SearchDialog(Gtk.Dialog):
    __gtype_name__ = "SearchDialog"

    entry = GtkTemplate.Child()
    treeview = GtkTemplate.Child()

    def __init__(self, *args, **kwargs):
        self.worker_run = kwargs["worker"]
        del kwargs["worker"]

        super().__init__(*args, use_header_bar=1, **kwargs)
        self.init_template()

        self.model = Gtk.ListStore(GObject.TYPE_PYOBJECT, str)
        self.treeview.set_model(self.model)
        self.query = ''
        self.result = None
        self.search_timeout_id = 0

    @GtkTemplate.Callback
    def search_clicked(self, widget):
        # Add a little bit more of a delay to the search entry.
        # The default delay of 150 ms is too fast. We want enough
        # Time for the user to finish typing and for Pandora to send
        # results back before we send another search query.
        # This helps stop redundant search queries.
        if self.search_timeout_id:
            GLib.source_remove(self.search_timeout_id)
            self.search_timeout_id = 0
        self.search_timeout_id = GLib.timeout_add(350, self.search)

    @GtkTemplate.Callback
    def get_selected(self):
        sel = self.treeview.get_selection().get_selected()
        if sel[1]:
            return self.treeview.get_model().get_value(sel[1], 0)

    def search(self):
        self.search_timeout_id = 0
        self.query = self.entry.get_text()
        self.model.clear()

        if not self.query:
            return

        def callback(results):
            self.model.clear()

            if not self.query:
                return

            for i in results:
                if i.resultType is 'song':
                    mk = '<b>{}</b> by {}'.format(html.escape(i.title), html.escape(i.artist))
                elif i.resultType is 'artist':
                    mk = '<b>{}</b> (artist)'.format(html.escape(i.name))
                elif i.resultType is 'genre':
                    mk = '<b>{}</b> (genre)'.format(html.escape(i.stationName))
                self.model.append((i, mk))
            self.treeview.show()
        self.worker_run('search', (self.query,), callback, "Searching...")

    def cursor_changed(self, *ignore):
        self.result = self.get_selected()
        self.set_response_sensitive(Gtk.ResponseType.OK, not not self.result)
