/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


(function(){

Ext.ns('Zenoss');

Zenoss.VerticalBrowsePanel = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            layout: 'hbox',
            border: false,
            layoutConfig: {
                align: 'stretch'
            },
            defaults: {
                flex: 1,
                autoScroll: true
            }
        });
        Zenoss.VerticalBrowsePanel.superclass.constructor.call(this, config);
    }
});

})();
