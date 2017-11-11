package com.markhneedham.open_roads;

import java.time.Clock;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import java.util.stream.Stream;

import org.neo4j.graphalgo.GraphAlgoFactory;
import org.neo4j.graphalgo.PathFinder;
import org.neo4j.graphalgo.impl.path.ShortestPath;
import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Path;
import org.neo4j.graphdb.PropertyContainer;
import org.neo4j.graphdb.Relationship;
import org.neo4j.graphdb.RelationshipType;
import org.neo4j.graphdb.impl.OrderedByTypeExpander;
import org.neo4j.graphdb.impl.StandardExpander;
import org.neo4j.helpers.collection.Pair;
import org.neo4j.procedure.Context;
import org.neo4j.procedure.Name;
import org.neo4j.procedure.Procedure;

import static java.util.stream.StreamSupport.stream;

public class RunFinder
{
    @Context
    public GraphDatabaseService db;


    public static class Hit
    {
        public Path path;

        public Hit( Path... paths )
        {
            path = new CombinedPath( paths );
        }
    }

    @Procedure(value = "roads.findMeARoute")
    public Stream<Hit> findMeARoute(
            @Name("start") Node start,
            @Name("middle1") Node middle1,
            @Name("middle2") Node middle2

    )
    {
        System.out.println( "start = " + start + ", middle1 = " + middle1 + ", middle2 = " + middle2 );

        List<Relationship> relationshipsSeenSoFar = new ArrayList<>();

        StandardExpander orderedExpander = new OrderedByTypeExpander()
                .add( RelationshipType.withName( "CONNECTS" ), Direction.BOTH );

        TimeConstrainedExpander expander = new TimeConstrainedExpander(orderedExpander, Clock.systemUTC(), 200);

        PathFinder<Path> shortestPathFinder = GraphAlgoFactory.shortestPath( expander, 250 );
        // pass in a predicate which filters based on the result of the path from the previous path finders
        ShortestPath shortestUniquePathFinder = new ShortestPath( Integer.MAX_VALUE, expander, path -> {
            return stream( path.relationships().spliterator(), false ).noneMatch( relationshipsSeenSoFar::contains );
        });

        List<Node> midPoints = new ArrayList<>();
        midPoints.add(middle1);
        midPoints.add(middle2);

        Path startToMiddle1Path = shortestPathFinder.findSinglePath( start, midPoints.get(0) );

        if ( startToMiddle1Path == null )
        {
            System.out.println( "paths expanded = " + expander.pathsExpanded() );
            return Stream.empty(  );
        }

        for ( Relationship relationship : startToMiddle1Path.relationships() )
        {
            relationshipsSeenSoFar.add( relationship );
        }

        List<Node> one = Stream.of( middle1, middle2 ).collect( Collectors.toList() );
        List<Node> two = Stream.of( middle2, start ).collect( Collectors.toList() );

        List<Pair<Node, Node>> pairs = IntStream.range( 0, Math.min( one.size(), two.size() ) )
                .mapToObj( index -> Pair.of( one.get( index ), two.get( index ) ) ).collect( Collectors.toList() );

        List<Path> paths = new ArrayList<>();
        paths.add( startToMiddle1Path );
        for ( Pair<Node, Node> pair : pairs )
        {
            Path path = shortestUniquePathFinder.findSinglePath( pair.first(), pair.other() );
            if ( path == null )
            {
                System.out.println( "paths expanded = " + expander.pathsExpanded() );
                return Stream.empty(  );
            }
            paths.add(path);

            for ( Relationship relationship : path.relationships() )
            {
                relationshipsSeenSoFar.add( relationship );
            }
        }

        return Stream.of( new Hit(paths.toArray( new Path[paths.size()] )) );
    }

    static class CombinedPath implements  Path {

        private final Path[] paths;

        CombinedPath( Path... paths)
        {
            this.paths = paths;
        }

        @Override
        public Node startNode()
        {
            return paths[0].startNode();
        }

        @Override
        public Node endNode()
        {
            return this.paths[paths.length - 1].endNode();
        }

        @Override
        public Relationship lastRelationship()
        {
            return this.paths[paths.length - 1].lastRelationship();
        }

        @Override
        public Iterable<Relationship> relationships()
        {
            return Arrays.stream( paths )
                    .flatMap(p -> stream(p.relationships().spliterator(), false))
                    .collect( Collectors.toList() );
        }

        @Override
        public Iterable<Relationship> reverseRelationships()
        {
            return Arrays.stream( paths )
                    .flatMap(p -> stream(p.relationships().spliterator(), false))
                    .sorted(Collections.reverseOrder())
                    .collect( Collectors.toList() );
        }

        @Override
        public Iterable<Node> nodes()
        {
            return Arrays.stream( paths )
                    .flatMap(p -> stream(p.nodes().spliterator(), false))
                    .collect( Collectors.toList() );
        }

        @Override
        public Iterable<Node> reverseNodes()
        {
            return Arrays.stream( paths )
                    .flatMap(p -> stream(p.nodes().spliterator(), false))
                    .sorted(Collections.reverseOrder())
                    .collect( Collectors.toList() );
        }

        @Override
        public int length()
        {
            return Arrays.stream( paths )
                    .map( Path::length )
                    .reduce( ( length, acc ) -> acc + length )
                    .orElse( 0 );
        }

        @Override
        public Iterator<PropertyContainer> iterator()
        {
            throw new UnsupportedOperationException();
        }
    }

}
