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
     * @class Zenoss.quickstart.Wizard.controller.AddDeviceController
     * This is the controller for the auto discovery page of the wizard
     * @extends Ext.app.Controller
     */
    Ext.define('Zenoss.quickstart.Wizard.controller.AddDeviceController', {
        models: [],
        views: [
            "AddDeviceView"
        ],
        refs: [{
            selector: 'wizardadddeviceview',
            ref: "form"
        }, {
            selector: 'deviceaddgrid',
            ref: 'grid'
        }],
        extend: 'Ext.app.Controller',
        init: function() {
            this.control({
                'wizardadddeviceview': {
                    show: function() {
                        this.setCategories();
                        this.setResubmitHandler();
                    }
                },
                'radiogroup[itemId="category"]': {
                    change: function(grp, val) {
                        this.setDeviceTypes(val.category);
                    }
                },
                'grid[itemId="deviceType"]': {
                    select: function(select, record, index){
                        var val = record.get("value");
                        if (!val) {
                            // select the first item
                            this.getCredentials(select.getStore().getAt(0).get('value'));
                        } else {
                            this.getCredentials(val);
                        }
                    }
                },
                'fieldset[itemId="credentials"]': {
                    afterrender: function(fieldset) {
                        fieldset.add({
                            xtype: 'panel',
                            html: Ext.String.format("<i>{0}</i>", _t('Please select a Device Type...'))
                        });
                        fieldset.getEl().mask();
                    }
                },
                'deviceaddgrid': {
                    afterrender: function() {
                        this.startGridRefresh();
                    }
                }
            });
            this.callParent(arguments);
        },
        setCategories: function() {
            // hack to get the empty text to show up
            Ext.Function.defer( function() {
                if (this.getGrid().getStore().data.length === 0) {
                    this.getGrid().getStore().load();
                }
            }, 500, this);
            Zenoss.remote.DeviceRouter.asyncGetTree({
                id: '/zport/dmd/Devices'
            }, function(response){
                var nodes = response[0].children,
                    i,
                    categories = [],
                    checked = true,
                    radiogroup = this.getForm().query('radiogroup[itemId="category"]')[0];

                for (i=0; i<nodes.length; i++) {
                    if (nodes[i].text.text === "Discovered") {
                        continue;
                    }
                    categories.push({
                        boxLabel: nodes[i].text.text, name: 'category', inputValue: nodes[i].uid,  checked: checked
                    });
                    checked = false;
                }
                radiogroup.removeAll();
                radiogroup.add(categories);
                this.setDeviceTypes(categories[0].inputValue);
            }, this);
        },
        setDeviceTypes: function(uid) {
            var grid = this.getForm().query('grid[itemId="deviceType"]')[0],
                store = grid.getStore();

            // reload the grid store and select the first one when done loading
            store.load({
                params: {
                    uid: uid
                },
                callback: function() {
                    grid.selModel.doSelect(store.getAt(0));
                }
            });
        },
        // expects a string and returns a list of unique tokens
        // this method is complicated because it returns unique responses
        // and allows the input to be separated by either commas or newlines or both interspersed.
        parseHosts: function(hosts) {
            var results = [], i, pieces = hosts.split("\n"), piece, key;
            for (i=0;i<pieces.length;i++) {
                piece = pieces[i];
                if (piece.indexOf(",") !== -1) {
                    for (key in piece.split(",")){
                        results.push(piece.split(",")[key].trim());
                    }
                } else {
                    results.push(piece.trim());
                }
            }
            return Ext.Array.unique(results);
        },
        getCredentials: function(uid) {
            // make sure it is a valid full uid incase the start typing
            if (!uid || !uid.startswith('/zport/dmd')) {
                return;
            }
            Zenoss.remote.DeviceRouter.getConnectionInfo({
                uid: uid
            }, this.addCredentials, this);
        },
        _getCredentialFields: function(connectionInfo){
            var hostField = {
                xtype: 'textarea',
                name: 'hosts',
                allowBlank: false,
                fieldLabel:  _t('Enter multiple similar devices, separated by a comma, using either hostname or IP Address'),
                width: "100%"
            } ,collectorField = {
                xtype: 'combo',
                width: "100%",
                // only show if we have multiple collectors
                hidden: Zenoss.env.COLLECTORS.length === 1,
                // if visible give it a good tabindex
                tabIndex: (Zenoss.env.COLLECTORS.length === 1) ? 100: 2,
                labelAlign: 'top',
                fieldLabel: 'Collector',
                queryMode: 'local',
                store: new Ext.data.ArrayStore({
                    data: Zenoss.env.COLLECTORS,
                    fields: ['name']
                }),
                valueField: 'name',
                value: 'localhost',
                name: 'collector',
                displayField: 'name',
                forceSelection: true,
                editable: false,
                allowBlank: false,
                triggerAction: 'all'
            }, fields = [hostField], i;

            var isSnmp = Ext.Array.some(connectionInfo, function(item) {
                return item.category === 'SNMP';
            });
            // convert the zproperty information into a field
            for (i=0; i < connectionInfo.length; i++ ) {
                var item = Zenoss.zproperties.createZPropertyField(connectionInfo[i]),
                    property = connectionInfo[i],
                    id = property.id;

                item.name = id;
                item.fieldLabel = property.label;
                item.width = "100%";

                if (!property.label) {
                    item.fieldLabel = Zenoss.zproperties.inferZPropertyLabel(id);
                }
                if (item.type !== "password") {
                    item.value = property.value || property.valueAsString;
                }

                if (property.description) {
                    item.inputAttrTpl = " data-qtip='" + property.description + "' ";
                }

                fields.push(item);
            }
            // finally add the collector field if they have more than one collector
            fields.push(collectorField);
            fields.push({
                xtype: 'button',
                formBind: true,
                disabled: true,
                text: _t('Add'),
                handler: Ext.bind(this.onClickAddButton, this)
            });
            return fields;
        },
        addCredentials: function(response) {
            var fieldset = this.getForm().query('fieldset[itemId="credentials"]')[0],
                el = fieldset.getEl(),
                fields = this._getCredentialFields(response.data);
            // we aren't rendered yet
            if (!el) {
                return;
            }
            if (el && el.isMasked()) {
                el.unmask();
            }
            fieldset.removeAll(true);
            fieldset.add(fields);
        },
        /**
         * This method gathers what we need from a device
         * submits it and adds a job record.
         **/
        onClickAddButton: function() {
            var values = this.getForm().getForm().getFieldValues(),
                hosts = values.hosts,
                collector = values.collector,
                zProperties = this.getZProperties(values),
                typeGrid = this.getForm().query('grid[itemId="deviceType"]')[0],
                grid = this.getGrid(),
                deviceClass = typeGrid.selModel.getSelection()[0].get("value");

            // allow either commas to separate or new lines or both
            hosts = this.parseHosts(values.hosts);
            var displayDeviceClass = typeGrid.getStore().findRecord('value', deviceClass, 0, false, true, true).get('shortdescription');
            // go through each host and add a record
            Ext.Array.each(hosts, function(host){
                if (Ext.isEmpty(host)) {
                    return;
                }
                var params = {
                    deviceName: host,
                    deviceClass: deviceClass.replace('/zport/dmd/Devices', ''),
                    zProperties: zProperties,
                    collector: collector,
                    model: true,
                    displayDeviceClass: displayDeviceClass,
                    pendingDelete: true // so we don't update while we are still adding the job
                };
                var record = Ext.create('Zenoss.quickstart.Wizard.model.AddDeviceJobRecord', params);
                grid.getStore().add(record);
                this._AddJob(record);
            }, this);
        },
        getZProperties: function(values) {
            var zProperties = {};
            for (var key in values) {
                if (key.startswith('z')) {
                    zProperties[key] = values[key];
                }
            }
            return zProperties;
        },
        startGridRefresh: function() {
            this.refreshTask = Ext.util.TaskManager.newTask({
                run: this.refreshGrid,
                interval: 5000,
                scope: this
            });
            this.refreshTask.start();
        },
        /**
         * Iterate through every job record we have added thus far,
         * and get its current status.
         **/
        refreshGrid: function() {
            var store = this.getGrid().getStore();
            store.data.each(function(record){
                var status = record.get('status');
                // make sure we aren't in the middle of deleting
                if (record.get('pendingDelete')) {
                    return;
                }
                // make sure we are updatable
                if (status === "STARTED" || status === "PENDING") {
                    Zenoss.remote.JobsRouter.getInfo({
                        jobid: record.get('uuid')
                    }, function(response) {
                        record.set(response.data);
                    });
                }
            });
        },
        setResubmitHandler: function() {
            Ext.getCmp('resubmit_job').handler = Ext.bind(this.resubmitJob, this);
        },
        resubmitJob: function(grid, rowIndex, colIndex, item, e, record) {
            if (record.get('pendingDelete')) {
                return;
            }
            record.set('pendingDelete', true);
            // delete the job and the device
            Zenoss.remote.JobsRouter.deleteJobs({
                jobids: [record.get('uuid')]
            }, function(response) {
                if (response.success) {
                    if (record.get('status') !== "PENDING") {
                        Zenoss.remote.DeviceRouter.removeDevices({
                            uids: [record.get('deviceUid')],
                            action: 'delete',
                            hashcheck: 1
                        }, function() {
                            this._AddJob(record);
                        },
                        this);
                    } else {
                        this._AddJob(record);
                    }
                }
            }, this);
        },
        _AddJob: function(record) {
            var dc = record.get('deviceClass'),
                me = this,
                params = {
                    deviceName: record.get('deviceName'),
                    deviceClass: dc,
                    zProperties: record.get('zProperties'),
                    collector: record.get('collector'),
                    model: true
                },
                callback = function(response){
                    if (response.success){
                        // On core the second entry is the modeling job and for some zenpacks the first is the modeling job
                        // so always grab the last one
                        var jobRecord = response.new_jobs.pop();
                        // set some properties we need
                        record.set(jobRecord);
                        record.set('status', 'PENDING');
                        record.set('pendingDelete', false);
                        // update the uid incase they rename the host
                        var deviceName = Zenoss.util.ipv6wrap(record.get('deviceName'));
                        record.set("deviceUid", "/zport/dmd/Devices" + record.get('deviceClass') + "/devices/" + deviceName);
                    } else {
                        me.getGrid().getStore().remove(record);
                    }
                };
            if (Zenoss.getCustomDeviceAdder(dc)) {
                Zenoss.getCustomDeviceAdder(dc)(record, callback);
            } else {
                Zenoss.remote.DeviceRouter.addDevice(params, callback, this);
            }
        },
        /**
         * This method and the one below are for the Edit zProperties dialog for a submitted job.
         * This allows the user to modify the credentials of a device once it has already been submitted.
         * Any edit will delete the device and re-add it.
         **/
        fetchConnectionInfoForDialog: function(recordId) {
            var store = this.getGrid().getStore(),
                recordIdx = store.findExact('uuid', recordId), record;

            // if for whatever reason we can't find a record with this Id
            if (recordIdx === -1) {
                return;
            }
            record = store.getAt(recordIdx);

            Zenoss.remote.DeviceRouter.getConnectionInfo({
                uid: "/zport/dmd/Devices" + record.get('deviceClass')
            }, function(response) {
                this.showZPropertiesEditDialog(response, record);
            }, this);
        },
        /**
         * Display the edit zproperties dialog so a user can change
         * the credentials of the device they just added.
         * Pressing submit on the dialog will delete the device and
         * resubmit the job.
         **/
        showZPropertiesEditDialog: function(response, record) {
            var fields = this._getCredentialFields(response.data), i, me = this;
            // remove the first and last element, host and the add button
            fields.shift();
            fields.pop();

            // set the value for the fields to what is in the record
            for (i=0; i<fields.length; i++) {
                fields[i].value = record.get(fields[i].name) || record.get('zProperties')[fields[i].name];
            }

            // show the dialog
            var win = Ext.create('Zenoss.dialog.BaseDialog', {
                items: [{
                    xtype: 'form',
                    ref: 'credForm',
                    defaults: {
                        labelAlign: 'top'
                    },
                    items: fields
                }],
                title: Ext.String.format('Edit Properties for {0}', record.get('deviceName')),
                buttons: [{
                    ui: 'dialog-dark',
                    text: _t('Resubmit'),
                    xtype: 'DialogButton',
                    handler: function() {
                        var values = win.credForm.getForm().getFieldValues();
                        record.set('collector', values.collector);
                        delete values.collector;
                        record.set('zProperties', values);

                        // resubmit the job, send nulls for what is normally sent by the
                        // actioncolumn handler
                        me.resubmitJob(null, null, null, null, null, record);
                    }
                }]
            });
            win.show();
        }
    });


    // globally namespaced function so it can be called from a column handler
    Zenoss.quickstart.Wizard.editZProperties = function(recordId) {
        var controller = window.globalApp.getController("AddDeviceController");
        controller.fetchConnectionInfoForDialog(recordId);
    };

})();
