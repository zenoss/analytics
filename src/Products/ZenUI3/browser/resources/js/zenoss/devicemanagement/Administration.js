/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2012, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

(function(){

Ext.ns('Zenoss', 'Zenoss.devicemanagement');

    var timeZone = "";

    Zenoss.devicemanagement = {
        createTooltip: function(text, overtext){
            return '<span style="cursor:pointer" title="'+overtext+'" >'+text+'</span>';
        },
        getProdStateValue: function(prodStateName){
            for ( var key in Zenoss.env.PRODUCTION_STATES_MAP) {
                if (Zenoss.env.PRODUCTION_STATES_MAP[key] === prodStateName){
                     return parseFloat(key);
                }
            }
            return false;
        },
        getStartTime: function(startTime){
            // @startTime format: 2012/10/22 08:05:00.000
            // break it up for the form elements
            var t = startTime.split(" ");
            var _start = {}
            _start.date = t[0].split("/")[1]+"/"+t[0].split("/")[2]+"/"+t[0].split("/")[0];        
            _start.hr = t[1].split(":")[0];
            _start.min = t[1].split(":")[1];
            return _start;
        },
        getDuration: function(duration){
            var patt1=/(?:(\d+) days )?(?:(\d\d):)?(\d\d):00/g;
            var match = patt1.exec(duration);
            var _duration = {};
            _duration.days = match[1] || 0;
            _duration.hrs  = match[2] || 0;
            _duration.mins = match[3] || 0;
            return _duration;
        },
        setUsersCombo: function(grid, combo, index){
            if(!Ext.isDefined(index)) {
                index = -1;
            }

            // create an object of users and return it - format like productionStates
            Zenoss.remote.DeviceManagementRouter.getUserList({uid:grid.uid}, function(response){
                if (response.success) {
                    Zenoss.devicemanagement.setComboFromData(response, combo, grid, 'user', index);
                }
            });
        },
        setRolesCombo: function(grid, uid, combo, index){
            if(!Ext.isDefined(index)) {
                index = -1;
            }
            Zenoss.remote.DeviceManagementRouter.getRolesList({uid:uid}, function(response){
                if (response.success) {
                    Zenoss.devicemanagement.setComboFromData(response, combo, grid, 'role', index);
                }
            });
        },
        setComboFromData: function(response, combo, grid, type, index){
            var data = [], gdata = grid.getView().getStore().data;
            for(var i=0;i < response.data.length; i++){
                if(type === "user"){
                    if( !this.alreadyInCombo(response.data[i], gdata, type)  ){
                        data.push([response.data[i]]);
                    }
                }else{
                    data.push([response.data[i]]);
                }
            }
            combo.store.loadData(data);
            if(index === -1) {
                return;
            }
            combo.setValue(combo.store.getAt(index));
        },
        alreadyInCombo: function(data, gdata){
            for(var i=0;i < gdata.items.length; i++){
                if(data === gdata.items[i].data.id) {
                    return true;
                }
            }
            return false;
        },
        setComboSleep: function(combo){
            combo.setDisabled(true);
            combo.setValue(combo.store.getAt(-1));
        }
    };

// ----------------------------------------------------------------- DIALOGS
    function maintDialog(grid, data) {
        if (!Ext.isDefined(data)) {
            data = "";
        }
        if (grid.uid === "/zport/dmd/Devices") {
            new Zenoss.dialog.SimpleMessageDialog({
                title: _t('Create Maintenance Window'),
                message: Ext.String.format(_t('Are you sure you want to create Maintenance Window at root class ' +
                    '"/Devices"? Creating unintended maintenance windows can have a significant impact on the system.' +
                    ' Please double check before progressing.'), data.name),
                buttonAlign: 'center',
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('OK'),
                    handler: function () {
                        createMaintDialog(grid, data);
                    }
                }, {
                    xtype: 'DialogButton',
                    text: _t('Cancel')
                }]
            }).show();
        } else {
            createMaintDialog(grid, data);
        }
    }

    function createMaintDialog(grid, data) {
        var addhandler, config, dialog, newEntry;
        var labelmargin = '5px 5px 0 0';
        newEntry = (data === "");

        addhandler = function() {
            var c = dialog.getForm().getForm().getValues();
            var padZero = function(num){
                if(num === "") {
                    return 0;
                }
                if(num.length === 1){
                    return "0"+num;
                }
                return num;
            };
            if(c.duration_days === 0 && c.duration_hrs === 0 && c.duration_mins === 0){ // if they didn't enter anything
                c.duration_mins = "1"; // have to have at least 1 minute
            }

            var params = {
                uid:                    grid.uid,
                id:                     c.id,
                name:                   c.name,
                startDate:              c.start_date,
                startHours:             padZero(c.start_hr),
                startMinutes:           padZero(c.start_min),
                timezone:               c.timezone,
                durationDays:           c.duration_days,
                durationHours:          padZero(c.duration_hrs),
                durationMinutes:        padZero(c.duration_mins),
                repeat:                 c.repeat,
                startProductionState:   c.start_state,
                enabled:                c.enabled,
                days:                   c.days,
                occurrence:             c.occurrence
            };

          if(newEntry){
                Zenoss.remote.DeviceManagementRouter.addMaintWindow({params:params}, function(response){
                    if (response.success) {
                        grid.refresh();
                    }
                });
            }else{
                Zenoss.remote.DeviceManagementRouter.editMaintWindow({params:params}, function(response){
                    if (response.success) {
                        grid.refresh();
                    }
                });
            }
        };

        // form config
        config = {
            submitHandler: addhandler,
            minHeight: 340,
            width: 400,
            id: 'addDialog',
            title: _t("Add New Maintenance Window"),
            listeners: {
                'afterrender': function(e){
                    if(!newEntry){ // this window will be used to EDIT the values instead of create from scratch
                        e.setTitle(_t("Edit Maintenance Window"));
                        var fields = e.getForm().getForm().getFields();
                        var prodState = Zenoss.devicemanagement.getProdStateValue(data.startProdState);
                        var startTime = Zenoss.devicemanagement.getStartTime(data.startTime_data);
                        var duration = Zenoss.devicemanagement.getDuration(data.duration_data); // returns object with days,hrs,mins
                        fields.findBy(
                            function(record){
                                switch(record.getName()){
                                    case "start_state"    : record.setValue(prodState);  break;
                                    case "start_date"     : record.setValue(startTime.date);  break;
                                    case "start_hr"       : record.setValue(startTime.hr); break;
                                    case "start_min"      : record.setValue(startTime.min); break;
                                    case "name"           : record.setValue(data.name);  break;
                                    case "id"             : record.setValue(data.name);  break;
                                    case "duration_days"  : record.setValue(duration.days);  break;
                                    case "duration_hrs"   : record.setValue(duration.hrs);  break;
                                    case "duration_mins"  : record.setValue(duration.mins);  break;
                                    case "repeat"         : record.setValue(data.repeat);  break;
                                    case "enabled"        : record.setValue(data.enabled);  break;
                                    case "days"           : record.setValue(data.days);  break;
                                    case "occurrence"     : record.setValue(data.occurrence);  break;
                                    case "timezone"       : record.setValue(data.timezone);  break;
                                }
                            }
                        );
                    }
                }
            },
            items: [
                {
                    xtype: 'panel',
                    layout: 'hbox',
                    margin: '0 0 30px 0',
                    items: [
                        {
                            xtype: 'textfield',
                            name: 'name',
                            disabled: !newEntry,
                            fieldLabel: _t('Name'),
                            margin: '0 10px 0 0',
                            width:220,
                            regex: Zenoss.env.textMasks.allowedNameText,
                            regexText: Zenoss.env.textMasks.allowedNameTextFeedback,
                            allowBlank: false
                        },{
                            xtype: 'hiddenfield',
                            name: 'id'
                        },{
                            xtype: 'panel',
                            layout: 'hbox',
                            margin: '18px 0 0 34px',
                            items:[
                                {
                                    xtype: 'label',
                                    text: _t('Enabled?'),
                                    margin: labelmargin
                                },{
                                    xtype: 'checkbox',
                                    name: 'enabled',
                                    checked: newEntry && true
                                }
                            ]
                        }
                    ]

                },{
                    xtype: 'panel',
                    layout: 'hbox',
                    margin: '0 0 30px 0',
                    items: [
                        {
                            xtype: 'datefield',
                            allowBlank: false,
                            name: 'start_date',
                            fieldLabel: _t('Start Date')
                        }]
                },{
                    xtype: 'panel',
                    layout: 'hbox',
                    margin: '30px 0 30px 0px',
                    items: [{
                        xtype: 'panel',
                        layout: 'hbox',
                        items: [{
                            xtype: 'panel',
                            layout: 'hbox',
                            margin: '14px 0 0 0',
                            items:[
                            {
                                xtype: 'label',
                                text: _t('Time: '),
                                margin: labelmargin
                            },{
                                xtype: 'numberfield',
                                maxValue: 23,
                                minValue: 0,
                                value: 0,
                                step: 1,
                                name: 'start_hr',
                                width: 45,
                                allowDecimals: false,
                                margin: '0 0px 0 0',
                                allowBlank: false
                            },{
                                xtype: 'label',
                                text: _t(':'),
                                margin: '5px 1px 0 1px'
                            },{
                                xtype: 'numberfield',
                                name: 'start_min',
                                maxValue: 59,
                                minValue: 0,
                                value: 0,
                                step: 1,
                                allowDecimals: false,
                                width: 45,
                                allowBlank: false
                            }]
                        },{
                                xtype: 'combo',
                                name: 'timezone',
                                fieldLabel: _t('Time Zone'),
                                margin: '0 0 0 20px',
                                valueField: 'name',
                                displayField: 'name',
                                width: 170,
                                forceSelection: true,
                                queryMode: 'local',
                                store: Ext.create('Ext.data.Store', {
                                    fields: ['name'],
                                    data: moment.tz.names().map(function(tz){
                                        return {
                                            name: tz,
                                        }
                                    })
                                }),
                                listeners: {
                                    afterrender: function(combo){
                                        if(combo.value === null) {
                                            combo.setValue(combo.store.findRecord('name', Zenoss.USER_TIMEZONE));
                                        }
                                    }
                                },
                            },
                        ]
                    }]
                },{
                    xtype: 'panel',
                    layout: 'hbox',
                    margin: '30px 0 30px 0px',
                    items: [
                        {
                            xtype: 'panel',
                            layout: 'hbox',
                            items: [
                                {
                                    xtype: 'label',
                                    text: _t('Duration in Days:'),
                                    margin: labelmargin
                                },{
                                    xtype: 'numberfield',
                                    name: 'duration_days',
                                    width: 50,
                                    value: 0,
                                    minValue: 0,
                                    maxValue: 999,
                                    margin: '0 14px 0 0',
                                    allowDecimals: false,
                                    allowBlank: false
                                }
                            ]
                        },{
                            xtype: 'panel',
                            layout: 'hbox',
                            items: [
                                {
                                    xtype: 'label',
                                    text: _t('Hrs:'),
                                    margin: labelmargin
                                },{
                                    xtype: 'numberfield',
                                    name: 'duration_hrs',
                                    width: 50,
                                    value: 0,
                                    maxValue: 23,
                                    minValue: 0,
                                    margin: '0 13px 0 0',
                                    allowDecimals: false,
                                    allowBlank: false
                                }
                            ]
                        },{
                            xtype: 'panel',
                            layout: 'hbox',
                            items: [
                                {
                                    xtype: 'label',
                                    text: _t('Mins:'),
                                    margin: labelmargin
                                },{
                                    xtype: 'numberfield',
                                    name: 'duration_mins',
                                    value: 0,
                                    maxValue: 59,
                                    minValue: 0,
                                    allowDecimals: false,
                                    width: 50,
                                    allowBlank: false
                                }
                            ]
                        }
                      ]
                    },{
                        xtype: 'panel',
                        layout: 'hbox',
                        margin: '0 0 30px 0',
                        items: [
                            {
                                xtype: 'combo',
                                name: 'repeat',
                                id: 'repeat-combo',
                                ref: 'repeat',
                                margin: '0 20px 0 0',
                                valueField: 'name',
                                value:'Never',
                                width: 160,
                                displayField: 'name',
                                typeAhead: false,
                                forceSelection: true,
                                triggerAction: 'all',
                                fieldLabel: _t('Repeat'),
                                listeners: {
                                                'select': function(field, value){
                                                    var cmb_occ = Ext.getCmp('occurrence-combo');
                                                    var cmb_days = Ext.getCmp('days-combo');
                                                    if (value && value[0].index === 5) {
                                                        cmb_occ.enable();
                                                        cmb_days.enable();
                                                    } else {
                                                        cmb_occ.disable();
                                                        cmb_days.disable();
                                                    }
                                                }
                                            },
                                listConfig: {
                                    maxWidth:160
                                },
                                store: new Ext.data.ArrayStore({
                                    model: 'Zenoss.model.Name',
                                    data: [
                                        ['Never'],['Daily'],['Every Weekday'],['Weekly'],
                                        ['Monthly: day of month'],['Monthly: day of week']
                                    ]
                                })
                            },{
                                xtype: 'combo',
                                disabled: true,
                                name: 'occurrence',
                                id: 'occurrence-combo',
                                ref: 'occurrence',
                                margin: '0 20px 0 0',
                                valueField: 'name',
                                value:'1st',
                                width: 70,
                                displayField: 'name',
                                typeAhead: false,
                                forceSelection: true,
                                triggerAction: 'all',
                                fieldLabel: _t('Occurrence'),
                                listConfig: {
                                    maxWidth:70
                                },
                                store: new Ext.data.ArrayStore({
                                    model: 'Zenoss.model.Name',
                                    data: [
                                        ['1st'], ['2nd'], ['3rd'], ['4th'], ['5th'], ['Last']
                                    ]
                                })
                            },{
                                xtype: 'combo',
                                disabled: true,
                                name: 'days',
                                id: 'days-combo',
                                ref: 'days',
                                margin: '0 20px 0 0',
                                valueField: 'name',
                                value:'Sunday',
                                width: 95,
                                displayField: 'name',
                                typeAhead: false,
                                forceSelection: true,
                                triggerAction: 'all',
                                fieldLabel: _t('Days'),
                                listConfig: {
                                    maxWidth:95
                                },
                                store: new Ext.data.ArrayStore({
                                    model: 'Zenoss.model.Name',
                                    data: [
                                        ['Monday'], ['Tuesday'], ['Wednesday'],
                                        ['Thursday'], ['Friday'], ['Saturday'],
                                        ['Sunday']
                                    ]
                                })
                            }
                       ]
                },  {
                        xtype: 'panel',
                        layout: 'hbox',
                        margin: '0 0 30px 0',
                        items: [
                            {
                                xtype: 'combo',
                                name: 'start_state',
                                ref: 'start_state',
                                id: 'start_state',
                                valueField: 'value',
                                displayField: 'name',
                                queryMode: 'local',
                                typeAhead: false,
                                forceSelection: true,
                                triggerAction: 'all',
                                fieldLabel: _t('Window Production State'),
                                listConfig: {
                                    maxWidth:185
                                },
                                listeners: {
                                    'afterrender': function(combo){
                                        if (newEntry) {
                                            combo.setValue(combo.store.findRecord('name', 'Maintenance'));
                                        }
                                    }
                                },
                                store: Ext.create('Ext.data.Store', {
                                    fields: ['value', 'name'],
                                    data : Zenoss.env.PRODUCTION_STATES
                                })
                            }

                       ]
                }
            ],
            // explicitly do not allow enter to submit the dialog
            keys: {}
        };


        if (Zenoss.Security.hasPermission('Maintenance Windows Edit')) {
            dialog = new Zenoss.SmartFormDialog(config);
            dialog.show();
        }else{ return false; }
    }


    function commandsDialog(grid, data) {
        if (!Ext.isDefined(data)) {
            data = "";
        }
        var addhandler, config, dialog, newEntry;
        var wintitle = _t("Add New User Command");
        newEntry = data === "";

        addhandler = function() {
            var c = dialog.getForm().getForm().getValues();

            var params = {
                uid:          grid.uid,
                id:           c.id,
                name:         c.name,
                description:  c.description,
                command:      c.command,
                password:     c.psword
            };
            if(newEntry){
                Zenoss.remote.DeviceManagementRouter.addUserCommand({params:params}, function(response){
                    if (response.success) {
                        grid.refresh();
                    }
                });
            }else{
                Zenoss.remote.DeviceManagementRouter.updateUserCommand({params:params}, function(response){
                    if (response.success) {
                        grid.refresh();
                    }
                });
            }
        };

        // form config
        config = {
            submitHandler: addhandler,
            minHeight: 315,
            autoHeight: true,
            width: 480,
            id: 'commandsDialog',
            listeners:{
                'afterrender': function(e){
                    if(!newEntry){ // this window will be used to EDIT the values instead of create from scratch
                        wintitle = _t("Edit User Command");
                        // set the dialog values after loading
                        e.setTitle(wintitle);
                        var fields = e.getForm().getForm().getFields();
                        fields.findBy(
                            function(record){
                                switch(record.getName()){
                                    case "name"         : record.setValue(data.id);  break;
                                    case "id"           : record.setValue(data.id);  break;
                                    case "description"  : record.setValue(data.description);  break;
                                    case "command"      : record.setValue(data.command); break;
                                }
                            }
                        );
                    }
                }
            },
            title: wintitle,
            items: [
                {
                    xtype: 'textfield',
                    name: 'name',
                    disabled: !newEntry,
                    fieldLabel: _t('Name'),
                    width:220,
                    regexText: Zenoss.env.textMasks.allowedNameTextFeedback,
                    regex: Zenoss.env.textMasks.allowedNameText,
                    allowBlank: false
                },{
                    xtype: 'hiddenfield',
                    name: 'id'
                },{
                    xtype: 'textareafield',
                    name: 'description',
                    margin: '3px 0 10px 0',
                    width:457,
                    height:55,
                    ref: 'desc',
                    regexText: Zenoss.env.textMasks.allowedDescTextFeedback,
                    regex: Zenoss.env.textMasks.allowedDescText,
                    fieldLabel: _t('Description')
                },{
                    xtype: 'textareafield',
                    name: 'command',
                    margin: '3px 0 10px 0',
                    width:457,
                    height:55,
                    ref: 'cmd',
                    fieldLabel: _t('Command')
                },{
                    xtype: 'password',
                    name: 'psword',
                    width:220,
                    fieldLabel: _t('Confirm Password')
                }
            ],
            // explicitly do not allow enter to submit the dialog
            keys: {}
        };

        if (Zenoss.Security.hasPermission('Define Commands Edit')) {
            dialog = new Zenoss.SmartFormDialog(config);
            dialog.show();
        }else{ return false; }

    }    // end add new commands dialog


    // ================================================= ADMIN DIALOG



    function adminsDialog(grid) {
        var addhandler, config, dialog;

        addhandler = function() {
            var c = dialog.getForm().getForm().getValues();
            var params = {
                uid:    grid.uid,
                name:   c.admin_combo,
                role:   c.role_combo
            };

            Zenoss.remote.DeviceManagementRouter.addAdminRole({params:params}, function(response){
                if (response.success) {
                    Zenoss.remote.DeviceManagementRouter.updateAdminRole({params:params}, function(response){
                        if (response.success) {
                            grid.reset();
                        }
                    });
                }
            });

        };

        // form config
        config = {
            submitHandler: addhandler,
            minHeight: 200,
            autoHeight: true,
            width: 250,
            autoScroll: false,
            id: 'adminsDialog',
            defaults:{
                applyLocalHidden: true
            },
            title: _t('Add Administrator'),
            items: [
                {
                    xtype: 'combo',
                    name: 'admin_combo',
                    ref: 'admin_combo',
                    editable: false,
                    fieldLabel: _t('Administrators'),
                    queryMode:'local',
                    listConfig: {
                        maxWidth:185
                    },
                    listeners: {
                        afterrender: function(combo){
                            Zenoss.devicemanagement.setUsersCombo(grid, combo, 0);
                        }
                    },
                    store: ['none']
                },{
                    xtype: 'combo',
                    name: 'role_combo',
                    margin: '20px 0 0 0',
                    ref: 'role_combo',
                    editable: false,
                    fieldLabel: _t('Role'),
                    queryMode:'local',
                    listConfig: {
                        maxWidth:185
                    },
                    listeners: {
                        afterrender: function(combo){
                            Zenoss.devicemanagement.setRolesCombo(grid, grid.uid, combo, 0);
                        }
                    },
                    store: ['none']
                }
            ],
            // explicitly do not allow enter to submit the dialog
            keys: {}
        };

        dialog = new Zenoss.SmartFormDialog(config);

        if (Zenoss.Security.hasPermission('Manage Device')) {
            dialog.show();
        }
    }    // end add new admin dialog


