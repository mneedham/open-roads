package com.markhneedham.open_roads;

import java.time.Clock;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Optional;
import java.util.stream.IntStream;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

import org.neo4j.graphalgo.GraphAlgoFactory;
import org.neo4j.graphalgo.PathFinder;
import org.neo4j.graphalgo.impl.path.ShortestPath;
import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Label;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Path;
import org.neo4j.graphdb.PropertyContainer;
import org.neo4j.graphdb.Relationship;
import org.neo4j.graphdb.RelationshipType;
import org.neo4j.graphdb.ResourceIterator;
import org.neo4j.graphdb.impl.OrderedByTypeExpander;
import org.neo4j.graphdb.impl.StandardExpander;
import org.neo4j.helpers.collection.Iterables;
import org.neo4j.helpers.collection.Pair;
import org.neo4j.helpers.collection.PrefetchingIterator;
import org.neo4j.procedure.Context;
import org.neo4j.procedure.Name;
import org.neo4j.procedure.Procedure;

import static java.util.stream.Collectors.toList;
import static java.util.stream.StreamSupport.stream;

import static org.neo4j.graphdb.Direction.BOTH;

public class RunFinder
{
    @Context
    public GraphDatabaseService db;


    public static class Hit
    {
        public List<Node> roads;
        public long distance;

        public Hit( long distance, Node... roads )
        {
            this.roads = Arrays.asList(roads);
            this.distance = distance;
        }
    }

    @Procedure(value = "roads.findMeARoute")
    public Stream<Hit> findMeARoute(
            @Name("start") Node start,
            @Name("midpoints") List<Node> midpoints,
            @Name("segmentId") String segmentId
    )
    {
        System.out.println( "start = " + start + ", midpoints = " + midpoints + ", segmentId = " + segmentId );
        StandardExpander orderedExpander = new OrderedByTypeExpander().add( RelationshipType.withName( "CONNECTS" ),
                BOTH );
        TimeConstrainedExpander expander = new TimeConstrainedExpander( orderedExpander, Clock.systemUTC(), 200 );
        List<Relationship> relationshipsSeenSoFar = new ArrayList<>();
        ShortestPath shortestUniquePathFinder = shortestPathFinder( relationshipsSeenSoFar, expander );

        List<Path> route = new ArrayList<>();
        List<Node> one;
        List<Node> two;

        List<Node> roads = new ArrayList<>();

        long distance = 0l;
        if ( !segmentId.isEmpty() )
        {
            Node segment = findSegment( segmentId );
            List<Node> roadsInSegment = findRoadsForSegment( segment );

            Node startOfSegment = roadsInSegment.get( 0 );
            Node endOfSegment = roadsInSegment.get( roadsInSegment.size() - 1 );

            Path path = shortestUniquePathFinder.findSinglePath( start, startOfSegment );
            if ( path == null )
            {
                return Stream.empty();
            }

            route.add( path );
            roads.addAll( Iterables.asList( path.nodes() ) );

            for ( Relationship relationship : path.relationships() )
            {
                relationshipsSeenSoFar.add( relationship );
                distance += Long.valueOf( relationship.getProperty( "length" ).toString() );
            }

            distance += Long.valueOf( segment.getProperty( "distance" ).toString() );
            roads.addAll( roadsInSegment );

            one = Stream.concat( Stream.of( endOfSegment ), midpoints.stream() ).collect( toList() );
            two = Stream.concat( midpoints.stream(), Stream.of( start ) ).collect( toList() );
        }
        else
        {
            one = Stream.concat( Stream.of( start ), midpoints.stream() ).collect( toList() );
            two = Stream.concat( midpoints.stream(), Stream.of( start ) ).collect( toList() );
        }

        List<Node> finalOne = one;
        List<Node> finalTwo = two;
        List<Pair<Node, Node>> pairs = IntStream.range( 0, Math.min( one.size(), two.size() ) )
                .mapToObj( index -> Pair.of( finalOne.get( index ), finalTwo.get( index ) ) )
                .collect( toList() );

        for ( Pair<Node, Node> pair : pairs )
        {
            Path path = shortestUniquePathFinder.findSinglePath( pair.first(), pair.other() );
            if ( path == null )
            {
                System.out.println( "route expanded = " + expander.pathsExpanded() );
                return Stream.empty();
            }
            route.add( path );
            roads.addAll(Iterables.asList(path.nodes()));

            for ( Relationship relationship : path.relationships() )
            {
                relationshipsSeenSoFar.add( relationship );
                distance += Long.valueOf( relationship.getProperty( "length" ).toString() );
            }
        }

        return Stream.of( new Hit( distance, roads.toArray( new Node[roads.size()] ) ) );
    }

