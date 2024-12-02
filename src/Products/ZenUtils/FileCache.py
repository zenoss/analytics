##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2010, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Based on Python recipe http://code.activestate.com/recipes/543263/ (r1)
# by Brian O. Bush, Thu 24-Jan-2008 06:53 bushbo

import os, sys, pickle, base64, threading, glob
import tempfile

_DEFAULT_NOT_SPECIFIED = object()

# This file cache is thread-safe
class FileCache(object):
    def __init__(self, path, protocol=-1): 
        self.path = path # path assumed existing; check externally
        if not os.path.exists(self.path): 
            os.makedirs(self.path)        
        self.gen_key = lambda x: '%s.pickle' % base64.b64encode(x)
        self.lock = threading.Lock()
        self._pickleProtocol = protocol
    def _makeFileNameFromKey(self, key):
        return os.path.join(self.path, self.gen_key(key))
    def _allFileNames(self):
        return glob.glob(os.path.join(self.path,'*.pickle'))
    def get(self, key, default=_DEFAULT_NOT_SPECIFIED):
        retval = default
        fn = self._makeFileNameFromKey(key)
        with self.lock:
            try:
                with open(fn, 'rb') as f:
                    retval = pickle.load(f)
            except IOError:
                if default is _DEFAULT_NOT_SPECIFIED:
                    raise KeyError('no such key ' + key)
                else:
                    return default
            return retval[1]
    def __getitem__(self, key):
        return self.get(key)
    def __setitem__(self, key, value):
        fn = self._makeFileNameFromKey(key)
        with self.lock:
            # use temp file to avoid partially written out pickles
            tempFd = None # file descriptor
            tempFn = None # file name
            try:
                # dump to a temp file in pickle dir
                tempFd, tempFn = tempfile.mkstemp(dir=os.path.dirname(fn))
                # open a file object
                with os.fdopen(tempFd, "wb") as tempF:
                    tempFd = None
                    pickle.dump((key, value), tempF, protocol=self._pickleProtocol)
                # rename the temp file
                # this is an atomic operation on most filesystems
                os.rename(tempFn, fn)
            except Exception as ex:
                if tempFd is not None:
                    os.close(tempFd)
                raise ex
            finally:
                if os.path.exists(tempFn):
                    try:
                        os.remove(tempFn)
                    except (OSError, IOError):
                        pass
    def __delitem__(self, key):
        fn = self._makeFileNameFromKey(key)
        with self.lock:
            try:
                os.remove(fn)
            except (OSError, IOError):
                raise KeyError('no such key ' + key)
    def clear(self):
        with self.lock:
            for fn in self._allFileNames():
                try:
                    os.remove(fn)
                except (OSError, IOError):
                    pass
    def items(self):
        with self.lock:
            return list(self.iteritems())
    def keys(self):
        with self.lock:
            return list(self.iterkeys())
    def values(self):
        with self.lock:
            return list(self.itervalues())
    def iterkeys(self):
        for fn in self._allFileNames():
            yield base64.b64decode(os.path.split(fn)[1][:-7])
    def itervalues(self):
        for k,v in self.iteritems():
            yield v
    def iteritems(self):
        for fn in self._allFileNames():
            try:
                with open(fn,'rb') as f:
                    yield pickle.load(f)
            except IOError:
                pass
    def __contains__(self, key):
        with self.lock:
            fn = self._makeFileNameFromKey(key)
            return os.path.exists(fn)
    def __len__(self):
        with self.lock:
            return len(self._allFileNames())
    def __bool__(self):
        with self.lock:
            return bool(self._allFileNames())
    __nonzero__ = __bool__

if __name__=='__main__':
    class Site:
        def __init__(self, name, hits=0):
            self.name = name
            self.hits = hits
        def __str__(self):
            return '%s, %d hits' % (self.name, self.hits)
    cache = FileCache('test')
    sites = [Site('cnn.com'), Site('kd7yhr.org', 1), Site('asdf.com', 3)]
    # We will use the site url as the key for our cache
    # Comment out the next two lines to test cache reading
    for site in sites:    
        cache[site.name] = site
    testitemname = sites[-1].name

    entry = cache.get(testitemname)
    if entry: 
        print type(entry), entry

    print cache.keys()
    import glob
    for fn in glob.glob('test/*'):
        print fn

    print testitemname in cache

    del cache[testitemname]
    print cache.keys()
    print testitemname in cache

    cache.clear()
    print cache.keys()
