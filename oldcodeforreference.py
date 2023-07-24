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