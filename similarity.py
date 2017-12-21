import numpy as np

from scipy.spatial.distance import euclidean
from fastdtw import fastdtw
from neo4j.v1 import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost")

find_routes_query = """\
MATCH (route1:Route), (route2:Route)
WHERE id(route1) > id(route2)
RETURN route1, route2
LIMIT 1000
"""

route_similarity_query = """\
MATCH (route1:Route {id: {route1Id}})
MATCH (route2:Route {id: {route2Id}})
MERGE (route1)-[similar:SIMILAR]->(route2)
SET similar.distance = {distance}
"""

with driver.session() as session:
    for row in session.run(find_routes_query):
        route1_points = [[float(p) for p in point.split(",")] for point in row["route1"]["points"]]
        route2_points = [[float(p) for p in point.split(",")] for point in row["route2"]["points"]]

        distance, path = fastdtw(route1_points, route2_points, dist=euclidean)
        print(row["route1"]["id"], row["route2"]["id"], distance)

        session.run(route_similarity_query, {
            "route1Id": row["route1"]["id"],
            "route2Id": row["route2"]["id"],
            "distance": distance
        })
