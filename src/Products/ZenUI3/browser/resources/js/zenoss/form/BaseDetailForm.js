/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function() {

var ZF = Ext.ns('Zenoss.form');

Ext.form.TextArea.prototype.grow = true;
Ext.form.TextArea.prototype.growMin = 20;


ZF.createDirectSubmitFunction = function(router) {

    // called in the Ext.form.Action.DirectSubmit.run method
    return function(formElDom, successFunction, directSubmitAction) {

        var form = directSubmitAction.form;

        // copy field values to the info object for fields that
        //   * are dirty (param passed to getFieldValues above)
        //   * have submitValue true
        //   * have an id or name set on them
        var info = {};
        var dirtyFieldValues = form.getValues(false, true);

        Ext.iterate(dirtyFieldValues, function(key, value) {
            var field = form.findField(key);
            if ( field.submitValue !== false && field.getName().indexOf("ext-gen") !== 0 ) {
                info[key] = value;
            }
        });


        // add the forms baseParams to the info object (often includes uid)
        Ext.applyIf(info, directSubmitAction.getParams());

        Ext.iterate(info, function(key, value) {
            if (key.indexOf("ext-gen") !== 0 ) {
                info[key] = value;
            }else {
                delete info[key];
            }
        });

        // define a callback to run after server responds
        var callback = function() {
            form.clearInvalid();
            form.setValues(dirtyFieldValues); // isDirty() will return false now
            form.afterAction(directSubmitAction, true);
            form.reset();
            Zenoss.message.info(_t("Details updated successfully"));
        };

        // the remote call
        router.setInfo(info, callback, directSubmitAction);

    };
};

Ext.define("Zenoss.form.BaseDetailForm", {
    extend: "Ext.form.FormPanel",
    alias: ['widget.basedetailform'],
    contextUid: null,
    isLoadInProgress: false,
    constructor: function(config){
        // Router doesn't technically matter, since they all do getInfo, but
        // getForm is definitely defined on DeviceRouter
        var router = config.router || Zenoss.remote.DeviceRouter;
        config.baseParams = Ext.applyIf(config.baseParams||{
            uid: config.contextUid
        });

        config = Ext.applyIf(config||{}, {
            paramsAsHash: true,
            autoScroll: 'y',
            cls: 'detail-form-panel',
            buttonAlign: 'left',
            fieldDefaults: {
                labelAlign: 'top'
            },
            trackResetOnLoad: true,
            permission: 'Manage Device',
            api: {
                submit: ZF.createDirectSubmitFunction(router),
                load: router.getInfo
            }
        });
        var hasPermission = function() {
            var perm = !Zenoss.Security.doesNotHavePermission(config.permission);
            if (Ext.isDefined(config.userCanModify)) {
                return config.userCanModify && perm;
            } else {
                return perm;
            }
        };
        if (hasPermission()) {
            Ext.apply(config, {
                buttons:  [{
                    xtype: 'button',
                    ref: '../savebtn',
                    text: _t('Save'),
                    disabled: true,
                    cls: 'detailform-submit-button',
                    handler: function(btn, e) {
                        this.refOwner.getForm().submit();
                    }
                },{
                    xtype: 'button',
                    ref: '../cancelbtn',
                    disabled: true,
                    text: _t('Cancel'),
                    cls: 'detailform-cancel-button',
                    handler: function(btn, e) {
                        this.refOwner.getForm().reset();
                    }
                }]
            });
        }
        ZF.BaseDetailForm.superclass.constructor.call(this, config);
    },
    initComponent: function() {
        this.callParent(arguments);
        var form = this.getForm();
        form.on('dirtychange', function(form, dirty, options ) {
            if (dirty && form.isValid()) {
                this.setButtonsDisabled(false);
            } else {
                this.setButtonsDisabled(true);
            }
        }, this);
        form.on('validityChange', function(f, valid, eOpts) {
            this.doButtons();
        }, this);
    },
    hasPermission: function() {
        var perm = !Zenoss.Security.doesNotHavePermission(this.permission);
        if (Ext.isDefined(this.userCanModify)) {
            return this.userCanModify && perm;
        } else {
            return perm;
        }
    },
    setButtonsDisabled: function(b) {
        if (this.hasPermission()) {
            this.savebtn.setDisabled(b);
            this.cancelbtn.setDisabled(b);
        }
    },
    doButtons: function() {
        this.setButtonsDisabled(!this.form.isDirty());
    },
    onFieldAdd: function(field) {
        if (!field.isXType('displayfield')) {
            this.mon(field, 'valid', this.doButtons, this);
        }
    },
    getFieldNames: function() {
        var keys = [];
        for (var k in this.getForm().getValues(false, false)) {
            if (Ext.Array.indexOf(keys, k)===-1) {
                keys.push(k);
            }
        }
        return keys;
    },
    load: function() {
        var o = Ext.apply({keys:this.getFieldNames()}, this.baseParams);
        this.form.load(o, function(result) {
            this.form.setValues(result.data);
            this.form.reset();
            this.doLayout();
        }, this);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.baseParams.uid = uid;
        this.isLoadInProgress = true;
        this.load();
    }
});

})();
