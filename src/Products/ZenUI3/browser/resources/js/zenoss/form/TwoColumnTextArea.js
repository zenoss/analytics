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
/**
 * This is a special case of a text area. It is designed to take up the entire column
 * on a two column layout.
 **/
Ext.define("Zenoss.form.TwoColumnTextArea", {
    alias:['widget.twocolumntextarea'],
    extend:"Ext.form.TextArea",
     constructor: function(config) {
         config.width = 500;
         config.height = 220;
         Zenoss.form.TwoColumnTextArea.superclass.constructor.apply(this, arguments);
     }
 });

})();
