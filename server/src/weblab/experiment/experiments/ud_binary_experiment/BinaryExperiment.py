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
# Author: Jaime Irurzun <jaime.irurzun@gmail.com>
# 

import os
import weblab.experiment.experiments.ud_xilinx_experiment.UdXilinxExperiment as UdXilinxExperiment
import weblab.experiment.Experiment as Experiment
import weblab.experiment.Util as ExperimentUtil

import weblab.data.ServerType as ServerType

from voodoo.override import Override
from voodoo.gen.caller_checker import caller_check
from voodoo.log import logged

class BinaryExperiment(UdXilinxExperiment.UdXilinxExperiment):
    
    def __init__(self, coord_address, locator, cfg_manager, *args, **kwargs):
        super(BinaryExperiment,self).__init__(coord_address, locator, cfg_manager, *args, **kwargs)

    @Override(Experiment.Experiment)
    @caller_check(ServerType.Laboratory)
    @logged("info")
    def do_start_experiment(self):
        self._clear()

    @Override(Experiment.Experiment)
    @caller_check(ServerType.Laboratory)
    @logged("info",except_for='file_content')
    def do_send_file_to_device(self, file_content, file_info):
        return ""    

    def _autoprogram(self):
        GAME_FILE_PATH = os.path.dirname(__file__) + os.sep + "JUEGO4B.jed"
        try:
            serialized_file_content = ExperimentUtil.serialize(open(GAME_FILE_PATH, "r").read())
            super(BinaryExperiment, self).do_send_file_to_device(serialized_file_content, "game")
        except:
            import traceback
            traceback.print_stack()
            import sys
            sys.stdout.flush()
    
    def do_send_command_to_device(self, command):
        if command == 'AutoProgram':
            self._autoprogram()
        else:
            super(BinaryExperiment, self).do_send_command_to_device(command)            
