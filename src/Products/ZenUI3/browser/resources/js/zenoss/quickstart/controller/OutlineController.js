/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){

    /**
     * @class Zenoss.quickstart.Wizard.controller.OutlineController
     * This is the controller for the first page of the wizard
     * @extends Ext.app.Controller
     */
    Ext.define('Zenoss.quickstart.Wizard.controller.OutlineController', {
        models: [],
        views: [
            "OutlineView"
        ],

        extend: 'Ext.app.Controller',
        init: function() {
            var me = this;
            this.control({
                'image[itemId="get_started"]': {
                    afterrender: function(image) {
                        image.getEl().on('click', me.onClickGetStarted, me);
                        image.getEl().setStyle('cursor', 'pointer');
                    }
                }
            });

            // grab the hostname and save it
            Zenoss.remote.SettingsRouter.setDmdSettings({"zenossHostname":window.location.origin});
        },
        onClickGetStarted: function() {
            this.getApplication().fireEvent('nextstep');
        }
    });
})();