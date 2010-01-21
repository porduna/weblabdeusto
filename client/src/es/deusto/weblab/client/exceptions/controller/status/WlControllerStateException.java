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
package es.deusto.weblab.client.exceptions.controller.status;

import es.deusto.weblab.client.exceptions.controller.WlControllerException;

public class WlControllerStateException extends WlControllerException {
	private static final long serialVersionUID = 1L;

	public WlControllerStateException() {
	}

	public WlControllerStateException(String arg0) {
		super(arg0);
	}

	public WlControllerStateException(Throwable arg0) {
		super(arg0);
	}

	public WlControllerStateException(String arg0, Throwable arg1) {
		super(arg0, arg1);
	}

}
