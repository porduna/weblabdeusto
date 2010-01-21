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

import sys
import threading
import SocketServer

# ZSI
try:
    import ZSI.ServiceContainer as ServiceContainer
except ImportError:
    ZSI_AVAILABLE = False
else:
    ZSI_AVAILABLE = True

# JSON/HTTP
import BaseHTTPServer
import simplejson
import datetime
import types

# XML-RPC
import SimpleXMLRPCServer

import voodoo.log as log
import voodoo.counter as counter
import voodoo.ResourceManager as ResourceManager

import weblab.facade.RemoteFacadeManager as RemoteFacadeManager
from weblab.facade.RemoteFacadeContext import get_context, create_context, delete_context
import weblab.exceptions.facade.FacadeExceptions as FacadeExceptions
import voodoo.exceptions.configuration.ConfigurationExceptions as ConfigurationExceptions

RFS_TIMEOUT_NAME                      = 'facade_timeout'
DEFAULT_TIMEOUT                       = 0.5

_resource_manager = ResourceManager.CancelAndJoinResourceManager("RemoteFacadeServer")

##################
# JSON/HTTP code #
##################

def simplify_response(response, limit = 10, counter = 0):
    if counter == limit:
        return None
    if isinstance(response, str) or isinstance(response, unicode) or isinstance(response, int) or isinstance(response, long) or isinstance(response, float) or isinstance(response, bool):
        return response
    if isinstance(response,list) or isinstance(response, tuple):
        new_response = []
        for i in response:
            new_response.append(simplify_response(i, limit, counter + 1,))
        return new_response
    if isinstance(response, dict):
        new_response = {}
        for i in response:
            new_response[i] = simplify_response(response[i], limit, counter + 1)
        return new_response
    if isinstance(response, datetime.datetime) or isinstance(response, datetime.date) or isinstance(response, datetime.time):
        return response.isoformat()
    ret = {}
    for attr in [ a for a in dir(response) if not a.startswith('_') ]:
        if not hasattr(response.__class__, attr):
            attr_value = getattr(response, attr)
            if not isinstance(attr_value, types.FunctionType) and not isinstance(attr_value, types.MethodType):
                ret[attr] = simplify_response(attr_value, limit, counter + 1)
    return ret


class JsonHttpHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    facade_manager = None
    server_route   = None

    def do_GET(self):
        methods = [ method for method in dir(self.facade_manager) if not method.startswith('_') ]
        methods_help = {}
        for method in methods:
            methods_help[method] = getattr(self.facade_manager, method).__doc__ or ''
        _show_help(self, "JSON", methods, methods_help)

    def do_POST(self):
        create_context(self.server, self.headers)
        
        try:
            length = int(self.headers['content-length'])
            post_content = self.rfile.read(length)

            # TODO: can there be only one instance?
            json_decoder = simplejson.JSONDecoder()
            json_encoder = simplejson.JSONEncoder()

            try:
                decoded = json_decoder.decode(post_content)
            except ValueError:
                response = {"is_exception":True,"message":"Couldn't deserialize message"}
                self.finish_error(response)
                return

            method_name = decoded.get('method')
            if method_name is None:
                response = {"is_exception":True,"message":"Missing 'method' attr"}
                self.finish_error(response)
                return

            params = decoded.get('params')
            if params is None:
                response = {"is_exception":True,"message":"Missing 'params' attr"}
                self.finish_error(response)
                return

            if self.facade_manager is None:
                response = {"is_exception":True,"message":"Facade manager not set"}
                self.finish_error(response)
                return

            if not hasattr(self.facade_manager, method_name):
                response = {"is_exception":True,"message":"Method not recognized"}
                self.finish_error(response)
                return

            method = getattr(self.facade_manager,method_name)

            newparams = {}
            try:
                for param in params:
                    newparams[str(param)] = params[param]
            except Exception, e:
                response = {"is_exception":True,"message":"unicode not accepted in param names"}
                self.finish_error(response)
                return

            try:
                return_value = method(**newparams)
            except RemoteFacadeManager.JSONException, jsone:
                response = jsone.args[0]
                self.finish_error(response)
                return
            except Exception, e:
                response = {"is_exception":True,"message":"Unexpected exception: %s" % e}
                self.finish_error(response)
                return

            try:
                parsed_return_value = simplify_response(return_value)
                response = json_encoder.encode({"result":parsed_return_value, "is_exception" : False})
            except Exception, e:
                response = {"is_exception":True,"message":"Error encoding return value"}
                self.finish_error(response)
                return
                
            self.finish_post(response)
        finally:
            delete_context()

    def finish_error(self, error):
        json_encoder = simplejson.JSONEncoder()
        self.finish_post(json_encoder.encode(error))

    def finish_post(self, response):
        self.send_response(200)
        self.send_header("Content-type", "text/xml")
        self.send_header("Content-length", str(len(response)))
        if self.server_route is not None:
            route = get_context().route
            if route is None:
                route = self.server_route
            self.send_header("Set-Cookie", "weblabsessionid=anythinglikeasessid.%s; path=/" % route)
        self.end_headers()
        self.wfile.write(response)
        self.wfile.flush()
        try:
            self.connection.shutdown(1)
        except:
            pass

    def log_message(self, format, *args):
        #args: ('POST /weblab/json/ HTTP/1.1', '200', '-')
        log.log(
            JsonHttpHandler,
            log.LogLevel.Info,
            "Request from %s: %s" % (get_context().get_ip_address(), format % args)
        )

