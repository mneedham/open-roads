show_route = """\
match (r:Route {id: {id} })
RETURN {latitude: r.start[0], longitude: r.start[1] } AS start,
       {latitude: r.middle1[0], longitude: r.middle1[1] } AS middle1,
       {latitude: r.middle2[0], longitude: r.middle2[1] } AS middle2,
       [point in r.points | apoc.map.fromLists(["latitude", "longitude"], [p in split(point, ",") | toFloat(p) ])  ] AS roads,
       r.distance AS distance,
       r.direction AS direction,
       r.estimatedDistance AS estimatedDistance
"""

generate_route = """\
MATCH (middle1:Road)
WHERE {middle1LatLow} < middle1.latitude < {middle1LatHigh}
AND   {middle1LongLow} < middle1.longitude < {middle1LongHigh}
AND SIZE((middle1)-[:CONNECTS]-()) > 1

MATCH (middle2:Road)
WHERE {middle2LatLow} < middle2.latitude < {middle2LatHigh}
AND   {middle2LongLow} < middle2.longitude < {middle2LongHigh}
AND SIZE((middle2)-[:CONNECTS]-()) > 1

WITH middle1, middle2  WHERE size(apoc.coll.toSet([middle1, middle2])) = 2
MATCH (start:Road {latitude: {lat}, longitude: {long}})
WITH start, middle1, middle2
ORDER BY rand()

CALL roads.findMeARoute(start, [middle1, middle2], {segmentId})
YIELD path

WITH start, middle1, middle2,
     nodes(path) as roads,
     relationships(path) as connections
LIMIT 1
MERGE (route:Route { points: [road in roads | road.latitude + "," + road.longitude] })
ON CREATE SET route.id =  apoc.create.uuid()
SET route.start = [start.latitude, start.longitude],
    route.middle1 = [middle1.latitude, middle1.longitude],
    route.middle2 = [middle2.latitude, middle2.longitude],
    route.distance = reduce(acc=0, connection in connections | acc + connection.length ),
    route.estimatedDistance = {estimatedDistance},
    route.direction = {direction}

return route.id AS routeId
"""

all_segments = """\
MATCH (segment:Segment)
RETURN segment
"""

all_routes = """\
MATCH (r:Route)
RETURN r
"""


find_segment = """\
MATCH (segment:Segment {id: {id}})
RETURN [point in segment.points | apoc.map.fromLists(["latitude", "longitude"], [p in split(point, ",") | toFloat(p) ])  ] AS roads
"""