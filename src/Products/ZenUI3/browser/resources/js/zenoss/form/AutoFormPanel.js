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

var ZF = Ext.ns('Zenoss.form');

Ext.define("Zenoss.form.AutoFormPanel", {
    extend: "Zenoss.form.BaseDetailForm",
    alias: ['widget.autoformpanel']
});



/*
* Zenoss.form.getGeneratedForm
* Accepts a uid and a callback.
* Asks the router for a form for the object represented by uid.
* Returns a config object that can be added to a container to render the form.
*/
ZF.getGeneratedForm = function(uid, callback, router) {
    // Router doesn't technically matter, since they all do getInfo, but
    // getForm is definitely defined on DeviceRouter
    router = router || Zenoss.remote.DeviceRouter;
    router.getForm({uid:uid}, function(response){
        callback(Ext.apply({
            xtype:'autoformpanel',
            contextUid: uid,
            layout: 'column',
            defaults: {
                layout: 'anchor',
                bodyStyle: 'padding:10px',
                fieldDefaults: {
                    labelAlign: 'top'
                },
                columnWidth: 0.5
            }
        }, response.form));
    });
};

Ext.define("Zenoss.form.AutoFormCombo", {
    extend: "Ext.form.ComboBox",
    alias: ['widget.autoformcombo'],
     constructor: function(config) {
         config = Ext.applyIf(config||{}, {
             editable: false,
             forceSelection: true,
             autoSelect: true,
             triggerAction: 'all',
             queryMode: 'local',
             store: config.values || []
         });
         Zenoss.form.AutoFormCombo.superclass.constructor.call(this, config);
     }

});


})();
