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

generate_mid_points = """\
MATCH (middle1:Road)
WHERE {middle1LatLow} < middle1.latitude < {middle1LatHigh}
AND   {middle1LongLow} < middle1.longitude < {middle1LongHigh}
AND SIZE((middle1)-[:CONNECTS]-()) > 1

MATCH (middle2:Road)
WHERE {middle2LatLow} < middle2.latitude < {middle2LatHigh}
AND   {middle2LongLow} < middle2.longitude < {middle2LongHigh}
AND SIZE((middle2)-[:CONNECTS]-()) > 1

WITH [middle1, middle2] AS midpoints 
WHERE size(apoc.coll.toSet(midpoints)) = 2

RETURN midpoints
ORDER BY rand()
"""

generate_route_midpoint = """\
UNWIND {midpoints} AS midpoint
MATCH (road:Road {id: midpoint })
WITH COLLECT(road) AS midpoints

MATCH (start:Road {latitude: {lat}, longitude: {long}})

CALL roads.findMeARoute(start, midpoints, {segmentId}) YIELD roads, distance

WITH midpoints, roads, distance, start

MERGE (route:Route { points: [road in roads | road.latitude + "," + road.longitude] })
ON CREATE SET route.id =  apoc.create.uuid()
SET route.start = [start.latitude, start.longitude],
    route.middle1 = [midpoints[0].latitude, midpoints[0].longitude],
    route.middle2 = [midpoints[1].latitude, midpoints[1].longitude],
    route.distance = distance,
    route.estimatedDistance = {estimatedDistance},
    route.direction = {direction}

RETURN route.id AS routeId
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
YIELD roads, distance

WITH start, middle1, middle2, roads, distance     
LIMIT 1
MERGE (route:Route { points: [road in roads | road.latitude + "," + road.longitude] })
ON CREATE SET route.id =  apoc.create.uuid()
SET route.start = [start.latitude, start.longitude],
    route.middle1 = [middle1.latitude, middle1.longitude],
    route.middle2 = [middle2.latitude, middle2.longitude],
    route.distance = distance,
    route.estimatedDistance = {estimatedDistance},
    route.direction = {direction}

RETURN route.id AS routeId
"""

all_segments = """\
MATCH (segment:Segment)
RETURN segment {
                    .id, 
                    .name,
                     roads: [point in segment.points | apoc.map.fromLists(["latitude", "longitude"], [p in split(point, ",") | toFloat(p) ])  ]
               }
ORDER BY segment.name               
"""

all_routes = """\
MATCH (r:Route)
WHERE 5000 < r.distance < 12000
RETURN r { 
            .id, 
            .distance, 
            roads: [point in r.points | apoc.map.fromLists(["latitude", "longitude"], [p in split(point, ",") | toFloat(p) ])  ]
          }
ORDER BY rand()
LIMIT 20
"""


find_segment = """\
MATCH (segment:Segment {id: {id}})
RETURN [point in segment.points | apoc.map.fromLists(["latitude", "longitude"], [p in split(point, ",") | toFloat(p) ])  ] AS roads
"""


show_segment = """\
match (s:Segment {id: {id} })
optional match (s)<-[:SEGMENT]-(effort)<-[:SEGMENT_EFFORT]-(activity)

WITH s, effort, activity
ORDER BY effort.movingTime 

RETURN [point in s.points | apoc.map.fromLists(["latitude", "longitude"], [p in split(point, ",") | toFloat(p) ])  ] AS roads,
       s.name AS name,
       s.distance AS distance,
       collect(CASE 
         WHEN effort IS NULL THEN NULL 
         ELSE {
         activityId: activity.id,
         effortId: effort.id, 
         time: effort.movingTime,
         date: apoc.date.format(effort.startDate,'s','dd MMM yyyy')
       } END) AS efforts
"""
