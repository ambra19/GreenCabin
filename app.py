from flask import Flask, jsonify, request, render_template, redirect, url_for
import requests
import geopandas as gpd
import folium
import os
import pyproj
import geojson
from shapely.ops import transform
from shapely.geometry import shape, mapping, Point
from functools import partial
import json

app = Flask(__name__, 
    static_url_path='/static',
    static_folder='static'
)

@app.route("/")
def input():
    if request.method == 'POST':
        address = request.form.get('address')
        if not address:
            return "Please provide an address", 400
        return redirect(url_for('address_map', address=address))
    return render_template("input.html")

@app.route("/map", methods=['GET','POST'])
def address_map():
    # GET Request to endpoint with address + params
    address = request.args.get('address')
    print(f"Received address: {address}")
    
    if not address:
        return "Please provide an address", 400
        
    geocode_url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
    params = {
        "q": address,     # The address you are searching for
        "rows": 1,        # Limit the response to 1 result (top match)
        "fl": "*"         # "fl" means "field list" — "*" means return all fields
    }

    response = requests.get(geocode_url, params=params)

    # convert response to JSON
    data = response.json()
    docs = data['response']['docs']
    location = docs[0]
    # get centroid that later is used to get polygon
    centroid = location['centroide_rd']
    x, y = map(float, centroid.replace('POINT(', '').replace(')', '').split())

    # use kadaster api to get parcel geometry
    buffer = 50  # reduced buffer to be more precise
    bbox = f"{x-buffer},{y-buffer},{x+buffer},{y+buffer}"

    # call wfs to get parcels for the specific centroid
    wfs_url = "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0"
    wfs_params = {
        "request": "GetFeature",
        "service": "WFS",
        "version": "2.0.0",
        "outputFormat": "application/json",
        "typeName": "kadastralekaart:perceel",
        "srsName": "EPSG:28992",
        "bbox": bbox
    }

    wfs_response = requests.get(wfs_url, params=wfs_params)
    wfs_data = wfs_response.json()
    print("WFS Data:", wfs_data)

    # get the best parcel from the WFS data
    features = wfs_data['features']
    if not features:
        return "No parcels found for this location", 400

    # Create a point from the address coordinates
    address_point = Point(x, y)
    
    # Find the closest parcel
    closest_feature = min(
        features,
        key=lambda f: shape(f['geometry']).distance(address_point)
    )
    
    # Transform geometry to WGS84 for folium
    geom_shape_rd = shape(closest_feature['geometry'])
    transformer = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    geom_shape_wgs = transform(transformer.transform, geom_shape_rd)
    
    # Get center for map
    center = geom_shape_wgs.centroid
    center_coords = [center.y, center.x]
    
    # render the folium map with the selected parcel
    m = folium.Map(
        location=center_coords,
        zoom_start=15,
        width='100%',
        height='100%',
        tiles=None  # Disable default tiles
    )
    
    # Add satellite tile layer
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satellite',
        overlay=False,
        control=True
    ).add_to(m)
    
    # Add the parcel
    folium.GeoJson(
        mapping(geom_shape_wgs),
        style_function=lambda x: {
            'fillColor': 'orange',
            'color': 'black',
            'weight': 2,
            'fillOpacity': 0.5
        }
    ).add_to(m)
    
    map_html = m.get_root().render()
    
    return render_template("map_view.html", map_html=map_html)

# Run Flask app
if __name__ == '__main__':
    app.run(debug=True)
    port = int(os.environ.get('PORT', 5000))
    # app.run(host='0.0.0.0', port=port)
