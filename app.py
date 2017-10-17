from __future__ import division
from flask import Flask, render_template, request
from neo4j.v1 import GraphDatabase

import csv
import json
import time


loop_query = """\
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

app = Flask(__name__)
driver = GraphDatabase.driver("bolt://localhost:7687")

@app.route('/search')
def search():
    estimated_distance = request.args.get('estimatedDistance')
    estimated_distance = int(estimated_distance) if estimated_distance else 5000

    direction = request.args.get('direction')
    adjustment = 1 if direction == "north" else -1

    lat_metres = (estimated_distance / 5) * adjustment
    lat_variability = abs(lat_metres / 10)

    runs = []

    with driver.session() as session:
        start = int(round(time.time() * 1000))
        result = session.run(loop_query, {
            "lat": 51.357397146246264,
            "long": -0.20153965352074504,

            "latMetres": lat_metres,
            "latVariability": lat_variability,

            "longMetres": 100,
            "longVariability": 200,

        })

        distance = -1
        for row in result:
            end = int(round(time.time() * 1000))

            print("Start: {start}, Middle: {middle1}, Middle: {middle2}, Distance: {distance}, Time: {time}"
                  .format(start=row["start"], middle1=row["middle1"], middle2=row["middle2"], distance=row["distance"], time = (end - start)))
            distance = row["distance"]
            if distance:
                for sub_row in row["roads"]:
                    runs.append({"latitude": sub_row["latitude"], "longitude": sub_row["longitude"]})

    lats = [run["latitude"] for run in runs]
    longs = [run["longitude"] for run in runs]
    lat_centre = sum(lats) / len(lats) if len(lats) > 0 else 0
    long_centre = sum(longs) / len(lats) if len(lats) > 0 else 0

    return render_template("halfPageMap.html",
                           direction = direction,
                           estimated_distance = estimated_distance,
                           runs = json.dumps(runs),
                           distance = distance,
                           lat_centre = lat_centre,
                           long_centre = long_centre
                           )


@app.route('/')
def home():
    return render_template("halfPageMap.html",
                           direction = "north",
                           estimated_distance = 5000,
                           runs = json.dumps([]),
                           lat_centre = 51.357397146246264,
                           long_centre = -0.20153965352074504
                           )

if __name__ == "__main__":
    app.run(port = 5001)
