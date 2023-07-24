import apifunctions as myfunc

stidlist = myfunc.find_stations_in_region()
print()
print(f"{len(stidlist)} stations found:")
print(stidlist)

start = input("enter a starting date and time to pull wind data from (YYYYmmddHHMM):")
end = input("enter a end date and time to pull wind data from (YYYYmmddHHMM):")
choice = input(f"would you like to save data for {len(stidlist)} stations? (Y/N):")
folder_name = input("Enter a folder name to save the XML files in:")
length = len(stidlist)

for station in stidlist:
    result = myfunc.apirequest(station, start, end)

    #omit station if the current station has no data or is inaccessible
    try:
        myfunc.save_to_xml(result, choice, folder_name)
    except KeyError:
        length -=1
        print()
        print(f"no data available for station: {station}")
        print(f"a total of {length} xml files will now be created")
        continue 
    except IndexError:
        length -= 1
        print()
        print(f"no data available for station: {station}")
        print(f"a total of {length} xml files will now be created")
        continue 

