/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.onReady(function () {

    Ext.ns('Zenoss.devices');


    // Extensions used on this page
    Ext.ns('Zenoss.extensions');
    var EXTENSIONS_adddevice = Zenoss.extensions.adddevice instanceof Array ?
        Zenoss.extensions.adddevice : [];
    Zenoss.env.treesm = null;

    // page level variables
    var REMOTE = Zenoss.remote.DeviceRouter;
    var deviceButtonsDisabled = false;

    Zenoss.env.initProductionStates();
    Zenoss.env.initPriorities();

    // get pairs [<zProperty name>, <zProperty type>]
    REMOTE.getAllCredentialsProps({}, function (data) {
        Zenoss.env.allCredentialsProps = data['data'];
    });

    var resetCombo = function (combo, manufacturer) {
        combo.clearValue();
        combo.getStore().setBaseParam('manufacturer', manufacturer);
        delete combo.lastQuery;
    };

    var hwManufacturers = {
        xtype: 'manufacturercombo',
        name: 'hwManufacturer',
        fieldLabel: _t('HW Manufacturer'),
        listeners: {
            'select': function (combo, record) {
                record = record[0];
                var productCombo = Ext.getCmp('hwproductcombo');
                resetCombo(productCombo, record.data.name);
            }
        }
    };

    var hwProduct = {
        xtype: 'productcombo',
        prodType: 'HW',
        listConfig: {
            resizable: true,
            minWidth: 250
        },
        name: 'hwProductName',
        fieldLabel: _t('HW Product'),
        id: 'hwproductcombo'
    };

    var osManufacturers = {
        xtype: 'manufacturercombo',
        name: 'osManufacturer',
        fieldLabel: _t('OS Manufacturer'),
        listeners: {
            'select': function (combo, record) {
                var record = record[0];
                var productCombo = Ext.getCmp('osproductcombo');
                resetCombo(productCombo, record.data.name);
            }
        }
    };

    var osProduct = {
        xtype: 'productcombo',
        prodType: 'OS',
        listConfig: {
            resizable: true,
            minWidth: 250
        },
        name: 'osProductName',
        id: 'osproductcombo',
        fieldLabel: _t('OS Product')
    };

    var deviceClassCombo = {
        xtype: 'combo',
        width: 300,
        name: 'deviceClass',
        fieldLabel: _t('Device Class'),
        id: 'add-device_class',
        typeAhead: true,
        forceSelection: true,
        valueField: 'name',
        displayField: 'name',
        allowBlank: false,
        queryMode: 'local',
        listConfig: {
            resizable: true,
            minWidth: 250
        },
        store: new Ext.data.DirectStore({
            id: 'deviceClassStore',
            root: 'deviceClasses',
            totalProperty: 'totalCount',
            model: 'Zenoss.model.Name',
            directFn: REMOTE.getDeviceClassesToAdd,
            filters: function(rec) {
                return !!rec.get('name') && rec.get('name') != "/";
            }
        }),
        listeners: {
            'afterrender': function (component) {
                component.store.load({
                    scope: this,
                    callback: function (records, operation, success) {
                        var selnode = getSelectionModel().getSelectedNode();
                        var isclass = selnode.data.uid.startswith('/zport/dmd/Devices');

                        if (selnode.data.uid === "/zport/dmd/Devices" || !isclass) {
                            //root node doesn't have a path attr
                            this.setValue(this.store.first());
                        }
                        else if (isclass) {
                            var path = selnode.data.path;
                            path = path.replace(/^Devices/, '');
                            if (this.findRecordByValue(path)) {
                                this.setValue(path);
                            }
                        }
                    }
                });
            },
            'change': function () {
                this.toggleAdditionalFields();
            },
            focus: function(combo) {
                combo.expand();
            }
        },
        toggleAdditionalFields: function () {
            if (!this.getValue()) {
                return;
            }
            REMOTE.getCredentialsProps({ deviceClass: this.getValue() }, function (data) {
                var credsProps = data['data'],
                    unusedCreds = Zenoss.env.allCredentialsProps.filter(function (prop) {
                        return credsProps[prop[0]] === undefined;
                    });
                for (prop in credsProps) {
                    Ext.getCmp(prop).setValue(credsProps[prop]);
                    Ext.getCmp(prop).show();
                }
                unusedCreds.forEach(function (prop) {
                    Ext.getCmp(prop[0]).hide();
                });
            });
        }
    };

    function setDeviceButtonsDisabled(bool) {
        // Save the flag so we can enable/disable these on permission change.
        deviceButtonsDisabled = bool;
        // must also check permissions before enable/disable the
        // 'deleteDevices' button
        Zenoss.devices.deleteDevices.setDisabled(bool ||
            Zenoss.Security.doesNotHavePermission('Delete Device'));
        if (Ext.getCmp('commands-menu')) {
            Ext.getCmp('commands-menu').setDisabled(bool ||
                Zenoss.Security.doesNotHavePermission('Run Commands'));
        }
        if (Ext.getCmp('actions-menu')) {
            Ext.getCmp('actions-menu').setDisabled(bool ||
                (Zenoss.Security.doesNotHavePermission('Change Device Production State') &&
                 Zenoss.Security.doesNotHavePermission('Manage Device')));
        }


    }

    function resetGrid() {
        Ext.getCmp('device_grid').refresh();
        setDeviceButtonsDisabled(true);
    }

    /**
      * Returns the selection model for the last selected tree, if no
      * trees have been selected then return the selection model for devices
      **/
    function getSelectionModel() {
        if (Zenoss.env.treesm) {
            return Zenoss.env.treesm;
        }
        return Ext.getCmp('devices').getSelectionModel();
    }

    /**
     * Each tree has a selection model but to the user
     * we only want to show one selection at any time.
     **/
    function deselectOtherTrees(treeid) {
        var treeids = Zenoss.util.filter(Ext.ComponentQuery.query('HierarchyTreePanel'),
            function (t) {
                return t.id !== treeid;
            });
        Ext.each(treeids, function (tree) {
            var sm = tree.getSelectionModel();
            if (sm.getSelectedNode()) {
                // do not fire deselect listeners
                sm.deselect(sm.getSelectedNode(), true);
            }
        });
    }

    /**
     * Anytime a node is clicked on one of the organizer trees this method is called.
     **/
    function treeselectionchange(sm, newnodes) {
        if (newnodes.length) {
            deselectOtherTrees(sm.tree);
            // update the treesm
            Zenoss.env.treesm = sm;
            var newnode = newnodes[0];
            var uid = newnode.data.uid;

            Zenoss.env.contextUid = uid;

            // ZEN-22556: now that we have more than one panel in addition to the device_grid
            // always switch back to the default panel when selection changed
            Ext.getCmp('detail_panel').layout.setActiveItem(0);

            Zenoss.util.setContext(uid, 'detail_panel', 'commands-menu', 'footer_bar');
            // explicitly set the new security context (to update permissions)
            Zenoss.Security.setContext(uid);

            // this router request is isolated so it is forced to happen after the other contexts are set
            Ext.getCmp('organizer_events').setContext(uid);

            setDeviceButtonsDisabled(true);

            //should "ask" the DetailNav if there are any details before showing
            //the button
            Ext.getCmp('master_panel').items.each(function (card) {
                card.navButton.setVisible(!newnode.data.hidden);
            });
        }
    }


    function selectedUids() {
        var grid = Ext.getCmp('device_grid'),
            sm = grid.getSelectionModel(),
            rows = sm.getSelection(),
            pluck = Ext.Array.pluck,
            uids = pluck(pluck(rows, 'data'), 'uid');
        return uids;
    }

    function gridUidSelections() {
        return {
            uids: selectedUids(),
            hashcheck: null
        };
    }

    function gridOptions() {
        // we disallow selections past pages so just grab the selected uids
        var opts = {
            uids: selectedUids(),
            hashcheck: null
        };

        return opts;
    }

    function refreshTreePanel() {
        Ext.each(Ext.ComponentQuery.query('HierarchyTreePanel'), function (tree) {
            tree.refresh();
        });
    }


    function deleteDevicesWithProgressBar(grid, uids, opts, callback) {
        grid.setLoading(false);
        var cancelled = false,
            remaining = uids.reverse(),
            win,
            total = remaining.length;

        function deleteDevice(response) {
            if (response && !Ext.isEmpty(response.notRemovedUids)) {
                var notRemovedId = response.notRemovedUids[0].replace("/zport/dmd/", "/");

                // if we weren't able to remove this device id then warn about it. This can happen
                // if we try to remove a device from a group it doesn't belong to.
                var errmsg = Ext.String.format(_t('The following device was not {0}d because it was not in the selected organizer: {1}'),
                    opts.action,
                    notRemovedId);
                Zenoss.message.info(errmsg);
            }

            var msg;
            if (cancelled || remaining.length === 0) {
                grid.getSelectionModel().selectNone();
                grid.getStore().load({
                    callback: win.close,
                    scope: win
                });

                if (callback) {
                    callback();
                }
                return;
            }
            var uid = remaining.pop();
            opts.uids = [uid];
            opts.hashcheck = 1;
            if (opts.ranges) {
                delete opts.ranges;
            }

            msg = Ext.String.format(_t("Removing device: {0}"), uid.replace("/zport/dmd/", "/"));
            win.progressBar.updateProgress(1 - (remaining.length / total), msg, true);
            REMOTE.removeDevices(opts, deleteDevice);
        }

        win = Ext.create('Zenoss.dialog.BaseWindow', {
            width: 500,
            modal: true,
            title: _t('Removing Devices'),
            layout: 'form',
            closable: false,
            bodyBorder: false,
            border: false,
            hideBorders: true,
            buttonAlign: 'left',
            items: [{
                xtype: 'panel',
                ref: 'panel',
                layout: 'form',
                items: [{
                    xtype: 'displayfield',
                    ref: '../status',
                    value: _t('Removing... '),
                    height: 20
                }, {
                    xtype: 'progressbar',
                    width: '100%',
                    unstyled: true,
                    ref: '../progressBar'
                }]
            }],
            buttons: [{
                xtype: 'button',
                ui: 'dialog-dark',
                text: _t('Cancel'),
                ref: '../cancelButton',
                handler: function () {
                    cancelled = true;
                    win.setTitle(_t('Cancelling...'));
                }
            }]
        });
        win.show();

        deleteDevice();
    }

    Ext.apply(Zenoss.devices, {
        deleteDevices: new Zenoss.ActionButton({
            //text: _t('Delete Devices'),
            iconCls: 'delete',
            id: 'delete-button',
            permission: 'Delete Device',
            handler: function () {
                var selnode = getSelectionModel().getSelectedNode(),
                    isclass = selnode.data.uid.includes('Device'),
                    grpText = selnode.data.text.text;
                var win = new Zenoss.FormDialog({
                    title: _t('Remove Devices'),
                    modal: true,
                    width: 322,
                    height: isclass ? 170 : 210,
                    items: [{
                        xtype: 'panel',
                        bodyStyle: 'font-weight: bold; text-align:center',
                        html: _t('Are you sure you want to remove these devices? ' +
                            'There is no undo.')
                    }, {
                        xtype: 'radiogroup',
                        id: 'removetype',
                        style: 'margin: 0 auto',
                        hidden: isclass,
                        columns: 1,
                        items: [{
                            inputValue: 'remove',
                            id: 'remove-radio',
                            name: 'removetype',
                            boxLabel: _t('Just remove from ') + grpText,
                            disabled: isclass,
                            checked: !isclass
                        }, {
                            inputValue: 'delete',
                            id: 'delete-radio',
                            name: 'removetype',
                            boxLabel: _t('Delete completely'),
                            checked: isclass,
                            listeners: {
                                change: function (chbox, isChecked) {
                                    Ext.getCmp('delete-device-events').setDisabled(!isChecked);
                                }
                            }
                        }]
                    }, {
                        id: 'delete-device-events',
                        boxLabel: _t('Close Events?'),
                        style: 'margin-left: 4px;',
                        xtype: 'checkbox',
                        checked: true,
                        disabled: !isclass
                    }],
                    buttons: [{
                        xtype: 'DialogButton',
                        text: _t('Remove'),
                        id: 'delete_device_remove_btn',
                        handler: function () {
                            var opts = Ext.apply(gridOptions(), {
                                uid: Zenoss.env.PARENT_CONTEXT,
                                action: Ext.getCmp('removetype').getValue().removetype,
                                deleteEvents: Ext.getCmp('delete-device-events').getValue()
                            }),
                                grid = Ext.getCmp('device_grid');
                            grid.setLoading(true);
                            if (opts.uids.length > 0) {
                                var uids = opts.uids;
                                if (opts.ranges && opts.ranges.length) {
                                    Zenoss.remote.DeviceRouter.loadRanges({
                                        ranges: opts.ranges,
                                        uid: opts.uid,
                                        hashcheck: opts.hashcheck,
                                        params: opts.params,
                                        sort: opts.sort,
                                        dir: opts.dir
                                    }, function (response) {
                                        for (var i = 0; i < response.length; i++) {
                                            uids.push(response[i]);
                                        }
                                        deleteDevicesWithProgressBar(grid, uids, opts);
                                    });
                                } else {
                                    deleteDevicesWithProgressBar(grid, uids, opts);
                                }
                            } else {
                                grid.setLoading(false);
                            }
                            setTimeout(refreshTreePanel, 1000);
                        }
                    },
                    Zenoss.dialog.CANCEL
                    ]
                });
                win.show();
            }
        }),
        addDevice: new Zenoss.Action({
            text: _t('Add a Single Device') + '...',
            id: 'addsingledevice-item',
            permission: 'Manage Device',
            handler: function () {
                var snmpAndRackItems = [{
                    //Add hidden input fields for preventing username/password autocomplete
                    xtype: 'textfield',
                    id: 'autocompleteUsername',
                    name: 'autocompleteUsername',
                    hidden: true
                }, {
                    xtype: 'password',
                    id: 'autocompletePassword',
                    name: 'autocompletePassword',
                    hidden: true
                }, {
                    xtype: 'textfield',
                    name: 'snmpCommunity',
                    fieldLabel: _t('Snmp Community')
                }, {
                    xtype: 'numberfield',
                    name: 'snmpPort',
                    fieldLabel: _t('Snmp Port'),
                    value: 161,
                    allowBlank: false,
                    allowNegative: false,
                    allowDecimals: false,
                    maxValue: 65535
                }, {
                    xtype: 'textfield',
                    name: 'tag',
                    fieldLabel: _t('Tag Number')
                }, {
                    xtype: 'textfield',
                    name: 'rackSlot',
                    fieldLabel: _t('Rack Slot')
                }, {
                    xtype: 'textfield',
                    name: 'serialNumber',
                    fieldLabel: _t('Serial Number')
                }],
                    manufacturersAndProductsItems = [hwManufacturers, hwProduct, osManufacturers, osProduct],
                    organizersItems = [{
                        xtype: 'textarea',
                        name: 'comments',
                        fieldLabel: _t('Comments'),
                        emptyText: _t('None...'),
                        height: 77,
                        width: 200
                    }, {
                        xtype: 'locationdropdown',
                        name: 'locationPath',
                        fieldLabel: _t('Location'),
                        emptyText: _t('None...'),
                        width: 200
                    }, {
                        xtype: 'groupdropdown',
                        name: 'groupPaths',
                        fieldLabel: _t('Groups'),
                        emptyText: _t('None...'),
                        multiSelect: true,
                        width: 200
                    }, {
                        xtype: 'systemdropdown',
                        name: 'systemPaths',
                        fieldLabel: _t('Systems'),
                        emptyText: _t('None...'),
                        multiSelect: true,
                        width: 200
                    }];

                // this is an attempt to provide some coarse consistency without
                // completely hardcoding it. it is ugly.
                var propsCollection = Zenoss.env.allCredentialsProps.slice(),
                    usernamesCollection,
                    passwordsCollection,
                    hostsCollection,
                    sslCollection,
                    portsCollection;

                // usernames go in the first column.
                usernamesCollection = propsCollection.filter(function (value) {
                    return (value[0].toLowerCase().endswith('user') || value[0].toLowerCase().endswith('username'));
                });
                usernamesCollection.forEach(function (value) {
                    snmpAndRackItems.push({
                        xtype: 'textfield',
                        id: value[0],
                        name: value[0],
                        fieldLabel: _t(value[0]),
                        hidden: true,
                        width: 160
                    });
                });
                propsCollection = propsCollection.filter(function (value) {
                    return usernamesCollection.every(function (prop) {
                        return prop[0] !== value[0];
                    });
                });

                // passwords go in the second column.
                passwordsCollection = propsCollection.filter(function (value) {
                    return value[1] == 'password';
                });
                passwordsCollection.forEach(function (value) {
                    manufacturersAndProductsItems.push({
                        xtype: 'textfield',
                        inputType: 'password',
                        id: value[0],
                        name: value[0],
                        fieldLabel: _t(value[0]),
                        hidden: true,
                        width: 160
                    });
                });
                propsCollection = propsCollection.filter(function (value) {
                    return passwordsCollection.every(function (prop) {
                        return prop[0] !== value[0];
                    });
                });

                // hosts go in the third column.
                hostsCollection = propsCollection.filter(function (value) {
                    return (value[0].toLowerCase().endswith('host') || value[0].toLowerCase().endswith('hostname'));
                });
                hostsCollection.forEach(function (value) {
                    organizersItems.push({
                        xtype: 'textfield',
                        id: value[0],
                        name: value[0],
                        fieldLabel: _t(value[0]),
                        hidden: true,
                        width: 160
                    });
                });
                propsCollection = propsCollection.filter(function (value) {
                    return hostsCollection.every(function (prop) {
                        return prop[0] !== value[0];
                    });
                });

                // ssl goes in the third column.
                sslCollection = propsCollection.filter(function (value) {
                    return value[0].toLowerCase().endswith('ssl') && value[1] === 'boolean';
                });
                sslCollection.forEach(function (value) {
                    organizersItems.push({
                        xtype: 'checkbox',
                        id: value[0],
                        name: value[0],
                        fieldLabel: _t(value[0]),
                        hidden: true,
                        width: 160,
                        checked: true
                    });
                });
                propsCollection = propsCollection.filter(function (value) {
                    return sslCollection.every(function (prop) {
                        return prop[0] !== value[0];
                    });
                });

                // ports go in the first column.
                portsCollection = propsCollection.filter(function (value) {
                    return value[0].toLowerCase().endswith('port') && value[1] === 'int';
                });
                portsCollection.forEach(function (value) {
                    snmpAndRackItems.push({
                        xtype: 'numberfield',
                        id: value[0],
                        name: value[0],
                        fieldLabel: _t(value[0]),
                        hidden: true,
                        width: 160,
                        value: 443,
                        allowBlank: false,
                        allowNegative: false,
                        allowDecimals: false,
                        maxValue: 65535
                    });
                });
                propsCollection = propsCollection.filter(function (value) {
                    return portsCollection.every(function (prop) {
                        return prop[0] !== value[0];
                    });
                });

                // everything else goes in the third column.
                propsCollection.forEach(function (value) {
                    organizersItems.push({
                        xtype: 'textfield',
                        id: value[0],
                        name: value[0],
                        fieldLabel: _t(value[0]),
                        hidden: true,
                        width: 160
                    });
                });

                var win = new Zenoss.dialog.CloseDialog({
                    width: 850,
                    height: 620,
                    autoScroll: true,
                    buttons: [{
                        xtype: 'DialogButton',
                        id: 'addsingledevice-submit',
                        text: _t('Add'),
                        handler: function () {
                            var form = win.childPanel.getForm(),
                                opts = form.getValues();
                            delete opts.autocompleteUsername;
                            delete opts.autocompletePassword;
                            REMOTE.getCredentialsProps({ deviceClass: opts.deviceClass }, function (data) {
                                var zProps = {},
                                    credsProps = data['data'];
                                for (prop in credsProps) {
                                    zProps[prop] = opts[prop];
                                }
                                Zenoss.env.allCredentialsProps.forEach(function (prop) {
                                    delete opts[prop[0]];
                                });
                                opts.zProperties = zProps;
                                Zenoss.remote.DeviceRouter.addDevice(opts, function (response) {
                                    if (!response.success) {
                                        Zenoss.message.error(_t('Error adding device job.'));
                                    }
                                });
                            });
                        }
                    }, Zenoss.dialog.CANCEL],
                    title: _t('Add a Single Device'),
                    listeners: {
                        show: function (panel) {
                            if (Zenoss.SELENIUM) {
                                var formArray = panel.childPanel.query('.field');
                                var i = 0;
                                for (i = 0; i < formArray.length; i++) {
                                    Ext.getDom(formArray[i].getInputId()).id = "add_device-input-" + i;
                                }
                                panel.query('.button')[1].id = "addsingledevice-cancel";
                            }
                        }
                    },
                    items: [{
                        xtype: 'form',
                        buttonAlign: 'left',
                        monitorValid: true,
                        fieldDefaults: {
                            labelAlign: 'top'
                        },
                        footerStyle: 'padding-left: 0',
                        ref: 'childPanel',
                        listeners: {
                            validitychange: function (form, isValid) {
                                // enable disable the button based on the form validity
                                Ext.getCmp('addsingledevice-submit').setDisabled(!isValid);
                            }
                        },
                        items: [{
                            xtype: 'panel',
                            layout: 'column',
                            items: [{
                                columnWidth: 0.5,
                                layout: 'anchor',
                                items: [{
                                    xtype: 'textfield',
                                    vtype: 'hostnameorIP',
                                    name: 'deviceName',
                                    width: 300,
                                    fieldLabel: _t('Hostname or IP address'),
                                    id: "add-device-name",
                                    allowBlank: false
                                }, deviceClassCombo, {
                                    xtype: 'combo',
                                    width: 300,
                                    name: 'collector',
                                    fieldLabel: _t('Collector'),
                                    id: 'add-device-collector',
                                    queryMode: 'local',
                                    store: new Ext.data.ArrayStore({
                                        data: Zenoss.env.COLLECTORS,
                                        fields: ['name']
                                    }),
                                    valueField: 'name',
                                    displayField: 'name',
                                    forceSelection: true,
                                    editable: false,
                                    allowBlank: false,
                                    triggerAction: 'all',
                                    listeners: {
                                        'afterrender': function (component) {
                                            var index = component.store.find('name', 'localhost');
                                            if (index >= 0) {
                                                component.setValue('localhost');
                                            }
                                        }
                                    }
                                }, {
                                    xtype: 'checkbox',
                                    name: 'model',
                                    width: 300,
                                    fieldLabel: _t('Model Device'),
                                    id: 'add-device-protocol',
                                    checked: true
                                }]
                            }, {
                                columnWidth: 0.5,
                                layout: 'anchor',
                                items: [{
                                    xtype: 'textfield',
                                    name: 'title',
                                    width: 250,
                                    fieldLabel: _t('Title')
                                }, {
                                    xtype: 'ProductionStateCombo',
                                    name: 'productionState',
                                    id: 'production-combo',
                                    width: 250,
                                    allowBlank: false,
                                    fieldLabel: _t("Production State"),
                                    listConfig: {
                                        minWidth: 250
                                    },
                                    listeners: {
                                        'afterrender': function (component) {
                                            component.store.load({
                                                callback: function () {
                                                    var index = component.store.find('value', 1000);
                                                    if (index >= 0) {
                                                        component.setValue(1000);
                                                    }
                                                }
                                            });
                                        }
                                    }
                                }, {
                                    xtype: 'PriorityCombo',
                                    name: 'priority',
                                    fieldLabel: _t("Device Priority"),
                                    width: 250,
                                    allowBlank: false,
                                    listConfig: {
                                        minWidth: 250
                                    },
                                    listeners: {
                                        'afterrender': function (component) {
                                            component.store.load({
                                                callback: function () {
                                                    var index = component.store.find('value', 3);
                                                    if (index >= 0) {
                                                        component.setValue(3);
                                                    }
                                                }
                                            });
                                        }
                                    }
                                }]
                            }]
                        }, {
                            xtype: 'panel',
                            html: '<a href="#">More...</a>',
                            toggleAttrs: function () {
                                var attrs = Ext.getCmp('add_attrs');
                                if (attrs.collapsed) {
                                    attrs.expand();
                                } else {
                                    attrs.collapse();
                                }
                                this.updateText();
                            },
                            updateText: function () {
                                var attrs = Ext.getCmp('add_attrs');
                                if (attrs.collapsed) {
                                    this.body.update('<a href="#">More...</a>');
                                } else {
                                    this.body.update('<a href="#">Less...</a>');
                                }
                            },
                            listeners: {
                                afterrender: function (component) {
                                    var el = component.getEl();
                                    el.on('click', this.toggleAttrs, component);
                                    component.updateText();
                                }
                            }
                        }, {
                            id: 'add_attrs',
                            collapsible: true,
                            collapsed: true,
                            hideCollapseTool: true,
                            hideLabel: true,
                            xtype: 'panel',
                            preventHeader: true,
                            layout: 'column',
                            ref: "moreAttributes",
                            listeners: {
                                expand: function () {
                                    win.center();
                                    win.doLayout();
                                },
                                collapse: function () {
                                    win.center();
                                    win.doLayout();
                                }
                            },
                            items: [{
                                columnWidth: 0.33,
                                layout: 'anchor',
                                defaults: {
                                    anchor: '65%'
                                },
                                items: snmpAndRackItems
                            }, {
                                bodyPadding: '41px 0px 0px 0px',
                                columnWidth: 0.33,
                                layout: 'anchor',
                                items: manufacturersAndProductsItems
                            }, {
                                columnWidth: 0.34,
                                layout: 'anchor',
                                id: 'add-device-organizer-column',
                                items: organizersItems
                            }]
                        }]

                    }]
                });
                win.show();
            }
        }),
        addMultiDevicePopUP: new Zenoss.Action({
            text: _t('Add Multiple Devices') + '...',
            id: 'addmultipledevices-item',
            permission: 'Manage Device',
            // only global roles can do this action
            permissionContext: '/zport/dmd/Devices',
            handler: function () {
                var loc = window.location.pathname;
                window.location = Ext.String.format('/zport/dmd/quickstart?came_from={0}#add-device', loc);
            }
        }),
        addDeviceDiscovery: new Zenoss.Action({
            text: _t('Discover Networks') + '...',
            id: 'adddevice-discovery',
            permission: 'Manage Device',
            // only global roles can do this action
            permissionContext: '/zport/dmd/Devices',
            handler: function () {
                var loc = window.location.pathname;
                window.location = Ext.String.format('/zport/dmd/quickstart?came_from={0}#discover-network', loc);
            }
        })
    });

    function commandMenuItemHandler(item) {
        var command = item.text,
            grid = Ext.getCmp('device_grid'),
            sm = grid.getSelectionModel(),
            selections = sm.getSelection(),
            devids = Ext.pluck(Ext.pluck(selections, 'data'), 'uid');
        function showWindow() {
            var win = new Zenoss.CommandWindow({
                uids: devids,
                target: getSelectionModel().getSelectedNode().data.uid + '/run_command',
                command: command
            });
            win.show();
        }

        showWindow();

    }


    function updateNavTextWithCount(node) {
        var sel = getSelectionModel().getSelectedNode();
        if (sel && Ext.isDefined(sel.data.text.count)) {
            var count = sel.data.text.count;
            node.setText('Devices (' + count + ')');
        }
    }


    function getTreeDropWarnings(dropTargetNode, droppedRecords) {
        // if we're moving a device to a device class whose underlying python class does not match, also warn
        // about the potentially destructive operation.
        var additionalWarnings = [""];
        if (dropTargetNode && droppedRecords && dropTargetNode.data && dropTargetNode.data.path &&
            dropTargetNode.data.path.indexOf('Devices') === 0) {
            var dropTargetClass = dropTargetNode.data.zPythonClass || "Products.ZenModel.Device";
            var droppedClasses = Ext.Array.map(droppedRecords, function (r) { return r.data.pythonClass; });
            if (Ext.Array.some(droppedClasses, function (droppedClass) { return dropTargetClass !== droppedClass; })) {
                additionalWarnings = additionalWarnings.concat(_t("WARNING: This may result in the loss of all components and configuration under these devices."));
            }
        }
        return additionalWarnings.join('<br><br>');
    }

    // page level variables
    var originalMessage,
        errorMessage = "You cannot move devices to a top-level organizer";
    function initializeTreeDrop(tree) {
        var rootOrganizers = [
            "/zport/dmd/Devices",
            "/zport/dmd/Locations",
            "/zport/dmd/Groups",
            "/zport/dmd/Systems",
        ]

        tree.getView().on('nodedragover', function(targetNode, position, dragData, e, eOpts) {
            var targetUid = targetNode.data.uid,
                dragText = dragData.ddel.getHTML(),
                isDevice;

            // get original dragText
            if (dragText && dragText !== errorMessage) {
                originalMessage = dragText;
            }

            // check whether we drag device, not organizer
            if (dragData.records) {
                isDevice = dragData.records[0].get("uid").includes('/devices/');
            }

            // if we drag device over organizer root then show errorMessage
            if (isDevice && rootOrganizers.includes(targetUid)) {
                dragData.ddel.update(errorMessage);
                return false;
            }

            // if everything became fine then return originalMessage back
            if (dragText === errorMessage) {
                dragData.ddel.update(originalMessage);
            }
            return true;
        }, tree);

        // fired when the user actually drops a node
        tree.getView().on('beforedrop', function (element, e, targetnode) {
            var targetuid = targetnode.data.uid,
                devids,
                me = this,
                isOrganizer = true;
            if (e.records) {
                // the tree drag and drop wraps the model in a node interface so we
                // need to look at the uid to figure out what they are dropping
                isOrganizer = e.records[0].get("uid").indexOf('/devices/') === -1;
            }

            if (!isOrganizer) {
                // move devices to the target node
                devids = Ext.Array.pluck(Ext.pluck(e.records, 'data'), 'uid');
                // show the confirmation about devices
                new Zenoss.dialog.SimpleMessageDialog({
                    message: Ext.String.format(_t("Are you sure you want to move {0} to {1}?") + getTreeDropWarnings(targetnode, e.records),
                        devids.length == 1 ? "this device" : "these " + devids.length + " devices", targetnode.data.text.text),
                    title: _t('Move Devices'),
                    buttons: [{
                        xtype: 'DialogButton',
                        text: _t('OK'),
                        handler: function () {
                            // move the devices
                            var opts = {
                                uids: devids,
                                ranges: [],
                                target: targetuid,
                                asynchronous: Zenoss.settings.deviceMoveIsAsync(devids)
                            };
                            REMOTE.moveDevices(opts, function (data) {
                                if (data.success) {
                                    if (data.remodel_required) {
                                        new Zenoss.dialog.ErrorDialog({
                                            title: _t('Remodel Required'),
                                            message: Ext.String.format(_t("Not all of the configuration could be preserved, so a remodel of the device(s)" +
                                                "is required. Performance templates have been reset to the defaults for the device class."))
                                        });
                                    }
                                    setTimeout(refreshTreePanel, 500);
                                }
                                resetGrid();
                            }, me);
                        }
                    }, {
                        xtype: 'DialogButton',
                        text: _t('Cancel')
                    }]
                }).show();
                // if we return true a dummy node will be appended to the tree
                return false;
            } else {

                // move the organizer under the target node
                var record = e.records[0];
                var organizerUid = record.get("uid");
                if (!tree.canMoveOrganizer(organizerUid, targetuid)) {
                    return false;
                }

                // show the confirmation about organizers
                // show a confirmation for organizer move
                new Zenoss.dialog.SimpleMessageDialog({
                    title: _t('Move Organizer'),
                    message: Ext.String.format(_t("Are you sure you want to move {0} to {1}?"), record.get("text").text, targetnode.get("text").text),
                    buttons: [{
                        xtype: 'DialogButton',
                        text: _t('OK'),
                        handler: function () {
                            // move the organizer
                            var params = {
                                organizerUid: organizerUid,
                                targetUid: targetuid
                            };
                            REMOTE.moveOrganizer(params, function (data) {
                                if (data.success) {
                                    // add the new node to our history
                                    Ext.History.add(me.id + Ext.History.DELIMITER + data.data.uid.replace(/\//g, '.'));
                                    tree.refresh({
                                        callback: resetGrid
                                    });
                                }
                            }, me);
                        }
                    }, {
                        xtype: 'DialogButton',
                        text: _t('Cancel')
                    }]
                }).show();

                // Ext shows the node as already moved when we are awaiting the
                // dialog confirmation, so always tell Ext that the move didn't work
                // here. If the move was successful the tree will redraw itself with
                // the new nodes in place
                return false;
            }

        }, tree);
    }

    /*
    * Special history manager selection to deal with the second level of nav
    * on the "Details" panel.
    */
    function detailSelectByToken(nodeId) {
        var parts = nodeId.split(Ext.History.DELIMITER),
            master = Ext.getCmp('master_panel'),
            container = master.layout,
            node = getSelectionModel().getSelectedNode(),
            item = Ext.getCmp('detail_nav');
        function changeDetail() {
            item.un('navloaded', item.selectFirst, item);

            // switch to the "details" panel
            master.setActiveItem(1);

            // wait until the nav has loaded from the server to
            // select the nav item
            item.on('navloaded', function () {
                item.selectByToken(parts[1]);
            }, item, { single: true });
        }
        if (parts[1]) {
            if (Ext.Array.indexOf(master.items.items, container.activeItem) === 1 ||
                (node && node.id === parts[0])) {
                Zenoss.HierarchyTreePanel.prototype.selectByToken.call(this, parts[0]);
                changeDetail();
            } else {
                this.getSelectionModel().on('selectionchange', changeDetail, this.getSelectionModel(), { single: true });
                Zenoss.HierarchyTreePanel.prototype.selectByToken.call(this, parts[0]);
            }
        } else {
            master.setActiveItem(0);
            Zenoss.HierarchyTreePanel.prototype.selectByToken.call(this, parts[0]);
        }
    }

    var treeLoaderFn = REMOTE.getTree, treeStateful = true;
    if (Zenoss.settings.incrementalTreeLoad) {
        treeLoaderFn = REMOTE.asyncGetTree;
        treeStateful = false;
    }
    // make sure the first visible root is expanded
    Zenoss.env.device_tree_data[0].expanded = true;
    Zenoss.env.system_tree_data[0].expanded = true;
    Zenoss.env.group_tree_data[0].expanded = true;
    Zenoss.env.location_tree_data[0].expanded = true;

    var devtree = {
        xtype: 'HierarchyTreePanel',
        viewConfig: {
            loadMask: true
        },
        id: 'devices',
        searchField: true,
        directFn: treeLoaderFn,
        extraFields: [{ name: 'zPythonClass', type: 'string' }],
        allowOrganizerMove: false,
        stateful: treeStateful,
        stateId: 'device_tree',
        ddAppendOnly: true,
        root: {
            id: 'Devices',
            uid: '/zport/dmd/Devices',
            text: 'Device Classes',
            children: Zenoss.env.device_tree_data
        },
        ddGroup: 'devicegriddd',
        forceEnableDd: true,
        selectByToken: detailSelectByToken,
        addNodeFn: REMOTE.addDeviceClassNode,
        selModel: Ext.create('Zenoss.TreeSelectionModel', {
            tree: 'devices',
            listeners: {
                selectionchange: treeselectionchange
            }
        }),
        router: REMOTE,
        nodeName: 'Device',
        deleteNodeFn: function (args, callback) {
            REMOTE.getDeviceUids(args, function (response) {
                deleteDevicesWithProgressBar(Ext.getCmp('device_grid'),
                    response.devices, { uid: args.uid, action: 'delete' }, function () {
                        REMOTE.deleteNode({ uid: args.uid }, callback);
                    });
                setTimeout(refreshTreePanel, 1000);
            });
        },
        listeners: {
            render: initializeTreeDrop,
            viewready: function (t) {
                // fixes 20000px width bug on the targetEl div bug in Ext
                t.ownerCt.ownerCt.searchfield.container.setWidth(t.body.getWidth());
            },
            filter: function (e) {
                Ext.getCmp('locs').filterTree(e);
                Ext.getCmp('groups').filterTree(e);
                Ext.getCmp('systemsTree').filterTree(e);
            }
        }
    };

    var grouptree = {
        xtype: 'HierarchyTreePanel',
        viewConfig: {
            loadMask: false
        },
        id: 'groups',
        searchField: false,
        directFn: treeLoaderFn,
        stateful: treeStateful,
        stateId: 'group_tree',
        ddAppendOnly: true,
        selectByToken: detailSelectByToken,
        root: {
            id: 'Groups',
            uid: '/zport/dmd/Groups',
            children: Zenoss.env.group_tree_data
        },
        ddGroup: 'devicegriddd',
        forceEnableDd: true,
        nodeName: 'Group',
        selModel: Ext.create('Zenoss.TreeSelectionModel', {
            tree: 'groups',
            listeners: {
                selectionchange: treeselectionchange
            }
        }),
        router: REMOTE,
        selectRootOnLoad: false,
        listeners: { render: initializeTreeDrop }
    };

    var systree = {
        xtype: 'HierarchyTreePanel',
        viewConfig: {
            loadMask: false
        },
        id: 'systemsTree',
        stateful: treeStateful,
        stateId: 'systems_tree',
        searchField: false,
        directFn: treeLoaderFn,
        ddAppendOnly: true,
        selectByToken: detailSelectByToken,
        root: {
            id: 'Systems',
            uid: '/zport/dmd/Systems',
            children: Zenoss.env.system_tree_data
        },
        ddGroup: 'devicegriddd',
        forceEnableDd: true,
        nodeName: 'System',
        router: REMOTE,
        selectRootOnLoad: false,
        selModel: Ext.create('Zenoss.TreeSelectionModel', {
            tree: 'systemsTree',
            listeners: {
                selectionchange: treeselectionchange
            }
        }),
        listeners: {
            render: initializeTreeDrop
        }
    };

    var loctree = {
        xtype: 'HierarchyTreePanel',
        viewConfig: {
            loadMask: false
        },
        stateful: treeStateful,
        stateId: 'loc_tree',
        id: 'locs',
        searchField: false,
        directFn: treeLoaderFn,
        ddAppendOnly: true,
        selectByToken: detailSelectByToken,
        root: {
            id: 'Locations',
            uid: '/zport/dmd/Locations',
            children: Zenoss.env.location_tree_data
        },
        ddGroup: 'devicegriddd',
        forceEnableDd: true,
        nodeName: 'Location',
        router: REMOTE,
        addNodeFn: REMOTE.addLocationNode,
        selectRootOnLoad: false,
        selModel: Ext.create('Zenoss.TreeSelectionModel', {
            tree: 'locs',
            listeners: {
                selectionchange: treeselectionchange
            }
        }),
        listeners: { render: initializeTreeDrop }
    };

    var treepanel = {
        xtype: 'HierarchyTreePanelSearch',
        items: [devtree, grouptree, systree, loctree]
    };

    Zenoss.nav.register({
        DeviceGroup: [
            {
                id: 'device_grid',
                text: 'Devices',
                listeners: {
                    render: updateNavTextWithCount
                }
            },
            {
                id: 'events_grid',
                text: _t('Events')
            },
            {
                id: 'modeler_plugins',
                text: _t('Modeler Plugins'),
                contextRegex: '^/zport/dmd/Devices'
            }, {
                id: 'configuration_properties',
                text: _t('Configuration Properties'),
                contextRegex: '^/zport/dmd/Devices'
            }, {
                id: 'custom_properties',
                text: _t('Custom Properties'),
                contextRegex: '^/zport/dmd/Devices'
            }, {
                id: 'device_admin',
                text: _t('Device Administration')
            }, {
                id: 'overridden_objects',
                text: _t('Overridden Objects'),
                contextRegex: '^/zport/dmd/Devices'
            }
        ]
    });

    var exporter = function (type) {
        var grid = Ext.getCmp("device_grid");
        var state = grid.getState();

        var devicesPath = getSelectionModel().getSelectedNode().data.path;
        var fields = Ext.Array.pluck(grid.columns.filter(function (column) {
            return column.isVisible();
        }), 'dataIndex');
        fields[fields.indexOf('uid')] = 'deviceClass';
        fields[fields.indexOf('ipAddress')] = 'ipAddressString';
        var params = {
            uid: devicesPath,
            type: type,
            sort: state.sort.property,
            sdir: state.sort.direction,
            params: grid.filterRow.getSearchValues(),
            fields: fields
        };
        Ext.get('devices_export_body').dom.value = Ext.encode(params);
        Ext.get('devices_export_form').dom.submit();
    };

    Ext.define("Zenoss.InfraDetailNav", {
        alias: ['widget.infradetailnav'],
        extend: "Zenoss.DetailNavPanel",
        constructor: function (config) {
            Ext.applyIf(config, {
                text: _t('Details'),
                target: 'detail_panel',
                manualAdjustHeight: true,
                menuIds: ['More', 'Add', 'TopLevel', 'Manage'],
                listeners: {
                    nodeloaded: function (detailNavPanel, navConfig) {
                        var excluded = {
                            'device_grid': true,
                            'events_grid': true,
                            'collectorplugins': true,
                            'configuration properties': true
                        };

                        if (!excluded[navConfig.id]) {
                            var config = detailNavPanel.panelConfigMap[navConfig.id];
                            if (config && !Ext.getCmp(config.id)) {

                                //create the panel in the center panel if needed
                                var detail_panel = Ext.getCmp('detail_panel');
                                detail_panel.add(config);
                                detail_panel.doLayout();
                            }
                        }
                    }
                }
            });
            Zenoss.InfraDetailNav.superclass.constructor.call(this, config);
        },
        selectByToken: function (nodeId) {
            var selNode = function () {
                var navtree = this.down('detailnavtreepanel'),
                    rootNode = navtree.getRootNode(),
                    toSelect = rootNode ? (rootNode.findChild('id', nodeId) || rootNode.firstChild) : null;

                if (toSelect) {
                    navtree.getSelectionModel().select(toSelect);
                    }
                };
            if (this.loaded) {
                selNode.call(this);
            } else {
                this.on('navloaded', selNode, this, { single: true });
            }
        },
        filterNav: function (navpanel, config) {
            //nav items to be excluded
            var excluded = {
                'status': true,
                'classes': true,
                'events': true,
                'templates': true,
                'performancetemplates': true,
                'historyevents': true,
                'collectorplugins': true,
                'configuration properties': true,
                'editcustschema': true,
                'devicemanagement': true,
                'administration': true,
                'overriddenobjects': true
            };
            var uid = Zenoss.env.PARENT_CONTEXT;
            if (config.contextRegex) {
                var re = new RegExp(config.contextRegex);
                return re.test(uid);
            }
            return !excluded[config.id];
        },
        onGetNavConfig: function () {
            return Zenoss.nav.get('DeviceGroup');
        },
        onSelectionChange: function (nodes) {
            var node = nodes && nodes[0];
            if (node) {
                var detailPanel = Ext.getCmp('detail_panel');
                var contentPanel = Ext.getCmp(node.data.id);
                contentPanel.setContext(this.contextId);
                detailPanel.layout.setActiveItem(node.data.id);
                var orgnode = getSelectionModel().getSelectedNode();
                Ext.History.add([
                    orgnode.getOwnerTree().id,
                    orgnode.get("uid").replace(/\//g, '.'),
                    node.get("id")
                ].join(Ext.History.DELIMITER));
            }
        }
    });

    var truncate = function (cmp_name, width, uid) {
        var path = uid.replace('/zport/dmd', ''),
            textwidth = Ext.util.TextMetrics.measure(cmp_name, path).width;
        if (textwidth < width) {
            return path;
        } else {
            var path_array = path.split('/'),
                device_class = path_array[path_array.length - 1];

            // check if DeviceClass's name length > field's length
            if (Ext.util.TextMetrics.measure(cmp_name, ('/../' + device_class)).width < width) {
                path_array[path_array.length - 2] = '..';
                while (path_array.length > 3 && Ext.util.TextMetrics.measure(cmp_name, path_array.join('/')).width >= width) {
                    path_array.splice(path_array.length - 3, 1);
                }
                return path_array.join('/');
            } else {
                return '/../' + device_class;
            }
        }
    }

    var device_grid = Ext.create('Zenoss.DeviceGridPanel', {
        ddGroup: 'devicegriddd',
        id: 'device_grid',
        multiSelect: true,
        header: {
            titlePosition: 0,
            items: [{
                xtype: 'displayfield',
                value: _t('/'),
                width: 'auto',
                id: 'device_panel_header',
                allowBlank: true,
                readOnly: true
            }]
        },
        viewConfig: {
            plugins: {
                ptype: 'gridviewdragdrop',
                dragGroup: 'devicegriddd'
            }
        },
        listeners: {
            scrollerhide: function () {
                // sometimes, items are a bit off the viewable, but not enough for paging scrollbars
                // so force some scrolling action for the user
                this.getView().applyConfig('autoScroll', true);
            },
            scrollershow: function (scroller) {
                // paging scroll works, so turn off native scrolling (this will be native all the way in ext 4.1)
                // also, check for scrollbar, and force it to redraw due to ext bug where by it loses connection
                // to the container it's suppose to scroll
                this.getView().applyConfig('autoScroll', false);
                if (scroller && scroller.scrollEl) {
                    scroller.clearManagedListeners();
                    scroller.mon(scroller.scrollEl, 'scroll', scroller.onElScroll, scroller);
                }
            },
            contextchange: function (grid, uid) {
                REMOTE.getInfo({ uid: uid, keys: ['name', 'description', 'address'] }, function (result) {
                    if (Zenoss.env.contextUid && Zenoss.env.contextUid !== uid) {
                        return;
                    }
                    var cmp_name = 'device_panel_header',
                        cmp = Ext.getCmp(cmp_name),
                        width = this.header.getWidth(),
                        title = truncate(cmp_name, width, uid),
                        desc = [''];
                    if (result.data.address) {
                        desc.push(result.data.address);
                    }
                    if (result.data.description) {
                        desc.push(result.data.description);
                    }
                    function encoder(element, index, array) { array[index] = Ext.htmlEncode(element); }
                    Ext.Array.each(desc, encoder);
                    // avoid a rendering of the grid if the title hasn't changed
                    if (cmp.value !== title) {
                        if (desc.length && Ext.util.TextMetrics.measure(cmp_name, title + desc).width < width) {
                            cmp.setValue(Ext.String.format("{0} {1}", title, desc.join(' - ')));
                        } else {
                            cmp.setValue(title);
                        }
                    }
                }, this);
            },
            scope: device_grid
        },
        selModel: new Zenoss.DeviceGridSelectionModel({
            listeners: {
                selectionchange: function (sm) {
                    if (!_has_global_roles()) {
                        if (sm.hasSelection()) {
                            var selection = sm.getSelection();
                            setDeviceButtonsDisabled(false);
                            selection.forEach(function(sel) {
                                Zenoss.Security.setContext(sel.data.uid)
                            });                            
                        } else {
                            setDeviceButtonsDisabled(true);
                        }
                    } else {
                        setDeviceButtonsDisabled(!sm.hasSelection());
                    }
                }
            }
        }),
        headerCfg: {
            tag: 'div',
            cls: 'x-panel-header',
            children: [
                { tag: 'span', cls: 'title', html: '' },
                { tag: 'span', cls: 'desc' }
            ]
        },
        tbar: {
            xtype: 'largetoolbar',
            id: 'detail-toolbar',
            items: [
                {
                    xtype: 'eventrainbow',
                    id: 'organizer_events',
                    width: 152,
                    listeners: {
                        click: {
                            fn: function() {
                                if (Zenoss.Security.hasPermission('View')) {
                                    Ext.getCmp("master_panel").setActiveItem(1);
                                    var detailnav = Ext.getCmp('detail_nav');
                                    detailnav.selectByToken('events_grid');
                                }
                            },
                            // will fire "click" on element click;
                            element: 'el'
                        }
                    }
                },
                '-',
                {
                    id: 'adddevice-button',
                    iconCls: 'adddevice',
                    menu: {
                        items: [
                            Zenoss.devices.addDevice,
                            Zenoss.devices.addMultiDevicePopUP,
                            Zenoss.devices.addDeviceDiscovery
                        ].concat(EXTENSIONS_adddevice)
                    }
                },
                Zenoss.devices.deleteDevices,
                {
                    text: _t('Select'),
                    listeners: {
                        afterrender: function (e) {
                            var textItem = e.menu.items.items[0];
                            var store = Ext.getCmp('device_grid').getStore();
                            store.on('load', function () {
                                /*
                                    added the guaranteeRange so that when the user is selecting the expected pagesize in select(all/none),
                                    they'll actually get the advertised range. Otherwise, it only loads some unexpected amount over the view
                                    which can be different depending on how tall the viewable grid is (and is NOT the pageSize, nor does it
                                    take the pageSize into account). This forces consistency.
                                */
                                var amount = Math.min(store.getTotalCount(), store.pageSize);
                                textItem.setText(Ext.String.format(_t("{0} at a time"), amount));
                            }, this);
                        }
                    },
                    menu: [
                        {
                            text: _t("All"),
                            handler: function () {
                                var grid = Ext.getCmp('device_grid');
                                grid.getSelectionModel().selectAll();
                            }
                        },
                        {
                            text: _t('None'),
                            handler: function () {
                                var grid = Ext.getCmp('device_grid');
                                grid.getSelectionModel().selectNone();
                            }
                        }
                    ]
                },
                {
                    text: _t('Configure'),
                    menu: [
                        {
                            id: 'nfrastructure_clearfilters',
                            text: _t('Clear filters'),
                            listeners: {
                                click: function () {
                                    Ext.getCmp('device_grid').filterRow.clearFilters();
                                }
                            }
                        }
                    ]
                }, {
                    text: _t('Export'),
                    menu: {
                        items: [{
                            text: 'XML',
                            handler: function () {
                                exporter('xml');
                            }
                        }, {
                            text: 'CSV',
                            handler: function () {
                                exporter('csv');
                            }
                        }]
                    }
                }, '->', {
                    id: 'refreshdevice-button',
                    xtype: 'refreshmenu',
                    ref: 'refreshmenu',
                    stateId: 'devicerefresh',
                    iconCls: 'refresh',
                    text: _t('Refresh'),
                    tooltip: _t('Refresh Device List'),
                    handler: function () {
                        var grid = Ext.getCmp('device_grid');
                        if (grid.isVisible(true)) {
                            grid.getStore().reload();
                            grid.refresh();
                            Ext.getCmp('organizer_events').refresh();
                            refreshTreePanel();
                        }
                    },
                    pollHandler: function (btn) {
                        var grid = Ext.getCmp('device_grid');
                        if (grid.refresh_in_progress === 0) {
                            this.handler(btn);
                        }
                    }
                },
                {
                    id: 'actions-menu',
                    xtype: 'deviceactionmenu',
                    deviceFetcher: gridUidSelections,
                    saveHandler: function () {
                        resetGrid();
                        // show any errors
                        Zenoss.messenger.checkMessages();
                    }
                },
                {
                    id: 'commands-menu',
                    text: _t('Commands'),

                    setContext: function (uid) {
                        var me = Ext.getCmp('commands-menu'),
                            menu = me.menu;
                        REMOTE.getUserCommands({ uid: uid }, function (data) {
                            if (Zenoss.env.contextUid && Zenoss.env.contextUid !== uid) {
                                return;
                            }
                            menu.removeAll();
                            Ext.each(data, function (d) {
                                menu.add({
                                    text: d.id,
                                    tooltip: d.description,
                                    handler: commandMenuItemHandler
                                });
                            });
                        });
                    },
                    menu: {}
                }
            ]
        }
    });

    /**
     * Toggle buttons based on permissions everytime they click a different tree node
     **/
    Zenoss.Security.onPermissionsChange(function () {
        var cmp = Ext.getCmp('master_panel_details');
        var btn = cmp.query("button[ref='details']")[0];
        if (btn) {
            btn.setDisabled(Zenoss.Security.doesNotHavePermission('Manage DMD'));
        }
        Ext.getCmp('addsingledevice-item').setDisabled(Zenoss.Security.doesNotHavePermission('Manage DMD'));
        Ext.getCmp('footer_add_button').setVisible(Zenoss.Security.hasPermission('Manage DMD'));
        Ext.getCmp('footer_delete_button').setVisible(Zenoss.Security.hasPermission('Manage DMD'));
        Ext.getCmp('master_panel').details.setDisabled(Zenoss.Security.doesNotHavePermission('View'));
        Ext.getCmp("context-configure-menu").setVisible(Zenoss.Security.hasPermission('Manage DMD'));
        Ext.getCmp('context-configure-menu').setDisabled(Zenoss.Security.doesNotHavePermission('Manage DMD'));

        // The commands-menu and actions-menu are enabled/disabled based on both selection and
        // granted permissions.  When permission changes, we'll reevaluate this using the last
        // flag given.
        setDeviceButtonsDisabled(deviceButtonsDisabled);
    });

    var createEventsGrid = function (re_attach_to_container) {
        var events_store = Ext.create('Zenoss.events.Store', {});
        if (!Zenoss.settings.enableInfiniteGridForEvents) {
            events_store.buffered = false;
        }
        var eventsGridId = 'events_grid';
        var event_console = Ext.create('Zenoss.EventGridPanel', {
            id: eventsGridId,
            stateId: 'infrastructure_events',
            //columns: Zenoss.env.getColumnDefinitions(['DeviceClass']),
            columns: Zenoss.env.getColumnDefinitionsToRender('infrastructure_events'),
            newwindowBtn: true,
            actionsMenu: false,
            commandsMenu: false,
            enableColumnHide: false,
            store: events_store,
            listeners: {
                beforeshow: function (grid, uid) {
                    grid.refresh();
                }
            }
        });

        if (re_attach_to_container === true) {
            var container_panel = Ext.getCmp('detail_panel');
            container_panel.items.insert(1, event_console);
            container_panel.layout.setActiveItem(1);
        }

        event_console.on('recreateGrid', function (grid) {
            var container_panel = Ext.getCmp('detail_panel');
            container_panel.remove(grid.id, true);
            var new_grid = createEventsGrid(true);
            if (Zenoss.env.contextUid) {
                new_grid.setContext(Zenoss.env.contextUid);
            }
        });
        return event_console;
    };

    var event_console = createEventsGrid(false);

    Ext.getCmp('center_panel').add({
        id: 'center_panel_container',
        layout: 'border',
        items: [{
            xtype: 'horizontalslide',
            id: 'master_panel',
            cls: 'x-zenoss-master-panel',
            region: 'west',
            split: true,
            width: 275,
            items: [{
                id: 'master_panel_details',
                text: _t('Infrastructure'),
                buttonText: _t('Details'),
                buttonRef: 'details',
                layout: 'fit',
                items: [treepanel]
            }, {
                xtype: 'detailcontainer',
                id: 'masterDetailNav',
                buttonText: _t('See All'),
                buttonRef: 'seeAll',
                items: [{
                    xtype: 'infradetailnav',
                    id: 'detail_nav',
                    padding: '0 0 10px 0',
                    style: { 'position': 'relative', 'top': '25px' }
                }, {
                    xtype: 'montemplatetreepanel',
                    id: 'templateTree',
                    detailPanelId: 'detail_panel'
                }]
            }],
            listeners: {
                beforecardchange: function (me, card, index) {
                    var node, selectedNode, tree;
                    if (index === 1) {
                        node = getSelectionModel().getSelectedNode().data;
                        card.setHeaderText(node.text.text, node.path);
                        me.lastActiveItem = Ext.getCmp('detail_panel').layout.getActiveItem();
                    } else if (index === 0) {
                        tree = Ext.getCmp('detail_nav').treepanel;
                        Ext.getCmp('detail_nav').items.each(function (item) {
                            selectedNode = item.getSelectionModel().getSelectedNode();
                            if (selectedNode) {
                                tree.getSelectionModel().deselect(selectedNode);
                            }
                        });
                        Ext.getCmp('detail_panel').layout.setActiveItem(me.lastActiveItem);
                    }
                },
                cardchange: function (me, card, index) {
                    var node = getSelectionModel().getSelectedNode();
                    if (index === 1) {
                        card.card.setContext(node.data.uid);
                        Ext.getCmp('footer_add_button').disable();
                        Ext.getCmp('footer_delete_button').disable();
                    } else if (index === 0) {
                        Ext.History.add([node.getOwnerTree().id, node.get("id")].join(Ext.History.DELIMITER));
                        if (Zenoss.Security.hasPermission('Manage DMD')) {
                            Ext.getCmp('footer_add_button').enable();
                            Ext.getCmp('footer_delete_button').enable();
                        }

                    }
                },
                resize: function (sidebar, newWidth, newHeight, oldWidth, oldHeight) {
                    var sidebarWidth = newWidth;
                    if (oldWidth === undefined) {
                        // page reload. restore width from state manager
                        savedWidth = Ext.state.Manager.get('devices_sidebar_width');
                        sidebarWidth = savedWidth === undefined ? sidebarWidth : savedWidth;
                    }
                    sidebar.splitter.setPosition(sidebarWidth + 20);
                    sidebar.setWidth(sidebarWidth);
                    Ext.state.Manager.set('devices_sidebar_width', sidebarWidth);
                }
            }
        }, {
            xtype: 'contextcardpanel',
            id: 'detail_panel',
            region: 'center',
            activeItem: 0,
            split: true,
            items: [
                device_grid,
                event_console,
                {
                    id: 'modeler_plugins',
                    xtype: 'modelerpluginpanel'
                }, {
                    id: 'configuration_properties',
                    xtype: 'configpropertypanel'
                }, {
                    id: 'custom_properties',
                    xtype: 'custompropertypanel'
                }, {
                    id: 'device_admin',
                    xtype: 'devadmincontainer'
                }, {
                    id: 'overridden_objects',
                    xtype: 'overriddenobjects'
                }
            ]
        }]
    });

    var bindTemplatesDialog = Ext.create('Zenoss.BindTemplatesDialog', {
        id: 'bindTemplatesDialog'
    });

    var resetTemplatesDialog = Ext.create('Zenoss.ResetTemplatesDialog', {
        id: 'resetTemplatesDialog'
    });

    function getOrganizerFields(mode) {
        var items = [];

        if (mode === 'add') {
            items.push({
                xtype: 'textfield',
                id: 'add_id',
                name: 'id',
                fieldLabel: _t('Name'),
                anchor: '80%',
                allowBlank: false
            });
        }

        items.push({
            xtype: 'textfield',
            id: 'description',
            name: 'description',
            fieldLabel: _t('Description'),
            anchor: '80%',
            allowBlank: true
        });


        var uid = "";
        if (getSelectionModel().getSelectedNode()) {
            uid = getSelectionModel().getSelectedNode().get('uid');
        }
        if (uid.startswith('/zport/dmd/Devices')) {
            var store = Ext.create('Zenoss.ConfigProperty.Store', {
                autoLoad: true
            });
            store.setBaseParam('uid', uid);
            items.push({
                xtype: 'combo',
                id: 'connectionInfo',
                queryMode: 'local',
                displayField: 'id',
                valueField: 'id',
                multiSelect: true,
                anchor: "80%",
                name: 'connectionInfo',
                fieldLabel: _t('Connection Information Properties'),
                store: store
            });
        }

        if (uid.startswith('/zport/dmd/Locations')) {
            items.push({
                xtype: 'textarea',
                id: 'address',
                name: 'address',
                fieldLabel: _t('Address'),
                allowBlank: true
            });
        }

        return items;
    }

    // Footer bar for the main Infrastructure page.
    // This extends Zenoss.footerHelper in FooterBar.js

    var footerBar = Ext.getCmp('footer_bar');
    Zenoss.footerHelper(
        '',
        footerBar,
        {
            hasOrganizers: false,

            // this footer bar has an add to zenpack option, but it defines its
            // own in contrast to using the canned one in footerHelper
            addToZenPack: false,

            // the message to display when user hits the [-] delete button.
            onGetDeleteMessage: function (itemName) {
                var node = getSelectionModel().getSelectedNode(),
                    tree = node.getOwnerTree(),
                    rootId = tree.getRootNode().data.id,
                    msg = _t('Are you sure you want to delete the {0} {1}? <br/>There is <strong>no</strong> undo.');
                if (rootId === devtree.root.id) {
                    msg = [msg, '<br/><br/><strong>',
                        _t('WARNING'), '</strong>:',
                        _t(' This will also delete all devices in this {0}.'),
                        '<br/>',
                        _t(' Type the full path of the class you want to remove to confirm')].join('');
                }
                return Ext.String.format(msg, itemName.toLowerCase(), '/' + node.data.path);
            },
            onGetAddDialogItems: function () { return getOrganizerFields('add'); },
            onGetItemName: function () {
                var node = getSelectionModel().getSelectedNode();
                if (node) {
                    var tree = node.getOwnerTree();
                    return tree.nodeName === 'Device' ? 'Device Class' : tree.nodeName;
                }
            },
            customAddDialog: {
            },
            buttonContextMenu: {
                xtype: 'ContextConfigureMenu',
                onSetContext: function (uid) {
                    bindTemplatesDialog.setContext(uid);
                    resetTemplatesDialog.setContext(uid);
                    Zenoss.env.PARENT_CONTEXT = uid;

                },
                onGetMenuItems: function (uid) {
                    var menuItems = [];
                    if (uid.match('^/zport/dmd/Devices')) {
                        menuItems.push([
                            {
                                xtype: 'menuitem',
                                text: _t('Bind Templates'),
                                hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
                                handler: function () {
                                    bindTemplatesDialog.show();
                                }
                            },
                            {
                                xtype: 'menuitem',
                                text: _t('Reset Bindings'),
                                hidden: Zenoss.Security.doesNotHavePermission('Edit Local Templates'),
                                handler: function () {
                                    resetTemplatesDialog.show();
                                }
                            }
                        ]);
                    }

                    menuItems.push({
                        xtype: 'menuitem',
                        text: _t('Clear Geocode Cache'),
                        hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        handler: function () {
                            REMOTE.clearGeocodeCache({}, function (data) {
                                var msg = (data.success) ?
                                    _t('Geocode Cache has been cleared') :
                                    _t('Something happened while trying to clear Geocode Cache');
                                var dialog = new Zenoss.dialog.SimpleMessageDialog({
                                    message: msg,
                                    buttons: [
                                        {
                                            xtype: 'DialogButton',
                                            text: _t('OK')
                                        }
                                    ]
                                });
                                dialog.show();
                            });
                        }
                    });

                    menuItems.push({
                        xtype: 'menuitem',
                        text: _t('Edit'),
                        hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                        handler: function () {
                            var node = getSelectionModel().getSelectedNode();

                            var dialog = new Zenoss.SmartFormDialog({
                                title: _t('Edit Organizer'),
                                formId: 'editDialog',
                                items: getOrganizerFields(),
                                formApi: {
                                    load: REMOTE.getInfo
                                }
                            });

                            dialog.setSubmitHandler(function (values) {
                                values.uid = node.get("uid");
                                REMOTE.setInfo(values);
                            });
                            dialog.getForm().load({
                                params: { uid: node.data.uid, keys: ['id', 'description', 'address', 'connectionInfo'] },
                                success: function () {
                                    dialog.show();
                                },
                                failure: function (form, action) {
                                    Ext.Msg.alert('Error', action.result.msg);
                                }
                            });

                        }
                    });

                    return menuItems;
                }
            }
        }
    );

    footerBar.add([
        {
            xtype: 'button',
            text: _t('Modeling'),
            iconCls: '',
            id: "context-model-menu",
            setContext: function(contextUid) {
                Ext.each(this.menu.items.items, function(i) {
                    i.contextUid = contextUid;
                });
            },
            menu: [
                {
                    xtype: 'menuitem',
                    text: _t('Model Devices'),
                    hidden: Zenoss.Security.doesNotHavePermission('Manage Device'),
                    handler: function () {
                        var win = new Zenoss.CommandWindow({
                            uids: [this.contextUid],
                            target: 'group_model',
                            title: _t('Model Devices in Organizer')
                        });
                        win.show();
                    }
                }, {
                    xtype: 'menuitem',
                    text: _t('Model Devices (Debug)'),
                    hidden: Zenoss.Security.doesNotHavePermission('Manage Device'),
                    handler: function () {
                        var win = new Zenoss.CommandWindow({
                            uids: [this.contextUid],
                            target: 'group_model_debug',
                            title: _t('Model Devices in Organizer')
                        });
                        win.show();
                    }
                }
            ]
        }, '-', {
            xtype: 'button',
            text: _t('Monitoring'),
            iconCls: '',
            id: "context-monitor-menu",
            setContext: function(contextUid) {
                Ext.each(this.menu.items.items, function(i) {
                    i.contextUid = contextUid;
                });
            },
            menu: [
                {
                    xtype: 'menuitem',
                    text: _t('Collect Devices data'),
                    hidden: Zenoss.Security.doesNotHavePermission('Manage Device'),
                    handler: function () {
                        var win = new Zenoss.CommandWindow({
                            uids: [this.contextUid],
                            target: 'group_monitor',
                            title: _t('Monitor Devices in Organizer')
                        });
                        win.show();
                    }
                }, {
                    xtype: 'menuitem',
                    text: _t('Collect Devices data (Debug)'),
                    hidden: Zenoss.Security.doesNotHavePermission('Manage Device'),
                    handler: function () {
                        var win = new Zenoss.CommandWindow({
                            uids: [this.contextUid],
                            target: 'group_monitor_debug',
                            title: _t('Monitor Devices in Organizer')
                        });
                        win.show();
                    }
                }
            ]
        }
    ]);

    footerBar.on('buttonClick', function (actionName, id, values) {
        var tree = getSelectionModel().getSelectedNode().getOwnerTree();
        switch (actionName) {
            // All items on this are organizers, no classes
            case 'addClass': tree.addChildNode(Ext.apply(values, { type: 'organizer' })); break;
            case 'addOrganizer': throw new Ext.Error('Not Implemented');
            case 'delete': tree.deleteSelectedNode(); break;
            default: break;
        }
    });
    if (Zenoss.settings.showPageStatistics) {
        Ext.create('Zenoss.stats.Infrastructure');
    }

    // if there is no history, select the top node
    if (!Ext.History.getToken()) {
        var node = Ext.getCmp('devices').getRootNode();
        node.fireEvent('expand', node);
    }

}); // Ext. OnReady
