/* global Graph:true, MinimapZoom:true,  DirectedAcyclicGraph:true, DirectedAcyclicGraphMinimap:true, getEntirePathLinks */
/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

(function(){
    /**
     * @class Zenoss.panel.TopologyPanel
     * @extends Ext.panel.Panel
     * @constructor
     * This panel uses d3, dagre and x-trace to render a graph display of nodes. This widget
     * makes the assumption that the JavaScript libraries are already included.
     */
    Ext.define('Zenoss.panel.TopologyPanel', {
        extend: 'Ext.Panel',
        alias: 'widget.topologypanel',
        /**
         * @cfg {Boolean} lightweight
         * If set to false then the lines will fade in instead of appearing when the nodes are rendered
         */
        lightweight: false,
        /**
         * @cfg {Object} graph
         * The nodes and edges from the X-Trace js library. This widget expects the nodes to
         * be added and set up correctly before rendering the graph.
         *
         * Each node is expected to have a property called "attrs" that is an object of properties of the node available in the template
         * An example usage would be
         * var graph = new Graph(),
         *     node1 = new Node("id1"),
         *     node2 = new Node("id2");
         * node1.addChild(node2);
         * Ext.create('Zenoss.panel.TopologyPanel', {
         *    graph: graph
         * });
         */
        graph: null,
        /**
         * @cfg {Boolean} includeMiniMap
         * set this to true to display a mini map in the lower right hand corner
         */
        includeMiniMap: true,
        /**
         * @cfg {Function} nodeTemplate
         * Template method where you fill in how the node will be rendered. Each node will be passed into
         * the method.
         */
        nodeTemplate: Ext.emptyFn,
        /**
         * @cfg {Function} updateNode
         * Template method where we update the node upon refresh
         */
        updateNode: Ext.emptyFn,
        /**
         * @cfg {Function} customLayout
         * This allows subclasses to specify their customize thier own layout of the nodes after dagree has ran.
         * The defined function will take two parameters
         *    1. nodes - a list of nodes
         *    2. edges - a list of edges
         * This is somewhat obtuse but the nodes are expected to have the x and y positions set on a dagre property
         * for each node
         */
        customLayout: null,
        /**
         *@cfg {string} d3interpolation
         * This is how we want d3 to interpolate the lines
         * Available options and what they mean:
         *     https://github.com/mbostock/d3/wiki/SVG-Shapes#line_interpolate
         **/
        d3interpolation: "basis",
        /**
         * @cfg {integer} nodewidth
         * specify how wide, in pixels, you want each node to be.
         */
        nodewidth: function() {
            return 60;
        },
        /**
         * @cfg {Function}
         * Override this method to determine how the edges should be rendered.
         * This will place a foreignObject in the exact middle of the line
         */
        edgeTemplate: Ext.emptyFn,
        destroyOldGraph: function(dom) {
            while (dom.firstChild) {
                dom.removeChild(dom.firstChild);
            }
        },
        /**
         * @cfg {Function} directFn
         * The router method that supplies the data for this control
         * The expected return is a list of nodes and edges.
         **/
        directFn: Ext.emptyFn,

        /**
         * Sets the context for this control, will call directFn
         **/
        setContext: function(uid) {
            this.uid = uid;
            this.isRefresh = false;
            this.update();
        },
        update: function() {
            this.directFn({
                uid: this.uid
            }, this.convertToDagre, this);
        },
        refresh: function() {
            this.isRefresh = true;
            this.update();
        },
        convertToDagre: function(response) {
            if (!response.success) {
                return;
            }

            var graph = new Graph();

            graph.edges = {};
            graph.getEdgeAttrs = function(d) {
                return this.edges[d.id];
            };
            // construct the graph
            var infos = response.data.nodes,
                // quick look up of nodes
                nodes = {},
                node,
                i,
                edge, el, view = this,
                edges = response.data.edges;
            el = view.body;

            if (el && el.isMasked()) {
                el.unmask();
            }

            // set up the nodes
            for (i=0; i<infos.length;i++) {
                node = new Node(infos[i].id);
                node.attrs = infos[i];
                nodes[infos[i].uid] = node;
                graph.addNode(node);
            }

            // set up the edges
            for (i=0;i<edges.length;i++) {
                edge = edges[i];
                nodes[edge.fromNode].addChild(nodes[edge.toNode]);
                graph.edges[nodes[edge.fromNode].id + nodes[edge.toNode].id] = edge;
            }

            // update the topology view
            if (this.isRefresh) {
                this.refreshTopologyView(graph);
            } else {
                this.setGraph(graph);
                this.renderTopologyView();
            }
        },
        setGraph: function(graph) {
            this.graph = graph;
        },
        getGraph: function() {
            return this.graph;
        },
        initComponent: function(){
            this.addEvents(
                /**
                 * @event nodeclicked
                 * Fires when the user clicks on an node
                 * @param {Node} d the node clicked on.
                 */
                'nodeclicked',
                /**
                 * @event edgeclicked
                 * Fires when the user clicks on an edge linking two nodes
                 * @param {Edge} d the edge clicked on.
                 */
                'edgeclicked');
            this.callParent(arguments);
        },
        refreshTopologyView: function(graph) {
            //TODO: reuse the edge reps instead of destroying and rebuilding them
            d3.selectAll(".edgeRep").remove();
            this.graph = graph;
            this.draw();
        },
        draw: function() {
            var start = (new Date()).getTime();
            this.graphSVG.datum(this.graph).call(this.DAG);    // Draw a DAG at the graph attach
            start = (new Date()).getTime();
            if (this.includeMiniMap) {
                this.minimapSVG.datum(this.graphSVG.node()).call(this.DAGMinimap);  // Draw a Minimap at the minimap attach
            }
            this.setupEvents();                      // Set up the node selection events
            start = (new Date()).getTime();
            this.refreshViewport();                  // Update the viewport settings
        },
        setupEvents: function(){
            var graphSVG = this.graphSVG,
                nodes = graphSVG.selectAll(".node"),
                edges = graphSVG.selectAll(".edge"),
                largeEdges = graphSVG.selectAll(".largeEdge"),
                edgeRep = graphSVG.selectAll(".edgeRep"),
                me = this;

            nodes.on("mouseover", function(d) {
                graphSVG.classed("hovering", true);
                edgeRep.style("opacity", ".2");
                highlightPath(d);
            }).on("mouseout", function(){
                graphSVG.classed("hovering", false);
                edges.classed("hovered", false).classed("immediate", false);
                nodes.classed("hovered", false).classed("immediate", false);
                edgeRep.style("opacity", "1");
            });

            edges.on("click", function(d){
                if (d3.event.defaultPrevented) {
                    return;
                }
                me.fireEvent('edgeclicked', me.graph.edges[d.id]);
            });
            largeEdges.on("click", function(d){
                if (d3.event.defaultPrevented) {
                    return;
                }
                me.fireEvent('edgeclicked', me.graph.edges[d.id]);
            });

            nodes.on("click", function(d){
                if (d3.event.defaultPrevented) {
                    return;
                }
                me.fireEvent('nodeclicked', d);
            });

            function highlightPath(center) {
                var path = getEntirePathLinks(center);

                var pathnodes = {};
                var pathlinks = {};
                var edgeRepIds = [];

                pathnodes[center.id]=true;
                path.forEach(function(p) {
                    pathnodes[p.source.id] = true;
                    pathnodes[p.target.id] = true;
                    pathlinks[p.id] = true;
                    edgeRepIds.push(p.id);
                });

                edges.classed("hovered", function(d) {
                    return pathlinks[d.id];
                });
                nodes.classed("hovered", function(d) {
                    return pathnodes[d.id];
                });

                Ext.each(edgeRepIds, function(id){
                    d3.select(Ext.String.format("g[id='{0}']", id)).style("opacity", "1");
                });
            }
        },
        refreshViewport: function() {
            var t = this.zoom.translate();
            var scale = this.zoom.scale();
            this.graphSVG.select(".graph").attr("transform","translate("+t[0]+","+t[1]+") scale("+scale+")");
            this.minimapSVG.select('.viewfinder')
                .attr("x", -t[0]/scale)
                .attr("y", -t[1]/scale)
                .attr("width", this.body.dom.offsetWidth/scale)
                .attr("height", this.body.dom.offsetHeight/scale);
            if (!this.lightweight) {
                this.graphSVG.selectAll(".node text").attr("opacity", 3*scale-0.3);
            }
        },
        resetViewport: function() {
            var dom = this.body.dom;
            var bbox = { x: this.originalBBox.x, y: this.originalBBox.y, width: this.originalBBox.width+450, height: this.originalBBox.height+250};
            var scale = Math.min(dom.offsetWidth/bbox.width, dom.offsetHeight/bbox.height);
            var extent = this.zoom.scaleExtent();
            scale = Math.max(extent[0], Math.min(scale, extent[1]));
            scale = 0.95;
            var w = dom.offsetWidth/scale;
            var h = dom.offsetHeight/scale;
            var tx = ((w - bbox.width)/4 - bbox.x + 25)*scale;
            var ty = ((h - bbox.height)/4 - bbox.y + 25)*scale;

            this.zoom.translate([tx, ty]).scale(scale);
            this.refreshViewport();
        },
        renderEdgeRepresentation: function(d) {
            var point = d.dagre.points[d.dagre.points.length /2];
            var group = d3.select(".graph").append("g").attr("class", "edgeRep").attr("id", d.id).attr("transform", Ext.String.format("translate({0}, {1})", point.x - 25, point.y - 30));
            this.edgeTemplate(group, d, point);
        },
        splineGenerator: function(d) {
            this.renderEdgeRepresentation(d);
            if (d.dagre.interpolate === false) {
                return d3.svg.line().x(function(d) { return d.x; })
                    .y(function(d) { return d.y;})
                (d.dagre.points);
            } else {
                // render the line
                return d3.svg.line().x(function(d) { return d.x; })
                    .y(function(d) { return d.y;})
                    .interpolate(d.dagre.type || this.d3interpolation)(d.dagre.points);
            }
        },
        renderTopologyView: function() {
            var graph = this.graph;
            var me = this;
            var dom = this.body.dom;
            this.destroyOldGraph(dom);
            var rootSVG = d3.select(dom).append("svg").attr("class", "graph-viewport").attr("width", "100%").attr("height", "100%");
            var graphSVG = rootSVG.append("svg").attr("width", "100%").attr("height", "100%").attr("class", "graph-attach");
            this.graphSVG = graphSVG;
            var DAG = new DirectedAcyclicGraph().animate(!this.lightweight).getedges(function (d) {
                var edges = [];
                d.getVisibleLinks().forEach(function (e) {
                    if (! e.source.hidingDescendants) {
                        edges.push(e);
                    }
                });
                return edges;
            }).d3interpolation(function() {
                return me.d3interpolation;
            }).nodewidth(this.nodewidth).nodeheight(this.nodeheight).edgepos(function(d){
                return d.dagre.points;
            });

            if (Ext.isFunction(this.customLayout)) {
                DAG.customlayout(Ext.bind(this.customLayout, this));
            }
            if (Ext.isFunction(this.splineGenerator)) {
                DAG.splineGenerator = Ext.bind(this.splineGenerator, this);
            }


            // setup local variables
            this.DAG = DAG;
            var minimapSVG = rootSVG.append("svg").attr("class", "minimap-attach");
            var DAGMinimap = new DirectedAcyclicGraphMinimap(DAG).width("19.5%").height("19.5%").x("80%").y("78%");

            var zoom = new MinimapZoom().scaleExtent([0.05, 2.0]).on("zoom", Ext.bind(this.refreshViewport, this));
            zoom.call(this, rootSVG, minimapSVG);
            this.zoom = zoom;
            this.minimapSVG = minimapSVG;
            this.DAGMinimap = DAGMinimap;

            DAG.updatenode(function(d){
                // remove the child dom elements
                me.updateNode(d3.select(this), d);
                // redraw the node
                DAG.drawnode(d);
            });
            DAG.drawnode(function(d) {

                // Attach box, the rx is how "rounded" the edges are
                d3.select(this).append("rect").attr("rx", 4).attr("stroke-width", "0");

                // Attach HTML body
                me.nodeTemplate(d3.select(this), d);


                var prior_pos = d.dagre;
                if (prior_pos!==null) {
                    d3.select(this).attr("transform", graph.nodeTranslate);
                }
            });

            this.originalBBox = graphSVG.node().getBBox();
            this.draw();
            this.resetViewport();
        }
    });

}());
