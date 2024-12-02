/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


/* package level */
(function() {

Ext.ns('Zenoss.form');

Ext.define("Zenoss.form.FieldRow", {

    alias: ['widget.fieldrow'],
    extend: "Ext.Container",
    constructor: function(config) {
         Ext.apply(config, {
             layout: 'hbox',
             align: 'top'
         });

         var items = config.items;
         config.items = [];

         Ext.each(items, function(item) {
             var cfg = {
                xtype: 'container',
                autoHeight: true,
                minWidth: 10,
                width: item.width,
                fieldDefaults: {
                    labelAlign: item.labelAlign || 'top'
                },
                layout: 'anchor',
                items: [item]
             };
             if (!item.width) {
                 cfg.flex = item.flex || 1;
             }
             config.items.push(cfg);
         });

         Zenoss.form.FieldRow.superclass.constructor.call(this, config);

     }
 });

})();
