import os 
import json
import math
import pyproj
import xml.etree.ElementTree as ET 
import requests 
import numpy as np
import matplotlib.path as mplPath
import datetime
from scipy.interpolate import interp1d
import time
import pytz
import pandas

#return latitude longitude and whether the user entered a station id 
def determine_entry(): 
    print()
    print("IMPORTANT INFO:")
    print("", "enter \"latlon\" to enter latitude, longitude coordinates", "\n", "enter \"utm\" to enter in UTM coordinates", "\n", "enter \"stationid\" to enter a station id", "\n", "enter \"domain\" to get data for stations within an area")
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
    elif input_type == "domain":
        stidlist = find_stations_in_region()
        return stidlist
    else:
        raise KeyError("Please input either \"latlon\", \"utm\", \"stationid\", or \"domain\"")

#------------------------------------------------------------------------------------------

def determine_nearest_stid(lat, lon):
    network = ""
    for i in range(1, 282):
        network += f"{i}, "
    network = network[:-2]

    response = requests.get('https://api.synopticdata.com/v2/stations/latest', params = {
        'token': 'REDACTED', 
        #'network': network, 
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

    params = {
        'stid': stid,
        'token': 'REDACTED',
        #'network': 'all_public', #!70, !148, !203, !258, !262, !1008, !2000, !3000, !3001, !3003, !3005, !3006, !3007, !3008, !3009, !3010, !3011, !3012, !3013, !3014, !3016, !3017, !3018, !3019, !3020, !3021, !3022
        'format': "json",
        'vars': 'wind_speed,wind_direction',
        'START': start, 
        'END': end, 
        'qc_checks': "basic",
        'qc':'on'
    }
    
    response = requests.get('https://api.synopticdata.com/v2/stations/timeseries', params=params)
    
    if response.status_code ==200:
        result = response.json()
        print(json.dumps(result, indent=4))
    else:
        print(response.status_code)
    #print(json.dumps(result, indent=4))

    #i know you (fabien) said not to use global variables, but having these will help me out with interpolation and make the code easier to be reused
    #also these variables will not be updated at all so it wont add to confusion :)
      
    try:
        time_set = result["STATION"][0]["OBSERVATIONS"]["date_time"]

        wind_speed_set = result["STATION"][0]["OBSERVATIONS"]["wind_speed_set_1"]
        
        wind_direction_set = result["STATION"][0]["OBSERVATIONS"]["wind_direction_set_1"]

        none_indices = [i for i, (value1, value2) in enumerate(zip(wind_speed_set, wind_direction_set)) if value1 is None or value2 is None]
        
        if len(none_indices) > 20: 
            print("WARNING: this station had a large amount of incomplete data that had to be removed")

        for index in reversed(none_indices):
            del time_set[index]
            del wind_speed_set[index]
            del wind_direction_set[index]
    except KeyError:
        result = None 
        print(f" no data available for station:{stid}", "\n", "make sure the datetime you entered is correct and that the station id you entered is a viable station")


    

    return result, time_set, wind_speed_set, wind_direction_set

#------------------------------------------------------------------------------

def save_to_xml(result, decision, folder_name, direction_interp, speed_interp, new_time_set):

#important: use the following line in implementation of this function
    '''
    folder_path = input("Enter the folder path to save the XML files:")
    '''

    if result:

        root = ET.Element('sensor')

        name = result["STATION"][0]['NAME']
        id = result["STATION"][0]['STID']

        

        root.append(ET.Comment("Station Name: {}".format(name)))
        root.append(ET.Comment("Station ID: {}".format(id)))
            
        site_latitude = ET.SubElement(root, 'site_latitude') #determine latitude value and add it as subelemenet
        site_latitude.text = result["STATION"][0]["LATITUDE"]

        site_longitude = ET.SubElement(root, 'site_longitude') #determine longitude value and add it as a subelement
        site_longitude.text = result["STATION"][0]["LONGITUDE"]

        site_coord_flag = ET.SubElement(root, 'site_coord_flag')
        site_coord_flag.text = '3' #location of site in program determined by lat/lon
        
        time_series = ET.SubElement(root, 'timeSet')

        for i in range(len(new_time_set)): #iterate through the timestamp and sensor variable lists so values can be output under their respective timestamp
            time_series = ET.SubElement(root, 'timeSeries')

            timeStamp = ET.SubElement(time_series, 'timeStamp')
            timeStamp.text = new_time_set[i]

            boundaryLayerFlag = ET.SubElement(time_series, 'boundaryLayerFlag')
            boundaryLayerFlag.text = '1'

            siteZ0 = ET.SubElement(time_series, 'siteZ0')
            siteZ0.text = '0.1'

            reciprocal = ET.SubElement(time_series, 'reciprocal')
            reciprocal.text = '0.0'

            height = ET.SubElement(time_series, 'height')
            height.text = '10.0'
            
            speed = ET.SubElement(time_series, 'speed')
            speed.text = str(speed_interp[i])
            
            direction = ET.SubElement(time_series, 'direction')
            direction.text = str(direction_interp[i])

            tree = ET.ElementTree(root)
    else: 
        raise LookupError("no data found for specified station", "\n", "make sure the datetime you entered is correct and that the station id you entered is a viable station")

    print()
    
    tree = ET.ElementTree(root)
    ET.indent(tree, '  ')
    
    #allow the user to choose if they would like the data to be saved as a file 
    
    if decision == True:
        
        #create a new folder to store the xml files in
        os.makedirs(folder_name, exist_ok=True) 
        
        filename = os.path.join(folder_name, f"{id}.xml")
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

#-------------------------------------------------------------------------------------

def convert_to_epoch_time_utc(times):
    if type(times) == list:
        epoch_set = []
        for time in times:
            time_obj = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%SZ")
            time_obj = time_obj.replace(tzinfo=pytz.UTC)  # Set the time zone to UTC
            epoch_time = time_obj.timestamp()
            epoch_set.append(epoch_time)
        return epoch_set
    else:
        time_obj = datetime.datetime.strptime(times, "%Y-%m-%dT%H:%M:%SZ")
        time_obj = time_obj.replace(tzinfo=pytz.UTC)  # Set the time zone to UTC
        epoch_time = time_obj.timestamp()
        return epoch_time
    
#-------------------------------------------------------------------------------------

def epoch_to_utc_time(epoch_time):
    try:
        # Convert epoch_time to a datetime object in UTC timezone
        #utc_datetime = datetime.datetime.utcfromtimestamp(epoch_time)

        # Format the datetime object as "YYYYmmDDHHMM"
        #formatted_time = utc_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")
        formatted_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch_time))

        return formatted_time
    except ValueError:
        # Handle any possible errors in case of invalid input
        return None
    
