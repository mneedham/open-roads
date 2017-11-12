from __future__ import division
from sortedcontainers import SortedSet

import json
import time
import os
import math
import random
import polyline

from flask import Flask, render_template, request, redirect, url_for
from neo4j.v1 import GraphDatabase, basic_auth

from haversine import haversine

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
            # print("Start: {start}, Middle: {middle1}, Middle: {middle2}, Distance: {distance}"
            #       .format(start=row["start"], middle1=row["middle1"], middle2=row["middle2"], distance=row["distance"]))
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

        lat = request.args.get("lat")
        lon = request.args.get("lon")

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
                                   lat = lat,
                                   lon = lon,
                                   route_id=route_id,
                                   segments = all_segments()
                                   )


generate_route_query = """\
MATCH (middle1:Road)
WHERE {middle1LatLow} < middle1.latitude < {middle1LatHigh}
AND   {middle1LongLow} < middle1.longitude < {middle1LongHigh}
AND SIZE((middle1)-[:CONNECTS]-()) > 1

MATCH (middle2:Road)
WHERE {middle2LatLow} < middle2.latitude < {middle2LatHigh}
AND   {middle2LongLow} < middle2.longitude < {middle2LongHigh}
AND SIZE((middle2)-[:CONNECTS]-()) > 1

WITH middle1, middle2  WHERE size(apoc.coll.toSet([middle1, middle2])) = 2
MATCH (start:Road {latitude: {lat}, longitude: {long}})
WITH start, middle1, middle2
ORDER BY rand()

CALL roads.findMeARoute(start, [middle1, middle2], {segmentId})
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

        lats = sorted([(estimated_distance / 5),(estimated_distance / 4)])
        radius = random.randint(lats[0], lats[1])
        # print(radius)

        lat = float(request.form.get('latitude'))
        lon = float(request.form.get('longitude'))

        points_to_generate = 200
        points = generate_points(lat, lon, estimated_distance / 4, points_to_generate)
        low_index = random.randint(0, points_to_generate)-1

        low_point = points[low_index]

        for point in points:
            point["distanceFromLowIndex"] = haversine((point["lat"], point["lon"]), (low_point["lat"], low_point["lon"])) * 1000

        suitable_high_points = [point for point in points if estimated_distance / 4  > point["distanceFromLowIndex"] > estimated_distance / 10]
        high_index = random.randint(0, len(suitable_high_points))-1
        high_point = suitable_high_points[high_index]

        lat_variability = 500
        long_variability = 500

        middle1_lat_low = low_point["lat"]
        middle1_long_low = low_point["lon"]

        middle1_lat_high = middle1_lat_low + (lat_variability * 0.0000089)
        middle1_long_high = middle1_long_low + ((long_variability * 0.0000089) / math.cos(lat * 0.018))

        middle2_lat_low = high_point["lat"]
        middle2_long_low = high_point["lon"]

        middle2_lat_high = middle2_lat_low + (lat_variability * 0.0000089)
        middle2_long_high = middle2_long_low + ((long_variability * 0.0000089) / math.cos(lat * 0.018))

        segment_id = request.form.get('segment')

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
                "direction": "N/A",

                "segmentId": segment_id
            }

        print(params)

        with driver.session() as session:
            start = int(round(time.time() * 1000))
            result = session.run(generate_route_query, params)
            row = result.peek()
            end = int(round(time.time() * 1000))
            route_id = row["routeId"]
            print("Route {id} generated in {time}".format(
                id=route_id, time=(end - start)))

        return redirect(url_for('lookup_route', route_id=route_id,
                                                lat = request.form.get('latitude'),
                                                lon = request.form.get('longitude')))

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
                           lon_high=long_high,
                           segments = all_segments()
                           )

all_segments_query = """\
MATCH (segment:Segment)
RETURN segment
"""

def all_segments():
    with driver.session() as session:
        result = session.run(all_segments_query)
        return [{"id": row["segment"]["id"], "name": row["segment"]["name"]} for row in result ]


@app.route('/')
def home():
    lat = "51.357397146246264"
    lon = "-0.20153965352074504"

    return render_template("halfPageMap.html",
                           direction="north",
                           estimated_distance=5000,
                           runs=json.dumps([]),
                           lat_centre=lat,
                           long_centre=lon,
                           lat =  lat,
                           lon = lon,
                           segments = all_segments()
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


find_segment_query = """\
MATCH (segment:Segment {id: {id}})
RETURN [point in segment.points | apoc.map.fromLists(["latitude", "longitude"], [p in split(point, ",") | toFloat(p) ])  ] AS roads
"""

@app.route('/segments/<segment_id>')
def find_segment(segment_id):
    lat = "51.357397146246264"
    lon = "-0.20153965352074504"

    with driver.session() as session:
        runs = []
        print(segment_id)
        result = session.run(find_segment_query, {"id": int(segment_id)})
        print(result)
        for row in result:
            for sub_row in row["roads"]:
                runs.append(
                    {"latitude": sub_row["latitude"], "longitude": sub_row["longitude"]})

        return render_template("halfPageMap.html",
                                direction="north",
                                estimated_distance=5000,
                                runs=json.dumps(runs),
                                lat_centre=lat,
                                long_centre=lon,
                                lat =  lat,
                                lon = lon
                                )


# if __name__ == "__main__":
#     app.run(port = 5001)
