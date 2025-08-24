# GreenCabin

A Flask web application that finds and displays land parcels for any Dutch address using geospatial APIs.

![GreenCabin background](static/assets/greencabin-bg.png)


## What it does

- Takes a Dutch address as input
- Geocodes the address using PDOK API
- Finds the nearest land parcel using Kadaster API
- Displays an interactive satellite map with the parcel highlighted

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the app:
   ```bash
   python app.py
   ```

3. Open http://localhost:5000 in your browser

## Requirements

- Python 3.7+
- Flask, geopandas, folium, pyproj, shapely, requests

## Note

If you encounter issues installing geospatial libraries, try using conda:
```bash
conda install -c conda-forge geopandas pyproj shapely
```
