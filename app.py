from flask import Flask, jsonify, request, render_template, redirect, url_for
import requests
import geopandas as gpd
import folium
import os
import pyproj
from shapely.geometry import shape, mapping
from functools import partial
import json

app = Flask(__name__)


@app.route("/input")
def input():
    return render_template("input.html")

@app.route("/address_map", methods=['GET','POST'])
def address_map():
    try:
        if request.method == 'POST':
            address = request.form.get('address')
            if not address:
                return "Please provide an address", 400
            # Redirect to GET with address as query parameter
            return redirect(url_for('address_map', address=address))
        
        # Handle GET request
        address = request.args.get('address')
        if not address:
            return "Please provide an address", 400
        
        # First, geocode the address using PDOK Locatieserver
        geocode_url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free"
        params = {
            "q": address,
            "rows": 1,
            "fl": "*"
        }
        
        geocode_response = requests.get(geocode_url, params=params)
        geocode_data = geocode_response.json()
        
        # print("Geocoding response:", json.dumps(geocode_data, indent=2))
        
        if not geocode_data.get('response', {}).get('docs', []):
            return "Address not found", 404
            
        location = geocode_data['response']['docs'][0]
        centroid = location['centroide_rd']
        
        # Extract coordinates first as we need them in both cases
        x, y = map(float, centroid.replace('POINT(', '').replace(')', '').split())
        
        # Get the cadastral identifier if available
        cadastral_id = None
        if location.get('gekoppeld_perceel'):
            cadastral_id = location['gekoppeld_perceel'][0]  # Get the first linked parcel
            print(f"Found gekoppeld_perceel: {cadastral_id}")
        else:
            print("No gekoppeld_perceel found in location data")
        
        # Fetch parcels using WFS with bbox
        wfs_url = "https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0"
        buffer = 50
        bbox = f"{x-buffer},{y-buffer},{x+buffer},{y+buffer}"
        
        wfs_params = {
            "request": "GetFeature",
            "service": "WFS",
            "version": "2.0.0",
            "outputFormat": "application/json",
            "typeName": "kadastralekaart:perceel",
            "srsName": "EPSG:28992",
            "bbox": bbox
        }
        
        print("WFS request params:", wfs_params)
        response = requests.get(wfs_url, params=wfs_params)
        
        # # Add debug information
        # print("Response status code:", response.status_code)
        # print("Response content:", response.text[:500])
        
        try:
            data = response.json()
            if data.get('features'):
                print(f"Number of features found: {len(data['features'])}")
                
                # If we have a cadastral ID, filter the features
                if cadastral_id:
                    parts = cadastral_id.split('-')
                    if len(parts) == 3:
                        gemeente_code = parts[0]  # ASD21
                        sectie = parts[1]         # Y
                        perceelnummer = int(parts[2])  # 3930
                        
                        filtered_features = [
                            feature for feature in data['features']
                            if (feature['properties'].get('AKRKadastraleGemeenteCodeWaarde') == gemeente_code and
                                feature['properties'].get('sectie') == sectie and
                                feature['properties'].get('perceelnummer') == perceelnummer)
                        ]
                        
                        if filtered_features:
                            data['features'] = filtered_features
                            print(f"Found matching parcel: {cadastral_id}")
                        else:
                            print(f"No matching parcel found for {cadastral_id}")
                            print("Available features:", [
                                (f['properties'].get('AKRKadastraleGemeenteCodeWaarde'),
                                 f['properties'].get('sectie'),
                                 f['properties'].get('perceelnummer'))
                                for f in data['features']
                            ])
            else:
                print("No features found in the response")
                return "No parcels found for this address", 404

        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {str(e)}")
            print("Full response:", response.text)
            return "Error processing WFS response", 500
        

        # Before transforming coordinates, send geometry data to your API
        biodiversity_data = {}  # This will store your API response
        try:
            # Prepare the geometry data for your API
            geometry_payload = {
                'data': {
                    'geometry': data['features'][0]['geometry']
                }
            }

            # print("Geometry payload sent to API:", json.dumps(geometry_payload, indent=2))
            
            # Make the API call to post the geometry data
            api_response = requests.post(
                'https://api-biodiversity-395367171754.europe-west4.run.app/biodiversity',  
                json=geometry_payload,
                headers={'Content-Type': 'application/json'}
            )
            
            if api_response.status_code == 200:
                biodiversity_data = api_response.json()
                # print(f"Biodiversity data received from API: {biodiversity_data}")
            else:
                print(f"API call failed with status code: {api_response.status_code}")
                print(f"API response content: {api_response.text}")
                biodiversity_data = {"error": "Failed to fetch biodiversity data"}
        
        except Exception as api_error:
            print(f"Error calling biodiversity API: {str(api_error)}")
            biodiversity_data = {"error": str(api_error)}

        # Create map centered on the address
        # Convert RD coordinates to WGS84
        transformer = pyproj.Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
        center_lon, center_lat = transformer.transform(x, y)
        
        show_biodiversity = request.args.get('show_biodiversity', 'false').lower() == 'true'
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
        
        folium.TileLayer(
            tiles='https://api-titiler-server-395367171754.europe-west4.run.app/cog/tiles/WebMercatorQuad/{z}/{x}/{y}?url=https://storage.googleapis.com/gee-ramiqcom-s4g-bucket/hack4good_biodiversity/lc_nl_raster.tif&bidx=1&rescale=0,10&colormap_name=rdylgn&nodata=-9999',
            attr='Biodiversity Layer',
            name='biodiversity_layer',
            overlay=True,
            show=show_biodiversity
        ).add_to(m)

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

        # Return template with necessary variables
        return render_template('map_view.html', 
                            map_html=m._repr_html_(), 
                            biodiversity_data=biodiversity_data,
                            show_biodiversity=show_biodiversity)

    except Exception as e:
        print(f"Error processing data: {str(e)}")
        return f"Error processing data: {str(e)}", 500

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
