from flask import Flask, render_template, request
from neo4j.v1 import GraphDatabase

import csv
import json


loop_query = """\
match (r1:Road) WHERE r1.latitude = 51.357397146246264 AND r1.longitude = -0.20153965352074504
call roads.findRoute(r1, {distance}) YIELD path AS pp
with pp LIMIT 1
unwind nodes(pp) AS road
RETURN road.latitude as lat, road.longitude as long
"""

app = Flask(__name__)
driver = GraphDatabase.driver("bolt://localhost:7687")

@app.route('/')
def my_runs():
    distance = request.args.get('distance')
    distance = int(distance) if distance else 5000

    runs = []

    with driver.session() as session:
        result = session.run(loop_query, {"distance": distance})
        for row in result:
            runs.append({"latitude": row["lat"], "longitude": row["long"]})


    return render_template("leaflet.html", runs = json.dumps(runs))

if __name__ == "__main__":
    app.run(port = 5001)
