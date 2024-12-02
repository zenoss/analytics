##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


## Script (Python) "scSortedTableGetBatch"
##parameters=tableName,objects,defaultSort="primarySortKey",defaultSortRule='cmp',batchSize=20,usebatch=1,sortedSence='asc'
##bind context=context
##title=Manage session information for table and get nessesary batch

import ZTUtils

request=context.REQUEST
session=request.SESSION

if hasattr(context, 'userDefaultBatchSize'):
    defaultBatchSize = context.userDefaultBatchSize
elif hasattr(context, 'defaultBatchSize'):
    defaultBatchSize = context.defaultBatchSize
else:
    defaultBatchSize = batchSize

tableatts = ( 'sortedHeader',
            'sortedSence',
            'sortRule',
            'start',
            'filter',
            'filterattribute',
            'negatefilter',
            'severity',
            'batchSize',
            )

if (session.has_key(tableName) 
    and session[tableName].has_key('url')
    and session[tableName]['url']==request.URL):
    sortedTableState = session[tableName]
    if request.has_key('tableName') and request['tableName'] == tableName:
        for attname in tableatts:
            if request.has_key(attname):
                sortedTableState[attname] = request[attname]
        if request.has_key('batchSize'):
            sortedTableState['start'] = 0
        if not request.has_key("negatefilter"):
            sortedTableState['negatefilter'] = 0
else:
    sortedTableState = {
        'start' : 0,
        'url' : request.URL,
        'sortedHeader' : defaultSort,
        'sortRule' : defaultSortRule,
        'sortedSence' : sortedSence,
        'batchSize' : defaultBatchSize,
        }

severity = sortedTableState.get('severity')
if severity:
    objects = filter(lambda x: x.getSeverityNumber() >= severity, objects)
            

if sortedTableState.has_key('filter') and sortedTableState['filter']:
    regex = sortedTableState['filter']
    if sortedTableState.has_key('filterattribute'):
        filteratt = sortedTableState['filterattribute']
    else:
        filteratt = 'getId'
    if sortedTableState.has_key('negatefilter'):
        negatefilter = sortedTableState['negatefilter']
    else: 
        negatefilter = 0
    objects = context.filterObjectsRegex(regex, objects, 
                                        filteratt, negatefilter)
   
sortedTableState['totalobjs'] = len(objects)
if sortedTableState['start'] > sortedTableState['totalobjs']:
    sortedTableState['start'] = 0

if sortedTableState['sortedHeader']:
    sortOn = (( sortedTableState['sortedHeader'], 
                sortedTableState['sortRule'], 
                sortedTableState['sortedSence']),)
    sortedObjects = sequence.sort(objects, sortOn)
else:
    sortedObjects = objects

if usebatch:
    batch = ZTUtils.Batch(sortedObjects, 
                    size=sortedTableState['batchSize'] or len(sortedObjects), 
                    start=sortedTableState['start'], orphan=0)
else:
    batch = sortedObjects

session[tableName] = sortedTableState

return batch
