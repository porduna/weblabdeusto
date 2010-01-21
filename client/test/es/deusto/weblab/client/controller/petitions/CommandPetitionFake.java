/*
* Copyright (C) 2005-2009 University of Deusto
* All rights reserved.
*
* This software is licensed as described in the file COPYING, which
* you should have received as part of this distribution.
*
* This software consists of contributions made by many individuals, 
* listed below:
*
* Author: Pablo Orduña <pablo@ordunya.com>
*
*/ 
package es.deusto.weblab.client.controller.petitions;

public class CommandPetitionFake extends CommandPetition {
	
	boolean called = false;
	
	@Override
	protected void request() {
		this.called = true;
	}
	
	public boolean wasCalled(){
		return this.called;
	}
	
	public void callCallback(){
		this.callback.onLoaded();
	}
}
