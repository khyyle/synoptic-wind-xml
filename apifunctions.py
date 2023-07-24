import os 
import json
import math
import pyproj
import pandas as pd 
import xml.etree.ElementTree as ET 
import requests 
import xml.dom.minidom as xdm
import geojson
import numpy as np
import matplotlib.path as mplPath

#return latitude longitude and whether the user entered a station id 
def determine_entry(): 
    print()
    print("IMPORTANT INFO:")
    print("", "enter \"latlon\" to enter latitude, longitude coordinates", "\n", "enter \"utm\" to enter in UTM coordinates", "\n", "enter \"stationid\" to enter a station id")
    input_type = str(input("What type of entry would you like to input?:")).lower()
    print("_" * 40)
    print()
    
    if input_type == "latlon":
        print("IMPORTANT INFO")
        print("please enter with a space in between and no extra spaces")
        print("format: <latitude> <longitude>")
        user_input = str(input("enter latitude longitude coordinates:"))
        parts = user_input.split(" ")
        lat = float(parts[0])
        lon = float(parts[1])
        stid = determine_nearest_stid(lat, lon)
        return stid
    elif input_type == "utm": 
        print("IMPORTANT INFO:")
        print("please enter with a space in between and no extra spaces")
        print("format:<zone> <easting> <northing>")
        user_input = str(input("enter UTM coordinates:"))
        parts = user_input.split(" ")
        lat, lon = convert_utm_to_lat_lon(parts)
        stid = determine_nearest_stid(lat,lon)
        return stid 
    elif input_type == "stationid":
        print("IMPORTANT INFO")
        print("enter however as many station ids as you want")
        print("format:<stid1> <stid2> <stid3>...")
        user_input = str(input("enter station id(s):"))
        parts = user_input.split(" ")
        stid = []
        if len(parts) > 1:
            for x in parts: 
                stid.append(x)
        else:
            stid.append(user_input)
        return stid
    else:
        raise ValueError("Please input either \"latlon\", \"utm\", or \"stationid\"")

#------------------------------------------------------------------------------------------

def determine_nearest_stid(lat, lon):
    network = ""
    for i in range(1, 282):
        network += f"{i}, "
    network = network[:-2]

    response = requests.get('https://api.synopticdata.com/v2/stations/latest', params = {
        'token': 'REDACTED', 
        'network': network, 
        'format': "json", 
        'radius': [lat, lon, 25], 
        'vars': 'wind_speed,wind_direction,air_temp,dew_point_temperature'}) #1, 2, 4, 10, 14
    data = response.json()
    if response.status_code == 200:
        for station in data["STATION"]:
            nearest_station = None
            min_distance = float('inf')
            distance = calculate_distance(lat, lon, float(station["LATITUDE"]), float(station["LONGITUDE"]))
            if distance < min_distance:
                min_distance = distance
                nearest_station = station
                nearest_STID = nearest_station["STID"]
    else:
        print("ERROR: ensure you used correct formatting or no station within a 25mi radius was found")
    return nearest_STID

#----------------------------------------------------------------------------

def apirequest(stid, start, end):
    #IMPORTANT:
    #use these outside function then call the function with them as parameters
    '''
    start = input("Enter a starting date and time to pull wind data from (YYYYmmddHHMM):")
    end = input("Enter a end date and time to pull wind data from (YYYYmmddHHMM):")
    '''
    
    network = ""
    for i in range(1, 282):
        network += f"{i}, "

    network = network[:-2]

    params = {
        'stid': stid,
        'token': 'REDACTED',
        'network': network, #1, 2, 4, 10, 14
        'format': "json",
        'vars': 'wind_speed,wind_direction,air_temp,dew_point_temperature',
        'START': start, 
        'END': end 
    }
    
    response = requests.get('https://api.synopticdata.com/v2/stations/timeseries', params=params)
    
    if response.status_code ==200:
        result = response.json()
    else:
        print(response.status_code)
    #print(json.dumps(result, indent=4))
    return result 

#------------------------------------------------------------------------------

