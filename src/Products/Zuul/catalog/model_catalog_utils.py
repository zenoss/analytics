##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################



import argparse
import zope.component
from zope.event import notify

from Products.Zuul.catalog.events import IndexingEvent
from Products.Zuul.catalog.model_catalog import get_solr_config
from zenoss.modelindex.model_index import SearchParams
from zenoss.modelindex.constants import ZENOSS_MODEL_COLLECTION_NAME
from Products.Zuul.catalog.indexable import OBJECT_UID_FIELD as UID


class ModelCatalogUtils(object):

    def __init__(self, dmd=None):
        self.model_index = zope.component.createObject('ModelIndex', get_solr_config())
        self.dmd = dmd

    def _get_zodb_connection(self):
        print("Connecting to zodb...")
        from Products.ZenUtils.ZenScriptBase import ZenScriptBase
        self.dmd = ZenScriptBase(connect=True).dmd

    def _get_object(self, uid):
        obj = None
        if not self.dmd:
            self._get_zodb_connection()
        try:
            obj = self.dmd.unrestrictedTraverse(uid)
        except Exception:
            print "Object not found: {}".format(uid)
        return obj

    def index_by_uid(self, uid):
        obj = self._get_object(uid)
        if obj:
            self.model_index.index(obj)

    def unindex_by_uid(self, uid):
        query={UID: uid}
        search_params=SearchParams(query=query)
        self.model_index.unindex_search(search_params, collection=ZENOSS_MODEL_COLLECTION_NAME)

    def generate_indexing_event(self, uid):
        obj = self._get_object(uid)
        if obj:
            notify(IndexingEvent(obj))


def main(options):
    utils = ModelCatalogUtils()
    if options.action == "index":
        utils.index_by_uid(options.uid)
    elif options.action == "unindex":
        utils.unindex_by_uid(options.uid)


def parse_options():
    parser = argparse.ArgumentParser(description="Model Catalog hacking tool", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("action", type=str, choices=['index', 'unindex'], help="Action to perform")
    parser.add_argument("-u", "--uid", dest="uid", type=str, help="Full path of the zodb object to operate on")
    return parser.parse_args()


if __name__ == "__main__":
    import sys
    options = parse_options()
    print("{} called with options {}\n".format(sys.argv[0], options))
    sys.argv = sys.argv[:1] # clean up the cli args so ZenScriptBase does not bark
    main(options)
