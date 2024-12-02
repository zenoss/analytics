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
     Ext.define("Zenoss.form.EventClass", {
         alias:['widget.eventclass'],
         extend:"Ext.form.ComboBox",
         constructor: function(config) {
             config = config || {};
             if (!Zenoss.env.EVENT_CLASSES) {
                 throw "You must include the js-snippets viewlet before you use the eventClass control";
             }
             Ext.applyIf(config, {
                 name: 'eventClass',
                 typeAhead: true,
                 editable: true,
                 forceSelection: true,
                 autoSelect: true,
                 triggerAction: 'all',
                 listConfig: {
                     maxWidth:250,
                     maxHeight: 250,
                     resizable: true
                 },
                 queryMode: 'local',
                 store: Zenoss.env.EVENT_CLASSES
             });
             this.callParent([config]);
         }
     });

}());
