##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from Products.ZenModel.migrate import Migrate

def main():
    m = Migrate.Migration()
    m.main()

if __name__ == '__main__':
    main()
