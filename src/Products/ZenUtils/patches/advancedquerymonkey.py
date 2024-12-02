from Products.AdvancedQuery.sorting import IndexSorter

from Products.ZenUtils.Utils import monkeypatch
from Products.ZenUtils.NaturalSort import NaturalObjectCompare

from BTrees.IIBTree import difference, IISet, IITreeSet, intersection
from BTrees.OOBTree import OOBTree

@monkeypatch(IndexSorter)
def group(self, seq):
  sortIndex = self._sortIndex;
  sortReverse = self._sortReverse
  ns = len(seq); ni = len(sortIndex)

  if ns >= 0.1 * ni:
    # result large compared to index -- sort via index
    handled = IISet();
    hn = 0
    _load = getattr(sortIndex, '_load', None)
    if _load is None:
      # not an optimized index
      items = sortIndex.items()
      _load = lambda (x1, x2): x2
      if sortReverse:
          items.reverse()
    elif sortReverse:
      gRO = getattr(sortIndex, 'getReverseOrder', None)
      items = gRO and gRO()
      if items is None:
        items = list(sortIndex._index.keys());
        items.reverse()
    else:
        items = sortIndex._index.keys()

    for i in items:
      ids = intersection(seq, _load(i))
      if ids:
        handled.update(ids);
        hn += len(ids)
        yield i, ids
    if hn != len(seq):
        yield None, difference(seq, handled)
  else:
    # result relatively small -- sort via result
    m = OOBTree()
    keyFor = getattr(sortIndex, 'keyForDocument', None)
    # work around "nogopip" bug: it defines "keyForDocument" as an integer
    if not callable(keyFor):
      # this will fail, when the index neither defines a reasonable
      # "keyForDocument" nor "documentToKeyMap". In this case,
      # the index cannot be used for sorting.
      keyFor = lambda doc, map=sortIndex.documentToKeyMap(): map[doc]
    noValue = IITreeSet()

    for doc in seq.keys():
      try: k = keyFor(doc)
      except KeyError: noValue.insert(doc); continue

      k = NaturalObjectCompare( k)
      l = m.get(k)
      if l is None: l = m[k] = IITreeSet()
      l.insert(doc)
    items = m.items()
    if sortReverse:
        items = list(items);
        items.reverse()

    for i in items:
        yield i
    if noValue: yield None, noValue
