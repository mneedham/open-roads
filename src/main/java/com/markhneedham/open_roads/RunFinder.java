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
}
