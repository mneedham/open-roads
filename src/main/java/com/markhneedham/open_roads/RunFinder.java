package com.markhneedham.open_roads;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

import org.neo4j.cypher.internal.frontend.v2_3.ast.functions.Labels;
import org.neo4j.graphalgo.CommonEvaluators;
import org.neo4j.graphalgo.EstimateEvaluator;
import org.neo4j.graphalgo.GraphAlgoFactory;
import org.neo4j.graphalgo.PathFinder;
import org.neo4j.graphalgo.WeightedPath;
import org.neo4j.graphalgo.impl.path.ShortestPath;
import org.neo4j.graphalgo.impl.util.DoubleEvaluator;
import org.neo4j.graphalgo.impl.util.PriorityMap;
import org.neo4j.graphalgo.impl.util.WeightedPathImpl;
import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Label;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Path;
import org.neo4j.graphdb.PathExpander;
import org.neo4j.graphdb.PropertyContainer;
import org.neo4j.graphdb.Relationship;
import org.neo4j.graphdb.RelationshipType;
import org.neo4j.graphdb.Transaction;
import org.neo4j.graphdb.impl.OrderedByTypeExpander;
import org.neo4j.graphdb.impl.StandardExpander;
import org.neo4j.graphdb.traversal.BranchSelector;
import org.neo4j.graphdb.traversal.TraversalBranch;
import org.neo4j.graphdb.traversal.TraversalContext;
import org.neo4j.graphdb.traversal.TraversalDescription;
import org.neo4j.graphdb.traversal.Traverser;
import org.neo4j.graphdb.traversal.Uniqueness;
import org.neo4j.helpers.collection.Iterables;
import org.neo4j.kernel.api.KernelTransaction;
import org.neo4j.kernel.impl.coreapi.PlaceboTransaction;
import org.neo4j.kernel.impl.coreapi.TopLevelTransaction;
import org.neo4j.kernel.impl.factory.GraphDatabaseFacade;
import org.neo4j.kernel.impl.util.NoneStrictMath;
import org.neo4j.procedure.Context;
import org.neo4j.procedure.Name;
import org.neo4j.procedure.Procedure;

import static java.util.stream.Collectors.toList;

