from __future__ import division

import json
import math
import os
import queries
import random
import util
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from flask_cors import CORS
from haversine import haversine
from neo4j.v1 import GraphDatabase, ResultError

neo4j_host = os.getenv('NEO4J_HOST', "bolt://localhost:7687")

app = Flask(__name__)
CORS(app)

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
            distance = row["distance"]
            if distance:
                for sub_row in row["roads"]:
                    runs.append({"latitude": sub_row["latitude"], "longitude": sub_row["longitude"]})
            direction = row["direction"]
            estimated_distance = int(row["estimatedDistance"])

        lats = [run["latitude"] for run in runs]
        longs = [run["longitude"] for run in runs]
        lat_centre = sum(lats) / len(lats) if len(lats) > 0 else 0
        long_centre = sum(longs) / len(lats) if len(lats) > 0 else 0

        lat = request.args.get("lat", "51.357397146246264")
        lon = request.args.get("lon", "-0.20153965352074504")
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


def request_wants_json():
    best = request.accept_mimetypes.best_match(['application/json', 'text/html'])
    return best == 'application/json' and request.accept_mimetypes[best] > request.accept_mimetypes['text/html']


@app.route('/routes2/<route_id>')
def lookup_route_json(route_id):
    distance = 0
    with driver.session() as session:
        runs = []

        result = session.run(queries.show_route, {"id": route_id})

        for row in result:
            distance = row["distance"]
            if distance:
                for sub_row in row["roads"]:
                    runs.append({"latitude": sub_row["latitude"], "longitude": sub_row["longitude"]})

    all_routes = {
        "roads": runs,
        "distance": distance
    }

    response = Response(json.dumps(all_routes), status=200, mimetype='application/json')
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response


def calculate_lat_high(lat_variability, lat_low):
    return lat_low + (lat_variability * 0.0000089)


def calculate_long_high(lat, long_variability, long_low):
    return long_low + ((long_variability * 0.0000089) / math.cos(lat * 0.018))


def filter_point(point, low_point, estimated_distance):
    distance_from_low_index = haversine((point["lat"], point["lon"]), (low_point["lat"], low_point["lon"])) * 1000
    return estimated_distance / 4 > distance_from_low_index > estimated_distance / 10


def generate_mid_points(lat, lon, radius, estimated_distance, filter_fn):
    points_to_generate = 1000
    generated_points = util.generate_points(lat, lon, radius, points_to_generate)

    low_index = random.randint(0, points_to_generate) - 1
    low_point = generated_points[low_index]

    suitable_high_points = [point for point in generated_points
                            if filter_fn(point, low_point, estimated_distance)]

    high_index = random.randint(0, len(suitable_high_points)) - 1
    high_point = suitable_high_points[high_index]

    lat_variability = estimated_distance / 10
    long_variability = estimated_distance / 10

    middle1_lat_low = low_point["lat"]
    middle1_long_low = low_point["lon"]

    middle1_lat_high = calculate_lat_high(lat_variability, middle1_lat_low)
    middle1_long_high = calculate_long_high(lat, long_variability, middle1_long_low)

    middle2_lat_low = high_point["lat"]
    middle2_long_low = high_point["lon"]

    middle2_lat_high = calculate_lat_high(lat_variability, middle2_lat_low)
    middle2_long_high = calculate_long_high(lat, long_variability, middle2_long_low)

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


def no_filter(point, low_point, estimated_distance):
    return True


