package com.markhneedham.open_roads;

import java.util.Collections;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Path;
import org.neo4j.graphdb.RelationshipType;
import org.neo4j.graphdb.traversal.TraversalDescription;
import org.neo4j.graphdb.traversal.Traverser;
import org.neo4j.graphdb.traversal.Uniqueness;
import org.neo4j.procedure.Context;
import org.neo4j.procedure.Name;
import org.neo4j.procedure.Procedure;

public class RunFinder
{
    @Context
    public GraphDatabaseService db;

    @Procedure(value = "roads.findRoute")

    public Stream<SearchHit> findRoute(
            @Name("startPoint") Node startPoint,
            @Name(value = "minimumLength", defaultValue = "0") Long minimumLength )
    {
//        PathExpanderBuilder pathExpanderBuilder = PathExpanderBuilder.allTypes( Direction.BOTH );
//
//        PathFinder<Path> pathFinder = GraphAlgoFactory.<Path>allPaths( pathExpanderBuilder.build(), numberOfHops.intValue());
//
//
//        Iterable<Path> allPaths = pathFinder.findAllPaths( startPoint, startPoint );

//        return StreamSupport.stream( allPaths.spliterator(), false)
//                .filter( path ->
//                {
//                    Double totalDistance = StreamSupport.stream( path.relationships().spliterator(), false )
//                            .map( x -> (double) x.getProperty( "length" ) )
//                            .reduce( 0.0, ( acc, value ) -> acc + value );
//                    return totalDistance > minimumLength;
//                } )
//                .map( SearchHit::new );

        Uniqueness uniqueness = Uniqueness.RELATIONSHIP_PATH;
        boolean bfs = false;
        Iterable<Node> startNodes = Collections.singleton( startPoint );
        Traverser traverser = traverse( db.traversalDescription(), startNodes, uniqueness, bfs );
        return traverser.stream()
                .filter( path -> path.endNode().equals( startPoint ) )
                .filter( path ->
                {
                    Double totalDistance = StreamSupport.stream( path.relationships().spliterator(), false )
                            .map( x -> (double) x.getProperty( "length" ) )
                            .reduce( 0.0, ( acc, value ) -> acc + value );
                    return totalDistance > minimumLength;
                } )
                .map( SearchHit::new );
    }

    public static Traverser traverse( TraversalDescription traversalDescription, Iterable<Node> startNodes, Uniqueness uniqueness, boolean bfs ) {
        TraversalDescription td = traversalDescription;
        // based on the pathFilter definition now the possible relationships and directions must be shown

        td = bfs ? td.breadthFirst() : td.depthFirst();
        td = td.relationships( RelationshipType.withName( "CONNECTS" ), Direction.BOTH );
        td = td.uniqueness(uniqueness); // this is how Cypher works !! Uniqueness.RELATIONSHIP_PATH
        // uniqueness should be set as last on the TraversalDescription

        return td.traverse(startNodes);
    }

    public static class SearchHit
    {
        public Path path;

        public SearchHit( Path path )
        {
            this.path = path;
        }
    }
}
