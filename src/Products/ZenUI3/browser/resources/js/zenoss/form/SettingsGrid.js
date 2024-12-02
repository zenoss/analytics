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
    Ext.define("Zenoss.form.SettingsGrid", {
        alias:['widget.settingsgrid'],
        extend:"Ext.form.FormPanel",
        constructor: function(config, itemsConfig) {
            config = config || {};
            var i,
                me = this,
                prop;

            // build the properties and editors
            for (i=0; i < itemsConfig.length; i++){
                prop = itemsConfig[i];
                prop.fieldLabel = prop.name;
                if (!Ext.isDefined(prop.value)) {
                    prop.value = prop.defaultValue;
                }
                if (prop.xtype === "checkbox") {
                    prop.checked = prop.value;
                }
                prop.ref = prop.id;
                prop.name = prop.id;
            }
            this.lastValues = itemsConfig;

            Ext.applyIf(config, {
                autoScroll: 'y',
                layout: 'anchor',
                fieldDefaults: {
                    labelAlign: 'top'
                },
                paramsAsHash: true,
                frame: false,
                buttonAlign: 'left',
                defaults: {
                    anchor: '95%',
                    labelStyle: 'font-size: 13px; color: #5a5a5a'
                },
                bodyStyle: 'padding: 10px',
                listeners: {
                    validitychange: function(form, isValid) {
                        me.query('button')[0].setDisabled(!isValid);
                    },
                    afterrender: function(form){
                        this.getForm().checkValidity();
                    },
                    scope: this
                },
                isDirty: function(){
                    return true;
                },
                buttons: [{
                    text: _t('Save'),
                    ref: '../savebtn',
                    formBind: true,
                    handler: function(btn){
                        var values = {};
                        Ext.each(itemsConfig, function(prop){
                            values[prop.id] = me[prop.id].getValue();
                        });
                        config.saveFn({values: values}, function(response){
                            if (response.success){
                                var message = _t("Configuration updated");
                                Zenoss.message.info(message);
                            }
                        });
                    }
                },{
                    text: _t('Cancel'),
                    ref: '../cancelbtn',
                    handler: function(btn) {
                        var form = btn.refOwner;
                        form.setInfo(form.lastValues);
                    }
                }],
                items: itemsConfig,
                setInfo: function(data) {
                    var me = this;
                    Ext.each(data, function(prop){
                        me[prop.id].setValue(prop.value);
                    });
                },

                autoHeight: true,
                viewConfig : {
                    forceFit: true
                }
            });
            this.callParent(arguments);
        }
    });


}());
