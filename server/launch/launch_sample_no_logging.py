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

import signal

import sys
sys.path.append('../src')

import libraries
import weblab
import voodoo.gen.loader.Launcher as Launcher

def before_shutdown():
    print "Stopping servers..."

import voodoo.rt_debugger as rt_debugger
rt_debugger.launch_debugger()

launcher = Launcher.Launcher(
            'sample',
            'main_machine',
            'main_instance',
            (
                Launcher.SignalWait(signal.SIGTERM),
                Launcher.SignalWait(signal.SIGINT),
                Launcher.RawInputWait("Press <enter> or send a sigterm or a sigint to finish.\n")
            ),
            "logging.configuration.no.log.txt",
            before_shutdown,
            (
                 Launcher.FileNotifier("_file_notifier", "server started"),
            )
        )
launcher.launch()

