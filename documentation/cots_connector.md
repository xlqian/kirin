# COTS Connector

## Overview
Realtime information for long distance trains of the SNCF network is received in a COTS stream. This document describes how a COTS realtime stream is modeled in Kirin.

## Input data description
A realtime COTS stream (link to provide) is obtained as a JSON file via a message queue mechanism. Each feed message represents an update on the information about a train (its status, the associated delay, causes, etc.).

The information concerning the displayed messages related to train modifications is referenced in a separate stream provided by an external web service. The latter returns a text message for all available situations associated with an id referenced in the COTS stream.

## Connector description
This document doesn't describe all the fields of the Kirin model. Only COTS relevant fields are described below. For example, the RealTimeUpdate.id field is managed by Kirin and is not detailed in the present specification.

### RealTimeUpdate

Kirin property | COTS object/value | Comment/Mapping rule
--- | --- | ---
connector |  | Fixed value `cots`
raw_data | _Complete received feed_ | 
contributor |  | Fixed value specified in the configuration of Kirin
trip_updates |  | List of trip updates information, see `TripUpdates` below

### TripUpdate
A COTS feed can udpate more than one `VehicleJourney`, see below for the mapping method.

Kirin property | COTS object/value | Comment/Mapping rule
--- | --- | ---
vj_id | | Id of the `VehicleJourney` in Navitia updated by this `TripUpdate`. See below for the mapping method.
status | *nouvelleVersion/statutOperationnel* | Status is set to `add` when value is "AJOUTEE", `delete`when value is this "SUPPRIMEE", and `update` in every other cases.
message | *nouvelleVersion/idMotifInterneReference* | The label of the message is referenced in the separate feed returned by the SNCF web service by the id that matches the value of *nouvelleVersion/idMotifInterneReference*
contibutor |  | Fixed value specified in the configuration of Kirin
stop_time_updates |  | List of arrival/departure time updates at stops for this trip, see `StopTimeUpdates` below

### VehicleJourney
#### Searching for corresponding VehicleJourneys in Navitia
Getting the right trips from Navitia impacted by a COTS stream is not straightforward.
Finding those `VehicleJourney` implies using:
* *nouvelleVersion/numeroCourse* : Train number, may be a secondary number referenced at the stop level
* *nouvelleVersion/indicateurFer* : Indication whether the impacted vehicle is a train (value `FERRE`) or a coach (otherwise)
* *nouvelleVersion/codeCompagnieTransporteur* : The company operating the vehicle
* the date of the trip is included in the `dateHeure` properties below

To narrow down the research, departure/arrival times at stops are also used. The COTS stream references passing stops, however only stations must be taken into account. Stops are listed in *nouvelleVersion/listePointDeParcours*, a `station` should have the `typeArret` property set to `CD`, `CH`, `FD`, `FH` or an empty value.

The time frame used for Navitia's VehicleJourney is defined by :
* *horaireVoyageurDepart/dateHeure* of the first `station` minus 1 hour
* *horaireVoyageurArrivee/dateHeure* of the last `station` plus 1 hour

When base_schedule information is modified with adapted data (when a strike is scheduled or in progress for example), the COTS stream should be applied to this updated trip.

**Use of *nouvelleVersion/indicateurFer***

*nouvelleVersion/indicateurFer* should be used to narrow the research to rail or road trips. All the physical_modes in Navitia are listed in [NTFS specifications](https://github.com/CanalTP/navitia/blob/dev/documentation/ntfs/ntfs_fr.md#physical_modestxt-requis).

When *nouvelleVersion/indicateurFer* is set to `FERRE`, use only corresponding physical_modes : LocalTrain, LongDistanceTrain, Metro, RapidTransit, RailShuttle, Train, Tramway
Otherwise, the previously listed modes should be removed.

**Use of *nouvelleVersion/codeCompagnieTransporteur***

To be defined.

#### Recording the VehicleJourneys 
Each `VehicleJourney` found in Navitia corresponding to the COTS stream is recorded, so that they are all impacted.

Kirin property | Comment/Mapping rule
--- | --- | ---
navitia_trip_id | `trip_id` of the VehicleJourney in Navitia. See above for the mapping rule.
start_timestamp | Start datetime of the `VehicleJourney` in Navitia
