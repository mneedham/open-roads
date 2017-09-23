package com.markhneedham.open_roads;

import java.util.Collections;
import java.util.Comparator;
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

import org.neo4j.graphalgo.CommonEvaluators;
import org.neo4j.graphalgo.EstimateEvaluator;
import org.neo4j.graphalgo.WeightedPath;
import org.neo4j.graphalgo.impl.util.DoubleEvaluator;
import org.neo4j.graphalgo.impl.util.PathInterestFactory;
import org.neo4j.graphalgo.impl.util.PriorityMap;
import org.neo4j.graphalgo.impl.util.WeightedPathImpl;
import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.GraphDatabaseService;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Path;
import org.neo4j.graphdb.PathExpander;
import org.neo4j.graphdb.PathExpanderBuilder;
import org.neo4j.graphdb.RelationshipType;
import org.neo4j.graphdb.traversal.BranchOrderingPolicies;
import org.neo4j.graphdb.traversal.BranchOrderingPolicy;
import org.neo4j.graphdb.traversal.BranchSelector;
import org.neo4j.graphdb.traversal.InitialBranchState;
import org.neo4j.graphdb.traversal.TraversalBranch;
import org.neo4j.graphdb.traversal.TraversalContext;
import org.neo4j.graphdb.traversal.TraversalDescription;
import org.neo4j.graphdb.traversal.Traverser;
import org.neo4j.graphdb.traversal.Uniqueness;
import org.neo4j.kernel.impl.util.NoneStrictMath;
import org.neo4j.procedure.Context;
import org.neo4j.procedure.Name;
import org.neo4j.procedure.Procedure;

import static org.neo4j.graphalgo.impl.util.BestFirstSelectorFactory.CONVERTER;

public class RunFinder
{
    @Context
    public GraphDatabaseService db;

    @Procedure(value = "roads.findRoute")

    public Stream<SearchHit> findRoute(
            @Name("startPoint") Node startPoint,
            @Name(value = "minimumLength", defaultValue = "0") Long minimumLength,
            @Name(value = "breadthFirst", defaultValue = "true") boolean bfs )
    {
        Uniqueness uniqueness = Uniqueness.RELATIONSHIP_PATH;
//        boolean bfs = true;
        DoubleEvaluator distanceEvaluator = new DoubleEvaluator( "length" );
        Traverser traverser = traverse( db.traversalDescription(), startPoint, uniqueness, bfs, minimumLength,
                distanceEvaluator );
        return traverser.stream()
//                .filter( path -> {
//                    System.out.println( "filter: path = " + path );
//                    return path.endNode().equals( startPoint );
//                } )
                .filter( path ->
                {
                    Double totalDistance = calculateDistance( path, distanceEvaluator );
//                    System.out.println( "totalDistance = " + totalDistance );
                    return totalDistance > minimumLength;
                } )
                .map( path ->
                {
                    Double totalDistance = calculateDistance( path, distanceEvaluator );
                    return new SearchHit( new WeightedPathImpl( totalDistance, path ) );
                } );
    }

    static Double calculateDistance( Path path, DoubleEvaluator doubleEvaluator )
    {
        return StreamSupport.stream( path.relationships().spliterator(), false )
                .map( x -> doubleEvaluator.getCost( x, Direction.BOTH ) )
                .reduce( 0.0, ( acc, value ) -> acc + value );
    }

    private static Traverser traverse( TraversalDescription traversalDescription, Node startPoint,
                                       Uniqueness uniqueness, boolean bfs, Long minimumLength,
                                       DoubleEvaluator distanceEvaluator )
    {
        TraversalDescription td = traversalDescription;
        // based on the pathFilter definition now the possible relationships and directions must be shown

//        td = bfs ? td.breadthFirst() : td.depthFirst();

        td = td.order( new BranchOrderingPolicy()
        {
            @Override
            public BranchSelector create( TraversalBranch startBranch, PathExpander expander )
            {
                return new DepthThenBreadthFirstBranchSelector( startBranch, expander, minimumLength, distanceEvaluator, startPoint );
            }
        } );

        PathExpanderBuilder builder = PathExpanderBuilder.empty();
        builder.add( RelationshipType.withName( "CONNECTS" ), Direction.BOTH );
        td = td.expand( builder.build(), InitialBranchState.DOUBLE_ZERO );

        td = td.relationships( RelationshipType.withName( "CONNECTS" ), Direction.BOTH );

        td = td.evaluator( new StopWhenEndNodeIsStartNode( startPoint, distanceEvaluator ) );

        td = td.uniqueness( uniqueness ); // this is how Cypher works !! Uniqueness.RELATIONSHIP_PATH
        // uniqueness should be set as last on the TraversalDescription

        return td.traverse( Collections.singletonList( startPoint ) );
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

    static class DepthThenBreadthFirstBranchSelector implements BranchSelector
    {
        private final PathExpander expander;
        private double distanceToChangeStrategy;
        private final Node destination;
        private double distanceSoFar = 0.0;
        private TraversalBranch current;
        private final DoubleEvaluator distanceEvaluator;
        private final EstimateEvaluator<Double> estimateEvaluator;

        private final PriorityMap<TraversalBranch, Node, Double> queue = new PriorityMap<>( CONVERTER,
                new Comparator<Double>()
                {
                    @Override
                    public int compare( Double x, Double y )
                    {
                        return NoneStrictMath.compare( x*-1, y*-1, NoneStrictMath.EPSILON );
                    }
                },
//                PathInterestFactory.allShortest( NoneStrictMath.EPSILON ).comparator(),
                false );

        DepthThenBreadthFirstBranchSelector( TraversalBranch source, PathExpander expander, double totalDistance,
                                             DoubleEvaluator distanceEvaluator, Node destination )
        {
            this.current = source;
            this.expander = expander;
            this.distanceEvaluator = distanceEvaluator;
            this.distanceToChangeStrategy = totalDistance - (0.1 * totalDistance);
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
                queue.put( next, cost );
            }

//            do
//            {
            PriorityMap.Entry<TraversalBranch, Double> entry = queue.pop();
            if ( entry != null )
            {
                System.out.println( "entry = " + entry.getEntity() + ", priority = " + entry.getPriority() );
                current = entry.getEntity();
                return current;
            }
            else
            {
                return null;
            }
//            } while ( true );
        }
    }
}