class JsonHttpServer(SocketServer.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    daemon_threads      = True
    request_queue_size  = 50 #TODO: parameter!
    allow_reuse_address = True

    def __init__(self, server_address, handler_class):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, handler_class)

    def get_request(self):
        sock, addr = BaseHTTPServer.HTTPServer.get_request(self)
        sock.settimeout(None)
        return sock, addr

################
# XML-RPC code #
################

class XmlRpcRequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):

    rpc_paths    = ('/','/RPC2','/weblab/xmlrpc','/weblab/xmlrpc/', '/weblab/login/xmlrpc', '/weblab/login/xmlrpc/')
    server_route = None

    def do_GET(self):
        methods = self.server.system_listMethods()
        methods_help = {}
        for method in methods:
            methods_help[method] = self.server.system_methodHelp(method)
        _show_help(self, "XML-RPC", methods, methods_help)

    def do_POST(self, *args, **kwargs):
        create_context(self.server, self.headers)
        try:
            SimpleXMLRPCServer.SimpleXMLRPCRequestHandler.do_POST(self, *args, **kwargs)
        finally:
            delete_context()

    def end_headers(self):
        if self.server_route is not None:
            route = get_context().route
            if route is None:
                route = self.server_route
            self.send_header("Set-Cookie","weblabsessionid=anythinglikeasessid.%s; path=/" % route)
        SimpleXMLRPCServer.SimpleXMLRPCRequestHandler.end_headers(self)

    def log_message(self, format, *args):
        #args: ('POST /weblab/xmlrpc/ HTTP/1.1', '200', '-')
        log.log(
            XmlRpcRequestHandler,
            log.LogLevel.Info,
            "Request from %s: %s" % (get_context().get_ip_address(), format % args)
        )

class XmlRpcServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer.SimpleXMLRPCServer):
    daemon_threads = True
    request_queue_size = 50 #TODO: parameter!
    allow_reuse_address = True
    
    def __init__(self, server_address, manager, the_server_route):
        class NewXmlRpcRequestHandler(XmlRpcRequestHandler):
            server_route = the_server_route

        if sys.version_info[:2] == (2,4):
            SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, server_address, NewXmlRpcRequestHandler)
        else:
            SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self, server_address, NewXmlRpcRequestHandler, allow_none = True)

        self.register_instance(manager)

    def get_request(self):
        sock, addr = SimpleXMLRPCServer.SimpleXMLRPCServer.get_request(self)
        sock.settimeout(None)
        return sock, addr

############
# ZSI code #
############

