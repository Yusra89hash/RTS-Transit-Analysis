#%%
import pandas as pd
import geopandas as gpd
from pathlib import Path


#%%
tracts = gpd.read_file("data/raw/tl_2023_12_tract.zip")

# %%
