from __future__ import division

import json
import time
import os
import math
import random

from flask import Flask, render_template, request, redirect, url_for
from neo4j.v1 import GraphDatabase, basic_auth

neo4j_host = os.getenv('NEO4J_HOST', "bolt://localhost:7687")

app = Flask(__name__)
driver = GraphDatabase.driver(neo4j_host)

show_route_query = """\
match (r:Route {id: {id} })
RETURN {latitude: r.start[0], longitude: r.start[1] } AS start,
       {latitude: r.middle1[0], longitude: r.middle1[1] } AS middle1,
       {latitude: r.middle2[0], longitude: r.middle2[1] } AS middle2,
       [point in r.points | apoc.map.fromLists(["latitude", "longitude"], [p in split(point, ",") | toFloat(p) ])  ] AS roads,
       r.distance AS distance,
       r.direction AS direction,
       r.estimatedDistance AS estimatedDistance
"""


@app.route('/routes/<route_id>')
def lookup_route(route_id):
    content_type = request.args.get("type", "")
    with driver.session() as session:
        distance = -1
        direction = "north"
        estimated_distance = 1000

        runs = []

        result = session.run(show_route_query, {"id": route_id})

        for row in result:
            print("Start: {start}, Middle: {middle1}, Middle: {middle2}, Distance: {distance}"
                  .format(start=row["start"], middle1=row["middle1"], middle2=row["middle2"], distance=row["distance"]))
            distance = row["distance"]
            if distance:
                for sub_row in row["roads"]:
                    runs.append(
                        {"latitude": sub_row["latitude"], "longitude": sub_row["longitude"]})
            direction = row["direction"]
            estimated_distance = row["estimatedDistance"]

        lats = [run["latitude"] for run in runs]
        longs = [run["longitude"] for run in runs]
        lat_centre = sum(lats) / len(lats) if len(lats) > 0 else 0
        long_centre = sum(longs) / len(lats) if len(lats) > 0 else 0

        if content_type == "gpx":
            return render_template("gpx.xml", runs=runs)
        else:
            return render_template("halfPageMap.html",
                                   direction=direction,
                                   estimated_distance=estimated_distance,
                                   runs=json.dumps(runs),
                                   distance=distance,
                                   lat_centre=lat_centre,
                                   long_centre=long_centre,
                                   route_id=route_id
                                   )


generate_route_query = """\
MATCH (middle1:Road)
WHERE {latLow} < middle1.latitude < {latHigh}
AND   {longLow} < middle1.longitude < {longHigh}
AND SIZE((middle1)-[:CONNECTS]-()) > 1

MATCH (middle2:Road)
WHERE {latLow} + ((({latMetres}-{latVariability})/3) * 0.0000089)
      < middle2.latitude <
      {latHigh} + ((({latMetres}+{latVariability})/3) * 0.0000089)
AND   {longLow} + ((({longMetres}-{longVariability})*3) * 0.0000089 / cos({lat} + (({latMetres}+100) * 0.0000089) * 0.018))
      < middle2.longitude <
      {longHigh} + ((({longMetres}+{longVariability})*3) * 0.0000089 / cos({lat} + (({latMetres}+100) * 0.0000089) * 0.018))
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
LIMIT 1
MERGE (route:Route { points: [road in roads | road.latitude + "," + road.longitude] })
ON CREATE SET route.id =  apoc.create.uuid()
SET route.start = [start.latitude, start.longitude],
    route.middle1 = [middle1.latitude, middle1.longitude],
    route.middle2 = [middle2.latitude, middle2.longitude],
    route.distance = reduce(acc=0, connection in connections | acc + connection.length ),
    route.estimatedDistance = {estimatedDistance},
    route.direction = {direction}

return route.id AS routeId
"""


@app.route('/routes', methods=['POST'])
def routes():
    if request.method == "POST":
        estimated_distance = request.form.get('estimatedDistance')
        estimated_distance = int(estimated_distance) if estimated_distance else 5000

        direction = request.form.get('direction')
        adjustment = 1 if direction == "north" else -1

        lats = sorted([(estimated_distance / 5) * adjustment,
                       (estimated_distance / 4) * adjustment])
        lat_metres = random.randint(lats[0], lats[1])

        lats_var = sorted(
            [int(abs(lat_metres / 10)), int(abs(lat_metres / 8))])
        lat_variability = random.randint(lats_var[0], lats_var[1])

        long_metres = 100
        long_variability = 200

        lat = 51.357397146246264
        lon = -0.20153965352074504

        lat_low = lat + ((lat_metres - lat_variability) * 0.0000089)
        lat_high = lat + ((lat_metres + lat_variability) * 0.0000089)

        long_low = lon + ((long_metres - long_variability)
                          * 0.0000089 / math.cos(lat * 0.018))
        long_high = lon + ((long_metres + long_variability)
                           * 0.0000089 / math.cos(lat * 0.018))

        with driver.session() as session:
            start = int(round(time.time() * 1000))
            result = session.run(generate_route_query, {
                "lat": lat,
                "long": lon,

                "latLow": lat_low,
                "latHigh": lat_high,

                "longLow": long_low,
                "longHigh": long_high,

                "latMetres": lat_metres,
                "latVariability": lat_variability,

                "longMetres": long_metres,
                "longVariability": long_variability,
                "direction": direction,
                "estimatedDistance": estimated_distance
            })
            row = result.peek()
            end = int(round(time.time() * 1000))
            route_id = row["routeId"]
            print("Route {id} generated in {time}".format(
                id=route_id, time=(end - start)))

        return redirect(url_for('lookup_route', route_id=route_id))


