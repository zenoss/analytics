/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2011, 2021 all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){
    var router = Zenoss.remote.DeviceRouter;

    /**
     * @class Zenoss.dialog.NotClosableDialogButton
     * @extends Zenoss.dialog.DialogButton
     * A button that doesn't close the dialog after click
     * @constructor
     */
    Ext.define("Zenoss.dialog.NotClosableDialogButton", {
        extend: "Zenoss.dialog.DialogButton",
        alias: ['widget.NotClosableDialogButton'],
        constructor: function (config) {
            Zenoss.dialog.DialogButton.superclass.constructor.call(this, config);
        },
        setHandler: function (handler, scope) {
            Zenoss.dialog.DialogButton.superclass.setHandler.call(this, handler, scope);
        }
    });

    /**
     * @class Zenoss.form.RenameDevice
     * @extends Zenoss.SmartFormDialog
     * Dialog for renaming a Device
     **/
    Ext.define('Zenoss.form.RenameDevice',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 310,
                width: 500,
                padding: '20 40 20 18',
                id: 'rename_device_dialog',
                title: _t('Reidentify Device'),
                submitHandler: Ext.bind(this.handleSubmit, this),

                items: [{
                    xtype: 'hidden',
                    name: 'uid',
                    value: config.uid
                },{
                    xtype: 'displayfield',
                    padding: '0 0 14 0',
                    value: _t(config.uid.split("/devices/")[1]),
                    labelAlign: 'left',
                    fieldLabel: _t('Current ID:')
                }, {
                    xtype: 'idfield',
                    padding: '0 0 14 0',
                    name: 'newId',
                    labelAlign: 'left',
                    fieldLabel: _t('New ID'),
                    allowBlank: false
                }, {
                    padding: '20 48 20 0',
                    xtype: 'displayfield',
                    fieldCls: 'x-form-display-field-jumbo',
                    value: _t('Caution: Existing performance data stored for this device will be lost.')
                }]
            });
            this.callParent([config]);
        },
        renameDevice: function(values) {
            router.renameDevice(values, function(response){
                if (response.success) {
                    var uid = response.uid;
                    window.location = uid;
                }
            });
        },
        closeDialog: function () {
            Ext.getCmp('rename_device_dialog').destroy();
        },
        handleSubmit: function (values) {
            if(values.retainGraphData) {
                Ext.create('Zenoss.dialog.SimpleMessageDialog', {
                    title: _t('Possible Data Loss'),
                    message: Ext.String.format(_t("Are you sure? Possible data loss for the devices \
                                                   that has a large number of components")),
                    buttons: [{
                        xtype: 'DialogButton',
                        text: _t('OK'),
                        handler: Ext.bind(function() {
                            this.renameDevice(values);
                            this.closeDialog();
                        }, this),
                    }, Zenoss.dialog.CANCEL]
                }).show();

            } else {
                this.renameDevice(values);
                this.closeDialog();
            }
        },
    });

    /**
     * @class Zenoss.form.DeleteDevice
     * @extends Zenoss.SmartFormDialog
     * Dialog for deleting a Device
     **/
    Ext.define('Zenoss.form.DeleteDevice',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 175,
                title: _t('Delete Device'),
                submitHandler: Ext.bind(this.removeDevice, this),
                items: [{
                    xtype: 'hidden',
                    name: 'uid',
                    value: config.uid
                },{
                    xtype: 'panel',
                    bodyStyle: 'font-weight: bold; text-align:center',
                    html: _t('Are you sure you want to remove this device? '+
                             'There is no undo.')
                },{
                    name: "deleteEvents",
                    fieldLabel: _t('Close Events?'),
                    xtype: 'checkbox',
                    checked: true
                }]
            });
            this.callParent([config]);
        },
        removeDevice: function(values) {
            var deviceClass= values.uid.split("/devices")[0],
                options = {
                action: 'delete',
                uids: [values.uid],
                hashcheck: 1,
                deleteEvents: values.deleteEvents
            };

            router.removeDevices(options, function(response){
                if (response.success) {
                    window.location = deviceClass;
                }
            });
        },
        initComponent: function() {
            this.callParent(arguments);
            var btn = this.query("button[ref='buttonSubmit']")[0];
            btn.setDisabled(false);
        }
    });


}());
