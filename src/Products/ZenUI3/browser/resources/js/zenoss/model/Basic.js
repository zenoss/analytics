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

    /**
     * Model that defines a uid and name
     **/
    Ext.define("Zenoss.model.Basic", {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: ['uid', 'name']
    });
    
    /**
     * Model that defines a uid and label
     **/
    Ext.define("Zenoss.model.Label", {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: ['uid', 'label']
    });    

    /**
     * Like the basic model but defined with the UUID instead of the uid
     **/
    Ext.define("Zenoss.model.BasicUUID", {
        extend: 'Ext.data.Model',
        idProperty: 'uuid',
        fields: ['uuid', 'name']
    });

    /**
     * Store that just defines a name
     **/
    Ext.define("Zenoss.model.Name", {
        extend: 'Ext.data.Model',
        idProperty: 'name',
        fields: ['name']
    });

    Ext.define("Zenoss.model.NameValue", {
        extend: 'Ext.data.Model',
        idProperty: 'value',
        fields: ['name', 'value']
    });

    Ext.define("Zenoss.model.IdName", {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: ['id', 'name']
    });

    Ext.define("Zenoss.model.ValueText", {
        extend: 'Ext.data.Model',
        idProperty: 'value',
        fields: ['value', 'text']
    });

}());
