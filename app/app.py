from __future__ import division

import json
import math
import os
import random
import time
import util

from flask import Flask, render_template, request, redirect, url_for
from haversine import haversine
from neo4j.v1 import GraphDatabase, ResultError
from flask import jsonify

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
        segment = request.args.get("segment_id")

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
                                   segments=all_segments(),
                                   segment_id=int(segment) if segment else segment
                                   )


def generate_mid_points(lat, lon, radius, estimated_distance):
    points_to_generate = 1000
    generated_points = util.generate_points(lat, lon, radius, points_to_generate)
    low_index = random.randint(0, points_to_generate) - 1

    low_point = generated_points[low_index]

    for point in generated_points:
        point["distanceFromLowIndex"] = haversine((point["lat"], point["lon"]),
                                                  (low_point["lat"], low_point["lon"])) * 1000

    suitable_high_points = [point for point in generated_points
                            if estimated_distance / 4 > point["distanceFromLowIndex"] > estimated_distance / 10]
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

    params = {
        "middle1LatLow": middle1_lat_low,
        "middle1LatHigh": middle1_lat_high,
        "middle1LongLow": middle1_long_low,
        "middle1LongHigh": middle1_long_high,

        "middle2LatLow": middle2_lat_low,
        "middle2LatHigh": middle2_lat_high,
        "middle2LongLow": middle2_long_low,
        "middle2LongHigh": middle2_long_high,
    }

    with driver.session() as session:
        result = session.run(queries.generate_mid_points, params)
        mid_points = [row for row in result]

    return mid_points


@app.route('/midpoints', methods=['GET'])
def midpoints():

    lat = float(request.args.get('latitude'))
    lon = float(request.args.get('longitude'))
    estimated_distance = float(request.args.get('distance', 5000))

    lats = sorted([(estimated_distance / 5), (estimated_distance / 4)])
    radius = random.randint(lats[0], lats[1])

    raw_mid_points = generate_mid_points(lat, lon, radius, estimated_distance)

    print("Combinations: {0}".format(len(raw_mid_points)))

    mid_points = [{"m1": mid_point["middle1"]["id"], "m2": mid_point["middle2"]["id"]}
                  for mid_point in raw_mid_points]

    with driver.session() as session:
        for mid_point in mid_points:
            params = {
                "lat": lat,
                "long": lon,
                "segmentId": "",
                "direction": "N/A",
                "estimatedDistance": estimated_distance,
                "midpoints": [mid_point["m1"], mid_point["m2"]]
            }

            try:
                result = session.run(queries.generate_route_midpoint, params)
                if result.peek():
                    row = result.peek()
                    return jsonify({"routeId": row["routeId"]})
            except ResultError as e:
                print("End of stream? {0}".format(e))
                continue
        return {"Error": "No route id found"}


@app.route('/routes', methods=['POST'])
def routes():
    if request.method == "POST":
        estimated_distance = request.form.get('estimatedDistance')
        estimated_distance = int(estimated_distance) if estimated_distance else 5000

        lats = sorted([(estimated_distance / 5), (estimated_distance / 4)])
        radius = random.randint(lats[0], lats[1])

        lat = float(request.form.get('latitude'))
        lon = float(request.form.get('longitude'))

        points_to_generate = 1000
        generated_points = util.generate_points(lat, lon, radius, points_to_generate)
        low_index = random.randint(0, points_to_generate) - 1

        low_point = generated_points[low_index]

        for point in generated_points:
            point["distanceFromLowIndex"] = haversine((point["lat"], point["lon"]),
                                                      (low_point["lat"], low_point["lon"])) * 1000

        suitable_high_points = [point for point in generated_points
                                if estimated_distance / 4 > point["distanceFromLowIndex"] > estimated_distance / 10]
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
                                lon=request.form.get('longitude'),
                                segment_id=segment_id))


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
        result = session.run(queries.find_segment, {"id": int(segment_id)})
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
                               lon=lon,
                               segment_id=int(segment_id) if segment_id else segment_id,
                               segments=all_segments()
                               )
