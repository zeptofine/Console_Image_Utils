from pathlib import Path

import pandas as pd

filepath = Path("hashes.h5")
outpath = Path("hashes.feather")
pd.read_hdf(filepath, 'table').to_feather(outpath)
# pd.read_feather(outpath).to_hdf("test.h5", "table")