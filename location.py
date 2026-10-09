#%%
import pandas as pd
import geopandas as gpd
from pathlib import Path
fl_state_plane = "EPSG:2238"
walk_distance_ft = 1320

# %%
#load tract boundries list
tracts = gpd.read_file("data/raw/tl_2023_12_tract.zip")
#tracts that have the alachua county code
alachua = tracts["COUNTYFP"] == "001"
alachua_tract = tracts[alachua]

# %% checks if every census tract has matching tract shape
census = pd.read_csv("data/census.csv", dtype={"GEOID":str})
#tract ids from both files
shape_ids = set(alachua_tract["GEOID"])
census_ids = set(census["GEOID"])
if shape_ids != census_ids:
    print("id missing")

# %% turns stops into map points
stops = pd.read_csv("data/stops.csv", dtype={"stop_id":str})
stop_points = gpd.GeoDataFrame(stops, geometry=(gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"])),crs="EPSG:4326")

# %% converts layers into fl state plane
alachua_tract = alachua_tract.to_crs(fl_state_plane)
stop_points = stop_points.to_crs(fl_state_plane)

# %%
valid_stops = stop_points["departures"] > 0
walkable = stop_points[valid_stops]
walkable = walkable.buffer(walk_distance_ft).union_all()

# %%
tract = alachua_tract.intersection(walkable)
alachua_tract["walking_coverage"] = tract.area / alachua_tract.area
alachua_tract["walking_coverage"].describe()
# %% stops withing a 5 min walk of each tract
#expands each tract by quarter mile so stops nearby count
expanded_tracts = alachua_tract[["GEOID", "geometry"]].copy()
expanded_tracts["geometry"] = expanded_tracts.buffer(walk_distance_ft)

#matches stops to the now expanded tracts
new_stops = gpd.sjoin(stop_points[valid_stops], expanded_tracts, predicate="within")

#adds the departures for each tract
dept_by_tract= new_stops.groupby("GEOID")["departures"].sum()

#includes total buses within 5 min walk of each tract
alachua_tract["buses_nearby"] = alachua_tract["GEOID"].map(dept_by_tract).fillna(0)
alachua_tract["buses_nearby"].describe()
# %% distance from the closest stop to each tract
#combine all stops into 1 shape
walking_distance = stop_points[valid_stops].union_all()
#gets distance to closest stop from each tract
alachua_tract["dist_to_stop"] = alachua_tract.geometry.distance(walking_distance)
alachua_tract["dist_to_stop"].describe()
# %%
