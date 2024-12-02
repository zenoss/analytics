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
     Ext.define("Zenoss.form.rrdtype", {
         alias:['widget.rrdtype'],
         extend:"Ext.form.ComboBox",
         constructor: function(config) {
             var record = config.record;
             config = config || {};
             var store = [];
             Ext.each(record.availableRRDTypes, function(item) {
                 store.push([item]);
             });
             Ext.apply(config, {
                 fieldLabel: _t('RRD Type'),
                 name: 'rrdtype',
                 editable: false,
                 forceSelection: true,
                 autoSelect: true,
                 triggerAction: 'all',
                 queryMode: 'local',
                 displayField: 'name',
                 valueField: 'name',
                 store:  Ext.create('Ext.data.ArrayStore', {
                     model: 'Zenoss.model.Name',
                     data: store
                 })
             });
             this.callParent(arguments);
         }
     });

}());
