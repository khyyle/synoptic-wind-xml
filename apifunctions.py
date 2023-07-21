import os 
import json
import math
import pyproj
import pandas as pd 
import xml.etree.ElementTree as ET 
import requests 
import xml.dom.minidom as xdm
import re


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
    

    '''
    print("FORMAT INFORMATION:")
    print("**terms should be input with a space between them and no excess spaces/characters at the end**")
    print("(UTM coords:<zone> <easting> <northing) (lat/lon coords:<latitude> <longitude>) (Station ID:<station ID>)")
    print()

    user_input = str(input("Enter UTM coordinates, latitude longitude coordinates, or a station ID:"))
    parts = user_input.split(" ")
    
    if len(parts) == 3:
        lat, lon = convert_utm_to_lat_lon(parts)
        stid = determine_nearest_stid(lat, lon)
        return stid
    elif len(parts) == 2:
        lat = float(parts[0])
        lon = float(parts[1])
        stid = determine_nearest_stid(lat, lon)
        return stid
    elif len(parts) == 1:
        stid = user_input 
        return stid 
    else: 
        print("invalid user entry format")
'''

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


def apirequest(stid, start, end):
    #period = { 
     #   'start': input("Enter a starting date and time to pull wind data from (YYYYmmddHHMM):"),
     #   'end': input("Enter a end date and time to pull wind data from (YYYYmmddHHMM):")
    #}
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
        'START': start, #period['start']
        'END': end   #period['end']
    }
    
    response = requests.get('https://api.synopticdata.com/v2/stations/timeseries', params=params)
    result = response.json()
    #print(json.dumps(result, indent=4))
    return result 

def save_to_xml(result):

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

    
    #xml_string = ET.tostring(root, encoding='utf-8').decode('utf-8')
    #formatted_xml = xdm.parseString(xml_string).toprettyxml(indent="    ")

    #tree = ET.ElementTree(ET.fromstring(formatted_xml))
    
    # Print the XML string
    #print("XML DATA RESULT:")
    #print(formatted_xml)
    print()
    
    tree = ET.ElementTree(root)
    ET.indent(tree, '  ')
    
    #allow the user to choose if they would like the data to be saved as a file 
    choice = input(f"Would you like to save the data for the station: NAME: {name}, ID: {id} as a .xml file? (Y/N):")
    decision = None

    if choice == "Y":
        decision = True
    elif choice == "N": 
        decision = False
    else: 
        raise KeyError("Please enter either \"Y\" or \"N\"")
    
    
    if decision == True:
        filename = input("Enter file name for data (include .xml in name ):")
        with open(filename, 'wb') as file:
            tree.write(file, encoding="utf-8", xml_declaration=True)
        print("XML file created", "\n", f"Name: {filename}")
        current_directory = os.getcwd()
        print("Location of file:", current_directory)

        #filename = input("Enter file name for data (include .xml in name ):")  
        #tree.write(filename, encoding="utf-8", xml_declaration=True)
        #print("XML file created", "\n", f"Name: {filename}")
        #current_directory = os.getcwd()
        #print("Location of file:", current_directory)
    


