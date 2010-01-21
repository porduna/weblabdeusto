#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2005-2009 University of Deusto
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.
#
# This software consists of contributions made by many individuals, 
# listed below:
#
# Author: Pablo Orduña <pablo@ordunya.com>

class Command(object):
    def __init__(self, commandstring):
        super(Command, self).__init__()
        self.commandstring = commandstring

    def get_command_string(self):
        return self.commandstring

    def __repr__(self):
        return u'<Command value="%s" />' % self.commandstring

    def __cmp__(self, other):
        if isinstance(other, Command):
            return cmp(self.commandstring, other.commandstring)
        return -1

class NullCommand(Command):
    def __init__(self):
        super(NullCommand, self).__init__(None)
    def __repr__(self):
        return u'<NullCommand/>'

