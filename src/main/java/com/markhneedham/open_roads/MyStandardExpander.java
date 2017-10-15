package com.markhneedham.open_roads;

import java.time.Clock;
import java.util.Collections;

import org.neo4j.graphdb.Direction;
import org.neo4j.graphdb.Path;
import org.neo4j.graphdb.PathExpander;
import org.neo4j.graphdb.Relationship;
import org.neo4j.graphdb.RelationshipType;
import org.neo4j.graphdb.impl.OrderedByTypeExpander;
import org.neo4j.graphdb.impl.StandardExpander;
import org.neo4j.graphdb.traversal.BranchState;

public class MyStandardExpander implements PathExpander
{
    private final StandardExpander expander;
    private final long startTime;
    private final Clock clock;
    private int pathsExpanded = 0;

    public MyStandardExpander( StandardExpander expander, Clock clock )
    {
        this.expander = expander;
        this.clock = clock;
        this.startTime = clock.instant().toEpochMilli();
    }

    @Override
    public Iterable<Relationship> expand( Path path, BranchState state )
    {
        long timeSoFar = clock.instant().toEpochMilli() - startTime;
        if ( timeSoFar > 200 )
        {
//            System.out.println( "timeSoFar = " + timeSoFar );
            return Collections.emptyList();
        }

        pathsExpanded++;
        return expander.expand( path, state );
    }

    public int pathsExpanded()
    {
        return pathsExpanded;
    }

    @Override
    public PathExpander reverse()
    {
        return expander.reverse();
    }
}
