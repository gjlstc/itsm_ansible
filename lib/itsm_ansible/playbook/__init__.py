# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Make coding more python3-ish
from __future__ import (absolute_import, division, print_function)

__metaclass__ = type

import os

from ansible.errors import AnsibleParserError
from ansible.playbook.play import Play
from ansible.playbook.playbook_include import PlaybookInclude
from ansible.plugins import get_all_plugin_loaders

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display

    display = Display()

__all__ = ['Playbook']


class Playbook:
    def __init__(self, loader):
        # Entries in the datastructure of a playbook may
        # be either a play or an include statement
        self._entries = []
        self._basedir = os.getcwd()
        self._loader = loader
        self._file_name = None

    @staticmethod
    def load(file_name, pt, variable_manager=None, loader=None):
        pb = Playbook(loader=loader)
        pb._load_playbook_data(file_name=file_name, variable_manager=variable_manager, pt=pt)
        return pb

    def _load_playbook_data(self, file_name, variable_manager, pt):

        if os.path.isdir(file_name) and os.path.isabs(file_name):
            self._basedir = file_name
        elif os.path.isabs(file_name) and (not os.path.isdir(file_name)):
            self._basedir = os.path.dirname(file_name)
        else:
            self._basedir = os.path.normpath(os.path.join(self._basedir, os.path.dirname(file_name)))

        # set the loaders basedir
        self._loader.set_basedir(self._basedir)

        self._file_name = file_name

        # dynamically load any plugins from the playbook directory
        for name, obj in get_all_plugin_loaders():
            if obj.subdir:
                plugin_path = os.path.join(self._basedir, obj.subdir)
                if os.path.isdir(plugin_path):
                    obj.add_directory(plugin_path)

        ds = pt
        if not isinstance(ds, list):
            raise AnsibleParserError("playbooks must be a list of plays", obj=ds)

        # Parse the playbook entries. For plays, we simply parse them
        # using the Play() object, and includes are parsed using the
        # PlaybookInclude() object
        for entry in ds:
            if not isinstance(entry, dict):
                raise AnsibleParserError("playbook entries must be either a valid play or an include statement",
                                         obj=entry)

            if 'include' in entry:
                pb = PlaybookInclude.load(entry, basedir=self._basedir, variable_manager=variable_manager,
                                          loader=self._loader)
                if pb is not None:
                    self._entries.extend(pb._entries)
                else:
                    display.display(
                        "skipping playbook include '%s' due to conditional test failure" % entry.get('include', entry),
                        color='cyan')
            else:
                entry_obj = Play.load(entry, variable_manager=variable_manager, loader=self._loader)
                self._entries.append(entry_obj)

    def get_loader(self):
        return self._loader

    def get_plays(self):
        return self._entries[:]
