#%% imports
import pandas as pd
from pathlib import Path
import requests
from census_key import ckey


#%% census data
census_url = "https://api.census.gov/data/2024/acs/acs5"

    #census_codes =
    #"NAME,
    #B01003_001E,  # total population
    #B08201_001E,  # total households
    #B08201_002E,  # households with no car
    #B17001_001E,  # people with poverty status known
    #B17001_002E,  # people below poverty
    #B14007_017E,  # undergrad students
    #B14007_018E,  # grad students
    #B01001_020E, B01001_021E, B01001_022E,  # men 65+
    #B01001_023E, B01001_024E, B01001_025E,
    #B01001_044E, B01001_045E, B01001_046E,  # women 65+
    #B01001_047E, B01001_048E, B01001_049E"

census_codes = "NAME,B01003_001E,B08201_001E,B08201_002E,B17001_001E,B17001_002E,B14007_017E,B14007_018E,B01001_020E,B01001_021E,B01001_022E,B01001_023E,B01001_024E,B01001_025E,B01001_044E,B01001_045E,B01001_046E,B01001_047E,B01001_048E,B01001_049E"
#requests data for every tract in alachua county
census_dict = {"get": census_codes, "for" : "tract:*", "in" : "state:12 county:001", "key" : ckey}
res = requests.get(census_url,params=census_dict)
print(res.status_code)
print(res.json())


# %% census response into dataframe
#responses are nested lists with 1st row being column name
rows = res.json()
#each row after header is one census tract
survey_res = pd.DataFrame(rows[1:],columns=rows[0])