def save_to_xml(result, choice):

    if result:
        root = ET.Element('sensor')

        name = result["STATION"][0]['NAME']
        id = result["STATION"][0]['STID']

        root.append(ET.Comment("Station Name: {}".format(result["STATION"][0]['NAME'])))
        root.append(ET.Comment("Station ID: {}".format(result["STATION"][0]['STID'])))
            
        site_latitude = ET.SubElement(root, 'site_latitude') #determine latitude value and add it as subelemenet
        site_latitude.text = result["STATION"][0]["LATITUDE"]

        site_longitude = ET.SubElement(root, 'site_longitude') #determine longitude value and add it as a subelement
        site_longitude.text = result["STATION"][0]["LONGITUDE"]

        site_coord_flag = ET.SubElement(root, 'site_coord_flag')
        site_coord_flag.text = '3' #location of site in program determined by lat/lon

        observations = result["STATION"][0]['OBSERVATIONS'] 
        for i in range(len(observations['date_time'])): #iterate through the timestamp and sensor variable lists so values can be output under their respective timestamp
            time_series = ET.SubElement(root, 'timeSeries')

            timeStamp = ET.SubElement(time_series, 'timeStamp')
            timeStamp.text = observations['date_time'][i]

            boundaryLayerFlag = ET.SubElement(time_series, 'boundaryLayerFlag')
            boundaryLayerFlag.text = '1'

            siteZ0 = ET.SubElement(time_series, 'siteZ0')
            siteZ0.text = '0.1'

            reciprocal = ET.SubElement(time_series, 'reciprocal')
            reciprocal.text = '0.0'

            height = ET.SubElement(time_series, 'height')
            height.text = '10.0'

            speed = ET.SubElement(time_series, 'speed')
            speed.text = str(observations['wind_speed_set_1'][i])

            direction = ET.SubElement(time_series, 'direction')
            direction.text = str(observations['wind_direction_set_1'][i])
                
            tree = ET.ElementTree(root)
    else: 
        raise ValueError("no data found for specified station. ensure you input the correct station id(s)")

    print()
    
    tree = ET.ElementTree(root)
    ET.indent(tree, '  ')
    
    #allow the user to choose if they would like the data to be saved as a file 
    decision = None

    if choice == "Y":
        decision = True
    elif choice == "N": 
        decision = False
    else: 
        raise KeyError("Please enter either \"Y\" or \"N\"")
    
    
    if decision == True:
        filename = f"{id}.xml"
        with open(filename, 'wb') as file:
            tree.write(file, encoding="utf-8", xml_declaration=True)
        print("XML file created", "\n", f"Name: {filename}")
        current_directory = os.getcwd()
        print("Location of file:", current_directory)
    
#-----------------------------------------------------------------------

def convert_utm_to_lat_lon(coordinates, extendeast=None, extendnorth=None):
    parts = coordinates.split()
    zone = parts[0].rstrip('CDEFGHJKLMNPQRSTUVWXYZ')
    easting = parts[1].rstrip('E')
    northing = parts[2].rstrip('N')

    if extendeast or extendnorth:
        easting = int(easting)
        northing = int(northing)

        easting += extendeast
        northing += extendnorth

        easting = str(easting)
        northing = str(northing)
    

    utm_proj = pyproj.Proj(proj='utm', zone=zone, ellps='WGS84')
    lon, lat = utm_proj(float(easting), float(northing), inverse=True)
    return lat, lon

#return list of station ids available within a domain 
def find_stations_in_region(UTMentry=None, extendeast=None, extendnorth=None):
    UTMentry = input("enter in UTM coordinates for southwest corner:")
    extendeast = float(input("enter east extension (in meters):"))
    extendnorth = float(input("enter north extension (in meters):"))

    SWlat, SWlon = convert_utm_to_lat_lon(UTMentry)
    print("finding stations between southwest corner: ", SWlat, SWlon)
    NElat, NElon = convert_utm_to_lat_lon(UTMentry, extendeast, extendnorth)
    print("and northeast corner: ", NElat, NElon)

#set up polygon object which will function as the domain to find stations in 
    poly_path = [
        [SWlon, SWlat],
        [SWlon, NElat],
        [NElon, NElat],
        [NElon, SWlat],
        [SWlon, SWlat]
    ]

    params = {
        "token": "REDACTED",
        "polygon": json.dumps((poly_path))
    }

#iterate through results and append the station id of the stations that are within the given domain
    response = requests.get("https://api.synopticdata.com/v2/stations/latest", params = params)
    if response.status_code == 200:
        stations_data = response.json()
        filtered_stations = []
        for station in stations_data["STATION"]:
            longitude = station["LONGITUDE"]
            longitude = float(longitude)
            latitude = station["LATITUDE"]
            latitude = float(latitude)
            point = (longitude, latitude)
            containstrue = contains(poly_path, point)
            if containstrue == True:
                filtered_stations.append(station['STID'])
        return filtered_stations    
    if not filtered_stations: 
        raise ValueError("no stations found within specified domain")

#determine if the current station is within the specified domain
def contains(polygon_coordinates, point):
    polygon=mplPath.Path(polygon_coordinates)

    return polygon.contains_point(point)
            
#-----------------------------------------------------------------

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(
        dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance
