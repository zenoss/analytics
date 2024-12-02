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
     Ext.define("Zenoss.form.parser", {
         alias:['widget.parser'],
         extend:"Ext.form.ComboBox",
         constructor: function(config) {
             var record = config.record;
             config = config || {};
             Ext.applyIf(config, {
                 fieldLabel: _t('Parser'),
                 name: 'parser',
                 editable: false,
                 forceSelection: true,
                 autoSelect: true,
                 triggerAction: 'all',
                 matchFieldWidth: false,
                 listConfig: {
                     resizable: true,
                     minWidth: 250
                 },
                 queryMode: 'local',
                 store: record.availableParsers
             });
             this.callParent(arguments);
         }
     });

}());
