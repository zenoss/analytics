/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

(function(){
    Ext.ns('Zenoss.events');
    Ext.ns('Zenoss.eventclasses');

    Zenoss.events.getRowClass = function(record) {
        var stateclass = record.get('eventState')==='New' ?
            'unacknowledged':'acknowledged';
        var sev = Zenoss.util.convertSeverity(record.get('severity'));
        var rowcolors = Ext.state.Manager.get('rowcolor') ? 'rowcolor rowcolor-' : '';
        return rowcolors + sev + '-' + stateclass + ' ' + stateclass;
    };

    /*
     * Show the dialog that allows one to add an event.
     */
    function showAddEventDialog(gridId) {
        if (Ext.getCmp('addeventwindow')) {
            Ext.getCmp('addeventwindow').show();
            return;
        }
        var device;
        if (Zenoss.env.device_uid) {
            device = Zenoss.env.device_uid.split("/").reverse()[0];
        } else {
            if (!_has_global_roles()) {
                device = Ext.getCmp(gridId).getSelectionModel().getSelected().data.device.text
            }
        }
        var collectors = new Ext.data.ArrayStore({
                        data: Zenoss.env.COLLECTORS,
                        fields: ['name']
                    })
        var defaultValue;
        if (Zenoss.env.COLLECTORS[0].indexOf('localhost') > -1){
            defaultValue = "localhost";
        } else {
            defaultValue = null;
        }
        var addevent = Ext.create('Zenoss.dialog.BaseWindow', {
            title: _t('Create Event'),
            id: 'addeventwindow',
            layout: 'fit',
            autoHeight: true,
            modal: true,
            width: 310,
            closeAction: 'hide',
            plain: true,
            items: [{
                id: 'addeventform',
                xtype: 'form',
                defaults: {width: 290},
                autoHeight: true,
                frame: false,
                listeners: {
                    validitychange: function(form, isValid){
                        addevent.query('DialogButton')[0].setDisabled(!isValid);
                    }
                },
                fieldDefaults: {
                    labelWidth: 100
                },
                items: [{
                    xtype: 'textarea',
                    name: 'summary',
                    id: 'add_event_summary_textarea',
                    fieldLabel: _t('Summary'),
                    allowBlank: false
                },{
                    xtype: 'textfield',
                    fieldLabel: _t('Device'),
                    id: 'add_event_device_textfield',
                    name: 'device',
                    allowBlank: false,
                    readOnly: !_has_global_roles(),
                    value: device
                },{
                    xtype: 'textfield',
                    fieldLabel: _t('Component'),
                    id: 'add_event_component_textfield',
                    name: 'component'
                },{
                    fieldLabel: _t('Severity'),
                    name: 'severity',
                    xtype: 'combo',
                    id: 'add_event_severity_combo',
                    store: Zenoss.env.SEVERITIES,
                    typeAhead: true,
                    allowBlank: false,
                    forceSelection: true,
                    triggerAction: 'all',
                    value: 5,
                    selectOnFocus: true,
                    listConfig: {
                        id: 'add_event_severity_combo_list'
                    }
                },{
                    xtype: 'textfield',
                    fieldLabel: _t('Event Class Key'),
                    id: 'add_event_key_textfield',
                    name: 'evclasskey'
                },{
                    fieldLabel: _t('Event Class'),
                    name: 'evclass',
                    xtype: 'combo',
                    id: 'add_event_evclass_combo',
                    allowBlank: true,
                    store: Zenoss.env.EVENT_CLASSES,
                    typeAhead: true,
                    forceSelection: true,
                    triggerAction: 'all',
                    selectOnFocus: true,
                    listConfig: {
                        resizable: true,
                        id: 'add_event_evclass_combo_list'
                    }
                },{
                    fieldLabel: _t('Collector'),
                    name: 'monitor',
                    xtype: 'combo',
                    allowBlank: false,
                    store: collectors,
                    valueField: 'name',
                    displayField: 'name',
                    typeAhead: true,
                    forceSelection: true,
                    triggerAction: 'all',
                    selectOnFocus: true,
                    value: defaultValue,
                    listConfig: {
                        resizable: true
                    }
                }],
                buttons: [{
                    text: _t('Submit'),
                    xtype: 'DialogButton',
                    id: 'add_event_submit_button',
                    formBind: true,
                    handler: function(){
                        var form = Ext.getCmp('addeventform');
                        Zenoss.remote.EventsRouter.add_event(
                            form.getForm().getValues(),
                            function(){
                                addevent.hide();
                                var grid = Ext.getCmp(gridId);
                                grid.refresh();
                            }
                        );
                    }
                },{
                    text: _t('Cancel'),
                    xtype: 'DialogButton',
                    id: 'add_event_cancel_button',
                    handler: function(){
                        addevent.hide();
                    }
                }]
            }]

        });
        addevent.show();
    }


    /*
     * Show the dialog that allows one to classify an event
     */
    function showClassifyDialog(gridId) {

        Zenoss.events.launchMappingDialog = function(uid){
            var grid = null;
            var data = {};
            data.whichPanel = 'default';
            data.uid = "/zport/dmd/"+uid.split("| ")[1];
            Zenoss.eventclasses.mappingDialog(grid, data);
        };


        var win = new Zenoss.dialog.BaseWindow({
            title: _t('Classify Events'),
            id: 'reclassify_events_window',
            width: 300,
            autoHeight: true,
            modal: true,
            plain: true,
            items: [{
                id: 'classifyEventForm',
                xtype: 'form',
                monitorValid: true,
                autoHeight: true,
                frame: false,
                items: [{
                    padding: 10,
                    style: {'font-size':'10pt'},
                    html: _t('Select the event class with which'+
                             ' you want to associate these events.')
                },{
                    xtype: 'combo',
                    store: Zenoss.env.EVENT_CLASSES,
                    typeAhead: true,
                    allowBlank: false,
                    forceSelection: true,
                    triggerAction: 'all',
                    width: 180,
                    style: {'margin-left':'100px'},
                    listConfig: {
                        resizable: true,
                        id: 'classify_event_combo_list'
                    },
                    emptyText: _t('Select an event class'),
                    selectOnFocus: true,
                    id: 'evclass_combo'
                }],
                listeners: {
                    fieldvaliditychange: function(form, field, isValid) {
                        Ext.getCmp('classifyEventFormSubmitButton').setDisabled(!isValid);
                    },
                    scope: win
                },
                buttons: [{
                    text: _t('Submit'),
                    xtype: 'DialogButton',
                    id: 'classifyEventFormSubmitButton',
                    disabled: true,
                    handler: function(){
                        var cb = Ext.getCmp('evclass_combo'),
                        grid = Ext.getCmp(gridId),
                        sm = grid.getSelectionModel(),
                        rs = sm.getSelection(),
                        evrows = [];
                        Ext.each(rs, function(record){
                            evrows[evrows.length] = record.data;
                        });
                        if (!evrows.length) {
                            win.hide();
                            new Zenoss.dialog.ErrorDialog({message: _t('No events were selected.')});
                        } else {
                            Zenoss.remote.EventsRouter.classify({
                                'evclass': cb.getValue(),
                                'evrows': evrows
                            }, function(result){
                                win.destroy();
                                var title = result.success ? _t('Classified'): _t('Error');

                                Ext.MessageBox.show({
                                    title: title,
                                    msg: '<a href="javascript:void(0)" onclick="Zenoss.events.launchMappingDialog(\''+result.msg+'\')" >Edit new mapping</a>',//Ext.htmlDecode(result.msg),
                                    buttons: Ext.MessageBox.OK
                                });
                            });
                        }
                    }
                },{
                    text: _t('Cancel'),
                    xtype: 'DialogButton',
                    handler: function(){
                        win.destroy();
                    }
                }]
            }]

        });

        win.show();
    }

    Zenoss.events.EventPanelToolbarActions = {
        acknowledge: new Zenoss.ActionButton({
            iconCls: 'acknowledge',
            tooltip: _t('Acknowledge events (Ctrl-Shift-a)'),
            permission: 'Manage Events',
            itemId: 'acknowledge',
            handler: function() {
                Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.acknowledge);
            }
        }),
        close: new Zenoss.ActionButton({
            iconCls: 'close',
            tooltip: _t('Close events (Ctrl-Shift-c)'),
            permission: 'Manage Events',
            itemId: 'close',
            handler: function() {
                Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.close);
            }
        }),
        reclassify: new Zenoss.ActionButton({
            iconCls: 'classify',
            tooltip: _t('Reclassify an event'),
            permission: 'Manage Events',
            itemId: 'classify',
            handler: function(button) {
                var gridId = button.ownerCt.ownerCt.id;
                showClassifyDialog(gridId);
            }
        }),
        reopen: new Zenoss.ActionButton({
            iconCls: 'unacknowledge',
            tooltip: _t('Unacknowledge events (Ctrl-Shift-u)'),
            permission: 'Manage Events',
            itemId: 'unacknowledge',
            handler: function() {
                Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.reopen);
            }
        }),
        unclose: new Zenoss.ActionButton({
            iconCls: 'reopen',
            tooltip: _t('Reopen events (Ctrl-Shift-o)'),
            permission: 'Manage Events',
            itemId: 'reopen',
            handler: function() {
                Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.reopen);
            }
        }),
        newwindow: new Zenoss.ActionButton({
            iconCls: 'newwindow',
            permission: 'View',
            tooltip: _t('Go to event console'),
            handler: function(btn) {
                var grid = btn.grid || this.ownerCt.ownerCt,
                curState = Ext.state.Manager.get('evconsole') || {},
                filters = curState.filters || {},
                opts = filters.options || {},
                pat = /devices\/([^\/]+)(\/.*\/([^\/]+)$)?/,
                matches = grid.view.getContext().match(pat),
                st, url;

                // on the device page
                if (matches) {
                    opts.device = matches[1];
                    if (matches[3]) {
                        opts.component = matches[3];
                    }
                }
                filters.options = opts;
                curState.filters = filters;
                st = encodeURIComponent(Zenoss.util.base64.encode(Ext.encode(curState)));
                url = '/zport/dmd/Events/evconsole?state=' + st;
                window.open(url, '_newtab', "");
            }
        }),
        refresh: new Zenoss.ActionButton({
            iconCls: 'refresh',
            permission: 'View',
            tooltip: _t('Refresh events'),
            handler: function(btn) {
                var grid = btn.grid || this.ownerCt.ownerCt;
                if(grid.getComponent("event_panel")) {
                    grid = grid.getComponent("event_panel");
                }
                grid.refresh();
            }
        })
    };

    Ext.define("Zenoss.model.EventType", {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: ['id', 'event_type']
    });

    Ext.define("Zenoss.form.ColumnItemSelector", {
        extend:"Ext.ux.form.ItemSelector",
        constructor: function(state_id, config) {
            var cols = Zenoss.env.getColumnDefinitions();
            var cols_to_display = Zenoss.env.getColumnIdsToRender(state_id);
            var data = [];
            Ext.Array.each(cols, function(col) {
                data.push([col.id, col.header]);
            });
            Ext.applyIf(config, {
                name: 'columnItemSelector',
                id: 'columns_item_selector',
                imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
                valueField: 'id',
                displayField: 'name',
                autoScroll:true,
                minHeight:500,
                maxHeight:500,
                height:500,
                store:  Ext.create('Ext.data.ArrayStore', {
                    data: data,
                    model: 'Zenoss.model.IdName',
                    sorters: [{
                        property: 'name',
                        direction: 'ASC'
                    }]
                }),
                value: cols_to_display
            });
            this.superclass.constructor.call(this, config);
        }
    });

    Ext.define('Zenoss.events.ColumnConfigDialog',{
        extend:'Zenoss.dialog.BaseWindow',
        title: _t('Column Configuration'),
        id: 'events_column_config_dialog',
        minHeight: 600,
        minWidth: 600,
        width: 600,
        height: 600,
        modal: true,
        margins: {top:2, left:2, right: 2, bottom:20},
        closeAction: 'destroy',
        plain: true,
        buttons: [
            {
                text: _t('Submit'),
                xtype: 'DialogButton',
                formBind: true,
                handler: function(){
                    var columns = Ext.getCmp('columns_item_selector').value;
                    var dialog = Ext.getCmp('events_column_config_dialog');
                    var grid = dialog.grid;

                    Zenoss.env.recreateGridWithNewColumns(grid, columns);
                }
            },
            {
                text: _t('Cancel'),
                xtype: 'DialogButton',
                handler: function(){
                    this.hide();
                }
            }
        ],
        constructor: function(grid)
        {
            this.superclass.constructor.call(this, { layout: {type:'vbox', align: 'stretch'} });

            this.grid = grid;

            var header_panel = Ext.widget('panel', {
                xtype: 'panel',
                margins: {top:10, left:2, right: 2, bottom:2},
                layout: {
                    type: 'hbox'
                },
                items: [ {
                    flex: 1,
                    xtype: 'panel',
                    html: "<center><b>Available</b></center>"
                },{
                    flex: 1,
                    xtype: 'panel',
                    html: "<center><b>Selected</b></center>"
                }
                ]
            });

            var item_selector = Ext.create('Zenoss.form.ColumnItemSelector', this.grid.stateId, {});

            var body_panel = Ext.widget('panel', {
                layout: {type:'fit', autoSize: true},
                margins: {top:0, left:10, right: 10, bottom: 10},
                items:[ item_selector ]
            });

            this.add(header_panel);
            this.add(body_panel);
        }
    });

    Zenoss.events.showColumnConfigDialog = function(grid)
    {
        var dialog = Ext.create('Zenoss.events.ColumnConfigDialog', grid);
        dialog.show();
    };

    Zenoss.events.Exp = function(gridId, type, format, expVisible){
        var context = Zenoss.env.device_uid || Zenoss.env.PARENT_CONTEXT;
        if (context === "/zport/dmd/Events") {
            context = location.pathname.replace('/viewEvents', '');
        }
        var grid = Ext.getCmp(gridId),
            state = grid.getState(),
            historyCombo = Ext.getCmp('history_combo'),
            params = {
                type: type,
          options: {
              fmt: format,
              datefmt: Zenoss.USER_DATE_FORMAT,
              timefmt: Zenoss.USER_TIME_FORMAT,
              tz: Zenoss.USER_TIMEZONE 
          },
                isHistory: false,
                params: {
                    uid: context,
                    fields: Ext.Array.pluck(state.columns, 'id'),
                    exportVisible: expVisible,
                    sort: state.sort.property,
                    dir: state.sort.direction,
                    params: grid.getExportParameters()
                }
            };
        if (historyCombo && historyCombo.getValue() === 1) {
            params.isHistory = true;
        }
        Ext.get('export_body').dom.value =
            Ext.encode(params);
        Ext.get('exportform').dom.submit();
    };

    Zenoss.EventConsoleTBar = Ext.extend(Zenoss.LargeToolbar, {
        constructor: function(config){
            var gridId = config.gridId,
                showActions = true,
                showCommands = true,
                configureMenuItems,
                tbarItems = config.tbarItems || [],
                eventSpecificTbarActions = ['acknowledge', 'close', 'reopen', 'unacknowledge', 'addNote'];
            if (!gridId) {
                throw ("Event console tool bar did not receive a grid id");
            }
            configureMenuItems = [{
                id: 'rowcolors_checkitem',
                xtype: 'menucheckitem',
                text: _t('Show severity row colors'),
                handler: function(checkitem) {
                    var checked = checkitem.checked;
                    var grid = Ext.getCmp(gridId);
                    grid.toggleRowColors(checked);
                }
            },{
                id: 'clearfilters',
                text: _t('Clear filters'),
                listeners: {
                    click: function(){
                        Ext.getCmp(gridId).clearFilters();
                    }
                }
            },{
                id: 'adjust_columns_item_selector',
                text: _t('Adjust columns'),
                listeners: {
                click: function(){
                    var grid = Ext.getCmp(gridId);
                    Zenoss.events.showColumnConfigDialog(grid);
                    }
                }
            },{
                text: _t("Restore defaults"),
                handler: function(){
                    new Zenoss.dialog.SimpleMessageDialog({
                        message: Ext.String.format(_t('Are you sure you want to restore ' +
                                                   'the default configuration? All' +
                                                   ' filters, column sizing, and column order ' +
                                                   'will be lost.')),
                        title: _t('Confirm Restore'),
                        buttons: [{
                            xtype: 'DialogButton',
                            text: _t('OK'),
                            handler: function() {
                                var grid = Ext.getCmp(gridId);
                                grid.resetGrid();
                            }
                        }, {
                            xtype: 'DialogButton',
                            text: _t('Cancel')
                        }]
                    }).show();
                }
            }];

            if (!_global_permissions()['manage events']) {
                configureMenuItems.unshift({
                    id: 'excludenonactionables_checkitem',
                    xtype: 'menucheckitem',
                    text: _t('Only show actionable events'),
                    handler: function(checkitem) {
                        var checked = checkitem.checked;
                        var grid = Ext.getCmp(gridId);
                        var tbar = grid.tbar;
                        if (tbar && tbar.getComponent) {
                            Ext.each(eventSpecificTbarActions, function(actionItemId) {
                                var cmp = tbar.getComponent(actionItemId);
                                if (cmp) {
                                    cmp.filtered = checked;
                                    cmp.updateDisabled();
                                }
                            });
                        }
                        grid.toggleNonActionables(checked);
                    }
                });
            }

            if (/^\/zport\/dmd\/Events/.test(window.location.pathname)) {
                configureMenuItems.splice(2, 0, {
                    text: _t('Save this configuration...'),
                    handler: function(){
                        var grid = Ext.getCmp(gridId),
                        link = grid.getPermalink();
                        new Zenoss.dialog.ErrorDialog({
                            message: Ext.String.format(_t('<div class="dialog-link">' +
                                                       'Drag this link to your bookmark bar ' +
                                                       '<br/>to return to this configuration later.' +
                                                       '<br/><br/><a href="' +
                                                       link +
                                                       '">Resource Manager: Events</a></div>')),
                            title: _t('Save Configuration')
                        });
                    }
                });
            }

            // actions
            if (Ext.isDefined(config.actionsMenu)) {
                showActions = config.actionsMenu;
            }
            if (showActions) {
                tbarItems.push({
                    id: 'event-actions-menu',
                    text: _t('Actions'),
                    xtype: 'deviceactionmenu',
                    deviceFetcher: function() {
                        var grid = Ext.getCmp(gridId),
                        sm = grid.getSelectionModel(),
                        rows = sm.getSelection(),
                        pluck = Ext.Array.pluck,
                        uids = pluck(pluck(pluck(rows, 'data'), 'device'), 'uid'),
                        opts =  {
                            uids: uids,
                            ranges: [],
                            hashcheck: 'none'
                        };
                        opts.params = grid.filterRow.getSearchValues();
                        // filter out the nulls
                        opts.uids = Zenoss.util.filter(opts.uids, function(uid){
                            return uid;
                        });

                        return opts;
                    },
                    saveHandler: Ext.emptyFn
                });
            }

            // commands
            if (Ext.isDefined(config.commandsMenu)) {
                showCommands = config.commandsMenu;
            }
            if (showCommands) {
                tbarItems.push({
                    id: 'event-commands-menu',
                    text: _t('Commands'),
                    hidden: !showCommands,
                    disabled: Zenoss.Security.doesNotHavePermission('Run Commands'),
                    setContext: function(uid) {
                        if (!uid) {
                            uid = '/zport/dmd/Devices';
                        }
                        var me = Ext.getCmp('event-commands-menu'),
                        menu = me.menu;
                        // load the available commands from the server
                        // commands are based on context
                        Zenoss.remote.DeviceRouter.getUserCommands({uid:uid}, function(data) {
                            menu.removeAll();
                            Ext.each(data, function(d) {
                                menu.add({
                                    text:d.id,
                                    tooltip:d.description,
                                    handler: function(item) {
                                        var command = item.text,
                                            grid = Ext.getCmp(gridId),
                                            sm = grid.getSelectionModel(),
                                            selections = sm.getSelection(),
                                            devids = Ext.Array.pluck(Ext.Array.pluck(Ext.Array.pluck(selections, 'data'), 'device'), 'uid');

                                        // filter out the none device events
                                        devids = Zenoss.util.filter(devids, function(uid){ return uid; });
                                        if (devids.length) {

                                            // only run commands for the visible devices
                                            var win = new Zenoss.CommandWindow({
                                                uids: devids,
                                                target: uid + '/run_command',
                                                command: command
                                            });
                                            win.show();
                                        }
                                    }
                                });
                            });
                        });
                    },
                    menu: {}
                });
            }
            this.gridId = gridId;

            if (!config.hideDisplayCombo) {
                tbarItems.push('-');
                tbarItems.push(Ext.create('Ext.toolbar.TextItem', {
                    hidden: config.hideDisplayCombo || false,
                    text: _t('Display: ')
                }));
                tbarItems.push(Ext.create('Ext.form.ComboBox', {
                    id: 'history_combo',
                    hidden: config.hideDisplayCombo || false,
                    name: 'event_display',
                    queryMode: 'local',
                    store: new Ext.data.SimpleStore({
                        model: 'Zenoss.model.EventType',
                        data: [[0,'Events'],[1,'Event Archive']]
                    }),
                    displayField: 'event_type',
                    valueField: 'id',
                    width: 120,
                    value: 0,
                    triggerAction: 'all',
                    forceSelection: true,
                    editable: false,
                    listeners: {
                        select: function(selection) {
                            var archive = selection.value === 1,
                                grid = Ext.getCmp(gridId),
                                yesterday = new Date();

                            // reload the grid. changing the filters
                            grid.setStoreParameter('archive', archive);

                            // if history set default lastseen to yesterday
                            if (archive) {
                                yesterday.setDate(yesterday.getDate() - 1);
                                grid.setFilter('lastTime', yesterday);
                            }else{
                                grid.setFilter('lastTime', null);
                            }
                        }
                    }
                }));

            }
            if (config.newwindowBtn) {
                tbarItems.push('-');
                tbarItems.push(Zenoss.events.EventPanelToolbarActions.newwindow);
            }

            Zenoss.EventActionManager.configure({
                onFinishAction: function() {
                    var grid = Ext.getCmp(gridId);
                    if(Ext.get('event_panel')){
                        grid = Ext.getCmp('event_panel');
                    }
                    if (grid) {
                        grid.refresh();
                    }
                    var dpanel = Ext.getCmp('dpanelcontainer');
                    if (dpanel && dpanel.isVisible()) {
                        dpanel.refresh();
                    }
                },
                findParams: function() {
                    var grid = Ext.getCmp(gridId);
                    if(Ext.get('event_panel')){
                        grid = Ext.getCmp('event_panel');
                    }
                    if (grid) {
                        var params =  grid.getSelectionParameters();
                        if (Zenoss.env.device_uid) {
                            params.uid = Zenoss.env.device_uid;
                        }
                        return params;
                    }
                }
            });

            Ext.applyIf(config, {
                ref: 'tbar',
                listeners: {
                    beforerender: function(){
                        var grid = Ext.getCmp(gridId),
                        tbar = this;
                        if (tbar.getComponent) {
                            Ext.each(eventSpecificTbarActions, function(actionItemId) {
                                var cmp = tbar.getComponent(actionItemId);
                                if (cmp) {
                                    cmp.filtered = grid.excludeNonActionables;
                                }
                            });
                        }
                    },
                    afterrender: function(){
                        var grid = Ext.getCmp(gridId),
                        store = grid.getStore(),
                        tbar = this,
                        view = grid.getView();
                        if(store.buffered) {
                            store.on('guaranteedrange', this.doLastUpdated);
                        } else {
                            store.on('load', this.doLastUpdated);
                        }
                        view.on('buffer', this.doLastUpdated);

                        view.on('filterchange', function(){
                            tbar.refreshmenu.setDisabled(!view.isValid());

                            // Hook up the "Last Updated" text
                            if ( !view.isValid() ) {
                                var box = Ext.getCmp('lastupdated');
                                box.setText(_t(''));
                            }
                        });
                        // set up the commands menu
                        var context = Zenoss.env.device_uid || Zenoss.env.PARENT_CONTEXT;
                        if (context === "/zport/dmd/Events") {
                            context = location.pathname.replace('/viewEvents', '');
                        }
                        this.setContext(context);
                    },
                    scope: this
                },
                items: Ext.Array.union([
                    // create new instances of the action otherwise Ext won't render them (probably a bug in 4.1)
                    new Zenoss.ActionButton({
                        iconCls: 'acknowledge',
                        tooltip: _t('Acknowledge events'),
                        permission: 'Manage Events',
                        id: 'events_toolbar_ack',
                        itemId: 'acknowledge',
                        handler: function() {
                            Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.acknowledge);
                        }
                    }),
                    new Zenoss.ActionButton({
                        iconCls: 'close',
                        tooltip: _t('Close events'),
                        permission: 'Manage Events',
                        itemId: 'close',
                        id: 'events_toolbar_close_events',
                        handler: function() {
                            Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.close);
                        }
                    }),
                    new Zenoss.ActionButton({
                        iconCls: 'classify',
                        tooltip: _t('Reclassify an event'),
                        permission: 'Manage Events',
                        itemId: 'classify',
                        id: 'events_toolbar_reclassify_event',
                        handler: function(button) {
                            var gridId = button.ownerCt.ownerCt.id;
                            showClassifyDialog(gridId);
                        }
                    }),
                    new Zenoss.ActionButton({
                        iconCls: 'unacknowledge',
                        tooltip: _t('Unacknowledge events'),
                        permission: 'Manage Events',
                        itemId: 'unacknowledge',
                        id: 'events_toolbar_unack',
                        handler: function() {
                            Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.reopen);
                        }
                    }),
                    new Zenoss.ActionButton({
                        iconCls: 'reopen',
                        tooltip: _t('Reopen events'),
                        permission: 'Manage Events',
                        itemId: 'reopen',
                        id: 'events_toolbar_reopen',
                        handler: function() {
                            Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.reopen);
                        }
                    }),
                    new Zenoss.ActionButton({
                        iconCls: 'addslide',
                        tooltip: _t('Add Log'),
                        permission: 'Manage Events',
                        itemId: 'addNote',
                        handler: function() {
                            var grid = Ext.getCmp(gridId),
                                sm = grid.getSelectionModel(),
                                selected = sm.getSelection(),
                                data = Ext.pluck(selected, "data"),
                                uuids = Ext.pluck(data, "evid"),
                                addNoteWindow;
                            addNoteWindow = Ext.create('Zenoss.dialog.BaseWindow', {
                                title: _t('Add Note'),
                                id: 'addNoteWindow',
                                layout: 'fit',
                                autoHeight: true,
                                modal: true,
                                width: 310,
                                plain: true,
                                items: [{
                                    id: 'addNoteForm',
                                    xtype: 'form',
                                    defaults: {width: 290},
                                    autoHeight: true,
                                    frame: false,
                                    fieldDefaults: {
                                        labelWidth: 100
                                    },
                                    items: [{
                                        xtype: 'textarea',
                                        maxHeight: Ext.getBody().getViewSize().height * 0.4,
                                        name: 'note',
                                        fieldLabel: _t('note'),
                                        allowBlank: false
                                    }],
                                    buttons: [{
                                        text: _t('Submit'),
                                        xtype: 'DialogButton',
                                        formBind: true,
                                        handler: function() {
                                            var form = Ext.getCmp('addNoteForm'),
                                                note = form.getValues().note;

                                            Ext.each(uuids, function(uuid) {
                                                Zenoss.remote.EventsRouter.write_log(
                                                {
                                                    evid: uuid,
                                                    message: note
                                                });
                                            });
                                        }
                                    },{
                                        text: _t('Cancel'),
                                        xtype: 'DialogButton',
                                        handler: function(){
                                            addNoteWindow.hide();
                                        }
                                    }]
                                }]
                            });
                            addNoteWindow.show();
                        }
                    }),
                    new Zenoss.ActionButton({
                        iconCls: 'add',
                        tooltip: _t('Add an event'),
                        permission: 'Manage Events',
                        id: 'add_event_main_button',
                        handler: function() {
                            showAddEventDialog(gridId);
                        }
                    }),
                    {
                        xtype: 'tbseparator'
                    },
                    Zenoss.events.EventPanelToolbarSelectMenu,
                    {
                    text: _t('Export'),
                    //iconCls: 'export',
                    handler: function(){

                    var dialog = Ext.create('Zenoss.dialog.Form', {
                    title: _t('Export events'),
                    minWidth: 350,
                    submitHandler: function(form) {
                        var values = form.getValues();
                        Zenoss.events.Exp(gridId, values['ftype'], values['ffmt'], values['exportVisible']);
                    },
                    form: {
                        layout: 'anchor',
                        defaults: {
                            xtype: 'displayfield',
                            padding: '0 0 10 0',
                            margin: 0,
                            anchor: '100%'
                        },
                        fieldDefaults: {
                            labelAlign: 'left',
                            labelWidth: 75,
                            labelStyle: 'color:#aaccaa'
                        },
                        items: [{
                            name: 'ftype',
                            fieldLabel: 'File type',
                            value: '',
                            xtype: 'combo',
                            allowBlank: false,
                            displayField:'name',
                            valueField:'id',
                            store: Ext.create('Ext.data.Store',{
                                  fields:['id','name'],
                                  data:[
                                        {id:'xml', name:'XML'},
                                        {id:'csv', name:'CSV'}
                                  ]
                            }),
                            editable: false,
                            disableKeyFilter: false,
                            submitValue: true
                        },
                        {
                            name: 'ffmt',
                            fieldLabel: 'Date/Time format',
                            xtype: 'combo',
                            allowBlank: false,
                            displayField:'name',
                            valueField:'id',
                            store: Ext.create('Ext.data.Store',{
                                       fields:['id','name'],
                                       data:[
                                            {id:'iso',  name:'ISO'},
                                            {id:'unix', name:'Unix'},
                                            {id:'user', name:'User settings'}
                                       ]
                            }),
                            listeners: {'select': function (combo, record){
                                if(record[0].data.id == "unix"){
                                    Ext.getCmp('fexample').setValue(moment.tz(new Date(), Zenoss.USER_TIMEZONE).format("x")).show();
                                } else if(record[0].data.id == "iso"){
                                    Ext.getCmp('fexample').setValue(moment.tz(new Date(), Zenoss.USER_TIMEZONE).format("YYYY-MM-DDTHH:mm:ssZ")).show();
                                } else if(record[0].data.id == "user"){
                                    Ext.getCmp('fexample').setValue(moment.tz(new Date(), Zenoss.USER_TIMEZONE).format(Zenoss.USER_DATE_FORMAT + ' ' + Zenoss.USER_TIME_FORMAT)).show();
                                }
                            }
                        },
                        editable: false,
                        disableKeyFilter: false,
                        submitValue: true
                    },
                    {
                        name: 'example',
                        id: 'fexample',
                        fieldLabel:'Format example',
                        value: '',
                        hidden: true,
                        submitValue: false
                    },{
                        name: 'exportVisible',
                        fieldLabel: 'Export visible columns',
                        xtype: 'checkbox',
                        checked: true,
                        submitValue: true
                    }
                    ]
                }
            });
            dialog.down('form');
            dialog.show();
                }
                    },
                    {
                        text: _t('Configure'),
                        id: 'configure-button',
                        //iconCls: 'customize',
                        menu: {
                            items: configureMenuItems
                        }
                    },{
                        xtype: 'tbfill'
                    },{
                        id: 'lastupdated',
                        xtype: 'tbtext',
                        cls: 'lastupdated',
                        text: _t('Updating...')
                    },{
                        xtype: 'refreshmenu',
                        ref: 'refreshmenu',
                        id: 'refresh-button',
                        refreshWhenHidden: true,
                        iconCls: 'refresh',
                        text: _t('Refresh'),
                        handler: function() {
                            var grid = Ext.getCmp(gridId);
                            if (grid.isVisible(true)) {
                                // Indicating grid updating progress
                                var box = Ext.getCmp('lastupdated');
                                var boxText = box.text;
                                box.setText(_t('<span>Updating... </span><img src="/++resource++zenui/img/ext4/icon/circle_arrows_ani.gif" width=12 height=12>'));
                                grid.refresh(function(records, operation, success) {
                                    if (success === false) {
                                        grid.refresh_in_progress -= 1;
                                        grid.isSuccessResponse = false;
                                        box.setText(boxText);
                                    }
                                });
                            }
                        },
                        pollHandler: function(btn) {
                            var grid = Ext.getCmp(gridId);
                            if (grid.refresh_in_progress === 0) {
                                this.handler(btn);
                            }
                        }
                    }
                ], tbarItems)
            });
            Zenoss.EventConsoleTBar.superclass.constructor.call(this, config);
        },
        doLastUpdated: function() {
            var box = Ext.getCmp('lastupdated'),
            dtext = Zenoss.date.renderWithTimeZone(new Date()/1000);
            dtext += " (" + Zenoss.USER_TIMEZONE + ")";
            box.setText(_t('Last updated at ') + dtext);
        },
        setContext: function(uid) {
            var commands = Ext.getCmp('event-commands-menu');
            if (commands) {
                commands.setContext(uid);
            }
        }
    });

    /**
     * @class Zenoss.EventPanelSelectionModel
     * @extends Zenoss.ExtraHooksSelectionModel
     *
     */
        Ext.define("Zenoss.EventPanelSelectionModel", {
            extend:"Zenoss.ExtraHooksSelectionModel",
            selectState: null,
            badIds: {},
            mode: 'MULTI',
            constructor: function(config){
                this.callParent([config]);
                this.on('select', this.handleRowSelect, this);
                this.on('deselect', this.handleRowDeSelect, this);
                this.on('selectionchange', function(selectionmodel) {
                    // Disable buttons if nothing selected (and vice-versa)
                    var actionsToChange = ['acknowledge', 'close', 'reopen',
                                           'unacknowledge', 'classify',
                                           'addNote', 'event-actions-menu'],
                        newDisabledValue = !selectionmodel.hasSelection() && selectionmodel.selectState !== 'All',
                        tbar = this.getGrid().tbar,
                        history_combo = Ext.getCmp('history_combo'),
                        archive = Ext.isDefined(history_combo) ? history_combo.getValue() === 1 : false;
                    if (archive) {
                        // These are always disabled on the archive event console
                        tbar.getComponent('acknowledge').setDisabled(true);
                        tbar.getComponent('close').setDisabled(true);
                        tbar.getComponent('reopen').setDisabled(true);
                        tbar.getComponent('unacknowledge').setDisabled(true);

                        // This is conditionally enabled/disabled based on selection
                        tbar.getComponent('classify').setDisabled(newDisabledValue);
                    }
                    else {
                        // tbar is not present on component event consoles
                        if (tbar && tbar.getComponent) {
                            Ext.each(actionsToChange, function(actionItemId) {
                                if(tbar.getComponent(actionItemId)){
                                    tbar.getComponent(actionItemId).setDisabled(newDisabledValue);
                                }
                            });
                        }
                    }
                    // If we don't have global role then set context explicitly for each selection 
                    if (!_has_global_roles()) {
                        if (selectionmodel.hasSelection() && selectionmodel.selectState !=='All') {
                            var selection = selectionmodel.getSelection();
                            selection.forEach(function(sel) {
                                Zenoss.Security.setContext(sel.data.device.uid)
                            });
                        }
                        // Disable add_event button for event console context if no global role
                        // In some contexts we don't have add event button so check it first
                        if (tbar && tbar.getComponent('add_event_main_button')) {
                            if (!Zenoss.env.device_uid && !selectionmodel.hasSelection()) {
                                tbar.getComponent('add_event_main_button').setDisabled(true);
                            } else {
                                tbar.getComponent('add_event_main_button').setDisabled(false);
                            }
                        }

                    }
                });
                Zenoss.Security.onPermissionsChange(function() {
                    var tbar = this.grid.tbar;
                    // event-commands-menu is not present on maintenance window page
                    if (tbar && tbar.getComponent('event-commands-menu')) {
                        tbar.getComponent('event-commands-menu').setDisabled(!Zenoss.Security.hasPermission("Run Commands"));
                    }
                }, this);

            },
            getGrid: function() {
                if (!Ext.isDefined(this.grid)) {
                    this.grid = Ext.getCmp(this.gridId);
                }
                return this.grid;
            },
            handleRowSelect: function(sm, record){
                if (record) {
                    delete this.badIds[record.get("evid")];
                }
            },
            handleRowDeSelect: function(sm, record){
                if (this.selectState && record) {
                    this.badIds[record.get("evid")] = 1;
                }
            },
            onStoreLoad: function() {
                var store = this.grid.getStore();
                if (this.selectState === 'All') {
                    this.suspendEvents();
                    var items = Zenoss.util.filter(store.data.items, function(item){
                        return (! this.badIds[item.get('evid')]);
                    }, this);
                    this.select(items, false, true);
                    this.resumeEvents();
                    this.fireEvent('selectionchange', this);
                }
            },
            selectEventState: function(state){
                var me = this,
                    grid = this.getGrid(),
                    store = grid.getStore();
                if (state === 'All') {
                    // suppress events
                    return this.selectAll(true);
                }
                this.clearSelections(true);
                // Suspend events to avoid firing the whole chain for every row
                this.suspendEvents();

                Ext.each(store.data.items, function(record){
                    if (record) {
                        if (record.data.eventState === state) {
                            me.select(record, true);
                        }
                    }
                });
                this.selectState = state;

                // Bring events back and fire one selectionchange for the batch
                this.resumeEvents();
                this.fireEvent('selectionchange', this);
            },
            clearSelectState: function() {
                this.selectState = null;
                this.grid.getStore().un('datachanged', this.onStoreLoad, this);
                this.grid.disableSavedSelection(false);
            },
            setSelectState: function(state) {
                this.selectState = state;
                if (state === 'All') {
                    this.grid.getStore().on('datachanged', this.onStoreLoad, this);
                    this.grid.disableSavedSelection(true);
                }
            },
            selectNone: function(){
                this.clearSelections(true);
                this.clearSelectState();
                // Fire one selectionchange to make buttons figure out their
                // disabledness
                this.fireEvent('selectionchange', this);
            },
            clearSelections: function(fast){
                if (this.isLocked() || !this.grid) {
                    return;
                }

                // Suspend events to avoid firing the whole chain for every row
                this.suspendEvents();
                if(!fast){
                    //make sure all rows are deselected so that UI renders properly
                    //base class only deselects rows it knows are selected; so we need
                    //to deselect rows that may have been selected via selectstate
                    this.deselect(this.grid.getStore().data.items);
                }
                // Bring events back and fire one selectionchange for the batch
                this.resumeEvents();
                this.fireEvent('selectionchange', this);

                this.badIds = {};
                Zenoss.EventPanelSelectionModel.superclass.clearSelections.apply(this, arguments);
            }
        });

    /**
     * @class Zenoss.EventsJsonReader
     * @extends Zenoss.ExtraHooksSelectionModel
     *
     * Subclass the Ext JsonReader so that we can override how data is fetched
     * from a record that is returned by the router. Custom details use keys that
     * contain dots (zenpacks.foo.bar.baz) so we need to force key-method access.
     */
    Ext.define("Zenoss.EventsJsonReader", {
        extend: "Ext.data.reader.Json",
        alias: 'reader.events',
        useSimpleAccessors: true,
        createAccessor : (function(){
            return function(expr) {
                return function(obj){
                    return obj[expr];
                };
            };
        }())
    });



    /**
     * @class Zenoss.events.Store
     * @extend Zenoss.DirectStore
     * Direct store for loading ip addresses
     */
    Ext.define("Zenoss.events.Store", {
        extend: "Zenoss.DirectStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.events.Model',
                initialSortColumn: 'severity',
                initialSortDirection: 'DESC',
                pageSize: Zenoss.settings.eventConsoleBufferSize,
                proxy: {
                    type: 'direct',
                    simpleSortMode: true,
                    directFn: config.directFn || Zenoss.remote.EventsRouter.query,
                    reader: {
                        type: 'events',
                        root: 'events',
                        totalProperty: 'totalCount'
                    }
                }


            });
            this.callParent(arguments);
        }
    });

    Zenoss.events.customColumns = {};
    Zenoss.events.registerCustomColumn = function(dataIndex, obj) {
        Zenoss.events.customColumns[dataIndex] = obj;
    };

    Zenoss.events.eventFields = [];
    /**
     * This is how zenpack authors can register event fields that they want pulled from the server,
     * but may not be visible in a colum. So if you add the following line to your javascript:
     *     Zenoss.events.registerEventField("ipAddress");
     * On every browser request the ipAddress field will be populated
     **/
    Zenoss.events.registerEventField = function(dataIndex) {
        Zenoss.events.eventFields.push(dataIndex);
    };

    /**
     * @class Zenoss.events.Grid
     * @extends Zenoss.FilterGridPanel
     * Base Class for the event panels
     **/
    Ext.define('Zenoss.events.Grid', {
        extend: 'Zenoss.FilterGridPanel',
        rowcolors: false,
        excludeNonActionables: false,
        constructor: function(config) {
            config = config || {};
            config.viewConfig = config.viewConfig || {};
            Ext.applyIf(config.viewConfig, {
                getRowClass: Zenoss.events.getRowClass,
        enableTextSelection: true
            });

            this.callParent(arguments);
            this.on('itemclick', this.onItemClick, this );
            this.on('filterschanged', this.onFiltersChanged, this);
            this.excludeNonActionables = !_global_permissions()['manage events'] && Ext.state.Manager.get('excludeNonActionables');
            this.getStore().autoLoad = true;
        },
        initComponent: function() {
            this.getSelectionModel().grid = this;
             // create keyboard shortcuts for the main event console
            function nonInputHandler(func, scope){

                return function(key, e) {
                    if (e.target.tagName !== "INPUT" && e.target.tagName !== "TEXTAREA") {
                        Ext.bind(func, scope)(key, e);
                        e.preventDefault();
                    }
                };
            }
            this.map = new Ext.util.KeyMap({
                target: document.body,
                binding: [{
                    key:  Ext.EventObject.A,
                    ctrl: true,
                    shift: false,
                    alt: false,
                    scope: this,
                    fn: nonInputHandler(function() {
                        this.getSelectionModel().selectEventState('All');
                    }, this)
                },{
                    key:  Ext.EventObject.ESC,
                    ctrl: false,
                    shift: false,
                    alt: false,
                    scope:this,
                    fn: nonInputHandler(function() {
                        this.getSelectionModel().clearSelections();
                        this.getSelectionModel().clearSelectState();
                    }, this)
                }, {
                    // acknowledge
                    key: Ext.EventObject.A,
                    shift: true,
                    ctrl: true,
                    alt: false,
                    fn: nonInputHandler(function() {
                        Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.acknowledge);
                    }, this)
                }, {
                    // close
                    key: Ext.EventObject.C,
                    shift: true,
                    ctrl: true,
                    alt: false,
                    fn: nonInputHandler(function() {
                        Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.close);
                    }, this)
                }, {
                    // reopen
                    key: Ext.EventObject.O,
                    shift: true,
                    ctrl: true,
                    alt: false,
                    fn: nonInputHandler(function() {
                        Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.reopen);
                    }, this)
                }, {
                    // unack
                    key: Ext.EventObject.U,
                    shift: true,
                    ctrl: true,
                    alt: false,
                    fn: nonInputHandler(function() {
                        Zenoss.EventActionManager.execute(Zenoss.remote.EventsRouter.reopen);
                    }, this)
                }]

            });
            this.on('show', function(){ this.map.enable();}, this);
            this.on('hide', function(){ this.map.disable();}, this);

            this.callParent(arguments);
        },
        onItemClick: function(){
            this.getSelectionModel().clearSelectState();
        },
        setGetFilterParameters: function() {
            var params = Ext.Object.fromQueryString(location.search),
                cleared = false;
            Ext.each(["severity", "eventState", "device", "component", "eventClass", "summary"], function(param) {
                var v = params[param];
                if (Ext.isDefined(v)) {
                    if (!cleared) {
                        // Clear filters first if anything is set, so we don't merge with existing state
                        this.clearFilters();
                        cleared = true;
                    }
                    // Do any modification of the values
                    switch (param) {
                        case "eventState":
                        case "severity":
                            v = v.split(',').map(function(item) {
                              return parseInt(item, 10);
                            });
                            break;
                        default:
                            // Let it go through
                            break;
                    }
                    // Set the filter value
                    this.setFilter(param, v);
                }
            }, this);
        },
        listeners: {
            beforerender: function(){
                this.rowcolors = Ext.state.Manager.get('rowcolor');
                // Some event consoles (Impact Events) do not use severity
                // config colors.  Check and see if it's being used before
                // trying to use it.
                var rowcolorsCheckItem = Ext.getCmp('rowcolors_checkitem');
                if (rowcolorsCheckItem) {
                    rowcolorsCheckItem.setChecked(this.rowcolors);
                }

                var excludeNonActionablesCheckItem = Ext.getCmp('excludenonactionables_checkitem');
                if (excludeNonActionablesCheckItem) {
                    excludeNonActionablesCheckItem.setChecked(this.excludeNonActionables);
                }
                this.setGetFilterParameters();
            }
        },
        applyOptions: function() {
            var store = this.getStore(),
                keys,
                columns = this.headerCt.getGridColumns();

            columns = Zenoss.util.filter(columns, function(col) {
                return !col.hidden;
            });
            keys = Ext.Array.pluck(columns, "dataIndex");
            // always have these fields for reclassifying
            keys = Ext.Array.union(keys, ["evid", "eventClass", "eventClassKey", "message"]);

            // grab any fields zenpack authors may add
            keys = Ext.Array.union(keys, Zenoss.events.eventFields);
            store.setBaseParam("keys", keys);
            store.setParamsParam("excludeNonActionables", this.excludeNonActionables);
        },
        getSelectionParameters: function() {
            var grid = this,
            sm = grid.getSelectionModel(),
            uid,
            evids = [],  // Event IDs selected
            sels = sm.getSelection();  // UI records selected
            if(Ext.isEmpty(sels)){ // if nothing is selected, check and see if there's an event_panel
                if(Ext.get('event_panel')) {
                    sels = Ext.getCmp('event_panel').getSelectionModel().getSelection();
                }
            }
            var selectedAll = (sm.selectState === 'All');
            if (selectedAll) {
                // If we are selecting all, we don't want to send back any evids.
                // this will make the operation happen on the filter's result
                // instead of whatever the view seems to have selected.
                sels = [];
            } else {
                Ext.each(sels, function(record){
                    evids[evids.length] = record.data.evid;
                });
            }

            // Don't run if nothing is selected.
            if (!selectedAll && Ext.isEmpty(sels)) {
                return false;
            }
            // if we are a contextual event console ALWAYS send the uid
            if (this.uid !== '/zport/dmd'){
                uid = this.uid;
            }
            var params = {
                evids: evids,
                excludeIds: sm.badIds,
                uid: uid
            };
            Ext.apply(params, this.getUpdateParameters());
            return params;
        },
        clearFilters: function(){
            this.filterRow.clearFilters();
        },
        onFiltersChanged: function(grid) {
            // ZEN-4441: Clear selections whenever the filter changes.
            var sm = grid.getSelectionModel();
            sm.clearSelections();
            sm.clearSelectState();
        },
        /*
         * Create parameters used for exporting events. This differs from
         * getSelectionParameters in that if no events are selected, all of
         * the events matching the current filters are exported.
         */
        getExportParameters: function() {
            var params = this.getSelectionParameters();
            if (params === false) {
                params = {
                    evids: [],
                    excludeIds: {}
                };
                Ext.apply(params, this.getUpdateParameters());
            }
            var timeParams = ["firstTime", "lastTime"];
            timeParams.forEach(function (paramKey) {
                var timeParam = params.params[paramKey];
                if (timeParam && timeParam.dateFrom) {
                    params.params[paramKey] = moment(timeParam.dateFrom).format("x") + " TO " + moment(timeParam.dateTo).format("x");
                } else {
                    delete params.params[paramKey];
                }
            });
            return params;
        },
        /*
         * Build parameters for updates (don't need to include sort information).
         */
        getUpdateParameters: function() {
            var o = {};
            o.params = this.filterRow.getSearchValues();
            o.params.excludeNonActionables = this.excludeNonActionables;
            return o;
        },
        toggleRowColors: function(bool) {
            this.rowcolors = bool;
            Ext.state.Manager.set('rowcolor', bool);
            this.refresh();
        },
        toggleNonActionables: function(bool) {
            this.excludeNonActionables = bool;
            Ext.state.Manager.set('excludeNonActionables', bool);
            this.refresh();
        },
        restoreURLState: function() {
            var qs = window.location.search.replace(/^\?/, ''), state;
            var decoded = Ext.urlDecode(qs);

            if (decoded.state) {
                try {
                    state = Ext.decode(Zenoss.util.base64.decode(decodeURIComponent(decoded.state)));
                    Ext.state.Manager.set(this.stateId, state);
                    this.fireEvent('recreateGrid', this);
                } catch(e) { }
            //in case parameters are not encoded
            } else {
                var filters = { filters: decoded };
                this.clearFilters();
                this.applyState(filters);
                this.filterRow.storeSearch();
            }
        },
        clearURLState: function() {
            var qs = Ext.urlDecode(window.location.search.replace(/^\?/, ''));
            if (qs.state) {
                delete qs.state;
                qs = Ext.urlEncode(qs);
                if (qs) {
                    window.location.search = '?' + Ext.urlEncode(qs);
                } else {
                    window.location.search = '';
                }
            }
        },
        getPermalink: function() {
            var l = window.location,
            path = l.protocol + '//' + l.host + l.pathname + l.hash,
            st = Zenoss.util.base64.encode(Ext.encode(this.getState()));
            return path + '?state=' + st;
        },
        resetGrid: function() {
            Ext.state.Manager.clear(this.stateId);
            this.clearFilters();
            this.fireEvent('recreateGrid', this);
        },
        updateRows: function(){
            this.refresh();
        }
    });

    /**
     * @class Zenoss.SimpleEventGridPanel
     * @extends Zenoss.events.Grid
     * Shows events in a grid panel similar to that on the event console.
     * Fixed columns.
         * @constructor
         */
    Ext.define("Zenoss.SimpleEventGridPanel", {
            extend:"Zenoss.events.Grid",
            alias: ['widget.SimpleEventGridPanel'],
        constructor: function(config){

            var id = config.id || Ext.id();
            config.viewConfig = config.viewConfig || {};
                Ext.applyIf(config.viewConfig, {
                    getRowClass:  Zenoss.events.getRowClass
                });
            Ext.applyIf(config, {
                id: 'eventGrid' + id,
                stateId: Zenoss.env.EVENTSGRID_STATEID || 'default_eventsgrid',
                enableDragDrop: false,
                stateful: true,
                rowSelectorDepth: 5,
                store: Ext.create('Zenoss.events.Store', {}),
                appendGlob: true,
                selModel: new Zenoss.EventPanelSelectionModel({
                    grid: this
                }),
                defaultFilters: {
                    severity: [Zenoss.SEVERITY_CRITICAL, Zenoss.SEVERITY_ERROR, Zenoss.SEVERITY_WARNING, Zenoss.SEVERITY_INFO],
                    eventState: [Zenoss.STATUS_NEW, Zenoss.STATUS_ACKNOWLEDGED]
                },
                viewConfig: {
                    getRowClass:  Zenoss.events.getRowClass
                }
            }); // Ext.applyIf
            Zenoss.SimpleEventGridPanel.superclass.constructor.call(this, config);
            this.on('itemdblclick', this.onRowDblClick, this);
        }, // constructor
        onRowDblClick: function(view, record) {
            var evid = record.get('evid'),
                url = '/zport/dmd/Events/viewDetail?evid='+evid;
            window.open(url, evid.replace(/-/g,'_'),
                        "status=1,width=600,height=500,resizable=1");
        },
        initComponent: function() {
            this.callParent(arguments);

            /**
             * @event eventgridrefresh
             * Fires when the events grid is refreshed.
             * @param {Zenoss.SimpleEventGridPanel} this The gridpanel.
             */
            this.addEvents('eventgridrefresh');
        },
        /**
         *Since on a regular event console you can not choose which columns
         * are present we are overriding the default implementation of getState
         * to not remember the widths of columns that are not visible.
         * This is necessary because of our column definitions were creating
         * cookies larger than 8192 (the default zope max cookie size)
         **/
        getState: function(){

            var val = Zenoss.SimpleEventGridPanel.superclass.getState.call(this);
            // do not store the state of the hidden ones
            val.columns = Zenoss.util.filter(val.columns, function(col) {
                return !col.hidden;
            });
            return val;
        },
        refresh: function() {
            this.getStore().reload();
            this.callParent(arguments);
            this.fireEvent('eventgridrefresh', this);
        }
    }); // SimpleEventGridPanel

    // Define all of the items that could be shown in an EventConsole toolbar.
    Zenoss.events.EventPanelToolbarSelectMenu = {
        text: _t('Select'),
        id: 'select-button',
        menu:{
            xtype: 'menu',
            items: [{
                text: _t("All"),
                tooltip: _t('Ctrl-a'),
                handler: function(){
                    var grid = Ext.getCmp('select-button').ownerCt.ownerCt,
                    sm = grid.getSelectionModel();
                    sm.selectEventState('All');
                    sm.setSelectState("All");
                }
            },{
                text: 'None',
                tooltip: _t('Esc'),
                handler: function(){
                    var grid = Ext.getCmp('select-button').ownerCt.ownerCt,
                    sm = grid.getSelectionModel();
                    sm.clearSelections();
                    sm.clearSelectState();
                }
            }]
        }
    };


    Ext.define("Zenoss.EventGridPanel", {
        extend: "Zenoss.SimpleEventGridPanel",
        alias: ['widget.EventGridPanel'],
        border:false,
        constructor: function(config) {
            Ext.applyIf(config, {
                tbar: new Zenoss.EventConsoleTBar({
                    gridId: config.id,
                    actionsMenu: config.actionsMenu,
                    commandsMenu: config.commandsMenu
                })
            });
            Zenoss.EventGridPanel.superclass.constructor.call(this, config);
        },
        onRowDblClick: function(view, record) {
            var evid = record.get('evid'),
                combo = Ext.getCmp('history_combo'),
                history = (combo.getValue() === '1') ? 'History' : '',
                url = '/zport/dmd/Events/view'+history+'Detail?evid='+evid;
            window.open(url, evid.replace(/-/g,'_'),
                        "status=1,width=600,height=500,resizable=1");
        },
        setContext: function(uid){
            if (uid) {
                this.uid = uid;
            }

            var toolbar = this.getDockedItems('toolbar')[0];
            if (toolbar && Ext.isDefined(toolbar.setContext)) {
                toolbar.setContext(uid);
            }
        }
    });

    Ext.define("Zenoss.EventRainbow", {
        extend:"Ext.toolbar.TextItem",
        alias: ['widget.eventrainbow'],
        constructor: function(config) {
            var severityCounts = {
                critical: {count: 0, acknowledged_count: 0},
                error:    {count: 0, acknowledged_count: 0},
                warning:  {count: 0, acknowledged_count: 0},
                info:     {count: 0, acknowledged_count: 0},
                debug:    {count: 0, acknowledged_count: 0},
                clear:    {count: 0, acknowledged_count: 0}
            };
            config = Ext.applyIf(config || {}, {
                height: 45,
                directFn: Zenoss.util.isolatedRequest(Zenoss.remote.DeviceRouter.getInfo),
                text: Zenoss.render.events(severityCounts, config.count || 3)
            });
            Zenoss.EventRainbow.superclass.constructor.call(this, config);
        },
        setContext: function(uid){
            if (uid) {
                this.uid = uid;
                this.refresh();
            }
        },
        refresh: function(){
            this.directFn({uid:this.uid, keys:['events']}, function(result){
                if (Zenoss.env.contextUid && Zenoss.env.contextUid !== this.uid) {
                    return;
                }
                this.updateRainbow(result.data.events);
            }, this);
        },
        updateRainbow: function(severityCounts) {
            this.setText(Zenoss.render.events(severityCounts, this.count));
        }
    });

    // Functions related to creating the grid with only the columns that are going to be visible.
    // We used to create the grid with all the available columns and then hide the ones that we dont want to display.
    // From now on, the grid will only contain the visible columns.
    // Grids that use this functionality:
    //
    //      -- File --             -- state_id --
    //      EvConsole.js            evconsole
    //      itinfrastructure.js     infrastructure_events
    //      devdetail.js            device_events
    //      EvHistory.js            histconsole
    //

    var getColumnDefinitionById = function(col_id)
    {
        var col_def;
        Ext.each(Zenoss.env.getColumnDefinitions(), function(col) {
            if (col.id === col_id) {
                col_def = col;
                return false;
            }
        });
        return col_def;
    };

    var getDefaultColumnIdsToRender = function()
    {
        var column_ids_to_render = [];
        Ext.each(Zenoss.env.COLUMN_DEFINITIONS, function(col) {
            if( !col.hidden) {
                column_ids_to_render.push(col.id);
            }
        });

        return column_ids_to_render;
    };

    // The columns to render are extracted from Zenoss.env.COLUMN_DEFINITIONS and
    // the pre existing grid state.
    Zenoss.env.getColumnIdsToRender = function(state_id)
    {
        var state = Ext.state.Manager.get(state_id);
        var column_ids_to_render = [];

        if (state !== undefined && state.columns !== undefined && state.columns.length > 0)
        {
            Ext.each(state.columns, function(col_state) {
                var col_def = getColumnDefinitionById(col_state.id);
                if ( (col_state.hidden === undefined && !col_def.hidden) || (col_state.hidden !== undefined && col_state.hidden === false) )
                {
                    column_ids_to_render.push(col_state.id);
                }
            });
        }
        else
        {
            column_ids_to_render = getDefaultColumnIdsToRender(state_id);
        }

        return column_ids_to_render;
    };

    var getColumnStateById = function(state_id, col_id)
    {
        var state = Ext.state.Manager.get(state_id);
        var col_state;

        if (state !== undefined && state.columns !== undefined && state.columns.length > 0)
        {
            Ext.each(state.columns, function(c_state) {
                if (c_state.id === col_id)
                {
                    col_state = c_state;
                    return false; // to exit the Ext.each
                }
            });
        }

        return col_state;
    };

    Zenoss.env.recreateGridWithNewColumns = function(grid, col_ids)
    {
        // We modify the grid's state to reflect the new column settings
        // this way when the grid is recreated picks the new config.
        var state_id = grid.stateId;

        // We iterate the new cols and search for previous setting for
        // them in the state. If found in the state we re use them
        // in order to preserve the user's settings
        var new_cols_state = [];
        Ext.each(col_ids, function(col_id) {
            var col_state = getColumnStateById(state_id, col_id);
            if (col_state === undefined)
            {
                var col_def = getColumnDefinitionById(col_id);
                col_state = {};
                col_state.id = col_id;
                if (col_def.hidden) {
                    col_state.hidden = false;
                }
            }
            new_cols_state.push(col_state);
        });

        // Save the new state
        var state = Ext.state.Manager.get(state_id);

        if (state !== undefined)
        {
            state.columns = new_cols_state;
            Ext.state.Manager.set(state);
        }

        // Sends this event so each grid can recreate itself
        grid.fireEvent('recreateGrid', grid);
    };

    Zenoss.env.getColumnDefinitionsToRender = function(state_id)
    {
        var column_ids = Zenoss.env.getColumnIdsToRender(state_id);
        var columns_to_render = [];

        Ext.each(Zenoss.env.COLUMN_DEFINITIONS, function(col) {
            var index = Ext.Array.indexOf(column_ids, col.id);
            if (index > -1) {
                columns_to_render.push(col);
            }
        });
        return columns_to_render;
    };

// End of functions related to saving the state the columns to display

})(); // end of function namespace scoping
