import apifunctions as myfunc
import matplotlib.pyplot as plt
 
#determine latitude, longitude, and whether a station id is being used or not
stid = myfunc.determine_entry()
print(stid)

start = input("Enter a starting date and time to pull wind data from (YYYYmmddHHMM):") # 
end =  input("Enter a end date and time to pull wind data from (YYYYmmddHHMM):") 
choice =  input(f"would you like to save data for {len(stid)} stations? (Y/N):") 
if choice == "Y":
    decision = True
elif choice == "N": 
    assert "program ended"
else: 
    raise KeyError("Please enter either \"Y\" or \"N\"")

folder_name =  input("Enter a folder name to save the XML files in:")
interval = int(input("enter desired interval for wind speeds and directions (in full minutes):"))

length = len(stid)
#iterate through the list of station ids and pull data for each one 
for station in stid:
    result = myfunc.apirequest(station, start, end)
    if result == None:
        continue
    else:
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
            myfunc.save_to_xml(result, decision, folder_name, direction_interp, speed_interp, new_time_set)
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
            
            