import math
from flask import render_template
import flask

from neo4j.v1 import GraphDatabase

app = flask.Flask('my app')

lat = 51.357874010145395
long = -0.198045110923591

lat_metres = -1000
long_metres = -100

lat_1 = lat + (lat_metres * 0.0000089)
long_1 = long + (long_metres * 0.0000089 / math.cos(lat * 0.018))

lat_2 = lat_1 + ((lat_metres/3) * 0.0000089)
long_2 = long_1 + (long_metres*3 * 0.0000089 / math.cos(lat_1 * 0.018))

query = """\
MATCH (middle1:Road) 
WHERE {lat} + (({latMetres}-{latVariability}) * 0.0000089) < middle1.latitude < {lat} + (({latMetres}+{latVariability}) * 0.0000089) 
AND   {long} + (({longMetres}-{longVariability}) * 0.0000089 / cos({lat} * 0.018))   < middle1.longitude <  {long} + (({longMetres}+{longVariability}) * 0.0000089 / cos({lat} * 0.018))
AND SIZE((middle1)-[:CONNECTS]-()) > 1

MATCH (middle2:Road)
WHERE {lat} + (({latMetres}-{latVariability}) * 0.0000089) + ((({latMetres}-{latVariability})/3) * 0.0000089)   
      < middle2.latitude < 
      {lat} + (({latMetres}+{latVariability}) * 0.0000089) + ((({latMetres}+{latVariability})/3) * 0.0000089) 
AND   {long} + (({longMetres}-{longVariability}) * 0.0000089 / cos({lat} * 0.018)) + ((({longMetres}-{longVariability})*3) * 0.0000089 / cos({lat} + (({latMetres}+100) * 0.0000089) * 0.018))  
      < middle2.longitude <  
      {long} + (({longMetres}+{longVariability}) * 0.0000089 / cos({lat} * 0.018)) + ((({longMetres}+{longVariability})*3) * 0.0000089 / cos({lat} + (({latMetres}+100) * 0.0000089) * 0.018))
AND SIZE((middle2)-[:CONNECTS]-()) > 1

WITH middle1, middle2  WHERE middle1 <> middle2
MATCH (start:Road {latitude: {lat}, longitude: {long}})
WITH start, middle1, middle2 
ORDER BY rand()
CALL roads.findMeARoute2(start, middle1, middle2)
YIELD path
WITH start, middle1, middle2,
     nodes(path) as roads,
     relationships(path) as connections
return start {.latitude, .longitude}, middle1 {.latitude, .longitude}, middle2 {.latitude, .longitude}, roads,  reduce(acc=0, connection in connections | acc + connection.length ) AS distance
LIMIT 1
"""

runs = []

driver = GraphDatabase.driver("bolt://localhost:7687")

while True:

    with driver.session() as session:
        result = session.run(query, {
            "lat": 51.357397146246264,
            "long": -0.20153965352074504,

            "latMetres": lat_metres,
            "latVariability": 100,

            "longMetres": long_metres,
            "longVariability": 200,

        })
        for row in result:
            print("Start: {start}, Middle: {middle1}, Middle: {middle2}, Distance: {distance}"
                  .format(start=row["start"], middle1=row["middle1"], middle2=row["middle2"], distance=row["distance"]))
            if not row["roads"]:
                print("No roads")
                break

# runs = [
#     {"latitude": lat, "longitude": long},
#     {"latitude": lat_1, "longitude": long_1},
#     {"latitude": lat_2, "longitude": long_2},
#     {"latitude": lat, "longitude": long}
# ]
#
# for run in runs:
#     print(run)