if ZSI_AVAILABLE:
    class WebLabRequestHandlerClass(ServiceContainer.SOAPRequestHandler):
        server_route = None

        def do_POST(self, *args, **kwargs):
            create_context(self.server, self.headers)
            try:
                ServiceContainer.SOAPRequestHandler.do_POST(self, *args, **kwargs)
            finally:
                delete_context()

        def end_headers(self):
            if self.server_route is not None:
                route = get_context().route
                if route is None:
                    route = self.server_route
                self.send_header("Set-Cookie","weblabsessionid=anythinglikeasessid.%s; path=/" % route)
            ServiceContainer.SOAPRequestHandler.end_headers(self)

        def log_message(self, format, *args):
            #args: ('POST /weblab/soap/ HTTP/1.1', '200', '-')
            log.log(
                WebLabRequestHandlerClass,
                log.LogLevel.Info,
                "Request from %s: %s" % (get_context().get_ip_address(), format % args)
            )

    class _AvoidTimeoutServiceContainer(SocketServer.ThreadingMixIn, ServiceContainer.ServiceContainer):

        daemon_threads = True
        request_queue_size = 50 #TODO: parameter!
        allow_reuse_address = True

        def __init__(self, *args, **kargs):
            ServiceContainer.ServiceContainer.__init__(self, *args, **kargs)

        def get_request(self):
            sock, addr = ServiceContainer.ServiceContainer.get_request(self)
            sock.settimeout(None)
            return sock, addr

###############
# COMMON CODE #
###############

def _show_help(request_inst, protocol, methods, methods_help):
        response = """<html>
        <head>
            <title>WebLab-Deusto %s service</title>
        </head>
        <body>
            Welcome to the WebLab-Deusto service through %s. Available methods:
            <ul>
        """ % (protocol, protocol)

        for method in methods:
            response += """<li><b>%s</b>: %s</li>\n""" % (method, methods_help[method])
        
        response += """</ul>
        </body>
        </html>
        """
        request_inst.send_response(200)
        request_inst.send_header("Content-type", "text/html")
        request_inst.send_header("Content-length", str(len(response)))
        request_inst.end_headers()
        request_inst.wfile.write(response)
        request_inst.wfile.flush()
        try:
            request_inst.connection.shutdown(1)
        except:
            pass

class AbstractProtocolRemoteFacadeServer(threading.Thread):
    protocol_name = 'FILL_ME!' # For instance: zsi

    def __init__(self, server, configuration_manager, remote_facade_server):
        threading.Thread.__init__(self)
        self.setName(counter.next_name("RemoteFacadeServer_" + self.protocol_name))
        self._configuration_manager = configuration_manager
        self._stopped               = False
        self._rfm                   = getattr(remote_facade_server,'_create_%s_remote_facade_manager' % self.protocol_name)(
                            server,
                            configuration_manager
                        )
        self._rfs                   = remote_facade_server

    def run(self):
        try:
            while not self._rfs._get_stopped():
                self._server.handle_request()
            self._server = None
        finally:
            _resource_manager.remove_resource(self)

    def get_timeout(self):
        return self._configuration_manager.get_value(RFS_TIMEOUT_NAME, DEFAULT_TIMEOUT)

    def parse_configuration(self, *args, **kargs):
        try:
            return self._configuration_manager.get_values(*args, **kargs)
        except ConfigurationExceptions.ConfigurationException, ce:
            raise FacadeExceptions.MisconfiguredException("Missing params: " + ce.args[0])

class AbstractRemoteFacadeServerZSI(AbstractProtocolRemoteFacadeServer):
    protocol_name = "zsi"

    def _retrieve_configuration(self):
        values = self.parse_configuration(
                self._rfs.FACADE_ZSI_PORT,
                **{
                    self._rfs.FACADE_ZSI_LISTEN: self._rfs.DEFAULT_FACADE_ZSI_LISTEN,
                    self._rfs.FACADE_ZSI_SERVICE_NAME: self._rfs.DEFAULT_FACADE_ZSI_SERVICE_NAME
                } 
           )
        listen       = getattr(values, self._rfs.FACADE_ZSI_LISTEN)
        port         = getattr(values, self._rfs.FACADE_ZSI_PORT)
        service_name = getattr(values, self._rfs.FACADE_ZSI_SERVICE_NAME)
        return listen, port, service_name

    def _create_service_container(self, listen, port, the_server_route):

        class NewWebLabRequestHandlerClass(WebLabRequestHandlerClass):
            server_route = the_server_route

        return _AvoidTimeoutServiceContainer(
                (listen,port), 
                RequestHandlerClass=NewWebLabRequestHandlerClass
            )

    def initialize(self):
        if not ZSI_AVAILABLE:
            msg = "The optional library 'ZSI' is not available, so the server will not support SOAP clients. However, it's being used so problems will arise." 
            print >> sys.stderr, msg
            log.log( self, log.LogLevel.Error, msg)

        listen, port, service_name = self._retrieve_configuration()
        self._interface = self.WebLabDeusto(impl = self._rfm)
        server_route = self._configuration_manager.get_value( self._rfs.FACADE_SERVER_ROUTE, self._rfs.DEFAULT_SERVER_ROUTE )
        self._server = self._create_service_container(listen,port,server_route)
        self._server.server_name = self._configuration_manager.get_value( self._rfs.FACADE_ZSI_PUBLIC_SERVER_HOST, self._rfs.DEFAULT_FACADE_ZSI_PUBLIC_SERVER_HOST )
        self._server.server_port = self._configuration_manager.get_value( self._rfs.FACADE_ZSI_PUBLIC_SERVER_PORT, self._rfs.DEFAULT_FACADE_ZSI_PUBLIC_SERVER_PORT )
        self._server.setNode(self._interface, url=service_name)

        timeout = self.get_timeout()
        self._server.socket.settimeout(timeout)

