#%% imports
import pandas as pd
import zipfile 
from datetime import datetime, timedelta

#%% what's in the zip
with zipfile.ZipFile("data/raw/rts_gtfs.zip") as zf:
    gtfs_files = zf.namelist()
    print(gtfs_files)

with zipfile.ZipFile("data/raw/tl_2023_12_tract.zip") as zf:
    tract_files = zf.namelist()
    print(tract_files)



#%% decompress the rts_gtfs.zip into dataframes

# dictionary of dataframes for each gtfs file
gtfs_dict = {}
with zipfile.ZipFile("data/raw/rts_gtfs.zip") as zf:
    #loop through each file in the zip and remove the .txt, add to the gtfs_dict as dataframe
    for file in gtfs_files:
        with zf.open(file) as f:
            fname = file[:-4]
            gtfs_dict[fname] = pd.read_csv(f, dtype=str)


# %%
