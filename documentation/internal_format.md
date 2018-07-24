# Kirin internal format

## Overview
Kirin's internal model is derived from GTFS-realtime `ServiceAlert` specifications.
It is composed of several objects : 
- VehicleJourney
- RealTimeUpdate
- TripUpdate
- StopTimeUpdate

## Model details
### VehicleJourney
Property | TYpe | Description
--- | --- | ---
id | UUID | Unique identifier
navitia_trip_id | String, Required | Identifier of Navitia's trip_id
start_timestamp | DateTime, Required | Identification of the start date of the VehicleJourney (UTC)

### RealTimeUpdate
Received raw data from a Real Time Update.

Property | TYpe | Description
--- | --- | ---
id | UUID | 
received_at | DateTime, Required | Date and time of the reception od the data (UTC)
connector | Enum, Required | Source of the data. See below for an available source format.
status | Enum, Required | Processing status of the received data (Possible values are `OK`, `KO` or `pending`)
error | String, Optionnal | Description of the error (if any)
raw_data | String, Optionnal | Content of the received raw data
contributor | String, Optionnal | Identifier of the realtime connector. It must be known by Kraken.
trip_updates | List | List of `TripUpdate` provided by this bloc of data

**Connector field possible values**
The `connector` field is restricted to the following values:
- `ire`: realtime informations of the SNCF long distance trains 
- `gtfs-rt`: realtime informations from the `TripUpdate` format of GTFS-realtime

### TripUpdate
Update information about a VehicleJourney. 

Property | TYpe | Description
--- | --- | ---
id | UUID | => est-ce que ça existe ?
vj_id | UUID | id of the VehicleJourney beeing updated
status | Enum, Required | Modification type for this trip (Possible values are `add`, `delete`, `update` or `none`)
message | String, Optionnal | Text to be displayed in Navitia for the `VehicleJourney`
contributor | String, Optionnal | Identifier of the realtime connector. It must be known by Kraken.
stop_time_updates | List | List of `StopTimeUpdate` provided by this bloc of data

### StopTimeUpdate
Property | TYpe | Description
--- | --- | ---
id | UUID | 
trip_update_id | UUID | id of the `TripUpdate` containing this `StopTimeUpdate`
order | Integer, Required | `StopTime` order in the `VehicleJourney`
stop_id | String, Required | id of the stop_point in navitia
message | String, Optionnal | Text to be displayed in Navitia for the `StopTime`
departure | DateTime, Optionnal | Base scheduled departure datetime of this StopTime
departure_delay | Integer, Optionnal | Delay for the departure at this StopTime (in minutes)
departure_status | Enum, Required | Modification type for the departure of the trip à this StopTime (Possible values are `add`, `delete`, `update` or `none`)
arrival | DateTime, Optionnal | Base scheduled arrival datetime of this StopTime
arrival_delay | Integer, Optionnal | Delay for the arrival at this StopTime (in minutes)
arrival_status | Enum, Required | Modification type for the arrival of the trip à this StopTime (Possible values are `add`, `delete`, `update` or `none`)