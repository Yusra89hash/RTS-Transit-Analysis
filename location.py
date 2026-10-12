#%%
import pandas as pd
import geopandas as gpd
import json
from pathlib import Path

# %%
#load tract boundaries list
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

# %% converts tracts into fl state plane
fl_state_plane = "EPSG:2238"
alachua_tract = alachua_tract.to_crs(fl_state_plane)

# %% bus service for each tract, from one schedule's stop file
walk_distance = 1320 #in ft

def tract_service(stops_file):
    #turns stops into map points in fl state plane
    stops = pd.read_csv(stops_file, dtype={"stop_id":str})
    stop_points = gpd.GeoDataFrame(stops, geometry=(gpd.points_from_xy(stops["stop_lon"], stops["stop_lat"])),crs="EPSG:4326")
    stop_points = stop_points.to_crs(fl_state_plane)

    #only stops that have buses that day
    valid_stops = stop_points["departures"] > 0
    served_stops = stop_points[valid_stops]

    #area within a 5 min walk of any stop
    walkable = served_stops.buffer(walk_distance).union_all()

    #one row per tract to hold the results
    service = alachua_tract[["GEOID"]].copy()

    #share of each tract within a 5 min walk
    tract = alachua_tract.intersection(walkable)
    service["walking_coverage"] = tract.area / alachua_tract.area

    #expands each tract by quarter mile so stops nearby count
    expanded_tracts = alachua_tract[["GEOID", "geometry"]].copy()
    expanded_tracts["geometry"] = expanded_tracts.buffer(walk_distance)
    #matches stops to the expanded tracts and adds up their departures
    new_stops = gpd.sjoin(served_stops, expanded_tracts, predicate="within")
    dept_by_tract = new_stops.groupby("GEOID")["departures"].sum()
    #total buses within 5 min walk of each tract
    service["buses_nearby"] = service["GEOID"].map(dept_by_tract).fillna(0)

    #distance to closest stop from each tract
    valid_walking_distance = served_stops.union_all()
    service["dist_to_stop"] = alachua_tract.geometry.distance(valid_walking_distance)

    return service

# %% service for both schedules
service_2026 = tract_service("data/stops_2026.csv")
service_2023 = tract_service("data/stops_2023.csv")

#fall 2026 is the main analysis, 2023 is for comparing
alachua_tract = alachua_tract.merge(service_2026, on="GEOID")

# %% add census numbers to the tracts
sorted_tracts = alachua_tract.merge(census, on="GEOID")

# %% validation
#at most 3 miles away, =15,840 ft
valid_area_distance = 15840
#true if within 3 mi of stop
sorted_tracts["valid_area"] = sorted_tracts["dist_to_stop"] <= valid_area_distance
#true if at least half of residents are students
sorted_tracts["student"] = sorted_tracts["students_%"] >= 0.5
#tracts ranked if they are in the valid area and have at least 100 residents
sorted_tracts["ranked"] = (sorted_tracts["valid_area"]) & (sorted_tracts["B01003_001E"]>=100)

# %% population density
#2,589,988 square meters = 1 square mile
land_sq_miles = sorted_tracts["ALAND"] / 2589988
sorted_tracts["pop_density"] = sorted_tracts["B01003_001E"] / land_sq_miles

# %% need score, 0-100
#only rank tracts inside the rts service area
ranked_tracts = sorted_tracts[sorted_tracts["ranked"]].copy()
#student poverty reflects student income, not hardship, so it's left out for student tracts
ranked_poverty = ranked_tracts["poverty_%"].where(ranked_tracts["student"] == False)

#percentile rank each need factor with 100 being the highest need
ranked_tracts["no_car_rank"] = ranked_tracts["no_car_%"].rank() / ranked_tracts["no_car_%"].count() * 100
ranked_tracts["poverty_rank"] = ranked_poverty.rank() / ranked_poverty.count() * 100
ranked_tracts["senior_rank"] = ranked_tracts["senior_citizens_%"].rank() / ranked_tracts["senior_citizens_%"].count() * 100
ranked_tracts["density_rank"] = ranked_tracts["pop_density"].rank() / ranked_tracts["pop_density"].count() * 100

#how much each factor weighs
need_weights = {"no_car_rank": 0.40, "poverty_rank": 0.30, "senior_rank": 0.15, "density_rank": 0.15}
#combines the ranks into one need score
weighted_total = 0
weight_used = 0
for col, weight in need_weights.items():
    has_value = ranked_tracts[col].notna()
    weighted_total = weighted_total + ranked_tracts[col].fillna(0) * weight
    weight_used = weight_used + has_value * weight
ranked_tracts["need_score"] = weighted_total / weight_used

