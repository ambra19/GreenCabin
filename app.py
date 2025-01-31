from flask import Flask, jsonify, request, render_template
import requests
import geopandas as gpd
import folium
import os
import pyproj
from shapely.geometry import shape, mapping
from functools import partial
import json

app = Flask(__name__)

# PDOK WFS Endpoint
WFS_URL = "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0"

# Function to fetch cadastral parcels from WFS
def get_wfs_data(bbox):
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "kadastralekaart:perceel",
        "bbox": f"{bbox},EPSG:4326",
        "outputFormat": "application/json"
    }

    response = requests.get(WFS_URL, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to fetch data: {response.status_code}"}

@app.route("/input")
def input():
    return render_template("input.html")

@app.route("/address_map")
def address_map():
    try:
        address = request.args.get('address')
        if not address:
            return "Please provide an address parameter", 400
        
        print(f"Searching for address: {address}")

        # First, geocode the address using PDOK Locatieserver
        geocode_url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
        params = {
            "q": address,
            "rows": 1,
            "fl": "*"
        }
        
        geocode_response = requests.get(geocode_url, params=params)
        geocode_data = geocode_response.json()
        
        print("Geocoding response:", json.dumps(geocode_data, indent=2))
        
        if not geocode_data.get('response', {}).get('docs', []):
            return "Address not found", 404
            
        location = geocode_data['response']['docs'][0]
        centroid = location['centroide_rd']
        
        # Extract X and Y coordinates from centroid string (format: 'POINT(X Y)')
        x, y = map(float, centroid.replace('POINT(', '').replace(')', '').split())
        
        print(f"Found coordinates: x={x}, y={y}")
        
        # Create a small buffer around the point (100 meters)
        buffer = 100
        bbox = f"{x-buffer},{y-buffer},{x+buffer},{y+buffer}"
        
        # Fetch parcels using WFS
        wfs_url = "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0"
        wfs_params = {
            "request": "GetFeature",
            "service": "WFS",
            "version": "1.1.0",
            "outputFormat": "application/json",
            "typeName": "kadastralekaart:Perceel",
            "bbox": bbox,
            "srsName": "EPSG:28992"
        }
        
        print("WFS request params:", wfs_params)
        response = requests.get(wfs_url, params=wfs_params)
        data = response.json()
        
        print("Number of features found:", len(data.get('features', [])))
        if data.get('features'):
            print("First feature example:", json.dumps(data['features'][0], indent=2))

        # Create map centered on the address
        # Convert RD coordinates to WGS84
        transformer = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
        center_lon, center_lat = transformer.transform(x, y)
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=18)
        
        # Add marker for the address
        folium.Marker(
            [center_lat, center_lon],
            popup=address,
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)

        # Transform and add parcels
        for feature in data['features']:
            if feature['geometry']:
                geom = shape(feature['geometry'])
                if geom.geom_type == 'Polygon':
                    coords = list(geom.exterior.coords)
                    transformed_coords = [transformer.transform(x, y) for x, y in coords]
                    feature['geometry']['coordinates'] = [transformed_coords]
                elif geom.geom_type == 'MultiPolygon':
                    transformed_polys = []
                    for poly in geom.geoms:
                        coords = list(poly.exterior.coords)
                        transformed_coords = [transformer.transform(x, y) for x, y in coords]
                        transformed_polys.append([transformed_coords])
                    feature['geometry']['coordinates'] = transformed_polys

        # Add the parcels to the map
        folium.GeoJson(
            data,
            style_function=lambda x: {
                'fillColor': 'orange',
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.5
            },
            popup=folium.GeoJsonPopup(
                fields=['identificatieLokaalID'],
                labels=False,
            )
        ).add_to(m)

        return m._repr_html_()

    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return f"Error processing data: {str(e)}", 500

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