class RemoteFacadeServerJSON(AbstractProtocolRemoteFacadeServer):
    protocol_name = "json"

    def _retrieve_configuration(self):
        values = self.parse_configuration(
                self._rfs.FACADE_JSON_PORT,
                **{
                    self._rfs.FACADE_JSON_LISTEN: self._rfs.DEFAULT_FACADE_JSON_LISTEN
                } 
           )
        listen = getattr(values, self._rfs.FACADE_JSON_LISTEN)
        port   = getattr(values, self._rfs.FACADE_JSON_PORT)
        return listen, port

    def initialize(self):
        listen, port = self._retrieve_configuration()
        the_server_route = self._configuration_manager.get_value( self._rfs.FACADE_SERVER_ROUTE, self._rfs.DEFAULT_SERVER_ROUTE )
        timeout = self.get_timeout()
        class NewJsonHttpHandler(JsonHttpHandler):
            facade_manager = self._rfm
            server_route   = the_server_route
        self._server = JsonHttpServer((listen, port), NewJsonHttpHandler)
        self._server.socket.settimeout(timeout)

class RemoteFacadeServerXMLRPC(AbstractProtocolRemoteFacadeServer):
    protocol_name = "xmlrpc"

    def _retrieve_configuration(self):
        values = self.parse_configuration(
                self._rfs.FACADE_XMLRPC_PORT,
                **{
                    self._rfs.FACADE_XMLRPC_LISTEN: self._rfs.DEFAULT_FACADE_XMLRPC_LISTEN
                } 
           )
        listen = getattr(values, self._rfs.FACADE_XMLRPC_LISTEN)
        port   = getattr(values, self._rfs.FACADE_XMLRPC_PORT)
        return listen, port

    def initialize(self):
        timeout = self.get_timeout()
        listen, port = self._retrieve_configuration()
        server_route = self._configuration_manager.get_value( self._rfs.FACADE_SERVER_ROUTE, self._rfs.DEFAULT_SERVER_ROUTE )
        self._server = XmlRpcServer((listen, port), self._rfm, server_route)
        self._server.socket.settimeout(timeout)


class AbstractRemoteFacadeServer(object):
    RemoteFacadeServerJSON   = RemoteFacadeServerJSON
    RemoteFacadeServerXMLRPC = RemoteFacadeServerXMLRPC

    def __init__(self, server, configuration_manager):
        self._configuration_manager = configuration_manager
        self._stopped               = False
        self._stop_lock             = threading.Lock()

        self._servers               = (
                    self.RemoteFacadeServerJSON  (server, configuration_manager, self),
                    self.RemoteFacadeServerXMLRPC(server, configuration_manager, self),
                )
        if ZSI_AVAILABLE:
            self._servers = (self.RemoteFacadeServerZSI(server, configuration_manager, self),) + self._servers

    def start(self):
        for server in self._servers:
            server.initialize()

        # And, if all of them are correctly configured...
        for server in self._servers:
            server.start()
            _resource_manager.add_resource(server)

    def cancel(self):
        # Used by the _resource_manager
        self.stop()

    def _get_stopped(self):
        self._stop_lock.acquire()
        try:
            return self._stopped
        finally:
            self._stop_lock.release()

    def stop(self):
        self._stop_lock.acquire()
        try:
            self._stopped = True
        finally:
            self._stop_lock.release()

        for server in self._servers:
            server.join()

