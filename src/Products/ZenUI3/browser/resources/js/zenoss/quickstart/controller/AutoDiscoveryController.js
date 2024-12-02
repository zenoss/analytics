/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    var router = Zenoss.remote.JobsRouter;

    /**
     * @class Zenoss.quickstart.Wizard.controller.AutoDiscoveryController
     * This is the controller for the auto discovery page of the wizard
     * @extends Ext.app.Controller
     */
    Ext.define('Zenoss.quickstart.Wizard.controller.AutoDiscoveryController', {
        models: ["Discovery"],
        views: [
            "AutoDiscoveryView",
            "JobLog"
        ],
        refs: [{
            ref: 'discoveryForm',
            selector: 'wizardautodiscoveryview'
        }, {
            ref: 'discoveryGrid',
            selector: 'discoverygrid'
        }, {
            ref: 'discoveryButton',
            selector: 'button[itemId="discoverButton"]'
        }],
        extend: 'Ext.app.Controller',
        init: function() {
            this.control({
                'wizardautodiscoveryview': {
                    show: function() {
                        // focus on the ip ranges when the user
                        // first sees this wizard step
                        Ext.getCmp('wizard_ip_ranges').focus();

                        // setup the default values for snmp communities
                        var cmp = Ext.getCmp('wizard_snmp_communities');

                        if (!cmp.getValue()) {
                            Zenoss.remote.PropertiesRouter.getZenProperty({
                                uid: '/zport/dmd/Devices/Discovered',
                                zProperty: 'zSnmpCommunities'
                            }, function(response){
                                cmp.setValue(response.data.valueAsString);
                            });
                        }
                        this.startDiscoveryGridRefresh();

                        // if the form is blank disable the button
                        if (!Ext.getCmp('wizard_ip_ranges').getValue()) {
                            this.getDiscoveryButton().disable();
                        }
                        Ext.getCmp('wizard_ip_ranges').focus();
                        // hack to get the empty text to show up
                        Ext.Function.defer( function() {
                            if (this.getDiscoveryGrid().getStore().data.length === 0) {
                                this.getDiscoveryGrid().getStore().load();
                            }
                        }, 500, this);
                    },
                    'validitychange': function(form, isValid) {
                        this.getDiscoveryButton().setDisabled(!isValid);
                    }
                },
                'button[itemId="discoverButton"]': {
                    click: Ext.bind(this.onClickDiscoverButton, this)
                }

            });
            this.callParent(arguments);
        },
        getFormValues: function() {
            var form = this.getDiscoveryForm();
            return form.getForm().getFieldValues();
        },
        onClickDiscoverButton: function() {
            // get all the values from the form
            var values = this.getFormValues(), params, ranges, zProperties = {};
            ranges = values.ip_ranges.split(",");
            ranges = ranges.concat(values.ip_ranges.split("\n"));
            ranges = Ext.Array.unique(ranges);
            // try to grab the zproperties from the input names so
            // we don't have to duplicate it here
            for (var key in values) {
                if (key.startswith('z')) {
                    zProperties[key] = values[key];
                }
            }
            if ('zSnmpCommunities' in zProperties) {
                zProperties['zSnmpCommunities'] = Ext.htmlEncode(zProperties['zSnmpCommunities']).split("\n");
            }
            params = {
                networks: ranges,
                zProperties: zProperties,
                collector: values.collector
            };
            // submit it to the server to get the job id and status
            Zenoss.remote.NetworkRouter.newDiscoveryJob(params, function(response){
                if (response.success) {
                    var i=0, data = response.data;
                    for(i=0;i< data.length; i++) {
                        Ext.applyIf(data[i], params);
                        this.addJobRecord(data[i]);
                    }

                    Zenoss.remote.MessagingRouter.getUserMessages();
                }
            }, this);

        },
        /**
         * This is the callback from the router scheduleDiscoveryJob.
         * It creates a new model entry and populates the discovery grid.
         * The results look something like this:
         *   {
         *     description: "Discover IP range 10.87.110.0-255",
         *     finished: null,
         *     id: "0f11d05c-359f-4b01-8d59-c0957dc5d9e8",
         *     inspector_type: "Object Manager",
         *     meta_type: "Object Manager",
         *     name: "JobManager",
         *     scheduled: 1407781945,
         *     started: null,
         *     status: "PENDING",
         *     type: "Shell Command",
         *     uid: "/zport/dmd/JobManager",
         *     user: "admin",
         *     uuid: "0f11d05c-359f-4b01-8d59-c0957dc5d9e8"
         *    }
         **/
        addJobRecord: function(params) {
            var record = Ext.create('Zenoss.quickstart.Wizard.model.Discovery', params);
            this.getDiscoveryGrid().getStore().add(record);
        },
        startDiscoveryGridRefresh: function() {
            this.refreshTask = Ext.util.TaskManager.newTask({
                run: this.refreshDiscoveryGrid,
                interval: 5000,
                scope: this
            });
            this.refreshTask.start();
        },
        /**
         * Iterate through every job record we have added thus far,
         * and get its current status.
         **/
        refreshDiscoveryGrid: function() {
            var store = this.getDiscoveryGrid().getStore();
            store.data.each(function(record){
                router.getInfo({
                    jobid: record.get('uuid')
                    }, function(response) {
                        record.set(response.data);
                    });
            });
        }
    });
})();
