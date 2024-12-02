# Copyright (c) 2004 Zope Corporation and Plone Solutions

# ZPL 2.1 license

import logging

from App.special_dtml import DTMLFile
from BTrees.IIBTree import IISet, intersection, union, multiunion
from BTrees.OOBTree import OOBTree
from BTrees.OIBTree import OIBTree

from Products.PluginIndexes.common.util import parseIndexRequest
from Products.PluginIndexes.common import safe_callable
from Products.PluginIndexes.PathIndex.PathIndex import PathIndex

_marker = []
logger = logging.getLogger('ExtendedPathIndex')

class ExtendedPathIndex(PathIndex):
    """ A path index stores all path components of the physical
    path of an object:

    Internal datastructure (regular pathindex):

    - a physical path of an object is split into its components

    - every component is kept as a  key of a OOBTree in self._indexes

    - the value is a mapping 'level of the path component' to
      'all docids with this path component on this level'

    In addition
    
    - there is a terminator (None) signifying the last component in the path

    """

    meta_type = "ExtendedPathIndex"

    manage_options= (
        {'label': 'Settings',
         'action': 'manage_main',
         'help': ('ExtendedPathIndex','ExtendedPathIndex_Settings.stx')},
    )

    query_options = ("query", "level", "operator", "depth", "navtree",
                                                              "navtree_start")

    def __init__(self, id, extra=None, caller=None):
        """ ExtendedPathIndex supports indexed_attrs """
        PathIndex.__init__(self, id, caller)

        def get(o, k, default):
            if isinstance(o, dict):
                return o.get(k, default)
            else:
                return getattr(o, k, default)

        attrs = get(extra, 'indexed_attrs', None)
        if attrs is None:
            return
        if isinstance(attrs, str):
            attrs = attrs.split(',')
        attrs = filter(None, [a.strip() for a in attrs])

        if attrs:
            # We only index the first attribute so snip off the rest
            self.indexed_attrs = tuple(attrs[:1])

    def clear(self):
        PathIndex.clear(self)
        self._index_parents = OOBTree()
        self._index_items = OIBTree()

    def insertEntry(self, comp, id, level, parent_path=None, object_path=None):
        """Insert an entry.

           parent_path is the path of the parent object

           path is the object path, it is assumed to be unique, i.e. there
           is a one to one mapping between physical paths and docids.  This
           will be large, and is only used for breadcrumbs.

           id is the docid
        """

        PathIndex.insertEntry(self, comp, id, level)

        if parent_path is not None:
            if not self._index_parents.has_key(parent_path):
                self._index_parents[parent_path] = IISet()

            self._index_parents[parent_path].insert(id)

        # We make the assumption that a full path corresponds one and only
        # one object.

        if object_path is not None:
            self._index_items[object_path] = id

    def index_object(self, docid, obj ,threshold=100):
        """ hook for (Z)Catalog """

        # PathIndex first checks for an attribute matching its id and
        # falls back to getPhysicalPath only when failing to get one.
        # The presence of 'indexed_attrs' overrides this behavior and
        # causes indexing of the custom attribute.

        attrs = getattr(self, 'indexed_attrs', None)
        if attrs:
            index = attrs[0]
        else:
            index = self.id

        f = getattr(obj, index, None)
        if f is not None:
            if safe_callable(f):
                try:
                    path = f()
                except AttributeError:
                    return 0
            else:
                path = f

            if not isinstance(path, (str, tuple)):
                raise TypeError('path value must be string or tuple '
                                'of strings: (%r, %s)' % (index, repr(path)))
        else:
            try:
                path = obj.getPhysicalPath()
            except AttributeError:
                return 0

        if isinstance(path, (list, tuple)):
            path = '/'+ '/'.join(path[1:])
        comps = filter(None, path.split('/'))
        parent_path = '/' + '/'.join(comps[:-1])

        # Make sure we reindex properly when path change
        if self._unindex.has_key(docid) and self._unindex.get(docid) != path:
            self.unindex_object(docid)

        if not self._unindex.has_key(docid):
            self._length.change(1)

        for i in range(len(comps)):
            self.insertEntry(comps[i], docid, i)

        # Add terminator
        self.insertEntry(None, docid, len(comps)-1, parent_path, path)

        self._unindex[docid] = path
        return 1

    def unindex_object(self, docid):
        """ hook for (Z)Catalog """

        if not self._unindex.has_key(docid):
            logger.log(logging.INFO,
                       'Attempt to unindex nonexistent object with id '
                       '%s' % docid)
            return

        # There is an assumption that paths start with /
        path = self._unindex[docid]
        if not path.startswith('/'):
            path = '/'+path
        comps =  path.split('/')
        parent_path = '/'.join(comps[:-1])

        def unindex(comp, level, docid=docid, parent_path=None,
                                                            object_path=None):
            try:
                self._index[comp][level].remove(docid)

                if not self._index[comp][level]:
                    del self._index[comp][level]

                if not self._index[comp]:
                    del self._index[comp]
                # Remove parent_path and object path elements
                if parent_path is not None:
                    self._index_parents[parent_path].remove(docid)
                    if not self._index_parents[parent_path]:
                        del self._index_parents[parent_path]
                if object_path is not None:
                    del self._index_items[object_path]
            except KeyError:
                logger.log(logging.INFO,
                           'Attempt to unindex object with id '
                           '%s failed' % docid)

        for level in range(len(comps[1:])):
            comp = comps[level+1]
            unindex(comp, level)

        # Remove the terminator
        level = len(comps[1:])
        comp = None
        unindex(comp, level-1, parent_path=parent_path, object_path=path)

        self._length.change(-1)
        del self._unindex[docid]

    def search(self, path, default_level=0, depth=-1, navtree=0,
                                                             navtree_start=0):
        """
        path is either a string representing a
        relative URL or a part of a relative URL or
        a tuple (path,level).

        level >= 0  starts searching at the given level
        level <  0  not implemented yet
        """

        if isinstance(path, basestring):
            startlevel = default_level
        else:
            startlevel = int(path[1])
            path = path[0]

        absolute_path = isinstance(path, basestring) and path.startswith('/')

        comps = filter(None, path.split('/'))

        orig_comps = [''] + comps[:]
        # Optimization - avoid using the root set
        # as it is common for all objects anyway and add overhead
        # There is an assumption about catalog/index having
        # the same container as content
        if default_level == 0:
            indexpath = list(filter(None, self.getPhysicalPath()))
            while min(len(indexpath), len(comps)):
                if indexpath[0] == comps[0]:
                    del indexpath[0]
                    del comps[0]
                    startlevel += 1
                else:
                    break

        if len(comps) == 0:
            if depth == -1 and not navtree:
                return IISet(self._unindex.keys())

        # Make sure that we get depth = 1 if in navtree mode
        # unless specified otherwise

        orig_depth = depth
        if depth == -1:
            depth = 0 or navtree

        # Optimized navtree starting with absolute path
        if absolute_path and navtree and depth == 1 and default_level==0:
            set_list = []
            # Insert root element
            if navtree_start >= len(orig_comps):
                navtree_start = 0
            # create a set of parent paths to search
            for i in range(len(orig_comps), navtree_start, -1):
                parent_path = '/'.join(orig_comps[:i])
                parent_path = parent_path and parent_path or '/'
                try:
                    set_list.append(self._index_parents[parent_path])
                except KeyError:
                    pass
            return multiunion(set_list)
        # Optimized breadcrumbs
        elif absolute_path and navtree and depth == 0 and default_level==0:
            item_list = IISet()
            # Insert root element
            if navtree_start >= len(orig_comps):
                navtree_start = 0
            # create a set of parent paths to search
            for i in range(len(orig_comps), navtree_start, -1):
                parent_path = '/'.join(orig_comps[:i])
                parent_path = parent_path and parent_path or '/'
                try:
                    item_list.insert(self._index_items[parent_path])
                except KeyError:
                    pass
            return item_list
        # Specific object search
        elif absolute_path and orig_depth == 0 and default_level == 0:
            try:
                return IISet([self._index_items[path]])
            except KeyError:
                return IISet()
        # Single depth search
        elif absolute_path and orig_depth == 1 and default_level == 0:
            # only get objects contained in requested folder
            try:
                return self._index_parents[path]
            except KeyError:
                return IISet()
        # Sitemaps, relative paths, and depth queries
        elif startlevel >= 0:

            pathset = None # Same as pathindex
            navset  = None # For collecting siblings along the way
            depthset = None # For limiting depth

            if navtree and depth and \
                   self._index.has_key(None) and \
                   self._index[None].has_key(startlevel):
                navset = self._index[None][startlevel]

            for level in range(startlevel, startlevel+len(comps) + depth):
                if level-startlevel < len(comps):
                    comp = comps[level-startlevel]
                    if not self._index.has_key(comp) or not self._index[comp].has_key(level): 
                        # Navtree is inverse, keep going even for
                        # nonexisting paths
                        if navtree:
                            pathset = IISet()
                        else:
                            return IISet()
                    else:
                        pathset = intersection(pathset,
                                                     self._index[comp][level])
                    if navtree and depth and \
                           self._index.has_key(None) and \
                           self._index[None].has_key(level+depth):
                        navset  = union(navset, intersection(pathset,
                                              self._index[None][level+depth]))
                if level-startlevel >= len(comps) or navtree:
                    if self._index.has_key(None) and self._index[None].has_key(level):
                        depthset = union(depthset, intersection(pathset,
                                                    self._index[None][level]))

            if navtree:
                return union(depthset, navset) or IISet()
            elif depth:
                return depthset or IISet()
            else:
                return pathset or IISet()

        else:
            results = IISet()
            for level in range(0,self._depth + 1):
                ids = None
                error = 0
                for cn in range(0,len(comps)):
                    comp = comps[cn]
                    try:
                        ids = intersection(ids,self._index[comp][level+cn])
                    except KeyError:
                        error = 1
                if error==0:
                    results = union(results,ids)
            return results

    def _apply_index(self, request, cid=''):
        """ hook for (Z)Catalog
            'request' --  mapping type (usually {"path": "..." }
             additionaly a parameter "path_level" might be passed
             to specify the level (see search())

            'cid' -- ???
        """

        record = parseIndexRequest(request,self.id,self.query_options)
        if record.keys==None: return None

        level    = record.get("level", 0)
        operator = record.get('operator', self.useOperator).lower()
        depth    = getattr(record, 'depth', -1) # Set to 0 or navtree later
                                                # use getattr to get 0 value
        navtree  = record.get('navtree', 0)
        navtree_start  = record.get('navtree_start', 0)

        # depending on the operator we use intersection of union
        if operator == "or":  set_func = union
        else: set_func = intersection

        res = None
        for k in record.keys:
            rows = self.search(k,level, depth, navtree, navtree_start)
            res = set_func(res,rows)

        if res:
            return res, (self.id,)
        else:
            return IISet(), (self.id,)

    def getIndexSourceNames(self):
        """ return names of indexed attributes """

        # By default PathIndex advertises getPhysicalPath even
        # though the logic in index_object is different.

        try:
            return tuple(self.indexed_attrs)
        except AttributeError:
            return ('getPhysicalPath',)

    index_html = DTMLFile('dtml/index', globals())
    manage_workspace = DTMLFile('dtml/manageExtendedPathIndex', globals())


manage_addExtendedPathIndexForm = DTMLFile('dtml/addExtendedPathIndex', globals())

def manage_addExtendedPathIndex(self, id, extra=None, REQUEST=None, RESPONSE=None, URL3=None):
    """Add an extended path index"""
    return self.manage_addIndex(id, 'ExtendedPathIndex', extra=extra,
                REQUEST=REQUEST, RESPONSE=RESPONSE, URL1=URL3)
