from neo4j.v1 import GraphDatabase

import app.queries as queries
import os

neo4j_host = os.getenv('NEO4J_HOST', "bolt://localhost:7687")
driver = GraphDatabase.driver(neo4j_host)

check_if_path_query = """\
MATCH (road1:Road)
MATCH (road2:Road)
WHERE road1.latitude = {road1Latitude} AND road1.longitude = {road1Longitude}
AND   road2.latitude = {road2Latitude} AND road2.longitude = {road2Longitude}
MATCH path = shortestpath((road1)-[*]-(road2))
RETURN path 
"""

segment_id = 9927088
filtered_roads = []

with driver.session() as session:
    result = session.run(queries.show_segment, {
        "id": segment_id
    })

    row = result.peek()
    segment_roads = row["roads"]
    filtered_roads.append(segment_roads[0])

    for pair in zip(segment_roads[:-1], segment_roads[1:]):
        road1, road2 = pair
        result = session.run(check_if_path_query, {
            "road1Latitude": road1["latitude"],
            "road1Longitude": road1["longitude"],
            "road2Latitude": road2["latitude"],
            "road2Longitude": road2["longitude"],
        })
        row = result.peek()
        if len(row["path"]) == 1:
            for r in row["path"].nodes:
                filtered_roads.append(r.properties)
    filtered_roads.append(segment_roads[-1])

    final_roads = []
    for pair in zip(filtered_roads[:-1], filtered_roads[1:]):
        road1, road2 = pair
        if road1 != road2:
            result = session.run(check_if_path_query, {
                "road1Latitude": road1["latitude"],
                "road1Longitude": road1["longitude"],
                "road2Latitude": road2["latitude"],
                "road2Longitude": road2["longitude"],
            })
            row = result.peek()
            for r in row["path"].nodes:
                final_roads.append(r.properties)

    print(final_roads)