def convert_utm_to_lat_lon(coordinates):
    parts = coordinates.split()
    zone = parts[0].rstrip('CDEFGHJKLMNPQRSTUVWXYZ')
    easting = parts[1].rstrip('E')
    northing = parts[2].rstrip('N')

    utm_proj = pyproj.Proj(proj='utm', zone=zone, ellps='WGS84')
    lon, lat = utm_proj(float(easting), float(northing), inverse=True)
    return lat, lon


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(
        dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance
'''
def fetch_weather_data(params, use_stid=False):
    global nearest_station2, stations, same, matching_station #wind_speed_data, wind_direction_data, time_list, 

#create separate response to be used within the function using new parameters 
    response2 = requests.get(wind_url, params= {
        'token': 'REDACTED',
        'network': '1, 2, 4, 10, 14',
        'format': 'json',
        'stid': ask_input,
        'vars': 'wind_speed,wind_direction,air_temp,dew_point_temperature',
        'units': 'metric',
        'START': period['start'],
        'END': period['end'],
    })


    if response.status_code == 200:
        data = response2.json()
        stations2 = data#['STATION'] #get a list of stations 
        if use_stid:
            for x in stations2["STATION"]:
                if x['STID'] == station_id: 
                    same = x #find the station that matches with the one specified 
            #time_list = same["OBSERVATIONS"]["date_time"] #wind time, direction, and speed data 
            #wind_speed_data = same["OBSERVATIONS"]["wind_speed_set_1"]
            #wind_direction_data = same["OBSERVATIONS"]["wind_direction_set_1"]
            return same
        else:
            global nearest_station2, min_distance2, nearest_station2_id #find the nearest station 
            min_distance2 = float('inf')
            nearest_station2_id = None
            nearest_station2 = None
            for station2 in stations2["STATION"]: #added ["STATION"]
                station_lat = float(station2["LATITUDE"])
                station_lon = float(station2["LONGITUDE"])
                distance = calculate_distance(lat, lon, station_lat, station_lon)
                if distance < min_distance2:
                    min_distance2 = distance
                    nearest_station2 = station2
                    nearest_station2_id = nearest_station2["STID"]
            
            params2 = {
                'token': 'REDACTED',
                'network': '1, 2, 4, 10, 14',
                'format': 'json',
                'station': nearest_station2_id, 
                'vars': 'wind_speed,wind_direction,air_temp,dew_point_temperature',
                'units': 'metric',
                'START': period['start'],
                'END': period['end'],
            }
            response3 = requests.get(wind_url, params=params2) #one last response using new params after having found the matching station's id
            data3 = response3.json()
            global matching_station
            matching_station = None
            for station in data3["STATION"]:
                if station['NAME'] == nearest_station2['NAME']: #find the correct station out of the list of stations
                    matching_station = station
                if matching_station:
                    pass
                    #time_list = matching_station["OBSERVATIONS"]["date_time"]
                    #wind_speed_data = matching_station["OBSERVATIONS"]["wind_speed_set_1"]
                    #wind_direction_data = matching_station["OBSERVATIONS"]["wind_direction_set_1"] 

            return matching_station#wind_speed_data, wind_direction_data, time_list
def api(lat, lon, station_id=None, use_UTM=False, use_stid=None):
    global base_url

    # Define parameters to pull data from the API
    token = 'REDACTED'
    network = '1, 2, 4, 10, 14'
    format = 'json'
    radius = [lat, lon, 25]
    

    if use_stid:
        # Retrieve data for the specified station ID
        params = {
            'token': token,
            'network': network,
            'format': format,
            'station': station_id,
            'vars': 'wind_speed,wind_direction,air_temp,dew_point_temperature',
            'units': 'metric'
        }
    else:
        # Find the nearest station to the specified coordinates
        params = {
            'token': token,
            'network': network,
            'format': format,
            'radius': radius,
            'vars': 'wind_speed,wind_direction,air_temp,dew_point_temperature',
            'station': station_id,
        }

    global response, data, stations, station, station_lat, station_lon, nearest_station
    response = requests.get(base_url, params=params)

    

    if response.status_code == 200:
        data = response.json()
        try:
            summary = data['SUMMARY']
            response_code = summary['RESPONSE_CODE']
            if response_code == 2:
                response_message = summary['RESPONSE_MESSAGE']
                print("Error occurred:", response_message)
            elif response_code == 1:
                if use_stid:
                    # Retrieve data for the specified station ID
                    stations = data['STATION']
                    if stations:
                        station = stations[0]  # Assuming only one station is returned
                        #print("   ")
                        #print("Station information: ")
                        # Print station information
                        #print("Wind speed:", station["OBSERVATIONS"]["wind_speed_value_1"]["value"], "m/s")
                        #print("Wind direction:", station["OBSERVATIONS"]["wind_direction_value_1"]["value"])
                        #print("Air temperature:", station["OBSERVATIONS"]["air_temp_value_1"]["value"], "Celcius")
                        #print("Dew point:", station["OBSERVATIONS"]["dew_point_temperature_value_1d"]["value"], "Celcius")
                    else:
                        print("No weather stations found for the specified station ID.")
                else:
                    # Find the nearest station as before
                    stations = data['STATION']
                    if stations:
                        min_distance = float('inf')
                        for station in stations:
                            station_lat = float(station["LATITUDE"])
                            station_lon = float(station["LONGITUDE"])
                            distance = calculate_distance(lat, lon, station_lat, station_lon)
                            if distance < min_distance:
                                min_distance = distance
                                nearest_station = station
                        
                        print("   ")
                        print("Nearest weather station:")
                        print("Name:", nearest_station["NAME"])
                        print("Station ID:", nearest_station["STID"])
                        print("Latitude:", nearest_station["LATITUDE"])
                        print("Longitude:", nearest_station["LONGITUDE"])
                        print("Distance to station (miles):", min_distance)
                        print("   ")
                        print("Wind direction:", nearest_station["OBSERVATIONS"]["wind_direction_value_1"]["value"])
                        print("Air temperature:", nearest_station["OBSERVATIONS"]["air_temp_value_1"]["value"], "Celcius")
                        print("Dew point:", nearest_station["OBSERVATIONS"]["dew_point_temperature_value_1d"]["value"], "Celcius")
                        print("Wind speed:", nearest_station["OBSERVATIONS"]["wind_speed_value_1"]["value"], "m/s")
                        
                    else:
                        print("No weather stations within a 25-mile radius found near the specified coordinates.")
            else:
                print("Invalid or unexpected API response format (1).")
        except KeyError:
            print("Invalid or unexpected API response format (2).")
    else:
        print('Error occurred:', response.status_code)

    if response.status_code == 200:
        data = response.json()
        if use_stid: #if station id is input use fetch function differently wind_speeds, wind_directions, time_list
            global xml_output
            xml_output = fetch_weather_data(params, use_stid=True)
            print()

        else: #wind_speeds, wind_directions, time_list (replaced all of this with xml)
            xml_output  = fetch_weather_data(params, use_stid=False)
            print()
            # Print the wind speed and direction values
        

        #original code used to print out wind values
        
        x = 0
        while x < len(time_list):
            print("Time (YYYY-MM-DD(T)HH:MM:SS(Z):", time_list[x])
            print("Wind speed:", wind_speeds[x], "m/s")
            print("Wind direction:", wind_directions[x])
            print()
            x += 1
        

        root = ET.Element('sensor')

    #define elements of the xml file as specified    
    site_coord_flag = ET.SubElement(root, 'site_coord_flag')
    site_coord_flag.text = '3' #location of site in program determined by lat/lon

    site_latitude = ET.SubElement(root, 'site_latitude') #determine latitude value and add it as subelemenet
    if nearest_station: 
        global matching_station
        site_latitude.text = nearest_station["LATITUDE"]
    else: 
        site_latitude.text = same["LATITUDE"]

    site_longitude = ET.SubElement(root, 'site_longitude') #determine longitude value and add it as a subelement
    if nearest_station: 
        site_longitude.text = nearest_station["LONGITUDE"]
    else: 
        site_longitude.text = same["LONGITUDE"]
    

    #site_UTM_x = ET.SubElement(root, 'site_UTM_x') (values given to locate are always in lat/lon so figured this is irrelevant)
    #site_UTM_x.text = '2.0'

    #site_UTM_y = ET.SubElement(root, 'site_UTM_y')
    #site_UTM_y.text = '2.0'

    #site_UTM_zone = ET.SubElement(root, 'site_UTM_zone')
    #site_UTM_zone.text = '0'

    observations = xml_output['OBSERVATIONS'] 
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

    # Create an ElementTree object with the root element
    tree = ET.ElementTree(root)

    # Convert the ElementTree object to a string
    xml_string = ET.tostring(root, encoding='utf-8').decode('utf-8')

    # Print the XML string
    print("XML DATA RESULT:")
    print(xml_string)
    print()
    
    #allow the user to choose if they would like the data to be saved as a file 
    choice = input("Would you like to save the above data as a .xml file? (Y/N):")
    global decision
    decision = None

    if choice == "Y":
        decision = True
    elif choice == "N": 
        decision = False
    else: 
        raise KeyError("Please enter either \"Y\" or \"N\"")
    
    
    if decision == True: 
        filename = input("Enter file name for data (include .xml in name ):")  
        with open(filename, 'w') as file:
            file.write(xml_string)
            print("XML file created", "\n", f"Name: {filename}")
            current_directory = os.getcwd()
            print("Location of file:", current_directory)
    elif decision == False: 
        print("----------CODE FINISHED EXECUTING----------")
        '''