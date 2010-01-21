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

import time

import voodoo.log as log
from voodoo.log import logged
from voodoo.override import Override
from voodoo.gen.caller_checker import caller_check
import weblab.experiment.devices.tftp_device.TFtpDevice as TFtpDevice
import weblab.experiment.devices.http_device.HttpDevice as HttpDevice
import weblab.experiment.experiments.ud_pic_experiment.UdPicBoardCommand as UdPicBoardCommand
import weblab.experiment.experiments.ud_pic_experiment.TFtpProgramSender as TFtpProgramSender
import weblab.experiment.Util as ExperimentUtil
import weblab.data.ServerType as ServerType

import weblab.experiment.Experiment as Experiment

import weblab.exceptions.experiment.ExperimentExceptions as ExperimentExceptions

# TODO: this is wrong. It wouldn't work for multiple pic experiments
TFTP_SERVER_HOSTNAME = 'pic_tftp_server_hostname'
TFTP_SERVER_PORT     = 'pic_tftp_server_port'
TFTP_SERVER_FILENAME = 'pic_tftp_server_filename'
HTTP_SERVER_HOSTNAME = 'pic_http_server_hostname'
HTTP_SERVER_PORT     = 'pic_http_server_port'
HTTP_SERVER_APP      = 'pic_http_server_app'

DEFAULT_SLEEP_TIME   = 5

class UdPicExperiment(Experiment.Experiment):
    def __init__(self, coord_address, locator, cfg_manager, *args, **kwargs):
        super(UdPicExperiment,self).__init__(*args, **kwargs)
        self._cfg_manager= cfg_manager

        self._initialize_tftp()
        self._initialize_http()

    def _initialize_tftp(self):
        tftp_server_hostname, tftp_server_port = self._parse_tftp_configuration()
        self._tftp_device = self._create_tftp_device(
                tftp_server_hostname,
                tftp_server_port
            )
        self._tftp_program_sender = TFtpProgramSender.TFtpProgramSender(
                self._tftp_device,
                self._tftp_remote_filename
            )

    def _initialize_http(self):
        http_server_hostname, http_server_port, http_server_app = self._parse_http_configuration()
        self._http_device = self._create_http_device(
                http_server_hostname,
                http_server_port,
                http_server_app
            )

    def _parse_tftp_configuration(self):
        tftp_server_hostname = self._cfg_manager.get_value(TFTP_SERVER_HOSTNAME)
        tftp_server_port     = self._cfg_manager.get_value(TFTP_SERVER_PORT)
        self._tftp_remote_filename =  self._cfg_manager.get_value(TFTP_SERVER_FILENAME)
        return tftp_server_hostname, tftp_server_port

    def _parse_http_configuration(self):
        http_server_hostname = self._cfg_manager.get_value(HTTP_SERVER_HOSTNAME)
        http_server_port     = self._cfg_manager.get_value(HTTP_SERVER_PORT)
        http_server_app      = self._cfg_manager.get_value(HTTP_SERVER_APP)
        return http_server_hostname, http_server_port, http_server_app

    def _create_tftp_device(self, hostname, port):
        # For testing purposes
        return TFtpDevice.TFtpDevice(hostname, port)
        
    def _create_http_device(self, hostname, port, app):
        # For testing purposes
        return HttpDevice.HttpDevice(hostname, port, app)
        
    @Override(Experiment.Experiment)
    @logged("info",except_for=(('file_content',1),))
    @caller_check(ServerType.Laboratory)
    def do_send_file_to_device(self, file_content, file_info):
        try:
            #TODO: encode? utf8?
            if isinstance(file_content, unicode):
                file_content_encoded = file_content.encode('utf8')
            else:
                file_content_encoded = file_content
            file_content_recovered = ExperimentUtil.deserialize(file_content_encoded)
            reset_command = UdPicBoardCommand.UdPicBoardSimpleCommand.create("RESET")
            reset_response = self._http_device.send_message(str(reset_command))
            # TODO: Check reset_response (200)
            time.sleep(DEFAULT_SLEEP_TIME)
            self._tftp_program_sender.send_content(file_content_recovered)
        except Exception, e:
            log.log(
                UdPicExperiment,
                log.LogLevel.Info,
                "Exception joining sending program to device: %s" % e.args[0]
            )
            log.log_exc(
                UdPicExperiment,
                log.LogLevel.Warning,
            )
            raise ExperimentExceptions.SendingFileFailureException(
                    "Error sending file to device: %s" % e.args[0]
                )

    @logged("info")
    @Override(Experiment.Experiment)
    @caller_check(ServerType.Laboratory)
    def do_send_command_to_device(self, command):
        cmds = UdPicBoardCommand.UdPicBoardCommand(command)
        for cmd in cmds.get_commands():
            response = self._http_device.send_message(str(cmd))
            # TODO: check the response code (200)
            #if response.lower() != "ok":
            #   raise UdPicExperimentExceptions.UdPicInvalidResponseException("the ") #TODO: message
            pass