#-------------------------------------------------------------------------------------

def interpolate_wind_speed (interval, time_set, wind_speed_set, wind_direction_set, start, end, stid):
    interval = interval * 60
    epoch_set = convert_to_epoch_time_utc(time_set)
    print("NOT RECCOMENDED UNLESS MOVING DATA FROM SMALLER TO LARGER INTERVALS:")
    time_averaging = input(f"would you like to use time averaging instead of interpolation for: {stid} (Y/N):")

    
    
    #determine if the station is weird
    wind_speed_set_interpolated = []
    wind_direction_set_interpolated = []     

    normalstation = None

    start_formatted = start[0] + start[1] + start[2] + start[3] + "-" +start[4]+start[5] + "-" +start[6] +start[7] + "T" + start[8] +start[9] + ":" + start[10] + start[11] + ":00Z"
    end_formatted = end[0] + end[1] + end[2] + end[3] + "-" + end[4] + end[5] + "-" + end[6] + end[7] + "T" + end[8] + end[9] + ":" + end[10] + end[11] + ":00Z"

    start_epoch = convert_to_epoch_time_utc(start_formatted)
    end_epoch = convert_to_epoch_time_utc(end_formatted)
    time_set_epoch0 = convert_to_epoch_time_utc(time_set[0]) 
    time_set_epoch1 = convert_to_epoch_time_utc(time_set[-1])
    if start_epoch == time_set_epoch0 and end_epoch == time_set_epoch1:
        normalstation = True
    else:
        normalstation = False
    #create the appropriate time set 
    if normalstation == True:
        new_time_set = []
        i = 0
        new_time = 0
        while new_time < epoch_set[-1]:
            new_time = epoch_set[0] + (i * interval)
            new_time_set.append(new_time)
            i += 1
    else:
        new_time_set = np.arange(start_epoch, end_epoch + interval, interval)
    
    # set up interpolation function for wind speed
    f_speed = interp1d(epoch_set, wind_speed_set, kind="linear", fill_value="extrapolate")

    # set up interpolation functions for wind direction
    wind_vectors = []
    for index, direction in enumerate(wind_direction_set):
        vector  = wind_direction_to_vector(direction, wind_speed_set[index])
        wind_vectors.append(vector)

    wind_vectors = np.array(wind_vectors)
    
    f_u = interp1d(epoch_set, wind_vectors[:, 0], kind="linear", fill_value="extrapolate")
    f_v = interp1d(epoch_set, wind_vectors[:, 1], kind="linear", fill_value="extrapolate")

    interpolate_u = f_u(new_time_set)
    interpolate_v = f_v(new_time_set)

    for index, time in enumerate(epoch_set):
        try:
            if (epoch_set[index+1] - time) > (interval * 5):
                print("** interpolating large chunk of missing data **")
                print(f"between {epoch_to_utc_time(time)} and {epoch_to_utc_time(epoch_set[index+1])} ")

        except IndexError:
            pass
            
    
    #implement time averaging
    if time_averaging == "Y" and normalstation == True:
        for index, time in enumerate(new_time_set):
            if index == 0:
                wind_speed_set_interpolated.append(wind_speed_set[0])
                wind_direction_set_interpolated.append(wind_direction_set[0])
                continue
            else:
                time_avg_set = []
                index_avg = []
                for index_time, epoch in enumerate(epoch_set):
                    if new_time_set[index - 1] <= epoch <= time: # use index in first for loop
                        time_avg_set.append(epoch)
                        index_avg.append(index_time)

                        print(wind_direction_set[index_time])
                        print(wind_speed_set[index_time])
                print("DONE")
                

                
                values_speed = 0
                count_speed = 0
                values_dir = 0
                count_dir = 0
                for i in index_avg:
                    # add up values within averaging range
                    current_val_speed = wind_speed_set[i]
                    current_val_dir = wind_direction_set[i]
                    
                    print("dir", current_val_dir)
                    print("speed", current_val_speed)

                    # for speed
                    values_speed += current_val_speed
                    count_speed += 1

                    # for direction
                    values_dir += current_val_dir
                    count_dir += 1

                # average it up
                averaged_speed = values_speed / count_speed
                wind_speed_set_interpolated.append(averaged_speed)

                averaged_dir = values_dir / count_dir
                wind_direction_set_interpolated.append(averaged_dir)
                
            
    elif time_averaging == "Y" and normalstation == False:
        # utilize interpolation so we can still average when we need to find an average between an odd interval
        interpolated_set_s = f_speed(new_time_set)

        vector_set = np.column_stack((interpolate_u, interpolate_v))
        interpolated_set_d = [vector_to_wind_direction(u,v) for u,v in vector_set]

        #handle the first data point which we never average
        
       

        
        # create a list of every value so that we can 
        # average where the interval does not end on a known value
            
        # for speed
        all_values = []
        new_index = 0
        old_index = 0
        try:
            while new_index < len(new_time_set) and old_index < len(epoch_set):
                if new_time_set[new_index] <= epoch_set[old_index]:
                    all_values.append(interpolated_set_s[new_index])
                    new_index += 1
                else:
                    all_values.append(wind_speed_set[old_index])
                    old_index += 1

            # If there are remaining values in either list, add them to all_values
            all_values.extend(interpolated_set_s[new_index:])
            all_values.extend(wind_speed_set[old_index:])
        except IndexError:
            pass

        # for direction  
        all_values_dir = []
        new_index2 = 0
        old_index2 = 0      
        try:
            while new_index2 < len(new_time_set) and old_index2 < len(epoch_set):
                if new_time_set[new_index2] <= epoch_set[old_index2]:
                    all_values_dir.append(interpolated_set_d[new_index2])
                    new_index2 += 1
                else:
                    all_values_dir.append(wind_speed_set[old_index2])
                    old_index2 += 1

            # If there are remaining values in either list, add them to all_values
            all_values_dir.extend(interpolated_set_d[new_index2:])
            all_values_dir.extend(wind_speed_set[old_index2:])
        except IndexError:
            pass
        print(new_time_set)
        print()
        print(epoch_set)
        print()
        
        list = new_time_set.tolist() # convert numpy array to list
        print(list)
        print(epoch_set)
        list.extend(epoch_set)
        list = set(list)
        all_times = sorted(list)
        print(all_times)

        dict_speed = {
            "alltimes": all_times,
            "allspeeds": all_values,
            "apispeeds": wind_speed_set,
            "interpspeed":interpolated_set_s,
            "apitimes": epoch_set,
            "interptimes": new_time_set.tolist()
        }

        dict_dir = {
            "alltimes": all_times, 
            "alldir": all_values_dir,
            "apidirs": wind_direction_set,
            "interpdir":interpolated_set_d,
            "apitimes": epoch_set,
            "interptimes": new_time_set.tolist()
        }
                
        # now we have all_times, all vals for direction, all vals for speed

        for index, time in enumerate(new_time_set):
            # handle the first point which could be either an interpolated or known time
            if index == 0:
                if new_time_set[0] < epoch_set[0]:
                    wind_direction_set_interpolated.append(interpolated_set_d[0])
                    wind_speed_set_interpolated.append(interpolated_set_s[0])
                elif new_time_set[0] == epoch_set[0]:
                    wind_direction_set_interpolated.append(wind_direction_set[0])
                    wind_speed_set_interpolated.append(wind_speed_set[0])
                continue
            else:
                times_to_avg = []
                for i, t in enumerate(all_times):
                    if new_time_set[index-1] <= t <= time:
                        times_to_avg.append(t)
                
                print(times_to_avg)
                values_speed = []
                values_dir = []

                
                for index3, time in enumerate(times_to_avg[:-1]):
                    #handle the first value which could be either an interpolated or known value
                    if index3 == 0 and time in epoch_set:
                        index_ = dict_speed["apitimes"].index(time)
                        values_speed .append( dict_speed["apispeeds"][index_]) # speed
                        values_dir.append( dict_dir["apidirs"][index_]) # direction
                        

                    elif index3 == 0 and time in new_time_set:
                        index_ = dict_speed["interptimes"].index(time)
                        values_speed.append( dict_speed["interpspeed"][index_]) # speed
                        values_dir.append( dict_dir["interpdir"][index_]) # direction

                    else: 
                        if time in epoch_set:
                            index = epoch_set.index(time)
                            values_speed.append(wind_speed_set[index])
                            values_dir.append( wind_direction_set[index])

                
            #handle the last value which could be either an interpolated or known time
                if times_to_avg[-1] in dict_speed["apitimes"]:
                    index = dict_speed["apitimes"].index(times_to_avg[-1]) 
                    values_speed.append(dict_speed["apispeeds"][index]) # speed
                    values_dir .append(dict_dir["apidirs"][index]) # direction


                else: 
                    index = dict_speed["interptimes"].index(times_to_avg[-1]) 
                    values_speed.append(dict_speed["interpspeed"][index])
                    values_dir.append(dict_dir["interpdir"][index])
                print("speeds")
                print(values_speed)
                print()
                print("directions")
                print(values_dir)

                speed_avg = sum(values_speed) / len(values_speed)
                wind_avg = sum(values_dir) / len(values_dir)

                wind_speed_set_interpolated.append(speed_avg)
                wind_direction_set_interpolated.append(wind_avg)


                
                




                        
            '''
            for index, time in enumerate(new_time_set):
                index_avg = []
                for index_time, epoch in enumerate(epoch_set):
                    if new_time_set[index - 1] <= epoch <= time: # use index in first for loop
                        index_avg.append(index_time)
                    
                    if not new_time_set[index-1] == epoch:
                        for current_time in all_times:
                            closest_time = float('inf')
                            closest_difference = float('inf')
                            difference = current_time - new_time_set[index - 1]
                            
                            if difference < closest_difference:
                                closest_time = current_time
                                closest_difference = difference

                        for i, epoch in enumerate(epoch_set):
                            if epoch == closest_time:
                                index_avg.append(i)
                        for i2, epoch2 in enumerate(new_time_set):
                            if epoch2 == closest_time:
                                index_avg.append(i2)

                        print(wind_direction_set[index_time])
                        print(wind_speed_set[index_time])
                print("DONE")

            for i in index_avg:
                    # add up values within averaging range
                current_val_speed = wind_speed_set[i]
                current_val_dir = wind_direction_set[i]
                    
                print("dir", current_val_dir)
                print("speed", current_val_speed)

                # for speed
                values_speed += current_val_speed
                count_speed += 1

                # for direction
                values_dir += current_val_dir
                count_dir += 1

                # average it up
            averaged_speed = values_speed / count_speed
            wind_speed_set_interpolated.append(averaged_speed)

            averaged_dir = values_dir / count_dir
            wind_direction_set_interpolated.append(averaged_dir)

            
            '''

    elif time_averaging == "N":
        #populate wind direction set
        wind_direction_set_interpolated_v = np.column_stack((interpolate_u, interpolate_v))
        wind_direction_set_interpolated = [vector_to_wind_direction(u,v) for u,v in wind_direction_set_interpolated_v]

        #populate wind speed set
        wind_speed_set_interpolated = f_speed(new_time_set)
        wind_speed_set_interpolated = wind_speed_set_interpolated.tolist()
        

        #make sure there are no negative values
        for speed in wind_speed_set_interpolated:
            if speed < 0:
                index = wind_speed_set_interpolated.index(speed)
                wind_speed_set_interpolated[index] = 0 

    else:
        raise KeyError("Please enter either \"Y\" or \"N\"")


    print("direction")
    print(wind_direction_set_interpolated)
    print("speed")
    print(wind_speed_set_interpolated)
    '''
   
    
    

    #make sure there are no negative values
    for speed in wind_speed_set_interpolated:
        if speed < 0:
            index = wind_speed_set_interpolated.index(speed)
            wind_speed_set_interpolated[index] = 0 
    
    #interpolate wind directions
    #wind_vectors = [wind_direction_to_vector(direction, speed) for direction,speed in zip(wind_direction_set, wind_speed_set)]
    wind_vectors = []
    for index, direction in enumerate(wind_direction_set):
        vector  = wind_direction_to_vector(direction, wind_speed_set[index])
        wind_vectors.append(vector)

    wind_vectors = np.array(wind_vectors)
    


    for index, time in enumerate(epoch_set):
        try:
            if (epoch_set[index+1] - time) > (interval * 5):
                print("** interpolating large chunk of missing data **")
                print(f"between {epoch_to_utc_time(time)} and {epoch_to_utc_time(epoch_set[index+1])} ")

        except IndexError:
            pass
        
    f_u = interp1d(epoch_set, wind_vectors[:, 0], kind="linear", fill_value="extrapolate")
    f_v = interp1d(epoch_set, wind_vectors[:, 1], kind="linear", fill_value="extrapolate")

    interpolate_u = f_u(new_time_set)
    interpolate_v = f_v(new_time_set)

    wind_direction_set_interpolated_v = np.column_stack((interpolate_u, interpolate_v))
    wind_direction_set_interpolated = [vector_to_wind_direction(u,v) for u,v in wind_direction_set_interpolated_v]
    '''    

    old_iso8601 = [epoch_to_utc_time(time) for time in epoch_set]
    new_iso8601 = [epoch_to_utc_time(time) for time in new_time_set]
    
    return wind_speed_set_interpolated, new_time_set, wind_speed_set, wind_direction_set_interpolated, wind_direction_set, old_iso8601, new_iso8601
     
