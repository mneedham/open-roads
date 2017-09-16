package com.markhneedham.open_roads;

import org.neo4j.graphdb.Node;
import org.neo4j.graphdb.Path;
import org.neo4j.graphdb.traversal.BranchState;
import org.neo4j.graphdb.traversal.Evaluation;
import org.neo4j.graphdb.traversal.PathEvaluator;

public class StopWhenEndNodeIsStartNode implements PathEvaluator
{
    private final Node startPoint;

    StopWhenEndNodeIsStartNode( Node startPoint )
    {
        this.startPoint = startPoint;
    }

    @Override
    public Evaluation evaluate( Path path, BranchState state )
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
