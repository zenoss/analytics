/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2017, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


/* package level */
(function() {
    Ext.ns('Zenoss.form');

    Ext.define("Zenoss.form.EventAction", {
        alias:['widget.eventaction'],
        extend:"Ext.form.ComboBox",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                fieldLabel: _t('Action'),
                name: 'action',
                editable: false,
                forceSelection: true,
                autoSelect: true,
                triggerAction: 'all',
                queryMode: 'local',
                store: Zenoss.env.ACTIONS
            });
            this.callParent(arguments);
        }
    });
}());
