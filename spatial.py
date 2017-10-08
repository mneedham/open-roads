from neo4j.v1 import GraphDatabase, basic_auth

driver = GraphDatabase.driver("bolt://localhost", auth=basic_auth("neo4j", "neo"))

session = driver.session()

result = session.run("""MATCH (r:Road)
                        REMOVE r:Process
                        RETURN count(*)""")

print result.peek()

# while True:
#     query = """MATCH (r:Process)
#                REMOVE r:Process
#                WITH r LIMIT 10000
#                WITH collect(r) AS roads
#                CALL spatial.addNodes('roads',roads) YIELD node
#                RETURN count(*) AS count"""
#     result = session.run(query)
#
#     roads_processed = result.peek()["count"]
#     print "processed {0}".format(roads_processed)
#     if roads_processed == 0:
#         break
#
# session.close()
