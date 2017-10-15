package com.markhneedham.open_roads;

import java.time.Clock;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import org.neo4j.graphalgo.GraphAlgoFactory;
import org.neo4j.graphalgo.PathFinder;
import org.neo4j.graphalgo.impl.path.ShortestPath;
import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Path;
import org.neo4j.graphdb.PathExpander;
import org.neo4j.graphdb.PropertyContainer;
import org.neo4j.graphdb.Relationship;
import org.neo4j.graphdb.RelationshipType;
import org.neo4j.graphdb.impl.OrderedByTypeExpander;
import org.neo4j.graphdb.impl.StandardExpander;
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
        public Path startToMiddle1Path;
        public Path middle1ToMiddle2Path;
        public Path middle2ToStartPath;

        public Hit( Path startToMiddle1Path, Path middle1ToMiddle2Path, Path middle2ToStartPath )
        {
            this.startToMiddle1Path = startToMiddle1Path;
            this.middle1ToMiddle2Path = middle1ToMiddle2Path;
            this.middle2ToStartPath = middle2ToStartPath;
        }
    }

    public static class Hit2
    {
        public Path path;

        public Hit2( Path... paths )
        {
            path = new CombinedPath( paths );
        }
    }

    @Procedure(value = "roads.findMeARoute2")
    public Stream<Hit2> findMeARoute2(
            @Name("start") Node start,
            @Name("middle1") Node middle1,
            @Name("middle2") Node middle2

    )
    {
        System.out.println( "start = " + start + ", middle1 = " + middle1 + ", middle2 = " + middle2 );

        /*
        Cul de sacs break this at the moment
        match (start)   where id(start)   = 184709
        match (middle1) where id(middle1) = 184763
        match (middle2) where id(middle2) = 184846
         */

        List<Relationship> relationshipsSeenSoFar = new ArrayList<>();

        StandardExpander orderedExpander = new OrderedByTypeExpander().add( RelationshipType.withName( "CONNECTS" ), Direction.BOTH );

        MyStandardExpander expander = new MyStandardExpander(orderedExpander, Clock.systemUTC());

        PathFinder<Path> shortestPathFinder = GraphAlgoFactory.shortestPath( expander, 250 );
        // pass in a predicate which filters based on the result of the path from the previous path finders
        ShortestPath shortestUniquePathFinder = new ShortestPath( Integer.MAX_VALUE, expander, path -> {
            return stream( path.relationships().spliterator(), false ).noneMatch( relationshipsSeenSoFar::contains );
        });

        Path startToMiddle1Path = shortestPathFinder.findSinglePath( start, middle1 );

        if ( startToMiddle1Path == null )
        {
            System.out.println( "paths expanded = " + expander.pathsExpanded() );
            return Stream.empty(  );
        }

        for ( Relationship relationship : startToMiddle1Path.relationships() )
        {
            relationshipsSeenSoFar.add( relationship );
        }

        Path middle1ToMiddle2Path = shortestUniquePathFinder.findSinglePath( middle1, middle2 );

        if ( middle1ToMiddle2Path == null )
        {
            System.out.println( "paths expanded = " + expander.pathsExpanded() );
            return Stream.empty(  );
        }

            for ( Relationship relationship : middle1ToMiddle2Path.relationships() )
            {
                relationshipsSeenSoFar.add( relationship );
            }

        Path middle2ToStartPath = shortestUniquePathFinder.findSinglePath( middle2, start );

        if ( middle2ToStartPath == null )
        {
            System.out.println( "paths expanded = " + expander.pathsExpanded() );
            return Stream.empty(  );
        }

        System.out.println( "paths expanded = " + expander.pathsExpanded() );
        return Stream.of( new Hit2(startToMiddle1Path, middle1ToMiddle2Path, middle2ToStartPath) );
    }

    @Procedure(value = "roads.findMeARoute")
    public Stream<Hit> findMeARoute(
            @Name("start") Node start,
            @Name("middle1") Node middle1,
            @Name("middle2") Node middle2

    )
    {
        System.out.println( "start = " + start + ", middle1 = " + middle1 + ", middle2 = " + middle2 );

        /*
        Cul de sacs break this at the moment
        match (start)   where id(start)   = 184709
        match (middle1) where id(middle1) = 184763
        match (middle2) where id(middle2) = 184846
         */

        List<Relationship> relationshipsSeenSoFar = new ArrayList<>();

        StandardExpander expander = new OrderedByTypeExpander().add( RelationshipType.withName( "CONNECTS" ), Direction.BOTH );


        PathFinder<Path> shortestPathFinder = GraphAlgoFactory.shortestPath( expander, 250 );
        // pass in a predicate which filters based on the result of the path from the previous path finders
        ShortestPath shortestUniquePathFinder = new ShortestPath( Integer.MAX_VALUE, expander, path -> {
            return stream( path.relationships().spliterator(), false ).noneMatch( relationshipsSeenSoFar::contains );
        });

        Path startToMiddle1Path = shortestPathFinder.findSinglePath( start, middle1 );

        for ( Relationship relationship : startToMiddle1Path.relationships() )
        {
            relationshipsSeenSoFar.add( relationship );
        }

        Path middle1ToMiddle2Path = shortestUniquePathFinder.findSinglePath( middle1, middle2 );

        if ( middle1ToMiddle2Path != null )
        {
            for ( Relationship relationship : middle1ToMiddle2Path.relationships() )
            {
                relationshipsSeenSoFar.add( relationship );
            }
        }

        Path middle2ToStartPath = shortestUniquePathFinder.findSinglePath( middle2, start );

        return Stream.of( new Hit(startToMiddle1Path, middle1ToMiddle2Path, middle2ToStartPath) );
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
