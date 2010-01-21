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
package es.deusto.weblab.client.exceptions.comm;

import es.deusto.weblab.client.exceptions.WlClientException;

public class WlCommException extends WlClientException {
	private static final long serialVersionUID = -5011226163704478398L;

	public WlCommException() {}

	public WlCommException(String arg0) {
		super(arg0);
	}

	public WlCommException(Throwable arg0) {
		super(arg0);
	}

	public WlCommException(String arg0, Throwable arg1) {
		super(arg0, arg1);
	}

}
