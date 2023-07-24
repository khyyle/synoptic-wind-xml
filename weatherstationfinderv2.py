import apifunctions as myfunc
 
#determine latitude, longitude, and whether a station id is being used or not
stid = myfunc.determine_entry()
print(stid)

start = input("Enter a starting date and time to pull wind data from (YYYYmmddHHMM):")
end = input("Enter a end date and time to pull wind data from (YYYYmmddHHMM):")
choice = input(f"would you like to save data for {len(stid)} stations? (Y/N):")

#iterate through the list of station ids and pull data for each one 
for station in stid:
    result = myfunc.apirequest(station, start, end)
    
    #save to an xml file
    myfunc.save_to_xml(result, choice)
    





