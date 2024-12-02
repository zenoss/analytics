/*
 * This file contains the prototypes for Graph and Node
 */

var Edge = function(source, target) {
    this.id = source.id + target.id;

    this.source = source;
    this.target = target;
}

var Node = function(id) {
    // Save the arguments
    this.id = id;
    
    // Default values for internal variables
    this.never_visible        = false;
    this.hidden               = false;
    this.source_edges         = {}; // edges for which this node is a source
    this.target_edges         = {}; // edges for which this node is a target
}

Node.prototype.visible = function(_) {
    if (arguments.length==0) return (!this.never_visible && !this.hidden)
    this.hidden = !_;
    return this;
}

Node.prototype.addChild = function(child) {
    var edge = new Edge(this, child);
    this.source_edges[child.id] = edge;
    child.target_edges[this.id] = edge;
}

Node.prototype.getParents = function() {
    return values(this.target_edges).map(function (d) { return d.source})
}

Node.prototype.getChildren = function() {
    return values(this.source_edges).map(function(d) { return d.target})
}

var Graph = function() {
    // Default values for internal variables
    this.nodelist = []
    this.nodes = {};
}

Graph.prototype.addNode = function(node) {
    this.nodelist.push(node);
    this.nodes[node.id] = node;
}

Graph.prototype.getNode = function(id) {
    return this.nodes[id];
}

Graph.prototype.getNodes = function() {
    return this.nodelist;
}

Graph.prototype.getVisibleNodes = function() {
    return this.nodelist.filter(function(node) { return node.visible(); });
}

Graph.prototype.getVisibleLinks = function() {
    var ret = [];
    var visible_nodes = this.getVisibleNodes();
    for (var i = 0; i < visible_nodes.length; i++) {
        var node = visible_nodes[i];
        values(node.target_edges).forEach(function(edge) {
            if (edge.source.visible())
                ret.push(edge);
        });
    }

    return ret;
}

/*
 * The functions below are just simple utility functions
 */

function getEntirePathLinks(center) {
    // Returns a list containing all edges leading into or from the center node
    var edges = [];

    var foundParent = {};
    var explore_parents = function(node) {
        if (foundParent[node.id]) return;
        foundParent[node.id] = true;
        values(node.target_edges).forEach(function(edge) {
            if (edge.source.visible())
            {
                edges.push(edge);
                explore_parents(edge.source);
            }
        });
    }

    var foundChild = {};
    var explore_children = function(node) {
        if (foundChild[node.id]) return;
        foundChild[node.id] = true;
        values(node.source_edges).forEach(function(edge) {
            if (edge.target.visible())
            {
                edges.push(edge);
                explore_children(edge.target);
            }
        });
    }
    
    explore_parents(center);
    explore_children(center);


    return edges;
}

function values(obj) {
    return Object.keys(obj).map(function(key) { return obj[key]; });
}

function flatten(arrays) {
    var flattened = [];
    return flattened.concat.apply(flattened, arrays);
}