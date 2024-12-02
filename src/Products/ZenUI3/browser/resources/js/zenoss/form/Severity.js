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
    Ext.define("Severity", {
        alias:['widget.severity'],
        extend:"Ext.form.ComboBox",
        constructor: function(config) {
            config = config || {};

            Ext.applyIf(config, {
                fieldLabel: _t('Severity'),
                name: 'severity',
                editable: false,
                forceSelection: true,
                autoSelect: true,
                triggerAction: 'all',
                queryMode: 'local',
                // this is defined in zenoss.js so should always be present
                store: Zenoss.env.SEVERITIES
            });
            this.callParent(arguments);
        }
    });


    Ext.define("ReverseSeverity", {
        alias:['widget.reverseseverity'],
        extend:"Severity",
        constructor: function(config) {
            var severities = [[0, "Critical"], [1, "Error"], [2, "Warning"], [3, "Info"], [4, "Debug"], [5, "Clear"]];
            config = config || {};
            Ext.applyIf(config, {
                store: severities
            });
            this.callParent(arguments);
        }
    });

    Ext.define("DefaultSeverity", {
        alias:['widget.defaultseverity'],
        extend:"Severity",
        constructor: function(config) {
            var severities = [[-1, "Default"]].concat(Zenoss.env.SEVERITIES);
            config = config || {};
            Ext.applyIf(config, {
                store: severities
            });
            this.callParent(arguments);
        }
    });

}());
