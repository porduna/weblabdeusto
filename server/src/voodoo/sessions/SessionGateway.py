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
# 
import voodoo.sessions.SessionType as SessionType
import voodoo.exceptions.sessions.SessionExceptions as SessionExceptions

def get_gateway_class(session_type):
    if session_type == SessionType.MySQL:
        from voodoo.sessions.SessionMySQLGateway  import SessionMySQLGateway
        return SessionMySQLGateway
    elif session_type == SessionType.Memory:
        from voodoo.sessions.SessionMemoryGateway import SessionMemoryGateway
        return SessionMemoryGateway
    else:
        raise SessionExceptions.SessionTypeNotImplementedException(
                "Session Type %s not implemented" % session_type.name
            )

