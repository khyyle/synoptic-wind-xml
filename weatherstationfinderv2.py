import apifunctions as myfunc

#determine latitude, longitude, and whether a station id is being used or not
stid = myfunc.determine_entry()

#api response
start = input("Enter a starting date and time to pull wind data from (YYYYmmddHHMM):")
end = input("Enter a end date and time to pull wind data from (YYYYmmddHHMM):")

#iterate through the list of station ids and pull data for each one 
for station in stid:
    result = myfunc.apirequest(station, start, end)
    
    #save to an xml file
    myfunc.save_to_xml(result)
    





