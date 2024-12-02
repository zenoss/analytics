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

Ext.define("Zenoss.form.UpDownField", {
    alias:['widget.updownfield'],
    extend:"Ext.form.ComboBox",
     constructor: function(config) {
         config = Ext.applyIf(config||{}, {
             editable: false,
             forceSelection: true,
             autoSelect: true,
             triggerAction: 'all',
             queryMode: 'local',
             store: [
                 [1, 'Up'],
                 [0, 'Down']
             ]
         });
         Zenoss.form.UpDownField.superclass.constructor.call(this, config);
     }
 });


})();
