import apifunctions as myfunc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
 
#determine latitude, longitude, and whether a station id is being used or not
stid = myfunc.determine_entry()
print(stid)
print()
print("--enter time in current timezone--")
start = input("enter a starting date and time to pull wind data from (YYYYmmddHHMM):") # 
end =  input(" enter a end date and time to pull wind data from (YYYYmmddHHMM):") 
choice =  input(f"would you like to save data for {len(stid)} stations? (Y/N):") 
if choice == "Y":
    decision = True
elif choice == "N": 
    raise KeyboardInterrupt("program ended")
else: 
    raise KeyError("please enter either \"Y\" or \"N\"")

folder_name =  input("enter a folder name to save the XML files in:")
interval = float(input("enter desired interval for wind speeds and directions (in full minutes):"))

length = len(stid)
#iterate through the list of station ids and pull data for each one 
for station in stid:
    result = myfunc.apirequest(station, start, end)
    if result == None:
        continue
    else:
        speed_interp, new_time_set, old_speed, direction_interp, old_wind_direction, old_iso8601, new_iso8601  = myfunc.interpolate_wind_speed(interval, station, start, end)
        
        datetime_old = [datetime.fromisoformat(timestamp) for timestamp in old_iso8601]
        datetime_new = [datetime.fromisoformat(timestamp) for timestamp in new_iso8601]
        
        plt.plot(datetime_old, old_wind_direction, label= "old values (direction)", marker = 'o', linestyle = '-', color='blue')
        plt.plot(datetime_new, direction_interp, label="new values (direction)", marker = "x", linestyle='-', color= 'red')
        
        plt.xlabel('Time')
        plt.ylabel('Wind direction')
        plt.title('wind directions graphed')
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M:%S"))  
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator()) 
        plt.xticks(rotation=45)
        plt.grid(True)
        plt.legend()   
        plt.savefig(f'direction_{station}.pdf')

        plt.show()


        plt.plot(datetime_old, old_speed, label= "old values (speed)", marker = 'o', linestyle = '-', color='green')
        plt.plot(datetime_new, speed_interp, label="new values (speed)", marker = "x", linestyle='-', color= 'orange')
        
        plt.xlabel('Time')
        plt.ylabel('Wind direction')
        plt.title('speed  graphed')
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M:%S")) 
        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())  
        plt.xticks(rotation=30)
        plt.grid(True)
        plt.legend()
        plt.savefig(f'speed_{station}.pdf')

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
            
            