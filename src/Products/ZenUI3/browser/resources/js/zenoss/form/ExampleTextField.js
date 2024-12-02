/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2012, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


(function() {
    /**
     * A regular text field that allows a person to provide an example of
     * valid input. This will appear in italics next to the input
     *
     *
     *@class Zenoss.form.ExampleTextField
     *@extends Ext.form.field.Text
     */
    Ext.define("Zenoss.form.ExampleTextField", {
        alias:['widget.exampletextfield'],
        extend:"Ext.form.field.Text",
        /**
         * @cfg {String} example A custom example message to display to the bottom right of the field.
         */
        config: {
            example: null
        },
        fieldSubTpl: [ // note: {id} here is really {inputId}, but {cmpId} is available
            '<input id="{id}" type="{type}" {inputAttrTpl}',
            ' size="1"', // allows inputs to fully respect CSS widths across all browsers
            '<tpl if="name"> name="{name}"</tpl>',
            '<tpl if="value"> value="{[Ext.util.Format.htmlEncode(values.value)]}"</tpl>',
            '<tpl if="placeholder"> placeholder="{placeholder}"</tpl>',
            '<tpl if="maxLength !== undefined"> maxlength="{maxLength}"</tpl>',
            '<tpl if="readOnly"> readonly="readonly"</tpl>',
            '<tpl if="disabled"> disabled="disabled"</tpl>',
            '<tpl if="tabIdx"> tabIndex="{tabIdx}"</tpl>',
            '<tpl if="fieldStyle"> style="{fieldStyle}"</tpl>',
            ' class="{fieldCls} {typeCls} {editableCls}" autocomplete="off"/><span class="example">Example: {example}</span>',
            {
                disableFormats: true
            }
        ],

        constructor: function(config){
            config = config || {};
            config.style = config.style || {};
            // make sure there is enough room for the example
            Ext.applyIf(config.style, {
                paddingBottom: 20
            });
            this.callParent([config]);
        },
        getSubTplData: function() {
            var me = this;

            return Ext.apply(me.callParent(), {
                example   : me.example
            });
        }
    });


}());
