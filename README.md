# Gainesville Transit Equity Analysis

**Live dashboard:** https://yusra89hash.github.io/RTS-Transit-Analysis/dashboard/

---

## Tech stack

Python (pandas, GeoPandas, requests) · HTML, CSS, JavaScript · Leaflet · GitHub Pages

---

## Data sources

| Source | What it provides |
|---|---|
| RTS GTFS feeds (2023-24 and Fall 2026) | Bus stops, trips, and service calendars |
| U.S. Census ACS 5-year estimates (2024), via the Census API | Car ownership, poverty, age, students, and population by tract |
| Census TIGER/Line tract boundaries (2023) | Neighborhood shapes for mapping and distance calculations |

---

## How it works

### 1. `outgoing_buses.py`: bus departures per stop
- Loads each GTFS feed and strips hidden whitespace from every value
- Determines which schedules run on a given date, using the regular calendar plus holiday and added-service exceptions
- Picks the **busiest Wednesday** in each feed so both years are compared on a typical full-service weekday
- Counts departures at each stop, excluding drop-off-only stops
- Outputs `data/stops_2023.csv` and `data/stops_2026.csv`

### 2. `census.py`: neighborhood demographics
- Pulls ACS data for every tract in Alachua County through the Census API
- Calculates the share of households with no car, residents in poverty, seniors (65+), and students
- Outputs `data/census.csv`

### 3. `location.py`: scoring and comparison
- Converts map data to **Florida State Plane (EPSG:2238)** so distances and areas are measured in feet
- Draws a **quarter-mile (about 5-minute) walking area** around every stop with service
- For each tract, measures **walking coverage** (share of land within a 5-minute walk of a stop) and **buses nearby** (departures from stops within a quarter mile)
- Scores each tract 0–100 using **percentile ranks**:
  - **Need:** no-car households 40%, poverty 30%, seniors 15%, population density 15%
  - **Service:** buses nearby 60%, walking coverage 40%
- **Gap = need − service.** Tracts with need ≥ 50 and service < 50 are labeled **underserved**.
- In student-majority tracts, poverty is left out of the need score, since student income doesn't reflect the same hardship
- Compares 2023-24 and Fall 2026 service for each tract
- Outputs `data/summary.json` and `data/scored_tracts.geojson` for the dashboard

### Dashboard (`dashboard/`)
Interactive Leaflet map with key findings, biggest gaps, map views for gap, need, service, and service change, and tract-level details.

---

## Running it

1. Install dependencies:
   ```bash
   pip install pandas geopandas requests
   ```
2. Place the raw files in `data/raw/`:
   - `rts_gtfs.zip` (2023-24 feed)
   - `rts_gtfs_fall2026.zip` (Fall 2026 feed)
   - `tl_2023_12_tract.zip` (Florida tract boundaries)
3. Create `census_key.py` with your Census API key (not included in the repo):
   ```python
   ckey = "YOUR_KEY_HERE"
   ```
4. Run the scripts in order:
   ```bash
   python outgoing_buses.py
   python census.py
   python location.py
   ```
5. Open `dashboard/index.html` locally or view the live version above.