# %% service score, 0-100
#percentile rank each service factor with 100 being the best service
ranked_tracts["coverage_rank"] = ranked_tracts["walking_coverage"].rank() / ranked_tracts["walking_coverage"].count() * 100
ranked_tracts["buses_rank"] = ranked_tracts["buses_nearby"].rank() / ranked_tracts["buses_nearby"].count() * 100

#buses count for 60% of service score
ranked_tracts["service_score"] = ranked_tracts["buses_rank"] * 0.60 + ranked_tracts["coverage_rank"] * 0.40

# %% gaps
#positive gap means more need than service
ranked_tracts["gap"] = ranked_tracts["need_score"] - ranked_tracts["service_score"]

#ranks tracts by gap, 1 = biggest gap
ranked_tracts["gap_rank"] = ranked_tracts["gap"].rank(ascending=False)

#labels each tract by whether its need and service are above or below 50
categories = []
for need, service in zip(ranked_tracts["need_score"], ranked_tracts["service_score"]):
    if need >= 50 and service < 50:
        categories.append("underserved")
    elif need >= 50 and service >= 50:
        categories.append("high need, well served")
    elif need < 50 and service >= 50:
        categories.append("more service than need")
    else:
        categories.append("low need, low service")
ranked_tracts["category"] = categories
ranked_tracts["category"].value_counts()

# %% stats
#underserved tracts only
underserved = ranked_tracts[ranked_tracts["category"] == "underserved"]
print("underserved tracts:", len(underserved))
print("residents:", underserved["B01003_001E"].sum())
print("car free households:", underserved["B08201_002E"].sum())

#which tracts they are
print(underserved[["NAME_y", "need_score", "service_score", "gap"]])

#car free households beyond a 5 min walk, across all of alachua county
car_free = sorted_tracts["B08201_002E"]
car_free_walk = (car_free * (1 - sorted_tracts["walking_coverage"])).sum()
print("car-free share beyond 5 min walk:", car_free_walk / car_free.sum())

# %% how service changed from 2023-24 to fall 2026
#2023 buses nearby for each tract
old_buses = dict(zip(service_2023["GEOID"], service_2023["buses_nearby"]))
ranked_tracts["buses_nearby_2023"] = ranked_tracts["GEOID"].map(old_buses)
ranked_tracts["buses_change"] = ranked_tracts["buses_nearby"] - ranked_tracts["buses_nearby_2023"]
#percent change, blank where there were no buses in 2023
had_buses = ranked_tracts["buses_nearby_2023"] > 0
ranked_tracts["buses_change_%"] = (ranked_tracts["buses_change"] / ranked_tracts["buses_nearby_2023"]).where(had_buses)

#total weekday departures each year
departures_2023 = pd.read_csv("data/stops_2023.csv")["departures"].sum()
departures_2026 = pd.read_csv("data/stops_2026.csv")["departures"].sum()
print("weekday departures 2023-24:", departures_2023, "fall 2026:", departures_2026)
print("system change:", departures_2026 / departures_2023 - 1)

#did the cuts hit high need tracts harder than low need tracts
high_need = ranked_tracts[ranked_tracts["need_score"] >= 50]
low_need = ranked_tracts[ranked_tracts["need_score"] < 50]
high_need_change = high_need["buses_nearby"].sum() / high_need["buses_nearby_2023"].sum() - 1
low_need_change = low_need["buses_nearby"].sum() / low_need["buses_nearby_2023"].sum() - 1
print("high need tracts change:", high_need_change)
print("low need tracts change:", low_need_change)

#tracts that lost the most service
print(ranked_tracts.sort_values("buses_change_%")[["NAME_y", "buses_nearby_2023", "buses_nearby", "buses_change_%", "category"]].head(5))

# %% headline numbers for the dashboard
#int and float turn numpy numbers into plain python numbers so json can save them
summary = {
    "scored_tracts": int(len(ranked_tracts)),
    "underserved_tracts": int(len(underserved)),
    "underserved_residents": int(underserved["B01003_001E"].sum()),
    "car_free_beyond_walk": float(car_free_walk / car_free.sum()),
    "departures_2023": int(departures_2023),
    "departures_2026": int(departures_2026),
    "high_need_change": float(high_need_change),
    "low_need_change": float(low_need_change)
}
#json is a format javascript can read directly
Path("data/summary.json").write_text(json.dumps(summary, indent=2))

# %% scored tracts
#dashboard cols
map_columns = ["GEOID", "NAME_y", "category", "need_score", "service_score", "gap", "gap_rank",
               "B01003_001E", "no_car_%", "poverty_%", "senior_citizens_%", "students_%",
               "walking_coverage", "buses_nearby", "buses_nearby_2023", "buses_change_%", "geometry"]
map_tracts = ranked_tracts[map_columns]

#convert to lat and long for leaflet
map_tracts = map_tracts.to_crs("EPSG:4326")
map_tracts.to_file("data/scored_tracts.geojson", driver="GeoJSON")