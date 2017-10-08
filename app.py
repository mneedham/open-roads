from flask import Flask, render_template, request
from neo4j.v1 import GraphDatabase

import csv
import json


# loop_query = """\
# match (r1:Road) WHERE r1.latitude = 51.357397146246264 AND r1.longitude = -0.20153965352074504
# call roads.findRoute(r1, {distance}, {bfs}) YIELD path AS pp
# with pp LIMIT 1
# unwind nodes(pp) AS road
# RETURN road.latitude as lat, road.longitude as long
# """

# loop_query = """\
# match (r1:Road) WHERE r1.latitude = 51.357397146246264 AND r1.longitude = -0.20153965352074504
# MATCH (r2:Road) WHERE r2.latitude = 51.36272835382321 AND r2.longitude = -0.16836400394638354
# MATCH path = shortestpath((r1)-[*]-(r2))
# unwind nodes(path) as road
# return road.latitude AS lat, road.longitude AS long
# """

loop_query = """\
match (r:Road)
where {lat} - ({latMetres} * 0.0000089) <  r.latitude < {lat} + ({latMetres} * 0.0000089) AND
      {long} - ({longMetres} * 0.0000089) / cos({lat} * 0.018) <  r.longitude < {long} + ({longMetres} * 0.0000089) / cos({lat} * 0.018)
WITH  r
ORDER BY rand()
LIMIT 2
WITH collect(r) AS roads
MATCH (start:Road {latitude: {lat}, longitude: {long}})
MATCH (middle1:Road {latitude: roads[0].latitude, longitude: roads[0].longitude})
MATCH (middle2:Road {latitude: roads[1].latitude, longitude: roads[1].longitude})
MATCH startToMiddle1Path = shortestpath((start)-[:CONNECTS*]-(middle1))
MATCH middle1ToMiddle2Path = shortestpath((middle1)-[:CONNECTS*]-(middle2))
MATCH middle2ToStartPath = shortestpath((middle2)-[:CONNECTS*]-(start))
WITH start, middle1, middle2,
     nodes(startToMiddle1Path) + nodes(middle1ToMiddle2Path) + nodes(middle2ToStartPath) as roads,
     relationships(startToMiddle1Path) + relationships(middle1ToMiddle2Path) + relationships(middle2ToStartPath) as connections
return start {.latitude, .longitude}, middle1 {.latitude, .longitude}, middle2 {.latitude, .longitude}, roads, reduce(acc=0, connection in connections | acc + connection.length ) AS distance
"""

app = Flask(__name__)
driver = GraphDatabase.driver("bolt://localhost:7687")

@app.route('/')
def my_runs():
    distance = request.args.get('distance')
    distance = int(distance) if distance else 5000
    bfs = request.args.get('bfs')
    bfs = bool(bfs)

    runs = []

    with driver.session() as session:
        result = session.run(loop_query, {
            "distance": distance,
            "bfs": bfs,
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


    return render_template("leaflet.html", runs = json.dumps(runs))

if __name__ == "__main__":
    app.run(port = 5001)
