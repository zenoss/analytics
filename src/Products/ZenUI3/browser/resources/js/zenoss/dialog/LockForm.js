(function(){

    /**
     * @class Zenoss.lockpanel
     * @extends Ext.Panel
     * Panel for locking an object
     **/
    Ext.define('Zenoss.LockPanel', {
        extend: 'Ext.panel.Panel',
        alias: ['widget.lockpanel'],
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                listeners:  {
                    show: Ext.bind(this.setCheckboxes, this)
                },
                items: [{
                    xtype: 'panel',
                    frame: false,
                    border: false,
                    layout: 'vbox',
                    height: 110,
                    defaults: {
                        xtype: 'checkbox',
                        flex: 1,
                        align: 'stretch'
                    },
                    items: [{
                        name: 'updates',
                        ref: '../updates',
                        boxLabel: _t('Lock from updates'),
                        listeners: {
                            change: Ext.bind(this.setCheckboxes, this)
                        },
                        checked: config.updatesChecked
                    },{
                        name: 'deletion',
                        ref: '../deletion',
                        boxLabel: _t('Lock from deletion'),
                        listeners: {
                            change: Ext.bind(this.setCheckboxes, this)
                        },
                        checked: config.deletionChecked
                    },{
                        name: 'sendEvent',
                        ref: '../sendEventWhenBlocked',
                        boxLabel: _t('Send an event when an action is blocked'),
                        checked: config.sendEventChecked
                    }]
                }]

            });

            this.callParent([config]);
        },
        /**
          * This dialog consists of three checkboxes.
          * The rules for enabling or disabling the checkboxes:
          *
          * 1. If either updates or deleted is enabled then
          * sendEvents is enabled.
          *
          * 2. If updates is checked then deletion is disabled.
          **/
        setCheckboxes: function() {
            var updatesChecked = this.updates.getValue(),
                    deletionChecked = this.deletion.getValue();
            // rule 1. sendEvents
            if (updatesChecked || deletionChecked) {
                this.sendEventWhenBlocked.enable();
            } else {
                this.sendEventWhenBlocked.setValue(false);
                this.sendEventWhenBlocked.disable();
            }

            // rule 2. updates and deletion
            if (updatesChecked) {
                this.deletion.setValue(true);
                this.deletion.disable();
            } else {
                this.deletion.enable();
            }

        }

    });


    /**
     * @class Zenoss.dialog.LockForm
     * @extends Zenoss.SmartFormDialog
     * Dialog for locking an object.
     **/
    Ext.define('Zenoss.dialog.LockForm',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                submitFn: Zenoss.remote.DeviceRouter.lockDevices,
                applyOptions: Ext.emptyFn,
                height: 220,
                title: _t('Locking'),
                submitHandler: Ext.bind(this.lockObject, this),
                items:{
                    xtype: 'lockpanel',
                    updatesChecked: config.updatesChecked,
                    deletionChecked: config.deletionChecked,
                    sendEventChecked: config.sendEventChecked
                }
            });
            this.callParent([config]);
        },

        lockObject: function(values) {
            this.applyOptions(values);
            this.submitFn(values);
        }
    });
}());
