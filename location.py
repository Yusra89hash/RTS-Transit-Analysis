#%%
import pandas as pd
import geopandas as gpd
from pathlib import Path

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
fl_state_plane = "EPSG:2238"
alachua_tract = alachua_tract.to_crs(fl_state_plane)
stop_points = stop_points.to_crs(fl_state_plane)

# %%
walk_distance= 1320 #in ft
valid_stops = stop_points["departures"] > 0
walkable = stop_points[valid_stops]
walkable = walkable.buffer(walk_distance).union_all()

# %%
tract = alachua_tract.intersection(walkable)
alachua_tract["walking_coverage"] = tract.area / alachua_tract.area
alachua_tract["walking_coverage"].describe()
# %% stops withing a 5 min walk of each tract
#expands each tract by quarter mile so stops nearby count
expanded_tracts = alachua_tract[["GEOID", "geometry"]].copy()
expanded_tracts["geometry"] = expanded_tracts.buffer(walk_distance)

#matches stops to the now expanded tracts
new_stops = gpd.sjoin(stop_points[valid_stops], expanded_tracts, predicate="within")

#adds the departures for each tract
dept_by_tract= new_stops.groupby("GEOID")["departures"].sum()

#includes total buses within 5 min walk of each tract
alachua_tract["buses_nearby"] = alachua_tract["GEOID"].map(dept_by_tract).fillna(0)
alachua_tract["buses_nearby"].describe()
# %% distance from the closest stop to each tract
#combine all stops into 1 shape
valid_walking_distance = stop_points[valid_stops].union_all()
#gets distance to closest stop from each tract
alachua_tract["dist_to_stop"] = alachua_tract.geometry.distance(valid_walking_distance)
alachua_tract["dist_to_stop"].describe()
# %% add census numbers to the tracts
sorted_tracts = alachua_tract.merge(census, on="GEOID")
sorted_tracts.columns

# %% validation
#at most 3 miles away, =15,840 ft
valid_area_distance = 15840
#true if within 3 mi of stop
sorted_tracts["valid_area"] = sorted_tracts["dist_to_stop"] <= valid_area_distance
#true if at least half of residents are students
sorted_tracts["student"] = sorted_tracts["students_%"] >= 0.5
#tracts ranked if they are in the valid area and have at leat 100 residents
sorted_tracts["ranked"] = (sorted_tracts["valid_area"]) & (sorted_tracts["B01003_001E"]>=100)
# %% calcualting population density
# %% population density (people per square mile)
#2,589,988 square meters = 1 square mile
land_sq_miles = sorted_tracts["ALAND"] / 2589988
sorted_tracts["pop_density"] = sorted_tracts["B01003_001E"] / land_sq_miles
sorted_tracts["pop_density"].describe()

# %% need score, 0-100
#only rank tracts inside the rts service area
ranked_tracts = sorted_tracts[sorted_tracts["ranked"]].copy()

#student poverty reflects student income
ranked_poverty = ranked_tracts["poverty_%"].where(ranked_tracts["student"] == False)

#percentile rank each need factor with 100 being the highest need
ranked_tracts["no_car_rank"] = ranked_tracts["no_car_%"].rank() / ranked_tracts["no_car_%"].count() * 100
ranked_tracts["poverty_rank"] = ranked_poverty.rank() / ranked_poverty.count() * 100
ranked_tracts["senior_rank"] = ranked_tracts["senior_citizens_%"].rank() / ranked_tracts["senior_citizens_%"].count() * 100
ranked_tracts["density_rank"] = ranked_tracts["pop_density"].rank() / ranked_tracts["pop_density"].count() * 100

#how much each factor weighs
need_weights = {"no_car_rank": 0.40, "poverty_rank": 0.30, "senior_rank": 0.15, "density_rank": 0.15}

#combines the ranks into one need score\
weighted_total = 0
weight_used = 0
for col, weight in need_weights.items():
    has_value = ranked_tracts[col].notna()
    weighted_total = weighted_total + ranked_tracts[col].fillna(0) * weight
    weight_used = weight_used + has_value * weight
ranked_tracts["need_score"] = weighted_total / weight_used
ranked_tracts["need_score"].describe()