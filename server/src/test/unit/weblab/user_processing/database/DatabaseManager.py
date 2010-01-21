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

import unittest

import test.unit.configuration as configuration

import voodoo.configuration.ConfigurationManager as ConfigurationManager
import weblab.user_processing.database.DatabaseManager as DatabaseManager
import weblab.database.DatabaseSession as DatabaseSession
import weblab.database.DatabaseConstants as Constants
import weblab.data.User as User

class DatabaseServerTestCase(unittest.TestCase):
    def setUp(self):
        cfg_manager= ConfigurationManager.ConfigurationManager()
        cfg_manager.append_module(configuration)
        self.dm = DatabaseManager.UserProcessingDatabaseManager(cfg_manager)
        
    def test_get_available_experiments(self):
        session_id = DatabaseSession.ValidDatabaseSessionId("student2", Constants.STUDENT)
        experiments = self.dm.get_available_experiments(session_id)
        self.assertTrue(
                len(experiments) >= 3
            )

        experiment_names =list( ( experiment.experiment.name for experiment in experiments ))

        self.assertTrue( 'ud-fpga' in experiment_names )
        self.assertTrue( 'ud-pld' in experiment_names )
        self.assertTrue( 'ud-gpib' in experiment_names )
        
    def test_retrieve_user_information_admin(self):
        session_id = DatabaseSession.ValidDatabaseSessionId("admin1", Constants.ADMINISTRATOR)
        user = self.dm.retrieve_user_information(session_id)

        self.assertNotEquals(user, None)
        self.assertTrue(isinstance(user,User.AdminUser))
        self.assertEquals("admin1",user.login)
        self.assertEquals("Name of administrator 1",user.full_name)
        self.assertEquals("weblab@deusto.es",user.email)

    def test_retrieve_user_information_professor(self):
        session_id = DatabaseSession.ValidDatabaseSessionId("prof1", Constants.PROFESSOR)
        user = self.dm.retrieve_user_information(session_id)

        self.assertNotEquals(user, None)
        self.assertTrue(isinstance(user,User.ProfessorUser))
        self.assertEquals("prof1",user.login)
        self.assertEquals("Name of professor 1",user.full_name)
        self.assertEquals("weblab@deusto.es",user.email)

    def test_retrieve_user_information_student(self):
        session_id = DatabaseSession.ValidDatabaseSessionId("student1", Constants.STUDENT)
        user = self.dm.retrieve_user_information(session_id)

        self.assertNotEquals(user, None)
        self.assertTrue(isinstance(user,User.StudentUser))
        self.assertEquals("student1",user.login)
        self.assertEquals("Name of student 1",user.full_name)
        self.assertEquals("weblab@deusto.es",user.email)

def suite():
    return unittest.makeSuite(DatabaseServerTestCase)

if __name__ == '__main__':
    unittest.main()