#-------------------------------------------------------------------------------------    

def wind_direction_to_vector(wind_direction_degrees, wind_speed):
    # Convert degrees to radians
    wind_direction_radians = math.radians(wind_direction_degrees)
   
    # Calculate the x and y components of the wind vector
    u = -(wind_speed) * math.sin(wind_direction_radians)
    v = -(wind_speed) * math.cos(wind_direction_radians) 

    # Return the wind vector as a tuple (x, y)
    return u, v

#-------------------------------------------------------------------------------------

def vector_to_wind_direction(u, v):
    wind_direction_degrees = (270.-180./math.pi*math.atan2(v,u)) %360 

    return wind_direction_degrees

#-------------------------------------------------------------------------------------

def extrapolate(x_known, x_known2, y_known, y_known2, x_target):
    x1, x2 = x_known, x_known2
    y1, y2 = y_known, y_known2

    slope = (y2 - y1)/ (x2 - x1) 

    y_target = y1 + slope * (x_target - x1) 

    return y_target

#-------------------------------------------------------------------------------------

#return list of station ids available within a domain 
def find_stations_in_region(UTMentry=None, extendeast=None, extendnorth=None):
    UTMentry = input("enter in UTM coordinates for southwest corner (<zone> <easting> <northing>):")
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

#-------------------------------------------------------------------------------------

#determine if the current station is within the specified domain
def contains(polygon_coordinates, point):
    polygon=mplPath.Path(polygon_coordinates)

    return polygon.contains_point(point)
            
#-----------------------------------------------------------------

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 3959
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) * math.sin(dlon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance
