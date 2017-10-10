package com.markhneedham.open_roads;

import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.StreamSupport;

import org.neo4j.graphalgo.impl.util.DoubleEvaluator;
import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Path;
import org.neo4j.graphdb.Relationship;
import org.neo4j.graphdb.traversal.BranchState;
import org.neo4j.graphdb.traversal.Evaluation;
import org.neo4j.graphdb.traversal.PathEvaluator;

public class StopWhenEndNodeIsStartNode implements PathEvaluator<Double>
{
    private final Node startPoint;
    private final DoubleEvaluator distanceEvaluator;
    private final Long minimumLength;
    private final AtomicInteger pathsAnalysed;

    StopWhenEndNodeIsStartNode( Node startPoint, DoubleEvaluator distanceEvaluator, Long minimumLength, AtomicInteger pathsAnalysed )
    {
        this.startPoint = startPoint;
        this.distanceEvaluator = distanceEvaluator;
        this.minimumLength = minimumLength;
        this.pathsAnalysed = pathsAnalysed;
    }

    private double calculateDistance( DoubleEvaluator distanceEvaluator, Iterable<Relationship> relationships )
    {
        return StreamSupport.stream( relationships.spliterator(), false )
                .map( x -> distanceEvaluator.getCost( x, Direction.BOTH ) )
                .reduce( 0.0, ( acc, value ) -> acc + value );
    }

    @Override
    public Evaluation evaluate( Path path, BranchState<Double> state )
    {
        return evaluate( path );
    }

    @Override
    public Evaluation evaluate( Path path )
    {
        pathsAnalysed.incrementAndGet();
        if ( everythingIsMe( path ) )
        {
            return Evaluation.EXCLUDE_AND_CONTINUE;
        }

        double distanceSoFar = calculateDistance( distanceEvaluator, path.relationships() );
        System.out.println( "distanceSoFar = " + distanceSoFar );
        if ( distanceSoFar > (minimumLength + (minimumLength * 0.1)) )
        {
            if ( path.endNode().equals( startPoint ) )
            {
                return Evaluation.INCLUDE_AND_PRUNE;
            }
            else
            {
                return Evaluation.EXCLUDE_AND_PRUNE;
            }
        }
        else
        {
            if ( path.endNode().equals( startPoint ) )
            {
                return Evaluation.INCLUDE_AND_PRUNE;
            }
            else
            {
                return Evaluation.EXCLUDE_AND_CONTINUE;
            }
        }
    }

    private boolean everythingIsMe( Path path )
    {
        return path.length() == 0 && path.startNode().equals( startPoint ) && path.endNode().equals( startPoint );
    }
}
