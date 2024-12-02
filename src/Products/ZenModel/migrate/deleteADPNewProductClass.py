##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import Migrate


import logging
log = logging.getLogger("zen.migrate")

class DeleteADPNewProductClass(Migrate.Step):
    version = Migrate.Version(2, 1, 0)
    
    def cutover(self, dmd):  
        try:
            adp = dmd.getObjByPath('/zport/dmd/Manufacturers/ADP')
            adp.manage_deleteProducts(ids=['new'])
        except KeyError:
            log.info('Could not find the manufacturer ADP')
        except AttributeError:
            log.info('Could not the product new on manufacturer ADP')
        except Exception:
            log.error('Unknown error occurred')
            
DeleteADPNewProductClass()
