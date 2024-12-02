/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2011-2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){
    var router = Zenoss.remote.DeviceRouter;
    /**
     * Generic model for things that only have a
     * name and uid
     **/
    Ext.define('Zenoss.component.add.UidNameModel', {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: ['uid', 'name']
    });


    /**
     * Dialogs for adding user created components to a device.
     * The convention is that your class has a namespace of  Zenoss.component.add.[ComponentName]
     *
     * You must provide the handler for saving the dialog but the component grid refresh will happen
     * automatically when the dialog is no longer shown.
     **/

    /**
     * @class Zenoss.component.add.IpRouteEntry
     * @extends Zenoss.SmartFormDialog
     * Adds an Ip Route Entry
     **/
    Ext.define('Zenoss.component.add.IpRouteEntry',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 250,
                title: _t('Add Ip Route Entry'),
                submitHandler: Ext.bind(this.createIpRouteEntry, this),
                items: [{
                    xtype: 'hidden',
                    name: 'userCreated',
                    value: true
                }, {
                    xtype: 'textfield',
                    name: 'dest',
                    fieldLabel: _t('Destination')
                }, {
                    xtype: 'textfield',
                    name: 'routemask',
                    fieldLabel: _t('Mask'),
                    size: 2
                },{
                    xtype: 'textfield',
                    name: 'nexthopid',
                    fieldLabel: _t('Next Hop')
                },{
                    xtype: 'combo',
                    fieldLabel: _t('Interfaces'),
                    valueField: 'name',
                    displayField: 'name',
                    name: 'interface',
                    triggerAction: 'all',
                    store: new Zenoss.NonPaginatedStore({
                        model: 'Zenoss.component.add.UidNameModel',
                        initialSortColumn: 'name',
                        directFn: Zenoss.remote.DeviceRouter.getComponents,
                        listeners: {
                            beforeload: function(store, operation){
                                operation.params.uid = config.uid;
                                operation.params.keys = ['uid', 'name'];
                                operation.params.meta_type =  'IpInterface';
                                delete operation.params.query;
                            }
                        }
                    })

                }, {
                    xtype: 'combo',
                    fieldLabel: _t('Protocol'),
                    name: 'routeproto',
                    editable: false,
                    forceSelection: true,
                    autoSelect: true,
                    triggerAction: 'all',
                    queryMode: 'local',
                    store: ['other', 'invalid', 'direct', 'indirect']
                },{
                    xtype: 'combo',
                    fieldLabel: _t('Type'),
                    name: 'routetype',
                    editable: false,
                    forceSelection: true,
                    autoSelect: true,
                    triggerAction: 'all',
                    queryMode: 'local',
                    store: ['other', 'local', 'netmgmt', 'icmp',
                            'egp', 'ggp', 'hello', 'rip', 'is-is', 'es-is',
                            'ciscoIgrp', 'bbnSpfIgrp', 'ospf', 'bgp']
                }]
            });
            this.callParent([config]);
        },
        createIpRouteEntry: function(values) {
            values.uid = this.uid;
            router.addIpRouteEntry(values, function(response){
                if (response.success) {
                    Zenoss.message.info(_t('Added Ip Route Entry'));
                }
            });
        }
    });

    /**
     * @class Zenoss.component.add.IpInterface
     * @extends Zenoss.SmartFormDialog
     * Dialog for adding an Ip Interface
     **/
    Ext.define('Zenoss.component.add.IpInterface',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 150,
                title: _t('Add Ip Interface'),
                submitHandler: Ext.bind(this.createIpInterface, this),
                items: [{
                    xtype: 'hidden',
                    name: 'userCreated',
                    value: true
                }, {
                    xtype: 'textfield',
                    name: 'newId',
                    fieldLabel: _t('ID')
                }]
            });
            this.callParent([config]);
        },
        createIpInterface: function(values) {
            values.uid = this.uid;
            router.addIpInterface(values, function(response){
                if (response.success) {
                    Zenoss.message.info(_t("Added Ip Interface"));
                }
            });
        }
    });

    /**
     * @class Zenoss.component.add.OSProcess
     * @extends Zenoss.SmartFormDialog
     * Dialog for adding an OS Process Class
     **/
    Ext.define('Zenoss.component.add.OSProcess',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 200,
                title: _t('Add Process'),
                submitHandler: Ext.bind(this.createOSProcess, this),
                items: [{
                    xtype: 'hidden',
                    name: 'userCreated',
                    value: true
                }, {
                    xtype: 'combo',
                    fieldLabel: _t('Process Class'),
                    displayField: 'name',
                    name: 'newClassName',
                    valueField: 'uid',
                    triggerAction: 'all',
                    store: new Zenoss.NonPaginatedStore({
                        model: 'Zenoss.component.add.UidNameModel',
                        initialSortColumn: 'name',
                        root: 'processes',
                        directFn: Zenoss.remote.ProcessRouter.query,
                        listeners: {
                            beforeload: function(store, operation){
                                operation.params.uid = '/zport/dmd/Processes';
                                operation.params.sort = 'name';
                                delete operation.params.query;
                            }
                        }
                    })
                }, {
                    xtype: 'textfield',
                    fieldLabel: _t('Example Command Line'),
                    name: 'example',
                    width: 300
                }]
            });
            this.callParent([config]);
        },
        createOSProcess: function(values) {
            values.uid = this.uid;
            router.addOSProcess(values, function(response){
                if (response.success) {
                    Zenoss.message.info(_t("Added OS Process"));
                }
            });
        }
    });

    /**
     * @class Zenoss.component.add.FileSystem
     * @extends Zenoss.SmartFormDialog
     * Dialog for adding a File System
     **/
    Ext.define('Zenoss.component.add.FileSystem',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                height: 150,
                title: _t('Add File System'),
                submitHandler: Ext.bind(this.createFileSystem, this),
                items: [{
                    xtype: 'hidden',
                    name: 'userCreated',
                    value: true
                }, {
                    xtype: 'textfield',
                    name: 'newId',
                    fieldLabel: _t('ID')
                }]
            });
            this.callParent([config]);
        },
        createFileSystem: function(values) {
            values.uid = this.uid;
            router.addFileSystem(values, function(response){
                if (response.success) {
                    Zenoss.message.info(_t("Added File System"));
                }
            });
        }
    });

    /**
     * @class Zenoss.component.add.IpService
     * @extends Zenoss.SmartFormDialog
     * Dialog for adding an Ip Service
     **/
    Ext.define('Zenoss.component.add.IpService',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            var modelId = Ext.id();
            Ext.define(modelId, {
                extend: 'Ext.data.Model',
                idProperty: 'value',
                fields: ['name', 'value']
            });
            Ext.applyIf(config, {
                height: 250,
                title: _t('Add Ip Service'),
                submitHandler: Ext.bind(this.createIpService, this),
                items: [{
                    xtype: 'hidden',
                    name: 'userCreated',
                    value: true
                }, {
                    xtype: 'combo',
                    fieldLabel: _t('Service Class'),
                    name: 'newClassName',
                    width: 150,
                    typeAhead:true,
                    forceSelection: true,
                    triggerAction: 'all',
                    displayField: 'name',
                    valueField: 'value',
                    store: new Zenoss.NonPaginatedStore({
                        model: modelId,
                        directFn: Zenoss.remote.ServiceRouter.getClassNames,
                        listeners: {
                            beforeload: function(store, operation){
                                operation.params.uid = '/zport/dmd/Services/IpService';
                            }
                        }
                    })

                },{
                    xtype: 'combo',
                    fieldLabel: _t('Protocol'),
                    name: 'protocol',
                    editable: false,
                    forceSelection: true,
                    autoSelect: true,
                    triggerAction: 'all',
                    queryMode: 'local',
                    store: ['tcp', 'udp']
                }]
            });
            this.callParent([config]);
        },
        createIpService: function(values) {
            values.uid = this.uid;
            router.addIpService(values, function(response){
                if (response.success) {
                    Zenoss.message.info(_t("Added Ip Service"));
                }
            });
        }
    });

    /**
     * @class Zenoss.component.add.WinService
     * @extends Zenoss.SmartFormDialog
     * Dialog for adding an Ip Service
     **/
    Ext.define('Zenoss.component.add.WinService',{
        extend: 'Zenoss.SmartFormDialog',
        constructor: function(config) {
            config = config || {};
            var modelId = Ext.id();
            Ext.define(modelId, {
                extend: 'Ext.data.Model',
                idProperty: 'value',
                fields: ['path', 'value']
            });
            Ext.applyIf(config, {
                height: 150,
                title: _t('Add Win Service'),
                submitHandler: Ext.bind(this.createWinService, this),
                items: [{
                    xtype: 'hidden',
                    name: 'userCreated',
                    value: true
                }, {
                    xtype: 'combo',
                    fieldLabel: _t('Service Class'),
                    name: 'newClassName',
                    width: 350,
                    typeAhead:true,
                    forceSelection: true,
                    displayField: 'path',
                    valueField: 'value',
                    triggerAction: 'all',
                    store: new Zenoss.NonPaginatedStore({
                        model: modelId,
                        directFn: Zenoss.remote.ServiceRouter.getClassNames,
                        listeners: {
                            beforeload: function(store, operation){
                                operation.params.uid = '/zport/dmd/Services/WinService';
                            }
                        }
                    })

                }]
            });
            this.callParent([config]);
        },
        createWinService: function(values) {
            values.uid = this.uid;
            router.addWinService(values, function(response){
                if (response.success) {
                    Zenoss.message.info(_t("Added Win Service"));
                }
            });
        }
    });

}());