    private List<Path> findPaths( StandardExpander orderedExpander, List<Node> roads )
    {
        List<Path> segmentPaths = new ArrayList<>();
        List<Node> two = roads.stream().skip( 1 ).collect( toList() );
        List<Node> one = roads.stream().limit( roads.size() - 1 ).collect( toList() );
        List<Pair<Node, Node>> pairs = IntStream.range( 0, Math.min( one.size(), two.size() ) )
                .mapToObj( index -> Pair.of( one.get( index ), two.get( index ) ) ).collect( toList() );
        PathFinder<Path> shortestPathFinder = GraphAlgoFactory.shortestPath( orderedExpander, 250 );
        for ( Pair<Node, Node> pair : pairs )
        {
            Path path = shortestPathFinder.findSinglePath( pair.first(), pair.other() );
            segmentPaths.add( path );
        }
        return segmentPaths;
    }

    private ShortestPath shortestPathFinder( List<Relationship> relationshipsSeenSoFar,
                                             TimeConstrainedExpander expander )
    {
        return new ShortestPath( Integer.MAX_VALUE, expander, path ->
                stream( path.relationships().spliterator(), false ).noneMatch( relationshipsSeenSoFar::contains ) );
    }


    private List<Node> findRoadsForSegment( Node segment )
    {
        List<Node> roads = new ArrayList<>();
        for ( String point : (String[]) segment.getProperty( "points" ) )
        {
            String[] parts = point.split( "," );
            Stream<Node> nodes = db.findNodes( Label.label( "Road" ), "latitude", Double.parseDouble( parts[0] ) )
                    .stream();
            Optional<Node> maybeRoad = nodes.filter( n -> n.getProperty( "longitude" ).equals( Double.parseDouble(
                    parts[1] ) ) ).findFirst();
            maybeRoad.ifPresent( roads::add );
        }
        return roads;
    }

    private Node findSegment( @Name("segmentId") String segmentId )
    {
        return db.findNode( Label.label( "Segment" ), "id", Integer.parseInt( segmentId ) );
    }

    static class CombinedPath implements Path
    {
        private final Path[] paths;

        CombinedPath( Path... paths )
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
                    .flatMap( p -> stream( p.relationships().spliterator(), false ) )
                    .collect( toList() );
        }

        @Override
        public Iterable<Relationship> reverseRelationships()
        {
            return Arrays.stream( paths )
                    .flatMap( p -> stream( p.relationships().spliterator(), false ) )
                    .sorted( Collections.reverseOrder() )
                    .collect( toList() );
        }

        @Override
        public Iterable<Node> nodes()
        {
            return Arrays.stream( paths )
                    .flatMap( p -> stream( p.nodes().spliterator(), false ) )
                    .collect( toList() );
        }

        @Override
        public Iterable<Node> reverseNodes()
        {
            return Arrays.stream( paths )
                    .flatMap( p -> stream( p.nodes().spliterator(), false ) )
                    .sorted( Collections.reverseOrder() )
                    .collect( toList() );
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
            Stream<PropertyContainer> combinedPaths = StreamSupport.stream( paths[0].spliterator(), false );

            for ( int i = 1; i < paths.length; i++ )
            {
                Path path = paths[i];
                Stream<PropertyContainer> thisPath = StreamSupport.stream( path.spliterator(), false ).skip( 1 );
                combinedPaths = Stream.concat( combinedPaths, thisPath );
            }

            return combinedPaths.iterator();
        }
    }

}
