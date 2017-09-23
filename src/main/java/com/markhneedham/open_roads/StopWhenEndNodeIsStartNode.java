package com.markhneedham.open_roads;

import org.neo4j.graphalgo.impl.util.DoubleEvaluator;
import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Path;
import org.neo4j.graphdb.traversal.BranchState;
import org.neo4j.graphdb.traversal.Evaluation;
import org.neo4j.graphdb.traversal.PathEvaluator;

import static org.neo4j.graphdb.Direction.OUTGOING;

public class StopWhenEndNodeIsStartNode implements PathEvaluator<Double>
{
    private final Node startPoint;
    private final DoubleEvaluator distanceEvaluator;

    StopWhenEndNodeIsStartNode( Node startPoint, DoubleEvaluator distanceEvaluator )
    {
        this.startPoint = startPoint;
        this.distanceEvaluator = distanceEvaluator;
    }

    @Override
    public Evaluation evaluate( Path path, BranchState<Double> state )
    {
        double nextState = state.getState();
//        System.out.println( "nextState = " + nextState + ", path = " + path );
        if ( path.length() > 0 )
        {
            nextState += distanceEvaluator.getCost( path.lastRelationship(), OUTGOING );
            state.setState( nextState );
        }

        if ( everythingIsMe( path ) )
        {
            return Evaluation.EXCLUDE_AND_CONTINUE;
        }

        if ( path.endNode().equals( startPoint ) )
        {
            return Evaluation.INCLUDE_AND_PRUNE;
        }
        else
        {
            return Evaluation.EXCLUDE_AND_CONTINUE;
        }
    }

    @Override
    public Evaluation evaluate( Path path )
    {
        if ( everythingIsMe( path ) )
        {
            return Evaluation.EXCLUDE_AND_CONTINUE;
        }

        if ( path.endNode().equals( startPoint ) )
        {
            return Evaluation.INCLUDE_AND_PRUNE;
        }
        else
        {
            return Evaluation.EXCLUDE_AND_CONTINUE;
        }
    }

    private boolean everythingIsMe( Path path )
    {
        return path.length() == 0 && path.startNode().equals( startPoint ) && path.endNode().equals( startPoint );
    }
}
