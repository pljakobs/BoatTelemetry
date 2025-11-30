this is a simple sming app and python script that I use to gather sensor data and ship it through mqtt to my influxdb instance.
The mqtt_to_influx.py is written to be generally useful for all sorts of mqtt data by being able to understand and break down json structures. 
See the topics.json file as an example of how to use json schema snippets to describe the data to write.