@app.route('/routes2', methods=['POST', 'OPTIONS', 'GET'])
def routes2():
    if request.method == "GET":
        with driver.session() as session:
            runs = [{
                "id": row["r"]["id"],
                "distance": row["r"]["distance"],
                "roads": [{"latitude": sub_row["latitude"], "longitude": sub_row["longitude"]} for sub_row in
                          row["r"]["roads"]]
            }
                for row in session.run(queries.all_routes)]

            return jsonify(runs)
    elif request.method == "POST":
        generate_route_request = request.get_json()

        estimated_distance = generate_route_request["estimatedDistance"]
        estimated_distance = int(estimated_distance) if estimated_distance else 5000

        start_lat = float(generate_route_request["startLatitude"])
        start_lon = float(generate_route_request["startLongitude"])

        shape_lat = generate_route_request.get("shapeLatitude")
        shape_lon = generate_route_request.get('shapeLongitude')
        shape_radius = generate_route_request.get("shapeRadius")

        midpoint_lat = float(shape_lat) if shape_lat else start_lat
        midpoint_lon = float(shape_lon) if shape_lon else start_lon
        radius = float(shape_radius) if shape_radius else calculate_radius(estimated_distance)

        if shape_radius:
            raw_mid_points = generate_mid_points(midpoint_lat, midpoint_lon, radius, estimated_distance, no_filter)
        else:
            raw_mid_points = generate_mid_points(midpoint_lat, midpoint_lon, radius, estimated_distance, filter_point)

        mid_points = [
            [mp["id"] for mp in mid_point["midpoints"]]
            for mid_point in raw_mid_points
        ]

        segment_id = generate_route_request.get('selectedSegment')
        segment_id = segment_id if segment_id else ""

        with driver.session() as session:
            for mid_point in mid_points:
                params = {
                    "lat": start_lat,
                    "long": start_lon,
                    "segmentId": segment_id,
                    "direction": "N/A",
                    "estimatedDistance": estimated_distance,
                    "midpoints": mid_point
                }

                try:
                    result = session.run(queries.generate_route_midpoint, params)
                    if result.peek():
                        row = result.peek()
                        route_id = row["routeId"]
                        return jsonify({"routeId": route_id})
                except ResultError as e:
                    print("End of stream? {0}".format(e))
                    continue
            raise Exception("Could not find route")

    else:
        return jsonify({})


@app.route('/routes', methods=['POST'])
def routes():
    if request.method == "POST":
        estimated_distance = request.form.get('estimatedDistance')
        estimated_distance = int(estimated_distance) if estimated_distance else 5000

        start_lat = float(request.form.get('latitude'))
        start_lon = float(request.form.get('longitude'))

        shape_lat = request.form.get('shapeLatitude')
        shape_lon = request.form.get('shapeLongitude')
        shape_radius = request.form.get("shapeRadius")

        midpoint_lat = float(shape_lat) if shape_lat else start_lat
        midpoint_lon = float(shape_lon) if shape_lon else start_lon
        midpoint_radius = float(shape_radius) if shape_radius else calculate_radius(estimated_distance)

        if shape_radius:
            filter_fn = lambda point, low_point, est_distance: True if shape_radius else None
            raw_mid_points = generate_mid_points(midpoint_lat, midpoint_lon, midpoint_radius, estimated_distance,
                                                 filter_fn)
        else:
            raw_mid_points = generate_mid_points(midpoint_lat, midpoint_lon, midpoint_radius, estimated_distance)

        mid_points = [
            [mp["id"] for mp in mid_point["midpoints"]]
            for mid_point in raw_mid_points
        ]

        segment_id = request.form.get('segment')

        with driver.session() as session:
            for mid_point in mid_points:
                params = {
                    "lat": start_lat,
                    "long": start_lon,
                    "segmentId": segment_id,
                    "direction": "N/A",
                    "estimatedDistance": estimated_distance,
                    "midpoints": mid_point
                }

                try:
                    result = session.run(queries.generate_route_midpoint, params)
                    if result.peek():
                        row = result.peek()
                        route_id = row["routeId"]
                        return redirect(url_for('lookup_route', route_id=route_id,
                                                lat=request.form.get('latitude'),
                                                lon=request.form.get('longitude'),
                                                segment_id=segment_id))
                except ResultError as e:
                    print("End of stream? {0}".format(e))
                    continue
            raise Exception("Could not find route")


def calculate_radius(estimated_distance):
    lats = sorted([(estimated_distance / 5), (estimated_distance / 4)])
    return random.randint(round(lats[0]), round(lats[1]))


def all_segments():
    with driver.session() as session:
        result = session.run(queries.all_segments)
        return [
            {
                "id": row["segment"]["id"],
                "name": row["segment"]["name"],
                "roads": row["segment"]["roads"]
            }
            for row in result]


@app.route("/segments2")
def get_all_segments():
    return jsonify(all_segments())


@app.route('/segments2/<segment_id>')
def lookup_segment_json(segment_id):
    with driver.session() as session:
        runs = []

        result = session.run(queries.show_segment, {"id": int(segment_id)})

        row = result.peek()
        name = row["name"]
        for sub_row in row["roads"]:
            runs.append({"latitude": sub_row["latitude"], "longitude": sub_row["longitude"]})

    segment = {
        "roads": runs,
        "name": name
    }

    response = Response(json.dumps(segment), status=200, mimetype='application/json')
    response.headers['Access-Control-Allow-Origin'] = '*'

    return response

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