import static org.neo4j.graphalgo.impl.util.BestFirstSelectorFactory.CONVERTER;
import static org.neo4j.kernel.api.security.SecurityContext.AUTH_DISABLED;

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

    @Procedure(value = "roads.findMeARoute")
    public Stream<Hit> findMeARoute(
            @Name("start") Node start,
            @Name("middle1") Node middle1,
            @Name("middle2") Node middle2

    )
    {
        System.out.println( "start = " + start + ", middle1 = " + middle1 + ", middle2 = " + middle2 );

        List<Relationship> relationshipsSeenSoFar = new ArrayList<>();

        StandardExpander expander = new OrderedByTypeExpander().add( RelationshipType.withName( "CONNECTS" ), Direction.BOTH );
        PathFinder<Path> shortestPathFinder = GraphAlgoFactory.shortestPath( expander, 250 );
        // pass in a predicate which filters based on the result of the path from the previous path finders
        ShortestPath shortestUniquePathFinder = new ShortestPath( Integer.MAX_VALUE, expander, path -> {
            return StreamSupport.stream( path.relationships().spliterator(), false ).noneMatch( relationshipsSeenSoFar::contains );
        });

        Path startToMiddle1Path = shortestPathFinder.findSinglePath( start, middle1 );

        for ( Relationship relationship : startToMiddle1Path.relationships() )
        {
            relationshipsSeenSoFar.add( relationship );
        }

        Path middle1ToMiddle2Path = shortestUniquePathFinder.findSinglePath( middle1, middle2 );

        for ( Relationship relationship : middle1ToMiddle2Path.relationships() )
        {
            relationshipsSeenSoFar.add( relationship );
        }

        Path middle2ToStartPath = shortestUniquePathFinder.findSinglePath( middle2, start );

        return Stream.of( new Hit(startToMiddle1Path, middle1ToMiddle2Path, middle2ToStartPath) );

    }

    @Procedure(value = "roads.findRoute")
    public Stream<SearchHit> findRoute(
            @Name("startPoint") Node startPoint,
            @Name(value = "minimumLength", defaultValue = "0") Long minimumLength,
            @Name(value = "breadthFirst", defaultValue = "true") boolean bfs )
    {
        AtomicInteger pathsAnalysed = new AtomicInteger( 0 );

        Uniqueness uniqueness = Uniqueness.RELATIONSHIP_PATH;
        DoubleEvaluator distanceEvaluator = new DoubleEvaluator( "length" );
        Traverser traverser = traverse( db.traversalDescription(), startPoint, uniqueness, bfs, minimumLength,
                distanceEvaluator, pathsAnalysed );

        return traverser.stream().filter( path ->
        {
            Double totalDistance = calculateDistance( distanceEvaluator, path.relationships() );
            return totalDistance > minimumLength;
        } ).map( path ->
        {
            Double totalDistance = calculateDistance( distanceEvaluator, path.relationships() );
            return new SearchHit( new WeightedPathImpl( totalDistance, path ), pathsAnalysed.get() );
        } );
    }

    static Double calculateDistance( DoubleEvaluator doubleEvaluator, Iterable<Relationship> relationships )
    {
        return StreamSupport.stream( relationships.spliterator(), false )
                .map( x -> doubleEvaluator.getCost( x, Direction.BOTH ) )
                .reduce( 0.0, ( acc, value ) -> acc + value );
    }

    private static Traverser traverse( TraversalDescription traversalDescription, Node startPoint,
                                       Uniqueness uniqueness, boolean bfs, Long minimumLength,
                                       DoubleEvaluator distanceEvaluator, AtomicInteger pathsAnalysed )
    {
        TraversalDescription td = traversalDescription;
        // based on the pathFilter definition now the possible relationships and directions must be shown

        td = bfs ? td.breadthFirst() : td.depthFirst();

//        td = td.order( new BranchOrderingPolicy()
//        {
//            @Override
//            public BranchSelector create( TraversalBranch startBranch, PathExpander expander )
//            {
////                return new DepthThenBreadthFirstBranchSelector( startBranch, expander, minimumLength,
////                        distanceEvaluator, startPoint );
//                return new DepthFirstSelector(startBranch, expander, distanceEvaluator);
//            }
//        } );

//        PathExpanderBuilder builder = PathExpanderBuilder.empty();
//        builder.add( RelationshipType.withName( "CONNECTS" ), Direction.BOTH );
//        td = td.expand( builder.build(), InitialBranchState.DOUBLE_ZERO );

        td = td.relationships( RelationshipType.withName( "CONNECTS" ), Direction.BOTH );

        td = td.evaluator( new StopWhenEndNodeIsStartNode( startPoint, distanceEvaluator, minimumLength, pathsAnalysed ) );

        td = td.uniqueness( uniqueness ); // this is how Cypher works !! Uniqueness.RELATIONSHIP_PATH
        // uniqueness should be set as last on the TraversalDescription

        return td.traverse( Collections.singletonList( startPoint ) );
    }

    public static class SearchHit
    {
        public Path path;
        public Double weight;
        public long pathsAnalysed;

        public SearchHit( WeightedPath path, int pathsAnalysed )
        {
            this.path = path;
            this.weight = path.weight();
            this.pathsAnalysed = pathsAnalysed;
        }
    }

    static class DepthFirstSelector implements BranchSelector
    {
        private TraversalBranch current;
        private final PathExpander expander;
        private DoubleEvaluator distanceEvaluator;

        DepthFirstSelector( TraversalBranch startSource, PathExpander expander, DoubleEvaluator distanceEvaluator )
        {
            this.current = startSource;
            this.expander = expander;
            this.distanceEvaluator = distanceEvaluator;
        }

        @Override
        public TraversalBranch next( TraversalContext metadata )
        {
            TraversalBranch result = null;
            while ( result == null )
            {
                if ( current == null )
                {
                    return null;
                }
                TraversalBranch next = current.next( expander, metadata );
                if ( next == null )
                {
                    current = current.parent();
                    continue;
                }
                current = next;
                result = current;
            }

            Double distanceSoFar = calculateDistance( distanceEvaluator, result.relationships() );
            System.out.println( "distanceSoFar = " + distanceSoFar + ", result = " + result );

            return result;
        }
    }

    static class DepthThenBreadthFirstBranchSelector implements BranchSelector
    {
        private final PathExpander expander;
        private double distanceToChangeStrategy;
        private final Node destination;
        private double distanceSoFar = 0.0;
        private TraversalBranch current;
        private final DoubleEvaluator distanceEvaluator;
        private final EstimateEvaluator<Double> estimateEvaluator;
        private boolean overHalfWay = false;

        private final PriorityMap<TraversalBranch, Node, Double> farAwayQueue = new PriorityMap<>( CONVERTER,
                ( x, y ) -> NoneStrictMath.compare( x * -1, y * -1, NoneStrictMath.EPSILON ), false );

        private final PriorityMap<TraversalBranch, Node, Double> nearByQueue = new PriorityMap<>( CONVERTER,
                ( x, y ) -> NoneStrictMath.compare( x, y, NoneStrictMath.EPSILON ), false );

        DepthThenBreadthFirstBranchSelector( TraversalBranch source, PathExpander expander, double totalDistance,
                                             DoubleEvaluator distanceEvaluator, Node destination )
        {
            this.current = source;
            this.expander = expander;
            this.distanceEvaluator = distanceEvaluator;
            this.distanceToChangeStrategy = totalDistance - (0.5 * totalDistance);
            this.destination = destination;
            estimateEvaluator = CommonEvaluators.geoEstimateEvaluator( "latitude", "longitude" );
        }

        @Override
        public TraversalBranch next( TraversalContext metadata )
        {
            while ( true )
            {
                TraversalBranch next = current.next( expander, metadata );
//                System.out.println( "result = " + next );
                if ( next == null )
                {
                    break;
                }

                Double cost = estimateEvaluator.getCost( next.endNode(), destination );
                farAwayQueue.put( next, cost );
                nearByQueue.put( next, cost );
            }

            if ( !overHalfWay )
            {
                PriorityMap.Entry<TraversalBranch, Double> entry = farAwayQueue.pop();

                if ( entry != null )
                {
                    current = entry.getEntity();

                    Double distanceSoFar = calculateDistance( distanceEvaluator, entry.getEntity().relationships() );

                    if ( distanceSoFar > distanceToChangeStrategy )
                    {
                        overHalfWay = true;
                    }

                    return current;
                }
                else
                {
                    return null;
                }
            }
            else
            {
                PriorityMap.Entry<TraversalBranch, Double> entry = nearByQueue.pop();

                if ( entry != null )
                {
                    current = entry.getEntity();
                    return current;
                }
                else
                {
                    return null;
                }
            }

        }
    }
}
