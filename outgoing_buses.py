#%% imports
import pandas as pd
import zipfile 
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
gtfs_dict["trips"]["service_id"].unique()
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


# %%

