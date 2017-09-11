LOAD CSV WITH HEADERS FROM "file:///roads.csv" as row
RETURN row
LIMIT 3;

create index on :Road(id);

USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM "file:///roads.csv" as row
MERGE (r:Road {id: row.id})
ON CREATE SET r.type = row.type,
              r.latitude = tofloat(row.lat),
              r.longitude = tofloat(row.lon);

USING PERIODIC COMMIT 1000
LOAD CSV WITH HEADERS FROM "file:///road_links.csv" as row
MATCH (start:Road {id: row.start_id})
MATCH (end:Road {id: row.end_id})
MERGE (start)-[connects:CONNECTS]->(end)
ON CREATE SET connects.classification = row.classification,
              connects.length = row.length,
              connects.classificationNumber = row.classification_number,
              connects.number = row.number,
              connect.name = row.name;
