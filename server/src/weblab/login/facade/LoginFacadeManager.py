#!/usr/bin/env python
#-*-*- encoding: utf-8 -*-*-
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

from voodoo.log import logged
import weblab.facade.RemoteFacadeManager as RFM
import weblab.data.ClientAddress as ClientAddress

import weblab.exceptions.login.LoginExceptions as LoginExceptions
import weblab.exceptions.WebLabExceptions as WebLabExceptions
import voodoo.gen.exceptions.exceptions as VoodooExceptions

import weblab.login.facade.LoginFacadeCodes as LFCodes

EXCEPTIONS = (
        #
        # EXCEPTION                                   CODE                                               PROPAGATE TO CLIENT
        #                                                               
        (LoginExceptions.InvalidCredentialsException, LFCodes.CLIENT_INVALID_CREDENTIALS_EXCEPTION_CODE, True),
        (LoginExceptions.LoginException,              LFCodes.LOGIN_SERVER_EXCEPTION_CODE,               False),
        (WebLabExceptions.WebLabException,            LFCodes.WEBLAB_GENERAL_EXCEPTION_CODE,             False),
        (VoodooExceptions.GeneratorException,         LFCodes.VOODOO_GENERAL_EXCEPTION_CODE,             False),
        (Exception,                                   LFCodes.PYTHON_GENERAL_EXCEPTION_CODE,             False)
    )

ADDRESSES_CALLING_LOGIN_BASED_ON_CLIENT_ADDRESS = 'login_facade_trusted_addresses'
DEFAULT_ADDRESSES_CALLING_LOGIN_BASED_ON_CLIENT_ADDRESS = ('127.0.0.1',)

class AbstractLoginRemoteFacadeManager(RFM.AbstractRemoteFacadeManager):
    @logged()
    def login_based_on_client_address(self, username, client_address):
        """ login_based_on_client_address(username, client_address) -> SessionID
            raises LoginException, InvalidCredentialsException
        """
        current_client_address = self._get_client_address()
        addresses_calling_this_method = self._cfg_manager.get_value(ADDRESSES_CALLING_LOGIN_BASED_ON_CLIENT_ADDRESS, DEFAULT_ADDRESSES_CALLING_LOGIN_BASED_ON_CLIENT_ADDRESS)
        if current_client_address in addresses_calling_this_method:
            return self._login_impl( username, ClientAddress.ClientAddress(client_address) )
        else:
            return self._raise_exception(
                    LFCodes.CLIENT_INVALID_CREDENTIALS_EXCEPTION_CODE,
                    "You can't login from IP address: %s" % current_client_address
                )

    @logged(except_for='password')
    def login(self, username, password):
        """ login(username, password) -> SessionID
            raises LoginException, InvalidCredentialsException
        """
        return self._login_impl(username, password)

    @RFM.check_exceptions(EXCEPTIONS)
    def _login_impl(self, username, password):
        return self._server.login(username, password)

class LoginRemoteFacadeManagerZSI(RFM.AbstractZSI, AbstractLoginRemoteFacadeManager):
    pass

class LoginRemoteFacadeManagerJSON(RFM.AbstractJSON, AbstractLoginRemoteFacadeManager):
    pass

class LoginRemoteFacadeManagerXMLRPC(RFM.AbstractXMLRPC, AbstractLoginRemoteFacadeManager):
    pass

