package com.markhneedham.open_roads;

import java.util.Collections;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

import org.neo4j.graphalgo.WeightedPath;
import org.neo4j.graphalgo.impl.path.AStar;
import org.neo4j.graphalgo.impl.util.DoubleEvaluator;
import org.neo4j.graphalgo.impl.util.WeightedPathImpl;
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
            @Name(value = "minimumLength", defaultValue = "0") Long minimumLength,
            @Name(value = "breadthFirst", defaultValue = "true") boolean bfs)
    {
        Uniqueness uniqueness = Uniqueness.RELATIONSHIP_PATH;
//        boolean bfs = true;
        Traverser traverser = traverse( db.traversalDescription(), startPoint, uniqueness, bfs, minimumLength );
        return traverser.stream()
//                .filter( path -> {
//                    System.out.println( "filter: path = " + path );
//                    return path.endNode().equals( startPoint );
//                } )
                .filter( path ->
                {
                    Double totalDistance = calculateDistance( path );
                    System.out.println( "totalDistance = " + totalDistance );
                    return totalDistance > minimumLength;
                } )
                .map( path -> {
                    Double totalDistance = calculateDistance( path );
                    return new SearchHit( new WeightedPathImpl( totalDistance, path ) );
                } );
    }

    private Double calculateDistance( Path path )
    {
        DoubleEvaluator doubleEvaluator = new DoubleEvaluator( "length" );
        return StreamSupport.stream( path.relationships().spliterator(), false )
                .map( x -> doubleEvaluator.getCost( x, Direction.BOTH ) )
                .reduce( 0.0, ( acc, value ) -> acc + value );
    }

    private static Traverser traverse( TraversalDescription traversalDescription, Node startPoint,
                                       Uniqueness uniqueness, boolean bfs, Long minimumLength ) {
        TraversalDescription td = traversalDescription;
        // based on the pathFilter definition now the possible relationships and directions must be shown

        td = bfs ? td.breadthFirst() : td.depthFirst();
        td = td.relationships( RelationshipType.withName( "CONNECTS" ), Direction.BOTH );

        td = td.evaluator( new StopWhenEndNodeIsStartNode(startPoint ) );

        td = td.uniqueness(uniqueness); // this is how Cypher works !! Uniqueness.RELATIONSHIP_PATH
        // uniqueness should be set as last on the TraversalDescription

        return td.traverse(Collections.singletonList(  startPoint));
    }

    public static class SearchHit
    {
        public Path path;
        public Double weight;

        public SearchHit( WeightedPath path )
        {
            this.path = path;
            this.weight = path.weight();
        }
    }
}
