/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function() {
    Ext.ns('Zenoss.Action');

    Ext.define('Zenoss.PermissionableAction', {
        permitted: false,
        filtered: false,
        updateDisabled: function() {
            this.setDisabled(this.checkDisabled());
        },
        checkDisabled: function() {
            return !(this.permitted || this.filtered);
        },
        checkPermitted: function() {
            if (this.permission) {
                if (this.permissionContext) {
                    if (Zenoss.env.PARENT_CONTEXT === this.permissionContext) {
                        return Zenoss.Security.hasPermission(this.permission);
                    } else {
                        return Zenoss.Security.hasGlobalPermission(this.permission);
                    }
                } else {
                    return !Zenoss.Security.doesNotHavePermission(this.permission);
                }
            } else {
                return true;
            }
        },
        setPermission: function(config) {
            var me = this;
            var recheck = function() {
                me.permitted = me.checkPermitted();
                me.updateDisabled();
            };
            // if they set the permissions config property
            // and the logged in user does not have permission, disable this element
            if (config.permission) {
                this.permission = config.permission;
                // register the control to be disabled or enabled based on the current context
                if (config.permissionContext) {
                    this.permissionContext = config.permissionContext;
                    Zenoss.Security.onPermissionsChange(recheck);
                } else {
                    // update when the context changes
                    Zenoss.Security.onPermissionsChange(recheck, this);
                }
            }
            this.permitted = this.checkPermitted();
        }
    });

    function setDisabled(disable) {
        this.callParent([this.checkDisabled()]);
    }

    Ext.define("Zenoss.Action", {
        extend: "Ext.menu.Item",
        alias: ['widget.Action'],
        mixins: {
            permissions: 'Zenoss.PermissionableAction'
        },
        constructor: function(config){
            this.setPermission(config);
            this.filtered = config.filtered;
            config.disabled = this.checkDisabled();
            this.callParent([config]);
        },
        setDisabled: setDisabled
    });

    Ext.define("Zenoss.ActionButton", {
        extend: "Ext.button.Button",
        alias: ['widget.buttonaction'],
        mixins: {
            permissions: 'Zenoss.PermissionableAction'
        },
        constructor: function(config){
            this.setPermission(config);
            this.filtered = config.filtered;
            config.disabled = this.checkDisabled();
            this.callParent([config]);
        },
        setDisabled: setDisabled
    });
}());
