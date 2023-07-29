import apifunctions as myfunc
import matplotlib.pyplot as plt
 
#determine latitude, longitude, and whether a station id is being used or not
stid = myfunc.determine_entry()
print(stid)

start = "202307141000"#input("Enter a starting date and time to pull wind data from (YYYYmmddHHMM):") # 
end =  "202307141100" #input("Enter a end date and time to pull wind data from (YYYYmmddHHMM):") 
choice =  "Y"#input(f"would you like to save data for {len(stid)} stations? (Y/N):") 
folder_name =  "test" #input("Enter a folder name to save the XML files in:") 

length = len(stid)
#iterate through the list of station ids and pull data for each one 
for station in stid:
    result = myfunc.apirequest(station, start, end)
    windspeedsinterp, interp_time_set, oldspeeds, oldtime, winddirecinterp, old_wind_direction  = myfunc.interpolate_wind_speed(station, start, end)

    
    
    plt.plot(oldtime, old_wind_direction, label= "old values", marker = 'o', linestyle = '-', color='blue')

    plt.plot(interp_time_set, winddirecinterp, label="new values", marker = "x", linestyle='-', color= 'red')
    
    plt.xlabel('Time')
    plt.ylabel('Wind direction')
    plt.title('wind directions graphed')
    plt.grid(True)

    plt.savefig('interp_comparison.pdf')

    plt.legend()

    plt.show()

    '''
    plt.plot(oldtime, oldspeeds, marker = 'o', linestyle = '-')

    plt.xlabel('Time')
    plt.ylabel('Wind speed')
    plt.title("old wind speeds graphed")
    plt.grid(True)

    plt.savefig('(normalstation)windspeeds_old.pdf')

    plt.show()
    '''

    try:
        myfunc.save_to_xml(result, choice, folder_name)
    except KeyError:
        length -= 1
        print() 
        print(f"no data available for station: {station}")
        print(f"now outputting data for {length} stations")
        continue 
    except IndexError:
        length -= 1
        print()
        print(f"no data available for station: {station}")
        print(f"now outputting data for {length} stations")
        continue 
         
        