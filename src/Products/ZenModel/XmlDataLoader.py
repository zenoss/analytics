##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import os
import transaction

from Products.ZenRelations.ImportRM import ImportRM

class XmlDataLoader(ImportRM):

    def loadDatabase(self):

        # This is an initial load, so we can forgo incremental commits
        self.options.chunk_size = 0

        datadir = os.path.join(os.path.dirname(__file__),"data")
        self.log.info("loading data from:%s", datadir)
        for path, dirname, filenames in os.walk(datadir):
            filenames.sort()
            for filename in filter(lambda f: f.endswith(".xml"), filenames):
                self.options.infile = os.path.join(path,filename)
                self.log.info("loading: %s", self.options.infile)
                ImportRM.loadDatabase(self)
        # Reindex ProductKeys and EventClassKeys after XML load
        self.dmd.Manufacturers.reIndex()
        self.dmd.Events.reIndex()
        transaction.commit()


if __name__ == "__main__":
    rl = XmlDataLoader()
    rl.loadDatabase()
