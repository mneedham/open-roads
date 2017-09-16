package com.markhneedham.open_roads;

import org.junit.Rule;
import org.junit.Test;

import org.neo4j.driver.v1.Config;
import org.neo4j.driver.v1.Driver;
import org.neo4j.driver.v1.GraphDatabase;
import org.neo4j.driver.v1.Session;
import org.neo4j.driver.v1.StatementResult;
import org.neo4j.driver.v1.Value;
import org.neo4j.harness.junit.Neo4jRule;

import static junit.framework.TestCase.assertTrue;
import static org.hamcrest.CoreMatchers.equalTo;
import static org.hamcrest.MatcherAssert.assertThat;

import static org.neo4j.driver.v1.Values.parameters;

public class RunFinderTest
{
    // This rule starts a Neo4j instance
    @Rule
    public Neo4jRule neo4j = new Neo4jRule()

            // This is the Procedure we want to test
            .withProcedure( RunFinder.class );

    @Test
    public void shouldFindARoute() throws Throwable
    {
        // In a try-block, to make sure we close the driver after the test
        try( Driver driver = GraphDatabase.driver( neo4j.boltURI() , Config.build().withoutEncryption().toConfig() ) )
        {
            try(Session session = driver.session())
            {
                session.run(
                        "CREATE (r1:Road { latitude: 51.357397146246264, longitude: -0.20153965352074504 } )\n" +
                           "CREATE (r2:Road { latitude: 51.367397146246264, longitude: -0.20153965352074504 } )\n" +
                           "CREATE (r3:Road { latitude: 51.377397146246264, longitude: -0.20153965352074504 } )\n" +
                           "MERGE (r1)-[c1:CONNECTS]->(r2) SET c1.length = 80.0\n" +
                           "MERGE (r2)-[c2:CONNECTS]->(r3) SET c2.length = 30.0\n" +
                           "MERGE (r3)-[c3:CONNECTS]->(r1) SET c3.length = 20.0\n"
                );

                String query = "match (r1:Road) WHERE r1.latitude = {lat} AND r1.longitude = {long}\n" +
                        "call roads.findRoute(r1, 20)\n" +
                        "yield path as pp\n" +
                        "return pp";
                Value params = parameters( "lat", 51.357397146246264, "long", -0.20153965352074504 );
                StatementResult result = session.run( query, params );

                assertTrue(result.hasNext());

                System.out.println( "result.peek() = " + result.peek() );
            }

            // When I use the index procedure to index a node

        }
    }
}
