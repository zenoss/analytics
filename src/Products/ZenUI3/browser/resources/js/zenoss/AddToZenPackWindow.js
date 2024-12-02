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



/**
 * @class Zenoss.AddToZenPackWindow
 * @extends Zenoss.dialog.BaseWindow
 */
Ext.define("Zenoss.AddToZenPackWindow", {
    alias:['widget.AddToZenPackWindow'],
    extend:"Zenoss.dialog.BaseWindow",
    constructor: function(config) {
        var me = this;
        config = Ext.applyIf(config || {}, {
            title: _t('Add to ZenPack'),
            layout: 'fit',
            modal: true,
            autoHeight: true,
            width: 310,
            plain: true,
            items: [{
                id: 'addzenpackform',
                xtype: 'form',
                listeners: {
                    validitychange: function(form, isValid) {
                        me.query('DialogButton')[0].setDisabled(!isValid);
                    }
                },
                defaults: {width: 250},
                autoHeight: true,
                frame: false,
                fieldDefaults: {
                    labelWidth: 100,
                    labelAlign: 'top'
                },
                buttonAlign: 'left',
                items: [{
                    fieldLabel: _t('ZenPack'),
                    name: 'zpname',
                    xtype: 'combo',
                    emptyText: _t('Please select a ZenPack...'),
                    listEmptyText: _t('No ZenPacks in development mode'),
                    allowBlank: false,
                    listConfig:{
                        resizable: true
                    },
                    store: new Zenoss.NonPaginatedStore({
                        id: 'myzpstore',
                        root: 'packs',
                        model: 'Zenoss.model.Name',
                        totalProperty: 'totalCount',
                        directFn: Zenoss.remote.ZenPackRouter.getEligiblePacks
                    }),
                    valueField: 'name',
                    displayField: 'name',
                    forceSelection: true,
                    triggerAction: 'all',
                    selectOnFocus: true,
                    id: 'zpcombobox'
                }],
                buttons: [{
                    text: _t('Submit'),
                    xtype: 'DialogButton',
                    disabled: true,
                    handler: function () {
                        var form = Ext.getCmp('addzenpackform'),
                            chosenzenpack = form.getForm().findField('zpname').getValue(), i, targets = [], callback;
                        if (!Ext.isArray(me.target)) {
                            targets.push(me.target);
                        } else {
                            targets = me.target;
                        }
                        callback = function() {
                            Zenoss.message.info(_t("The item was added to {0}"), chosenzenpack);
                        };
                        for (i=0; i<targets.length; i++ ) {
                            Zenoss.remote.ZenPackRouter.addToZenPack({
                                topack: targets[i],
                                zenpack: chosenzenpack
                            }, callback);
                        }
                    }
                },{
                    text: _t('Cancel'),
                    xtype: 'DialogButton'
                }]
            }]
        });
        Zenoss.AddToZenPackWindow.superclass.constructor.call(this, config);
    },
    setTarget: function (target) {
        this.target = target;
    }
});


})();
