:param lat: 51.357397146246264
:param long: -0.20153965352074504
:param latMetres: 3000
:param longMetres: 100

match (r:Road)
where {lat} - ({latMetres} * 0.0000089) <  r.latitude < {lat} + ({latMetres} * 0.0000089) AND
      {long} - ({longMetres} * 0.0000089) / cos({lat} * 0.018) <  r.longitude < {long} + ({longMetres} * 0.0000089) / cos({lat} * 0.018)
WITH  r
ORDER BY rand()
LIMIT 2
RETURN {lat}, {long}, collect(r) AS roads;


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
unwind nodes(startToMiddle1Path) + nodes(middle1ToMiddle2Path) + nodes(middle2ToStartPath) AS road
return road.latitude AS lat, road.longitude AS long
