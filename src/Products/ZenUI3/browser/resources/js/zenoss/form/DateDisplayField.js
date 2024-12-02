/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function() {
    Ext.define("Zenoss.form.DateDisplayField", {
        alias:['widget.datedisplayfield'],
        extend:"Ext.form.field.Display",
        dateFormat: Zenoss.USER_DATE_FORMAT + ' ' + Zenoss.USER_TIME_FORMAT,

        constructor: function(config) {
            config = config || {};
            config.value = this.formatDate(config.value);
            this.callParent([config]);
        },

        formatDate: function(date) {
            return Zenoss.render.date(date, this.dateFormat)
        },

        setValue: function(value) {
            this.callParent([this.formatDate(value)]);
        },

        afterRender: function(){
            Zenoss.registerTooltip({
                html: Zenoss.USER_TIMEZONE,
                target: this.getInputId()
            });
        }
    });
}());
