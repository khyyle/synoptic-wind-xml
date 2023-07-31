import apifunctions as myfunc
import matplotlib.pyplot as plt

stidlist = myfunc.find_stations_in_region()
print()
print(f"{len(stidlist)} stations found:")
print(stidlist)

start = input("enter a starting date and time to pull wind data from (YYYYmmddHHMM):")
end = input("enter a end date and time to pull wind data from (YYYYmmddHHMM):")
choice = input(f"would you like to save data for {len(stidlist)} stations? (Y/N):")
if choice == "Y":
    decision = True
elif choice == "N": 
    assert "program ended"
else: 
    raise KeyError("Please enter either \"Y\" or \"N\"")

folder_name = input("Enter a folder name to save the XML files in:")
interval = int(input("enter desired interval for wind speeds and directions (in full minutes):"))
length = len(stidlist)

for station in stidlist:
    result = myfunc.apirequest(station, start, end)
    if result == None:
        continue
    speed_interp, new_time_set, old_speed, old_time, direction_interp, old_wind_direction  = myfunc.interpolate_wind_speed(interval, station, start, end)
    
    plt.plot(old_time, old_wind_direction, label= "old values (direction)", marker = 'o', linestyle = '-', color='blue')
    plt.plot(new_time_set, direction_interp, label="new values (direction)", marker = "x", linestyle='-', color= 'red')
    
    plt.xlabel('Time')
    plt.ylabel('Wind direction')
    plt.title('wind directions graphed')
    plt.grid(True)

    plt.savefig('interp_comparison_WBB.pdf')

    plt.legend()

    plt.show()
    new_time_set = [myfunc.epoch_to_utc_time(time) for time in new_time_set]
    try:
        myfunc.save_to_xml(result, choice, folder_name, direction_interp, speed_interp, new_time_set)
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