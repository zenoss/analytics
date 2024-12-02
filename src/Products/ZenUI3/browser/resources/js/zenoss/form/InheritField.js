/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


(function() {

Ext.ns('Zenoss.form');

Ext.define("Zenoss.form.InheritField", {
    extend: "Zenoss.form.FieldRow",
    alias: ['widget.inheritfield'],
    constructor: function(config) {
        var item;

        // Take the first member of items
        if (Ext.isObject(config.items)) {
            item = config.items;
        } else {
            item = config.items[0];
        }

        // Add the checkbox
        this.inheritbox = new Ext.form.Checkbox({
            fieldLabel: _t('Inherit?'),
            width: 60
        });
        config.items = [this.inheritbox, item];
        Zenoss.form.InheritField.superclass.constructor.call(this, config);
        this.field = this.items.items[1].items.items[0];
    },
    inherit: function() {
        return this.inheritbox.checked;
    },
    getValue: function() {
        return {
            inherited: this.inherit(),
            value: this.field.getValue()
        };
    },
    setValue: function(value) {
        if (Ext.isObject(value)) {
            this.inheritbox.setValue(
                Ext.isDefined(value.inherited) ? value.inherited : false
            );
            value = value.value;
        } else {
            this.inheritbox.setValue(false);
        }
        this.field.setValue(value);
    }
 });


})();
