#%% imports
import pandas as pd
import zipfile 
from pathlib import Path
from datetime import datetime, timedelta
gtfs = "data/raw/rts_gtfs_fall2026.zip"


#%% what's in the zip
with zipfile.ZipFile(gtfs) as zf:
    gtfs_files = zf.namelist()
    print(gtfs_files)

with zipfile.ZipFile("data/raw/tl_2023_12_tract.zip") as zf:
    tract_files = zf.namelist()
    print(tract_files)



#%% decompress the rts_gtfs.zip into dataframes

# dictionary of dataframes for each gtfs file
gtfs_dict = {}
with zipfile.ZipFile(gtfs) as zf:
    #loop through each file in the zip and remove the .txt, add to the gtfs_dict as dataframe
    for file in gtfs_files:
        with zf.open(file) as f:
            fname = file[:-4]
            df = pd.read_csv(f, dtype=str)
        #cleans up whitespace, only clean data in df  
        for col in df.columns:
            df[col] = df[col].str.strip()
        gtfs_dict[fname] = df


calendar = gtfs_dict["calendar"]
calendar_dates = gtfs_dict["calendar_dates"]
trips = gtfs_dict["trips"]
stop_times = gtfs_dict["stop_times"]
stops = gtfs_dict["stops"]


# %%
gtfs_dict["calendar"]

# %%
gtfs_dict["calendar_dates"]

# %%
gtfs_dict["trips"].head()

# %%

def active_services(date):
    #turns string into a date
    day = datetime.strptime(date,"%Y%m%d")
    #find the day that date falls on, lowercase to match
    day_name = day.strftime("%A").lower()
    
    #finds which schedules run on wed
    valid_day = (calendar[day_name] == "1" ) & (calendar["start_date"] <= date) & (calendar["end_date"] >= date)
    active = set(calendar[valid_day]["service_id"])

    #finds exceptions where a bus runs on date
    exception1 =  (calendar_dates["date"] == date)&(calendar_dates["exception_type"]=="1")
    added = set(calendar_dates[exception1]["service_id"])
    #add into scheduele
    active |= added

    #finds exceptions where bus doesn't run on date
    exception2 = (calendar_dates["date"] == date)&(calendar_dates["exception_type"]=="2")
    removed = set(calendar_dates[exception2]["service_id"])
    #remove from scheduele
    active -= removed

    return active

active_services("20260902")


# %% counts departures per stop

def stop_departures(date):
    #finds active services
    active = active_services(date)

    #keeps only trips on active sched
    valid_trips = trips["service_id"].isin(active)
    active_trips = trips[valid_trips]

    #matches each stop visit to its trip, keeping only active visits
    active_trip_ids = active_trips["trip_id"]
    is_active_visit = stop_times["trip_id"].isin(active_trip_ids)
    stop_visits = stop_times[is_active_visit]

    #removes stops where riders cant get on the bus
    valid_ride = stop_visits["pickup_type"] != "1"
    stop_visits = stop_visits[valid_ride]

    #counts how many buses leave each stop
    departures = stop_visits.groupby("stop_id").size()
    return departures
test_dep = stop_departures("20260902")

# %% find the busiest wednesday 
def busiest_wednesday():
    first_date = datetime.strptime(calendar["start_date"].min(), "%Y%m%d")
    last_date = datetime.strptime(calendar["end_date"].max(), "%Y%m%d")

    #all wednesdays in that time range
    wednesdays = pd.date_range(first_date, last_date, freq ="W-WED")

    #counts trips on each wednesday and keeps the one with highest frequency
    best_wed = "" 
    most_trips = 0
    for day in wednesdays:
        date = day.strftime("%Y%m%d")
        active = active_services(date)
        num_trips = trips["service_id"].isin(active).sum()
        if num_trips > most_trips:
            most_trips = num_trips
            best_wed = date

    return best_wed
service_date = busiest_wednesday()
departures = stop_departures(service_date)

# %% tracks how many buses leave a certain stop
#looks up each stop's departure count 
stop_counts = stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]].copy()
stop_counts["departures"] = stop_counts["stop_id"].map(departures).fillna(0).astype(int)

#makes sure output folder exists
data_path = Path("data")
stop_counts.to_csv(data_path/ "stops.csv", index=False)
# %%
