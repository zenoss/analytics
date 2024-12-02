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

Ext.define("Zenoss.form.Password", {
    alias:['widget.password'],
    extend:"Ext.form.TextField",
    constructor: function(config) {
         config.inputType = 'password';
         Zenoss.form.Password.superclass.constructor.apply(this, arguments);
     }
 });


})();
