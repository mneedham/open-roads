import os
import polyline
import requests
from neo4j.v1 import GraphDatabase

token = os.environ["TOKEN"]
headers = {'Authorization': "Bearer {0}".format(token)}

r = requests.get("https://www.strava.com/api/v3/segments/14343345", headers=headers)
response = r.json()
print(response["name"], response["id"])
line = response["map"]["polyline"]

neo4j_host = os.getenv('NEO4J_HOST', "bolt://localhost:7687")
driver = GraphDatabase.driver(neo4j_host)

lookup_points_query = """\
OPTIONAL MATCH (road:Road)
WHERE {point}.latitude  - (100 * 0.0000089) < road.latitude < {point}.latitude + (100 * 0.0000089)
AND   {point}.longitude - (100 * 0.0000089 / cos(road.latitude * 0.018)) < road.longitude <  {point}.longitude + (100 * 0.0000089 / cos(road.latitude * 0.018))
return {point} AS point, road, id(road) as nodeId
order by distance(point(road), point({point}))
limit 1
"""

create_segment_query = """\
MERGE (segment:Segment {id: {id}})
SET segment.name = {name}, segment.points = [road in {roads} | road.latitude + "," + road.longitude]
"""

check_if_path_query = """\
MATCH (road1:Road)
MATCH (road2:Road)
WHERE road1.latitude = {road1Latitude} AND road1.longitude = {road1Longitude}
AND   road2.latitude = {road2Latitude} AND road2.longitude = {road2Longitude}
MATCH path = shortestpath((road1)-[*]-(road2))
RETURN path 
"""


unique_roads = []
unique_node_ids = []

with driver.session() as session:
    points = polyline.decode(line)
    for point in points:
        result = session.run(lookup_points_query, {"point": {"latitude": point[0], "longitude": point[1]}})

        for row in result:
            if row["road"]:
                point = (row["road"]["latitude"], row["road"]["longitude"])
                if point not in unique_roads:
                    unique_roads.append(point)
                    unique_node_ids.append(row["nodeId"])

    for pair in zip(unique_roads[:-1], unique_roads[1:]):
        road1, road2 = pair
        result = session.run(check_if_path_query, {
            "road1Latitude": road1[0],
            "road1Longitude": road1[1],
            "road2Latitude": road2[0],
            "road2Longitude": road2[1],
        })
        row = result.peek()

    print(unique_roads)
    session.run(create_segment_query, {
        "roads": [{"latitude": road[0], "longitude": road[1]} for road in unique_roads],
        "id": response["id"],
        "name": response["name"]
    })
