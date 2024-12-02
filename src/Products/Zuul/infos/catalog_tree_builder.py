##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import logging
import time
from collections import defaultdict

from Products.AdvancedQuery import And, Eq, MatchGlob
from Products.Zuul.catalog.interfaces import IModelCatalogTool
from Products.Zuul.catalog.model_catalog import OBJECT_UID_FIELD as UID

log = logging.getLogger("catalog_tree_builder")


class ModelCatalogTreeNode(object):
    def __init__(self, path):
        self.path = path
        self.id = path.split("/")[-1]
        self.child_trees = {}         # { partial_path_from_self.path : ModelCatalogTreeNode }
        self.partial_leaf_count = 0   # count not including children
        self.total_leaf_count = 0     # count including children
        self.leaves = set()           # leaves' uids
        self.all_leaves = set()       # this node and its subnodes leaves' uids


class ModelCatalogTreeBuilder(object):
    """
    Builds a Navigation Tree using Model Catalog 
    """
    def __init__(self, root, node_type, leaf_type, load_leaves=False, facet_field=None):
        """
        @param root:            root node of the tree
        @param node_type:       value of the object_implements field to query the catalog for nodes
                                    Ex: "Products.ZenModel.DeviceOrganizer.DeviceOrganizer"
        @param leaf_type:       value of the object_implements field to query the catalog for leaves
                                    Ex: "Products.ZenModel.Device.Device"
        @param load_leaves:     load leaves' brains from catalog or not
        @param facet_field:     field to retrieve leaf count using facets
        """
        self.root = root               # root object for which we are building the tree
        self.brains = {}               # obj_uid : obj brain
        self.trees = {}                # obj_uid : ModelCatalogTreeNode
        self.root_tree = None
        self.root_path = "/".join(self.root.getPrimaryPath())
        self.model_catalog = IModelCatalogTool(self.root.dmd)
        self.node_objectImplements = node_type
        self.leaf_objectImplements = leaf_type
        self.load_leaves = load_leaves
        self.facet_field = facet_field
        # Leaf brain field to use to determine the leaf's parent in case
        # parent and leaves primary paths dont belong to the same tree.
        # Example:
        #   Group:   uid => /zport/dmd/Groups/my_group
        #   Device:  uid => /zport/dmd/Devices/blabla/my_device
        #            we need a different field to get the parent - child relationship
        #
        self.parenthood_field = "uid"
        self.get_node_uid_from_parenthood_field = lambda x: "/".join(x.split("/")[:-2])
        if self.root_path.startswith("/zport/dmd/Groups") or \
           self.root_path.startswith("/zport/dmd/Systems") or \
           self.root_path.startswith("/zport/dmd/Locations"):
           self.parenthood_field = "deviceOrganizers"
           self.get_node_uid_from_parenthood_field = lambda x: x

        # Build the tree
        start = time.time()
        self.build_tree()
        log.debug("Building tree for %s took %s seconds.", self.root_path, time.time()-start)

    def _query_catalog(self, objectImplements, filter_permissions=True, limit=None, fields=None, facet_field=None):
        requested_fields = set([ UID, "name", "id", "uuid", "meta_type" ])
        params = {}
        params["types"] = objectImplements
        params["paths"] = self.root_path
        if fields:
            if isinstance(fields, basestring):
                fields = [fields]
            requested_fields |= set(fields)
        params["fields"] = list(requested_fields)
        params["filterPermissions"] = filter_permissions
        if limit:
            params["limit"] = limit
        if facet_field:
            params["facets_for_field"] = facet_field
        return self.model_catalog.search(**params)

    def build_tree(self):
        """
        Builds the tree for a given root node and its subtrees
        """
        # Load the nodes
        search_results = self._query_catalog(self.node_objectImplements, filter_permissions=False)
        nodes = set()
        for brain in search_results.results:
            self.brains[brain.uid] = brain
            nodes.add(brain.uid)

        self.root_tree = ModelCatalogTreeNode(self.root_path)
        self.trees[self.root_path] = self.root_tree

        for path in nodes:
            if not path.startswith(self.root_path) or \
               path == self.root_path:
                continue
            current_path = self.root_path
            current_tree = self.root_tree

            # get subtrees
            # Example:
            #    root:       /zport/dmd/Devices
            #    path:       /zport/dmd/Devices/Server/Linux
            #    subtrees:   Server
            #                Server/Linux
            #
            subtrees = path.replace(self.root_path, "").strip("/").split("/")

            for subtree in subtrees:
                if not subtree:
                    continue
                current_path = "{}/{}".format(current_path, subtree)
                if subtree not in current_tree.child_trees:
                    new_tree = ModelCatalogTreeNode(current_path)
                    current_tree.child_trees[subtree] = new_tree
                    self.trees[current_path] = new_tree
                current_tree = current_tree.child_trees[subtree]

        if self.load_leaves or not self.facet_field:
            # We need to load all leaves
            self._load_leaves()
            self._load_leaf_counts() # gets count counting unique leaves
        else:
            # Get all the counts in just one solr call
            self._load_leaf_counts_using_facets()

    def _load_leaves(self):
        """
        Loads the leaves for each node
        """
        search_results = self._query_catalog(self.leaf_objectImplements, fields=self.parenthood_field)
        for leaf_brain in search_results:
            nodes = set()
            self.brains[leaf_brain.uid] = leaf_brain
            parenthood_field_value = getattr(leaf_brain, self.parenthood_field, None)
            if parenthood_field_value:
                if isinstance(parenthood_field_value, basestring):
                    parenthood_field_value = [parenthood_field_value]
                # get the nodes this leaf belongs to
                for v in parenthood_field_value:
                    node_uid = self.get_node_uid_from_parenthood_field(v)
                    if node_uid.startswith(self.root_path):
                        nodes.add(node_uid)
                # add the leaf uid to the organizers it belongs to
                for node_uid in nodes:
                    if node_uid in self.trees:
                        log.debug("adding leaf %s to node %s", leaf_brain.uid, node_uid)
                        self.trees[node_uid].leaves.add(leaf_brain.uid)

    def _load_leaf_counts(self):
        # Load leaves for all nodes from the bottom up and
        # calculate the leaf count
        nodes_uids = self.trees.keys()
        nodes_uids.sort(reverse=True, key=lambda x: len(x.split("/")))
        for node_uid in nodes_uids:
            current_tree = self.trees[node_uid]
            all_leaves = set(current_tree.leaves)
            for child_tree in current_tree.child_trees.itervalues():
                all_leaves = all_leaves | child_tree.all_leaves
            current_tree.all_leaves = all_leaves
            current_tree.partial_leave_count = len(current_tree.leaves)
            current_tree.total_leaf_count = len(current_tree.all_leaves)

    def _load_leaf_counts_using_facets(self):
        # facets values are returned in lower case
        path_translator = {}
        for tree_path in self.trees.iterkeys():
            lower_case_path = tree_path.lower()
            path_translator[lower_case_path] = tree_path

        # query to retrieve the counts using facets
        search_results = self._query_catalog(self.leaf_objectImplements, limit=0, facet_field=self.facet_field)

        # load the partial child counts using facets
        if search_results.facets and search_results.facets.get(self.facet_field):
            facets = search_results.facets[self.facet_field]
            for lower_case_path, count in facets.get_values().iteritems():
                real_path = path_translator.get(lower_case_path)
                if real_path:
                    self.trees[real_path].partial_leaf_count = count
            # Calculate the total leaf count adding up the partial counts
            nodes_uids = self.trees.keys()
            nodes_uids.sort(reverse=True, key=lambda x: len(x.split("/")))
            for node_uid in nodes_uids:
                current_tree = self.trees[node_uid]
                leaf_count = 0
                for child_tree in current_tree.child_trees.itervalues():
                    leaf_count += child_tree.total_leaf_count
                current_tree.total_leaf_count = current_tree.partial_leaf_count + leaf_count

    def get_children(self, node_path):
        tree = self.trees[node_path]
        subtrees = tree.child_trees.values()
        subtrees.sort( key=lambda x: x.id )
        brains = [ self.brains[subtree.path] for subtree in subtrees if self.brains.get(subtree.path)]
        return brains

    def get_leaf_count(self, node_path):
        count = 0
        node_tree = self.trees.get(node_path)
        if node_tree:
            count = node_tree.total_leaf_count
        return count
    
    def _get_sorted_brains(self, uids, order_by="name"):
        brains = [ self.brains[uid] for uid in uids ]
        if brains and order_by:
            brains.sort(reverse=False, key=lambda x: getattr(x, order_by, x.id).lower())
        return brains

    def get_child_nodes_brains(self, node_path, order_by="name"):
        brains = []
        if self.trees.get(node_path):
            node_tree = self.trees[node_path]
            children_uids = [ tree.path for tree in node_tree.child_trees.values() ]
            brains = self._get_sorted_brains(children_uids, order_by)
        return brains

    def get_node_leaves(self, node_path, include_subnodes=False, order_by="name"):
        """
        return the leaves brains for the received node
        """
        brains = []
        if self.load_leaves:
            node_tree = self.trees[node_path]
            leaves = node_tree.all_leaves if include_subnodes else node_tree.leaves
            brains = self._get_sorted_brains(leaves, order_by)
        return brains
