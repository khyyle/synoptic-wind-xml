import apifunctions as myfunc
import matplotlib.pyplot as plt
 
#determine latitude, longitude, and whether a station id is being used or not
stid = myfunc.determine_entry()
print(stid)

start = input("Enter a starting date and time to pull wind data from (YYYYmmddHHMM):") #"202307141000" 
end =  input("Enter a end date and time to pull wind data from (YYYYmmddHHMM):") #"202307141100"
choice =  input(f"would you like to save data for {len(stid)} stations? (Y/N):") #"Y"
folder_name =  input("Enter a folder name to save the XML files in:") #"test"

length = len(stid)
#iterate through the list of station ids and pull data for each one 
for station in stid:
    result = myfunc.apirequest(station, start, end)
    windspeedsinterp, timesinterp, oldspeeds, oldtime  = myfunc.interpolate_wind_speed(stid, start, end)
    '''
    plt.plot(timesinterp, windspeedsinterp, marker = 'o', linestyle = '-')

    plt.xlabel('Time')
    plt.ylabel('Wind speed')
    plt.title('interpolated wind speeds graphed')
    plt.grid(True)

    plt.savefig('(normalstation)windspeeds_interp.pdf')

    plt.show()

    
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
         
        