// --------------------------------------------------------------- GRIDS & WINDOW
Ext.define("Zenoss.devicemanagement.Administration", {
    alias:['widget.devadmincontainer'],
    extend:"Ext.Panel",
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'border',
            defaults: {
                split: true
            },
            items: [{
                xtype: 'MaintWindowsGrid',
                id: 'maintWindowGrid',
                region: 'north',
                height: '60%',
                ref: 'maintWindow'
            },{
                xtype: 'panel',
                layout: 'border',
                region: 'center',
                defaults: {
                    split: true
                },
                items: [{
                    xtype: 'AdminCommandsGrid',
                    id: 'deviceCommandsGrid',
                    ref: '../devicecommands',
                    region: 'west',
                    width: '50%'
                }, {
                    xtype: 'AdministratorsGrid',
                    id: 'adminsGrid',
                    ref: '../admins',
                    region: 'center'
                }]
            }]
        });
        Zenoss.devicemanagement.Administration.superclass.constructor.call(this, config);
    },
    setContext: function(uid){
        Ext.getCmp('maintWindowGrid').setContext(uid);
        Ext.getCmp('deviceCommandsGrid').setContext(uid);
        Ext.getCmp('adminsGrid').setContext(uid);
    }
});




// ------------------------------------------------------- Maint Window:
    /**
     * @class Zenoss.maintwindow.Model
     * @extends Ext.data.Model
     **/
    Ext.define('Zenoss.maintwindow.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: [
            {name: 'name'},
            {name: 'enabled'},
            {name: 'start'},
            {name: 'startTime'},
            {name: 'startTime_data', mapping:'startTime'},
            {name: 'duration'},
            {name: 'duration_data', mapping:'duration'},
            {name: 'repeat'},
            {name: 'niceRepeat'},
            {name: 'startProdState'},
            {name: 'days'},
            {name: 'occurrence'},
            {name: 'timezone'}
        ]
    });

    /**
     * @class Zenoss.maintwindow.Store
     * @extends Zenoss.DirectStore
     * Store for our maintenance window grid
     **/
    Ext.define("Zenoss.maintwindow.Store", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.maintwindow.Model',
                initialSortColumn: "name",
                directFn: Zenoss.remote.DeviceManagementRouter.getMaintWindows,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.maintwindow.Grid", {
        alias: ['widget.MaintWindowsGrid'],
        extend:"Zenoss.FilterGridPanel",
        constructor: function(config) {
            config = config || {};

            Zenoss.Security.onPermissionsChange(function() {
                disableButtons(this);
            }, this);

            Ext.applyIf(config, {
                stateId: config.id || 'maintwindow_grid',
                sm: Ext.create('Zenoss.SingleRowSelectionModel', {}),
                stateful: true,
                title: "Maintenance Windows",
                tbar:[
                    {
                    xtype: 'button',
                    iconCls: 'add',
                    tooltip: _t('Set up a new Maintenance Window'),
                    requiredPermission: 'Maintenance Windows Edit', // change the line below as well
                    disabled: Zenoss.Security.doesNotHavePermission('Maintenance Windows Edit'),
                    ref: 'addButton',
                        handler: function() {
                            var grid = Ext.getCmp("maintWindowGrid");
                            maintDialog(grid);
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'delete',
                        tooltip: _t('Delete selected Maintenance Window'),
                        requiredPermission: 'Maintenance Windows Edit', // change the line below as well
                        disabled: Zenoss.Security.doesNotHavePermission('Maintenance Windows Edit'),
                        handler: function() {
                            var grid = Ext.getCmp("maintWindowGrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();
                            if (Ext.isEmpty(selected)) {
                                return;
                            }

                            data = selected[0].data;
                            new Zenoss.dialog.SimpleMessageDialog({
                                title: _t('Delete Maintenance Window'),
                                message: Ext.String.format(_t("Are you sure you want to delete {0}?"), data.name),
                                buttons: [{
                                    xtype: 'DialogButton',
                                    text: _t('OK'),
                                    handler: function() {
                                        if (grid.uid) {
                                            Zenoss.remote.DeviceManagementRouter.deleteMaintWindow({uid:grid.uid, id:data.name}, function(response){
                                                if (response.success) {
                                                    grid.refresh();
                                                }
                                            });
                                        }
                                    }
                                }, {
                                    xtype: 'DialogButton',
                                    text: _t('Cancel')
                                }]
                            }).show();
                        }
                    },
                    {
                    xtype: 'button',
                    iconCls: 'customize',
                    tooltip: _t('Edit selected Maintenance Window'),
                    requiredPermission: 'Maintenance Windows Edit', // change the line below as well
                    disabled: Zenoss.Security.doesNotHavePermission('Maintenance Windows Edit'),
                    ref: 'customizeButton',
                        handler: function() {
                            var grid = Ext.getCmp("maintWindowGrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();

                            if (Ext.isEmpty(selected)) {
                                return;
                            }
                            // single selection
                            data = selected[0].data;
                            maintDialog(grid, data);
                        }
                    },
                    {
                    xtype: 'button',
                    iconCls: 'suppress',
                    tooltip: _t('Toggle Enable/Disable on selected Maintenance Window'),
                    requiredPermission: 'Maintenance Windows Edit', // change the line below as well
                    disabled: Zenoss.Security.doesNotHavePermission('Maintenance Windows Edit'),
                    ref: 'disableMaintButton',
                        handler: function() {
                            var grid = Ext.getCmp("maintWindowGrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();

                            if (Ext.isEmpty(selected)) {
                                return;
                            }
                            data = selected[0].data;
                            if (grid.uid) {
                                var prodState = Zenoss.devicemanagement.getProdStateValue(data.startProdState);
                                var startTime = Zenoss.devicemanagement.getStartTime(data.startTime_data);
                                var duration = Zenoss.devicemanagement.getDuration(data.duration_data);
                                var enabled = (!data.enabled);

                                var params = {
                                    uid:                    grid.uid,
                                    id:                     data.name,
                                    name:                   data.name,
                                    startDate:              startTime.date,
                                    startHours:             startTime.hr,
                                    startMinutes:           startTime.min,
                                    durationDays:           duration.days,
                                    durationHours:          duration.hrs,
                                    durationMinutes:        duration.mins,
                                    repeat:                 data.repeat,
                                    days:                   data.days,
                                    occurrence:             data.occurrence,
                                    startProductionState:   prodState,
                                    enabled:                enabled
                                };
                                Zenoss.remote.DeviceManagementRouter.editMaintWindow({params:params}, function(response){
                                    if (response.success) {
                                        grid.refresh();
                                    }
                                });
                            }
                            // do an update that only toggles the enabled
                        }
                    }
                ],
                store: Ext.create('Zenoss.maintwindow.Store', {}),
                columns: [
                    {
                        id: 'maint_enabled',
                        dataIndex: 'enabled',
                        header: _t('Enabled'),
                        width: 50,
                        sortable: true,
                        filter: false,
                        renderer: function(value){
                            if (value) {
                                return '<span style="color:green;">Yes</span>';
                            }
                            return '<span style="color:red;">No</span>';
                        }
                    },{
                        header: _t("Name"),
                        id: 'maint_name',
                        dataIndex: 'name',
                        flex: 1,
                        filter: false,
                        sortable: true
                    },{
                        id: 'maint_start_data',
                        dataIndex: 'startTime_data',
                        hidden:true
                    },{
                        id: 'maint_start',
                        dataIndex: 'startTime',
                        header: _t('Start'),
                        width: 140,
                        filter: false,
                        sortable: true,
                        renderer: function(val){
                            return val;
                        }
                    },{
                        id: 'maint_duration_data',
                        dataIndex: 'duration_data',
                        hidden:true
                    },{
                        id: 'maint_duration',
                        dataIndex: 'duration',
                        header: _t('Duration'),
                        width: 140,
                        filter: false,
                        sortable: true,
                        renderer: function(val){
                            if(val.length === 5){ // it's only minutes
                                return val+" mins";
                            }else if(val.length === 8){
                                return val+" hrs";
                            }

                            return val;
                        }
                    },{
                        id: 'maint_repeat',
                        dataIndex: 'niceRepeat',
                        header: _t('Repeat'),
                        width: 150,
                        filter: false,
                        sortable: true
                    },{
                        id: 'maint_startstate',
                        dataIndex: 'startProdState',
                        header: _t('State'),
                        width: 100,
                        filter: false,
                        sortable: true
                    }]
            });
            this.callParent(arguments);
            this.on('itemdblclick', this.onRowDblClick, this);
        },
        setContext: function(uid) {
            this.uid = uid;
            // load the grid's store
            this.callParent(arguments);
        },
        onRowDblClick: function() {
            var data,
                selected = this.getSelectionModel().getSelection();
            if (!selected) {
                return;
            }
            data = selected[0].data;
            maintDialog(this, data);
        },
        beforeRender: function() {
            Zenoss.remote.DeviceManagementRouter.getTimeZone({}, function(response){
                if(response.success){
                    timeZone = response.data;
                }
            });
        }
    });

    var contextIsDevice = function(uid){
        var split = uid.split('/devices/');
        if(split[1]){
            return true;
        }
        return false;
    };

    var disableButtons = function(cmp) {
        var btns = cmp.query("button");
        Ext.each(btns, function(btn){
            if(btn.requiredPermission) {
                btn.setDisabled(Zenoss.Security.doesNotHavePermission(btn.requiredPermission));
            }
        });
    }


// ------------------------------------------------------- Commands:

    Ext.define('Zenoss.admincommands.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: [
            {name: 'id'},
            {name: 'command'},
            {name: 'description'}
        ]
    });

    /**
     * @class Zenoss.admincommands.Store
     * @extends Zenoss.DirectStore
     * Store for our admincommands window grid
     **/
    Ext.define("Zenoss.admincommands.Store", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.admincommands.Model',
                initialSortColumn: "id",
                directFn: Zenoss.remote.DeviceManagementRouter.getUserCommands,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.admincommands.Grid", {
        alias: ['widget.AdminCommandsGrid'],
        extend:"Zenoss.FilterGridPanel",
        constructor: function(config) {
            config = config || {};

            Zenoss.Security.onPermissionsChange(function() {
                disableButtons(this);
            }, this);

            Ext.applyIf(config, {
                stateId: config.id || 'admincommands_grid',
                sm: Ext.create('Zenoss.SingleRowSelectionModel', {}),
                stateful: true,
                title: "User Commands",
                tbar:[
                    {
                    xtype: 'button',
                    iconCls: 'add',
                    tooltip: _t('Add a User Command'),
                    requiredPermission: 'Define Commands Edit', // change the line below as well
                    disabled: Zenoss.Security.doesNotHavePermission('Define Commands Edit'),
                    ref: 'addButton',
                        handler: function() {
                            var grid = Ext.getCmp("deviceCommandsGrid");
                            commandsDialog(grid);
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'delete',
                        tooltip: _t('Delete selected User Command'),
                        requiredPermission: 'Define Commands Edit', // change the line below as well
                        disabled: Zenoss.Security.doesNotHavePermission('Define Commands Edit'),
                        handler: function() {
                            var grid = Ext.getCmp("deviceCommandsGrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();
                            if (Ext.isEmpty(selected)) {
                                return;
                            }

                            data = selected[0].data;
                            new Zenoss.dialog.SimpleMessageDialog({
                                title: _t('Delete User Command'),
                                message: Ext.String.format(_t("Are you sure you want to delete the User Command {0}?"), data.id),
                                buttons: [{
                                    xtype: 'DialogButton',
                                    text: _t('OK'),
                                    handler: function() {
                                        if (grid.uid) {
                                            Zenoss.remote.DeviceManagementRouter.deleteUserCommand({uid:grid.uid, id:data.id}, function(response){
                                                if (response.success) {
                                                    grid.refresh();
                                                }
                                            });
                                        }
                                    }
                                }, {
                                    xtype: 'DialogButton',
                                    text: _t('Cancel')
                                }]
                            }).show();
                        }
                    },
                    {
                    xtype: 'button',
                    iconCls: 'customize',
                    tooltip: _t('Edit selected User Command'),
                    requiredPermission: 'Define Commands Edit', // change the line below as well
                    disabled: Zenoss.Security.doesNotHavePermission('Define Commands Edit'),
                    ref: 'customizeButton',
                        handler: function() {
                            var grid = Ext.getCmp("deviceCommandsGrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();

                            if (Ext.isEmpty(selected)) {
                                return;
                            }
                            // single selection
                            data = selected[0].data;
                            commandsDialog(grid, data);
                        }
                    }, {
                    xtype: 'button',
                    iconCls: 'export',
                    tooltip: _t('Add selected User Command to ZenPack'),
                    ref: '../refreshButton',
                    requiredPermission: 'Define Commands Edit', // change the line below as well
                    disabled: Zenoss.Security.doesNotHavePermission('Define Commands Edit'),
                    handler: function() {
                        var grid = Ext.getCmp("deviceCommandsGrid");
                        var zp_dialog = Ext.create('Zenoss.AddToZenPackWindow', {});
                        zp_dialog.setTarget(grid.uid);
                        zp_dialog.show();
                    }
                    },{
                        xtype: 'button',
                        iconCls: 'acknowledge',
                        tooltip: _t('Run the selected command'),
                        requiredPermission: 'Manage Device', // change the line below as well
                        disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
                        listeners: {
                            afterrender: function(b){
                                b.setVisible(contextIsDevice(Ext.getCmp("deviceCommandsGrid").uid));
                            }
                        },
                        handler: function(){
                                var grid = Ext.getCmp("deviceCommandsGrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();

                            if (Ext.isEmpty(selected)) {
                                return;
                            }
                            // single selection
                            data = selected[0].data;
                            var win = new Zenoss.CommandWindow({
                                uids: [grid.uid],
                                target: grid.uid + '/run_command',
                                command: data.id
                            });
                            win.show();
                        }
                    }
                ],
                store: Ext.create('Zenoss.admincommands.Store', {}),
                columns: [{
                        header: _t("Name"),
                        id: 'cmd_name',
                        dataIndex: 'id',
                        width: 150,
                        filter: false,
                        sortable: true,
                        renderer: function(val, o, fields){
                            return Zenoss.devicemanagement.createTooltip(val, fields.data.description);
                        }
                    },{
                        id: 'cmd_command',
                        dataIndex: 'command',
                        header: _t('Command'),
                        flex: 1,
                        filter: false,
                        sortable: true,
                        renderer: function(val, o, fields){
                            return Zenoss.devicemanagement.createTooltip(val, fields.data.description);
                        }
                    }]
            });
            this.callParent(arguments);
            this.on('itemdblclick', this.onRowDblClick, this);
        },
        setContext: function(uid) {
            this.uid = uid;
            // load the grid's store
            this.callParent(arguments);
        },
        onRowDblClick: function() {
            var data,
                selected = this.getSelectionModel().getSelection();
            if (!selected) {
                return;
            }
            data = selected[0].data;
            if(!data) {
                return;
            }
            commandsDialog(this, data);
        }
    });


// ------------------------------------------------------- Admins:
    /**
     * @class Zenoss.maintwindow.Model
     * @extends Ext.data.Model
     **/
    Ext.define('Zenoss.administrators.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: [
            {name: 'id'},
            {name: 'description'},
            {name: 'role'},
            {name: 'email'},
            {name: 'pager'}
        ]
    });

    /**
     * @class Zenoss.administrators.Store
     * @extends Zenoss.DirectStore
     * Store for our device administrators grid
     **/
    Ext.define("Zenoss.administrators.Store", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.administrators.Model',
                initialSortColumn: "id",
                directFn: Zenoss.remote.DeviceManagementRouter.getAdminRoles,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.administrators.Grid", {
        alias: ['widget.AdministratorsGrid'],
        extend:"Zenoss.FilterGridPanel",
        constructor: function(config) {
            config = config || {};

            Zenoss.Security.onPermissionsChange(function() {
                disableButtons(this);
            }, this);

            Ext.applyIf(config, {
                stateId: config.id || 'admins_grid',
                sm: Ext.create('Zenoss.SingleRowSelectionModel', {}),
                stateful: true,
                title: "Administrators",
                tbar:[
                    {
                    xtype: 'button',
                    iconCls: 'add',
                    tooltip: _t('Add a User'),
                    requiredPermission: 'Manage Device', // change the line below as well
                    disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
                    ref: 'addButton',
                        handler: function() {
                            var grid = Ext.getCmp("adminsGrid");
                            adminsDialog(grid);
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'delete',
                        tooltip: _t('Remove selected User from the Device Administrators panel'),
                        requiredPermission: 'Maintenance Windows Edit', // change the line below as well
                        disabled: Zenoss.Security.doesNotHavePermission('Maintenance Windows Edit'),
                        handler: function() {
                            var grid = Ext.getCmp("adminsGrid"),
                                data,
                                selected = grid.getSelectionModel().getSelection();
                            if (Ext.isEmpty(selected)) {
                                return;
                            }

                            data = selected[0].data;
                            new Zenoss.dialog.SimpleMessageDialog({
                                title: _t('Remove Admin from Device'),
                                message: Ext.String.format(_t("Are you sure you want to remove this admin?")),
                                buttons: [{
                                    xtype: 'DialogButton',
                                    text: _t('OK'),
                                    handler: function() {
                                        if (grid.uid) {
                                            Zenoss.remote.DeviceManagementRouter.removeAdmin({uid:grid.uid, id:data.id}, function(response){
                                                if (response.success) {
                                                    grid.reset();
                                                }
                                            });
                                        }
                                    }
                                }, {
                                    xtype: 'DialogButton',
                                    text: _t('Cancel')
                                }]
                            }).show();
                        }
                    },
                    {
                    xtype: 'button',
                    iconCls: 'set',
                    tooltip: _t('Edit users on the advanced user account edit page'),
                    requiredPermission: 'Manage Device', // change the line below as well
                    disabled: Zenoss.Security.doesNotHavePermission('Manage Device'),
                    ref: 'editAdminButton',
                        handler: function() {
                            Ext.getCmp("adminsGrid").editpage();
                        }
                    },{
                        xtype: 'panel',
                        tooltip: _t('Edit selected Admin Role'),
                        layout: 'hbox',
                        bodyStyle: 'background:transparent;',
                        items:[
                            {
                                xtype: 'label',
                                margin: '5px 3px 0 5px',
                                text: _t('Change Role:')
                            },
                            {
                            xtype: 'combo',
                            disabled: true,
                            id: 'changeroleCombo',
                            editable: false,
                            queryMode:'local',
                            listConfig: {
                                maxWidth:155
                            },
                            listeners: {
                                select: function(combo){
                                    var grid = Ext.getCmp("adminsGrid"),
                                        gridrow = grid.getSelectionModel().getSelection(),
                                        griddata = gridrow[0].data,
                                        params = {
                                            uid:    grid.uid,
                                            name:   griddata.id,
                                            role:   combo.value
                                        };
                                    Zenoss.remote.DeviceManagementRouter.updateAdminRole({params:params}, function(response){
                                        if (response.success) {
                                            grid.reset();
                                        }
                                    });
                                }
                            },
                            store: ['none']
                            }
                        ]
                    }
                ],
                store: Ext.create('Zenoss.administrators.Store', {}),
                columns: [{
                        header: _t("Name"),
                        id: 'admin_name',
                        dataIndex: 'id',
                        width: 150,
                        filter: false,
                        sortable: true,
                        renderer: function(e){
                            var gotoWin = window.location.protocol + '//' + window.location.host;
                            gotoWin += '/zport/dmd/ZenUsers/' + e;
                            return '<a href="'+gotoWin+'" title="Edit the user '+e+' on the user accounts page">'+e+'</a>';
                        }
                    },{
                        id: 'admin_role',
                        dataIndex: 'role',
                        header: _t('Role'),
                        width: 90,
                        filter: false,
                        sortable: true
                    },{
                        id: 'admin_email',
                        dataIndex: 'email',
                        header: _t('Email'),
                        flex: 1,
                        filter: false,
                        sortable: true
                    },{
                        id: 'admin_pager',
                        dataIndex: 'pager',
                        header: _t('Pager'),
                        width: 120,
                        filter: false,
                        sortable: true
                    }]
            });
            this.callParent(arguments);
            this.on('select', this.onRowSelect, this);
        },
        setContext: function(uid) {
            this.uid = uid;
            this.callParent(arguments);
            Zenoss.devicemanagement.setRolesCombo(this, uid, Ext.getCmp('changeroleCombo'));
        },
        onRowSelect: function(model, selectedRow){
            if (Zenoss.Security.hasPermission('Manage Device')) {
                var combo = Ext.getCmp('changeroleCombo');
                combo.setDisabled(false);
                var index = combo.getStore().find('field1', selectedRow.data.role);
                combo.setValue(combo.store.getAt(index));
            }
        },
        reset: function(){
            this.refresh();
            Zenoss.devicemanagement.setComboSleep(Ext.getCmp('changeroleCombo'));
        },
        editpage: function(){
            var location,
                selected = this.getSelectionModel().getSelection();

            if (Ext.isEmpty(selected)) {
                location = '/zport/dmd/ZenUsers/manageUserFolder';
            }else{
                location = '/zport/dmd/ZenUsers/' + encodeURIComponent(selected[0].data.id);
            }

            var hostString = window.location.protocol + '//' + window.location.host;
            window.location = hostString + location;
            // take them to the accounts page under advanced
        }
    });


})();