generate_route_query2 = """\
MATCH (middle1:Road)
WHERE {middle1LatLow} < middle1.latitude < {middle1LatHigh}
AND   {middle1LongLow} < middle1.longitude < {middle1LongHigh}
AND SIZE((middle1)-[:CONNECTS]-()) > 1

MATCH (middle2:Road)
WHERE {middle2LatLow} < middle2.latitude < {middle2LatHigh}
AND   {middle2LongLow} < middle2.longitude < {middle2LongHigh}
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
LIMIT 1
MERGE (route:Route { points: [road in roads | road.latitude + "," + road.longitude] })
ON CREATE SET route.id =  apoc.create.uuid()
SET route.start = [start.latitude, start.longitude],
    route.middle1 = [middle1.latitude, middle1.longitude],
    route.middle2 = [middle2.latitude, middle2.longitude],
    route.distance = reduce(acc=0, connection in connections | acc + connection.length ),
    route.estimatedDistance = {estimatedDistance},
    route.direction = {direction}

return route.id AS routeId
"""


@app.route('/routes2', methods=['POST'])
def routes2():
    if request.method == "POST":
        estimated_distance = request.form.get('estimatedDistance')
        estimated_distance = int(estimated_distance) if estimated_distance else 5000

        lats = sorted([(estimated_distance / 5),(estimated_distance / 4)])
        radius = random.randint(lats[0], lats[1])
        print(radius)

        lat = 51.357397146246264
        lon = -0.20153965352074504

        points = generate_points(lat, lon, 2000.0, 20)
        low_index = random.randint(0, 20)-1
        high_index = random.randint(0, 20)-1

        lat_variability = 500
        long_variability = 500

        middle1_lat_low = points[low_index]["lat"]
        middle1_long_low = points[low_index]["lon"]

        middle1_lat_high = middle1_lat_low + (lat_variability * 0.0000089)
        middle1_long_high = middle1_long_low + ((long_variability * 0.0000089) / math.cos(lat * 0.018))

        middle2_lat_low = points[high_index]["lat"]
        middle2_long_low = points[high_index]["lon"]

        middle2_lat_high = middle2_lat_low + (lat_variability * 0.0000089)
        middle2_long_high = middle2_long_low + ((long_variability * 0.0000089) / math.cos(lat * 0.018))

        params = {
                "lat": lat,
                "long": lon,

                "middle1LatLow": middle1_lat_low,
                "middle1LatHigh": middle1_lat_high,
                "middle1LongLow": middle1_long_low,
                "middle1LongHigh": middle1_long_high,

                "middle2LatLow": middle2_lat_low,
                "middle2LatHigh": middle2_lat_high,
                "middle2LongLow": middle2_long_low,
                "middle2LongHigh": middle2_long_high,
                "estimatedDistance": estimated_distance,
                "direction": "N/A"
            }

        print(params)

        with driver.session() as session:
            start = int(round(time.time() * 1000))
            result = session.run(generate_route_query2, params)
            row = result.peek()
            end = int(round(time.time() * 1000))
            route_id = row["routeId"]
            print("Route {id} generated in {time}".format(
                id=route_id, time=(end - start)))

        return redirect(url_for('lookup_route', route_id=route_id))

def generate_points(centerLat, centerLon, radius, N=10):
    circle_points = []
    for k in xrange(N):
        angle = math.pi * 2 * k / N
        dx = radius * math.cos(angle)
        dy = radius * math.sin(angle)
        point = {}
        point['lat'] = centerLat + (180 / math.pi) * (dy / 6378137)
        point['lon'] = centerLon + (180 / math.pi) * (dx / 6378137) / math.cos(centerLat * math.pi / 180)

        circle_points.append(point)
    return circle_points

@app.route('/points')
def points():
    points = generate_points(51.357397146246264, -0.20153965352074504, 2000.0, 20)
    low_index = random.randint(0, 20)-1
    high_index = random.randint(0, 20)-1

    lat_low = points[low_index]["lat"]
    long_low = points[low_index]["lon"]

    lat_high = points[high_index]["lat"]
    long_high = points[high_index]["lon"]

    return render_template("markers.html",
                           runs=json.dumps([]),
                           lat_centre=51.357397146246264,
                           long_centre=-0.20153965352074504,
                           lat_low=lat_low,
                           lon_low=long_low,
                           lat_high=lat_high,
                           lon_high=long_high
                           )

@app.route('/')
def home():
    return render_template("halfPageMap.html",
                           direction="north",
                           estimated_distance=5000,
                           runs=json.dumps([]),
                           lat_centre=51.357397146246264,
                           long_centre=-0.20153965352074504
                           )


get_routes_query = """\
MATCH (r:Route)
RETURN r
"""


@app.route("/routes")
def get_routes():
    with driver.session() as session:
        runs = [row["r"] for row in session.run(get_routes_query)]

    return render_template("listRoutes.html",
                           runs=runs
                           )

# if __name__ == "__main__":
#     app.run(port = 5001)
