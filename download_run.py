import os
import polyline
import requests
import json
from dateutil import parser
from neo4j.v1 import GraphDatabase

token = os.environ["TOKEN"]
headers = {'Authorization': "Bearer {0}".format(token)}


def retrieve_activity(activity_id):
    r = requests.get("https://www.strava.com/api/v3/activities/{0}".format(activity_id), headers=headers)
    return r.json()


neo4j_host = os.getenv('NEO4J_HOST', "bolt://localhost:7687")
driver = GraphDatabase.driver(neo4j_host)

create_activity_query = """\
MERGE (activity:Activity{id: {id}})
SET activity.points = [road in {roads} | road.latitude + "," + road.longitude]

WITH activity

UNWIND {segmentEfforts} AS segmentEffort
MATCH (segment:Segment {id: segmentEffort.segmentId })
MERGE (effort:SegmentEffort {id: segmentEffort.id })
SET effort.elapsedTime = segmentEffort.elapsedTime,
    effort.movingTime = segmentEffort.movingTime,
    effort.startDate = segmentEffort.startDate

MERGE (activity)-[:SEGMENT_EFFORT]->(effort)
MERGE (effort)-[:SEGMENT]->(segment)
"""

activity_id = 1338437328


def segment_efforts(activity):
    return [
        {
            "id": segment_effort["id"],
            "movingTime": segment_effort["moving_time"],
            "elapsedTime": segment_effort["elapsed_time"],
            "startDate": int(parser.parse(segment_effort["start_date"]).timestamp()),
            "segmentId": segment_effort["segment"]["id"]
        }
        for segment_effort in activity["segment_efforts"]
    ]


with driver.session() as session:
    activity = retrieve_activity(activity_id)
    print(json.dumps(activity["segment_efforts"]))

    line = activity["map"]["polyline"]
    points = [{"latitude": point[0], "longitude": point[1]}
              for point in polyline.decode(line)]

    params = {"id": activity["id"], "roads": points, "segmentEfforts": segment_efforts(activity)}

    session.run(create_activity_query, params)
