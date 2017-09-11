from neo4j.v1 import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687")

roads_query = """\
with point({ latitude: 51.357397146246264, longitude: -0.20153965352074504 }) AS centre
match (r1:Road)
return r1.latitude as lat, r1.longitude as long, distance(point({latitude: r1.latitude, longitude: r1.longitude}), centre) AS dist
ORDER BY dist
limit 1000
"""

# loop_query = """\
# match (r1:Road) WHERE r1.latitude = 51.357397146246264 AND r1.longitude = -0.20153965352074504
# match path = (r1)-[:CONNECTS*..25]-(r1)
# WITH path, reduce(acc = 0, link in relationships(path) | acc + link.length) AS distance ORDER BY distance DESC  LIMIT 1
# unwind nodes(path) AS road
# RETURN road.latitude as lat, road.longitude as long
# """

# loop_query = """\
# match (r1:Road) WHERE r1.latitude = 51.357397146246264 AND r1.longitude = -0.20153965352074504
# call apoc.path.expand(r1,"CONNECTS","+Road",0,25) yield path as pp
# WHERE nodes(pp)[-1] = r1 AND reduce(acc = 0, link in relationships(pp) | acc + link.length) > 3000
# with pp LIMIT 1
# unwind nodes(pp) AS road
# RETURN road.latitude as lat, road.longitude as long
# """

loop_query = """\
match (r1:Road) WHERE r1.latitude = 51.357397146246264 AND r1.longitude = -0.20153965352074504
call roads.findRoute(r1, 20000) YIELD path AS pp
with pp LIMIT 1
unwind nodes(pp) AS road
RETURN road.latitude as lat, road.longitude as long
"""

with driver.session() as session:
    result = session.run(loop_query)
    for row in result:
        print("{lat},{long}".format(lat=row["lat"], long=row["long"]))
