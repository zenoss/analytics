##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import string 
import warnings

warnings.filterwarnings('ignore', '.*non-existing path.*',
                        UserWarning,
                        '.*DirectoryView.*')

def findZenPackRoot(base):
    """
    Search upwards for the root of a ZenPack.

    >>> import os, tempfile; root = os.path.realpath(tempfile.mkdtemp())
    >>> skindir = os.path.join(root, 'ZenPacks/ZenPacks.zenoss.NotAPack-1.2.3-py2.6.egg/ZenPacks/zenoss/NotAPack/skins')
    >>> os.makedirs(skindir)
    >>> findZenPackRoot(skindir).replace(root, '/opt/zenoss')
    '/opt/zenoss/ZenPacks/ZenPacks.zenoss.NotAPack'
    """
    p = d = os.path.realpath(base)
    while d:
        if os.path.isdir(os.path.join(p, 'ZenPacks')):
            # Ditch version and extension if an egg
            if p.endswith('.egg'):
                fullpath = p.split(os.sep)
                name = fullpath.pop().split('-')[0]
                fullpath.append(name)
                p = os.sep.join(fullpath)
            return p
        p, d = os.path.split(p)
    return None


def skinDirs(base):
    layers = []
    for p, ds, fs in os.walk(os.path.join(base, 'skins')):
        for d in ds:
            if not d.startswith('.'):
                layers.append(d)
        # stop at one level
        break
    return layers


def registerSkin(self, base, positionAfter='custom'):
    """setup the skins in a product"""
    layers = skinDirs(base)
    try:
        from Products.CMFCore.utils import getToolByName
        from Products.CMFCore.DirectoryView import addDirectoryViews
        skinstool = getToolByName(self, 'portal_skins')
        for layer in layers:
            if layer not in skinstool.objectIds():
                path = os.path.join(base, 'skins')
                if not os.path.exists(path): os.mkdir(path, mode=0755)
                root = findZenPackRoot(path).split('/')[-1]
                addDirectoryViews(skinstool, path, dict(__name__=root))
        skins = skinstool.getSkinSelections()
        for skin in skins:
            path = skinstool.getSkinPath(skin)
            path = map(string.strip, string.split(path,','))
            for layer in layers:
                if layer not in path:
                    try:
                        path.insert(path.index(positionAfter)+1, layer)
                    except ValueError:
                        path.append(layer)
            path = ','.join(path)
            skinstool.addSkinSelection(skin, path)
    except ImportError as e:
        if "Products.CMFCore.utils" in e.args: pass
        else: raise
    except AttributeError as e:
        if "portal_skin" in e.args: pass
        else: raise

def unregisterSkin(self, base, positionAfter='custom'):
    """setup the skins in a product"""
    from Products.ZenUtils.Utils import unused
    unused(positionAfter)
    layers = skinDirs(base)
    if layers is None: return
    try:
        from Products.CMFCore.utils import getToolByName
        skinstool = getToolByName(self, 'portal_skins')
        for layer in layers:
            if layer in skinstool.objectIds():
                try:
                    skinstool._delOb(layer)
                except AttributeError:
                    pass
        obs = skinstool._objects
        goodlayers = filter(lambda x:getattr(skinstool, x['id'], False), obs)
        skinstool._objects = tuple(goodlayers)
    except ImportError as e:
        if "Products.CMFCore.utils" in e.args: pass
        else: raise
    except AttributeError as e:
        if "portal_skin" in e.args: pass
        else: raise
