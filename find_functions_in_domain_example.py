import apifunctions as myfunc

#example implementation
stidlist = myfunc.find_stations_in_region()
print(stidlist)

start = input("enter a starting date and time to pull wind data from (YYYYmmddHHMM):")
end = input("enter a end date and time to pull wind data from (YYYYmmddHHMM):")
choice = input(f"would you like to save data for {len(stidlist)} stations? (Y/N):")

for station in stidlist:
    result = myfunc.apirequest(station, start, end)
    myfunc.save_to_xml(result, choice)

