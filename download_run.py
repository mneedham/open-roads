import os
import polyline
import requests
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
"""

activity1_id = 1355676694

with driver.session() as session:
    activity = retrieve_activity(activity1_id)

    line = activity["map"]["polyline"]
    points = [{"latitude": point[0], "longitude": point[1]}
              for point in polyline.decode(line)]

    print(activity)

    session.run(create_activity_query, {
        "id": activity["id"],
        "roads": points
    })
