#%% imports
import pandas as pd
import zipfile
from pathlib import Path
from datetime import datetime, timedelta

#%% loads one gtfs zip into a dictionary of dataframes
def load_gtfs(gtfs_path):
    gtfs_dict = {}
    with zipfile.ZipFile(gtfs_path) as zf:
        gtfs_files = zf.namelist()
        #loop through each file in the zip and remove the .txt, add to the gtfs_dict as dataframe
        for file in gtfs_files:
            with zf.open(file) as f:
                fname = file[:-4]
                df = pd.read_csv(f, dtype=str)
            #strip hidden tabs/spaces from every column
            for col in df.columns:
                df[col] = df[col].str.strip()
            gtfs_dict[fname] = df
    return gtfs_dict

# %% schedules running on a date
def active_services(date):
    #turns string into a date
    day = datetime.strptime(date,"%Y%m%d")
    #find the day that date falls on, lowercase to match
    day_name = day.strftime("%A").lower()

    #finds which schedules run on that day and are in season
    valid_day = (calendar[day_name] == "1" ) & (calendar["start_date"] <= date) & (calendar["end_date"] >= date)
    active = set(calendar[valid_day]["service_id"])

    #finds exceptions where a bus runs on date
    exception1 =  (calendar_dates["date"] == date)&(calendar_dates["exception_type"]=="1")
    added = set(calendar_dates[exception1]["service_id"])
    #add into schedule
    active |= added

    #finds exceptions where bus doesn't run on date
    exception2 = (calendar_dates["date"] == date)&(calendar_dates["exception_type"]=="2")
    removed = set(calendar_dates[exception2]["service_id"])
    #remove from schedule
    active -= removed

    return active

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

    #removes stops where riders cant get on the bus, not every feed has this column
    if "pickup_type" in stop_visits.columns:
        valid_ride = stop_visits["pickup_type"] != "1"
        stop_visits = stop_visits[valid_ride]

    #counts how many buses leave each stop
    departures = stop_visits.groupby("stop_id").size()
    return departures

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

# %% counts departures for each schedule and saves one file per schedule
#schedules to compare, name: zip path
feeds = {"2023": "data/raw/rts_gtfs.zip", "2026": "data/raw/rts_gtfs_fall2026.zip"}
data_path = Path("data")

for feed_name, feed_path in feeds.items():
    #tables for this schedule, the functions above use these
    gtfs_dict = load_gtfs(feed_path)
    calendar = gtfs_dict["calendar"]
    calendar_dates = gtfs_dict["calendar_dates"]
    trips = gtfs_dict["trips"]
    stop_times = gtfs_dict["stop_times"]
    stops = gtfs_dict["stops"]

    #busiest wednesday and how many buses leave each stop that day
    service_date = busiest_wednesday()
    departures = stop_departures(service_date)
    print(feed_name, service_date, departures.sum(), "departures at", len(departures), "stops")

    #looks up each stop's departure count
    stop_counts = stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]].copy()
    stop_counts["departures"] = stop_counts["stop_id"].map(departures).fillna(0).astype(int)

    #save, one file per schedule
    stop_counts.to_csv(data_path / ("stops_" + feed_name + ".csv"), index=False)