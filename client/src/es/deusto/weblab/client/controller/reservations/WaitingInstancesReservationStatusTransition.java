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
package es.deusto.weblab.client.controller.reservations;

import es.deusto.weblab.client.controller.ReservationStatusCallback;
import es.deusto.weblab.client.controller.WebLabController;
import es.deusto.weblab.client.dto.reservations.ReservationStatus;
import es.deusto.weblab.client.dto.reservations.WaitingInstancesReservationStatus;

public class WaitingInstancesReservationStatusTransition extends WaitingInQueueReservationStatusTransition {

	public WaitingInstancesReservationStatusTransition(ReservationStatusCallback reservationStatusCallback) {
		super(reservationStatusCallback);
	}

	@Override
	protected int getMinPollTime() {
		return this.reservationStatusCallback.getConfigurationManager().getIntProperty(
				WebLabController.WAITING_INSTANCES_MIN_POLLING_TIME_PROPERTY, 
				WebLabController.DEFAULT_WAITING_INSTANCES_MIN_POLLING_TIME
			);
	}

	@Override
	protected int getMaxPollTime() {
		return this.reservationStatusCallback.getConfigurationManager().getIntProperty(
				WebLabController.WAITING_INSTANCES_MAX_POLLING_TIME_PROPERTY, 
				WebLabController.DEFAULT_WAITING_INSTANCES_MAX_POLLING_TIME
			);
	}

	@Override
	protected void showReservation(ReservationStatus reservationStatus) {
		this.reservationStatusCallback.getUimanager().onWaitingInstances(
				(WaitingInstancesReservationStatus)reservationStatus
			);
	}

	@Override
	protected int getPosition(ReservationStatus reservationStatus) {
		return ((WaitingInstancesReservationStatus)reservationStatus).getPosition();
	}
}
