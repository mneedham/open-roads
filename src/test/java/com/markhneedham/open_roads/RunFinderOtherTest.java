package com.markhneedham.open_roads;

import java.io.File;
import java.util.Map;

import org.junit.Test;

import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Result;
import org.neo4j.graphdb.factory.GraphDatabaseFactory;
import org.neo4j.kernel.impl.proc.Procedures;
import org.neo4j.kernel.internal.GraphDatabaseAPI;

public class RunFinderOtherTest
{
//    @Test
//    public void should() throws Exception
//    {
//        // given
//        File path = new File("/Users/markneedham/projects/open-roads/neo4j-community-3.2.5/data/databases/graph.db/" );
//        GraphDatabaseAPI db = (GraphDatabaseAPI) new GraphDatabaseFactory().newEmbeddedDatabase( path );
//        Procedures procedures = db.getDependencyResolver().resolveDependency( Procedures.class );
//
//        procedures.registerProcedure( RunFinder.class    );
//
//        Result result = db.execute( "match (start) where id(start) = 184709\n" +
//                "match (middle1) where id(middle1) = 187191\n" +
//                "match (middle2) where id(middle2) = 186990\n" +
//                "CALL roads.findMeARoute(start, middle1, middle2)\n" +
//                "YIELD startToMiddle1Path, middle1ToMiddle2Path, middle2ToStartPath\n" +
//                "WITH start, middle1, middle2,\n" +
//                "     nodes(startToMiddle1Path) + nodes(middle1ToMiddle2Path) + nodes(middle2ToStartPath) as roads,\n" +
//                "     relationships(startToMiddle1Path) + relationships(middle1ToMiddle2Path) + relationships" +
//                "(middle2ToStartPath) as connections\n" +
//                "return start {.latitude, .longitude}, middle1 {.latitude, .longitude}, middle2 {.latitude, " +
//                ".longitude}, roads,  reduce(acc=0, connection in connections | acc + connection.length ) AS " +
//                "distance\n" +
//                "LIMIT 1" );
//
//        System.out.println( "result = " + result );
//
//        while(result.hasNext()) {
//            Map<String, Object> row = result.next();
//            System.out.println(row);
//        }
//
//        db.shutdown();
//
//        // when
//
//        // then
//    }

    @Test
    public void should() throws Exception
    {
        // given
        File path = new File("/Users/markneedham/projects/open-roads/neo4j-community-3.2.5/data/databases/graph.db/" );
        GraphDatabaseAPI db = (GraphDatabaseAPI) new GraphDatabaseFactory().newEmbeddedDatabase( path );
        Procedures procedures = db.getDependencyResolver().resolveDependency( Procedures.class );

        procedures.registerProcedure( RunFinder.class    );

        long start = System.currentTimeMillis();
        Result result = db.execute( "match (start) where id(start) = 184709\n" +
                "match (middle1) where id(middle1) = 187191\n" +
                "match (middle2) where id(middle2) = 186990\n" +
                "CALL roads.findMeARoute2(start, middle1, middle2)\n" +
                "YIELD path\n" +
                "WITH start, middle1, middle2,\n" +
                "     nodes(path) as roads,\n" +
                "     relationships(path) as connections\n" +
                "return start {.latitude, .longitude}, middle1 {.latitude, .longitude}, middle2 {.latitude, " +
                ".longitude}, roads,  reduce(acc=0, connection in connections | acc + connection.length ) AS " +
                "distance\n" +
                "LIMIT 1" );

        System.out.println( "result = " + result );
        long end = System.currentTimeMillis();
        System.out.println( "duration =  " + (end - start) );

        while(result.hasNext()) {
            Map<String, Object> row = result.next();
            System.out.println(row);
        }

        db.shutdown();

        // when

        // then
    }
}
