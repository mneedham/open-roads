import math
from flask import render_template
import flask

from neo4j.v1 import GraphDatabase

app = flask.Flask('my app')

lat = 51.357397146246264
long = -0.20153965352074504

lat_metres = 2000
long_metres = 100

lat_1 = lat + (lat_metres * 0.0000089)
long_1 = long + (long_metres * 0.0000089 / math.cos(lat * 0.018))

lat_2 = lat_1 + ((lat_metres/3) * 0.0000089)
long_2 = long_1 + (long_metres*3 * 0.0000089 / math.cos(lat_1 * 0.018))


query = """\
MATCH (middle1:Road) 
WHERE {lat} + (1900 * 0.0000089) < middle1.latitude < {lat} + (2100 * 0.0000089) 
AND   {long} + (50 * 0.0000089 / cos({lat} * 0.018))   < middle1.longitude <  {long} + (100 * 0.0000089 / cos({lat} * 0.018))
MATCH (middle2:Road)
WHERE {lat} + (2100 * 0.0000089) + ((1900/3) * 0.0000089)   
      < middle2.latitude < 
      {lat} + (2100 * 0.0000089) + ((2100/3) * 0.0000089) 
AND   {long} + (100 * 0.0000089 / cos({lat} * 0.018)) + ((50*3) * 0.0000089 / cos({lat} + (2100 * 0.0000089) * 0.018))  
      < middle2.longitude <  
      {long} + (100 * 0.0000089 / cos({lat} * 0.018)) + ((100*3) * 0.0000089 / cos({lat} + (2100 * 0.0000089) * 0.018))

WITH middle1, middle2  WHERE middle1 <> middle2
MATCH (start:Road {latitude: {lat}, longitude: {long}})

MATCH startToMiddle1Path = shortestpath((start)-[:CONNECTS*]-(middle1))
MATCH middle1ToMiddle2Path = shortestpath((middle1)-[:CONNECTS*]-(middle2))
MATCH middle2ToStartPath = shortestpath((middle2)-[:CONNECTS*]-(start))
WITH start, middle1, middle2,
     nodes(startToMiddle1Path) + nodes(middle1ToMiddle2Path) + nodes(middle2ToStartPath) as roads,
     relationships(startToMiddle1Path) + relationships(middle1ToMiddle2Path) + relationships(middle2ToStartPath) as connections
return start {.latitude, .longitude}, middle1 {.latitude, .longitude}, middle2 {.latitude, .longitude}, roads,  reduce(acc=0, connection in connections | acc + connection.length ) AS distance
ORDER BY rand()
LIMIT 1
"""

runs = []

driver = GraphDatabase.driver("bolt://localhost:7687")

with driver.session() as session:
    result = session.run(query, {
        "lat": 51.357397146246264,
        "long": -0.20153965352074504,
        "latMetres": 3000,
        "longMetres": 100
    })
    for row in result:
        print("Start: {start}, Middle: {middle1}, Middle: {middle2}, Distance: {distance}"
              .format(start=row["start"], middle1=row["middle1"], middle2=row["middle2"], distance=row["distance"]))
        for sub_row in row["roads"]:
            runs.append({"latitude": sub_row["latitude"], "longitude": sub_row["longitude"]})

# runs = [
#     {"latitude": lat, "longitude": long},
#     {"latitude": lat_1, "longitude": long_1},
#     {"latitude": lat_2, "longitude": long_2},
#     {"latitude": lat, "longitude": long}
# ]
#
# for run in runs:
#     print(run)

with app.app_context():
    rendered = render_template('leaflet.html', runs=runs)

    with open("/tmp/map.html", "wb") as file:
        file.write(rendered.encode('utf-8'))
