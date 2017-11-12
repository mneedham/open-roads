from __future__ import division

import json
import math
import os
import random
import time

from flask import Flask, render_template, request, redirect, url_for
from haversine import haversine
from neo4j.v1 import GraphDatabase

import queries

neo4j_host = os.getenv('NEO4J_HOST', "bolt://localhost:7687")

app = Flask(__name__)
driver = GraphDatabase.driver(neo4j_host)


@app.route('/routes/<route_id>')
def lookup_route(route_id):
    content_type = request.args.get("type", "")
    with driver.session() as session:
        distance = -1
        direction = "north"
        estimated_distance = 1000

        runs = []

        result = session.run(queries.show_route, {"id": route_id})

        for row in result:
            # print("Start: {start}, Middle: {middle1}, Middle: {middle2}, Distance: {distance}"
            #       .format(start=row["start"], middle1=row["middle1"], middle2=row["middle2"], distance=row["distance"]))
            distance = row["distance"]
            if distance:
                for sub_row in row["roads"]:
                    runs.append({"latitude": sub_row["latitude"], "longitude": sub_row["longitude"]})
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
                                   lat=lat,
                                   lon=lon,
                                   route_id=route_id,
                                   segments=all_segments()
                                   )


@app.route('/routes', methods=['POST'])
def routes():
    if request.method == "POST":
        estimated_distance = request.form.get('estimatedDistance')
        estimated_distance = int(estimated_distance) if estimated_distance else 5000

        lats = sorted([(estimated_distance / 5), (estimated_distance / 4)])
        radius = random.randint(lats[0], lats[1])

        lat = float(request.form.get('latitude'))
        lon = float(request.form.get('longitude'))

        points_to_generate = 200
        points = generate_points(lat, lon, radius, points_to_generate)
        low_index = random.randint(0, points_to_generate) - 1

        low_point = points[low_index]

        for point in points:
            point["distanceFromLowIndex"] = haversine((point["lat"], point["lon"]),
                                                      (low_point["lat"], low_point["lon"])) * 1000

        suitable_high_points = [point for point in points if
                                estimated_distance / 4 > point["distanceFromLowIndex"] > estimated_distance / 10]
        high_index = random.randint(0, len(suitable_high_points)) - 1
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

        with driver.session() as session:
            start = int(round(time.time() * 1000))
            result = session.run(queries.generate_route, params)
            row = result.peek()
            end = int(round(time.time() * 1000))
            route_id = row["routeId"]
            print("Route {id} generated in {time}".format(id=route_id, time=(end - start)))

        return redirect(url_for('lookup_route', route_id=route_id,
                                lat=request.form.get('latitude'),
                                lon=request.form.get('longitude')))


def generate_points(lat, lon, radius, number_of_points=10):
    circle_points = []
    for k in range(number_of_points):
        angle = math.pi * 2 * k / number_of_points
        dx = radius * math.cos(angle)
        dy = radius * math.sin(angle)
        point = {'lat': lat + (180 / math.pi) * (dy / 6378137),
                 'lon': lon + (180 / math.pi) * (dx / 6378137) / math.cos(lat * math.pi / 180)}
        circle_points.append(point)
    return circle_points


@app.route('/points')
def points():
    points = generate_points(51.357397146246264, -0.20153965352074504, 2000.0, 20)
    low_index = random.randint(0, 20) - 1
    high_index = random.randint(0, 20) - 1

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
                           segments=all_segments()
                           )


def all_segments():
    with driver.session() as session:
        result = session.run(queries.all_segments)
        return [{"id": row["segment"]["id"], "name": row["segment"]["name"]} for row in result]


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
                           lat=lat,
                           lon=lon,
                           segments=all_segments()
                           )


@app.route("/routes")
def get_routes():
    with driver.session() as session:
        runs = [row["r"] for row in session.run(queries.all_routes)]

    return render_template("listRoutes.html",
                           runs=runs
                           )


@app.route('/segments/<segment_id>')
def find_segment(segment_id):
    lat = "51.357397146246264"
    lon = "-0.20153965352074504"

    with driver.session() as session:
        runs = []
        print(segment_id)
        result = session.run(queries.find_segment, {"id": int(segment_id)})
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
                               lat=lat,
                               lon=lon
                               )
