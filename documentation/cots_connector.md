# COTS Connector

## Overview
Realtime information for long distance trains of the SNCF network is received in a COTS stream. This document describes how a COTS realtime stream is modeled in Kirin.

## Input data description
A realtime COTS stream [link to provide] is obtained as a JSON file via a message queue mechanism. Each feed message represents a `notification` object that contains the information about the train (its status, the associated delay, etc.).

The information concerning the displayed messages related to train modifications is referenced in a separate stream. This stream is provided as another JSON file by an external web service called *paramatreLIV* [link to provide]. Each such message representes a `Motif` object.
<br/>-- Validation of parametreLIV ??

## Connector description
### RealTimeUpdate

Kirin object | COTS object/value | Description
--- | --- | ---
id |  | Unique id of the received stream
received_at | `YYYY-MM-DD` | System date and time at data reception (UTC)
connector | `cots` | Name of the realtime data source
status | ??? | Processing status of the received data (ok, ko, pending)
error | ??? | Description of the error
raw_data | `notification` | Content of the received raw data
contributor | `COTS_CONTRIBUTOR` | Kirin contributor
trip_updates | [`TripUpdates`] | A list of `TripUpdates`

### TripUpdate
Kirin object | COTS object/value | Description
--- | --- | ---
id |  | Unique id of the `TripUpdate`
vj_id | *VehicleJourney/id* | Id of the `VehicleJourney` found in Navitia
status | If *nouvelleVersion/statutOperationnel* = "AJOUTEE", then status = `add` <br/>If *nouvelleVersion/statutOperationnel* = "SUPPRIMEE", then status = `delete` <br/>If *nouvelleVersion/statutOperationnel* = "PERTURBEE", then status = `update` <br/>Otherwise, status = `update` | Modification type of the trip
message | This field value is resolved with respect to the `Motif` object. <br/>It contains the value of *Motif/LabelExt*, if it is specified, where *nouvelleVersion/idMotifInterneReference* = *Motif/Id* | Text to be displayed in Navitia for this `VehicleJourney`
contibutor | `COTS_CONTRIBUTOR` | Kirin contributor
stop_time_updates | [`StopTimeUpdates`] | A list of `StopTimeUpdates`

