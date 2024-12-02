(function() {
/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2012, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


Ext.ns('Zenoss.model');

    // Common fields used by all tree models
    Zenoss.model.BASE_TREE_FIELDS = [
        {
            name: 'hidden',
            type: 'boolean'
        },
        {
            name: 'leaf',
            type: 'boolean'
        },
        {
            name: 'uid',
            type: 'string'
        },
        {
            name: 'text'
        },
        {
            name: 'id',
            type: 'string'
        },
        {
            name: 'path',
            type: 'string'
        },
        {
            name: 'iconCls',
            type: 'string'
        },
        {
            name: 'uuid',
            type: 'string'
        }
    ];

    // A model defined which uses the default tree fields
    Ext.define("Zenoss.model.Tree", {
        extend: 'Ext.data.Model',
        fields: Zenoss.model.BASE_TREE_FIELDS
    });
}());
