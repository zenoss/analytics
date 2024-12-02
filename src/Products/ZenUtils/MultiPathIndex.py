##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import time
import logging
LOG = logging.getLogger('ZenUtils.MultiPathIndex')

from App.special_dtml import DTMLFile

from ExtendedPathIndex import ExtendedPathIndex
from Products.PluginIndexes.common import safe_callable
from BTrees.OOBTree import OOSet
from BTrees.IIBTree import IISet, intersection, union, multiunion

def _isSequenceOfSequences(seq):
    if not seq:
        return False
    return (isinstance(seq, (tuple, list)) and
            all(isinstance(item, (tuple, list)) for item in seq))

def _recursivePathSplit(seq):
    if isinstance(seq, (tuple, list)):
        return map(_recursivePathSplit, seq)
    if '/' in seq:
        return seq.split('/')
    else:
        return seq


class MultiPathIndex(ExtendedPathIndex):
    """
    A path index that is capable of indexing multiple paths per object.
    """
    meta_type = "MultiPathIndex"


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

        if depth > 0:
            raise ValueError("Can't do depth searches anymore")

        if not comps:
            comps = ['dmd']
            startlevel = 1
        elif comps[0] == 'zport':
            comps = comps[1:]
        elif comps[0] != 'dmd':
            raise ValueError("Depth searches must start with 'dmd'")
        startlevel = len(comps)
        #startlevel = len(comps)-1 if len(comps) > 1 else 1

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
            for level in range(startlevel, startlevel+len(comps)):
                if level <= len(comps):
                    comp = "/".join(comps[:level])
                    if (not self._index.has_key(comp)
                        or not self._index[comp].has_key(level)):
                        # Navtree is inverse, keep going even for
                        # nonexisting paths
                        if navtree:
                            pathset = IISet()
                        else:
                            return IISet()
                    else:
                        return self._index[comp][level]
                    if navtree and depth and \
                           self._index.has_key(None) and \
                           self._index[None].has_key(level+depth):
                        navset  = union(navset, intersection(pathset,
                                              self._index[None][level+depth]))
                if level-startlevel >= len(comps) or navtree:
                    if (self._index.has_key(None)
                        and self._index[None].has_key(level)):
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


    def getIndexSourceNames(self):
        """ return names of indexed attributes """
        return (self.id, )

    def index_object(self, docid, obj, threshold=100):
        """ hook for (Z)Catalog """

        f = getattr(obj, self.id, None)
        if f is not None:
            if safe_callable(f):
                try:
                    paths = f()
                except AttributeError:
                    return 0
            else:
                paths = f
        else:
            try:
                paths = obj.getPhysicalPath()
            except AttributeError:
                return 0

        if not paths: return 0
        paths = _recursivePathSplit(paths)
        if not _isSequenceOfSequences(paths):
            paths = [paths]

        if docid in self._unindex:
            if isinstance(self._unindex[docid], set):
                self._unindex[docid] = OOSet(self._unindex[docid])

            unin = set(self._unindex[docid])
            paths_set = {'/'.join(x) for x in paths}

            for oldpath in unin - paths_set:
                self.unindex_paths(docid, (oldpath,))
        else:
            self._unindex[docid] = OOSet()
            self._length.change(1)

        self.index_paths(docid, paths)

        return 1

    def index_paths(self, docid, paths):
        for path in paths:
            if isinstance(path, (list, tuple)):
                path = '/'+ '/'.join(path[1:])
            comps = filter(None, path.split('/'))
            parent_path = '/' + '/'.join(comps[:-1])

            for i in range(len(comps)):
                comp = "/".join(comps[1:i+1])
                if comp:
                    self.insertEntry(comp, docid, i)

            # Add terminator
            self.insertEntry(None, docid, len(comps)-1, parent_path, path)

            self._unindex.setdefault(docid, OOSet()).insert(path)


    def unindex_paths(self, docid, paths):

        if not self._unindex.has_key(docid):
            return

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
                # Failure
                pass

        old = set(self._unindex.get(docid, ()))
        mkstr = lambda path:'/'.join(path) if isinstance(path, tuple) else path
        paths = map(mkstr, paths)
        toremove = set(paths) & old
        tokeep = old - toremove
        for path in toremove:
            if not path.startswith('/'):
                path = '/'+path
            comps =  path.split('/')
            parent_path = '/'.join(comps[:-1])

            for level in range(1, len(comps[2:])+1):
                comp = "/".join(comps[2:level+2])
                unindex(comp, level, docid, parent_path, path)
            # Remove the terminator
            level = len(comps[1:])
            comp = None
            unindex(comp, level-1, parent_path=parent_path, object_path=path)

            self._unindex[docid].remove(path)

        if tokeep:
            self.index_paths(docid, tokeep)
        else:
            # Cleared out all paths for the object
            self._length.change(-1)
            del self._unindex[docid]


    def unindex_object(self, docid):
        """ hook for (Z)Catalog """
        if not self._unindex.has_key(docid):
            return
        self.unindex_paths(docid, self._unindex[docid])

    manage = manage_main = DTMLFile('dtml/manageMultiPathIndex', globals())
    manage_main._setName('manage_main')


manage_addMultiPathIndexForm = DTMLFile('dtml/addMultiPathIndex', globals())

def manage_addMultiPathIndex(self, id, REQUEST=None, RESPONSE=None,
                             URL3=None):
    """
    Add a MultiPathIndex.
    """
    return self.manage_addIndex(id, 'MultiPathIndex', extra=None,
                                REQUEST=REQUEST, RESPONSE=RESPONSE,
                                URL1=URL3)
