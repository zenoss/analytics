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
    /**
     * This is a display field that takes an array as its value and
     * renders them with one element per line
     **/
    Ext.define("Zenoss.form.MultiLineDisplayField", {
        alias:['widget.multilinedisplayfield'],
        extend:"Ext.form.DisplayField",
        constructor: function(config) {
            // if a string was passed in then defer to the parents behavior
            if ((typeof config.value) !== 'string') {
                config.value = config.value.join('<br />');
            }

            Zenoss.form.MultiLineDisplayField.superclass.constructor.apply(this, arguments);
        }
    });

}());
