/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

Ext.ns('Zenoss.triggers');

Ext.onReady(function () {

    Zenoss.env.ZP_DETAILS_TRIGGER_PREFIX = "zp_det";

    var router = Zenoss.remote.TriggersRouter,
        ZFR = Zenoss.form.rule,
        STRINGCMPS = ZFR.STRINGCOMPARISONS,
        NUMCMPS = ZFR.NUMBERCOMPARISONS,
        addScheduleDialogue,
        addScheduleDialogueConfig,
        addTriggerDialogue,
        detailPanelConfig,
        displayEditTriggerDialogue,
        displayNotificationEditDialogue,
        displayScheduleEditDialogue,
        editScheduleDialogue,
        editScheduleDialogueConfig,
        editTriggerDialogue,
        masterPanelConfig,
        masterPanelTreeStore,
        navSelectionModel,
        notificationPanelConfig,
        notificationsPanelConfig,
        notification_panel,
        reloadNotificationGrid,
        reloadScheduleGrid,
        reloadTriggersGrid,
        schedulesPanelConfig,
        schedules_panel,
        triggersPanelConfig,
        disableTabContents;

    // visual items
    var bigWindowHeight = 450;
    var bigWindowWidth = 600;
    var panelPadding = 10;

    Ext.define("Zenoss.trigger.AddDialogue", {
        alias:['widget.triggersadddialogue'],
        extend:"Zenoss.dialog.BaseWindow",
        constructor: function(config) {
            var me = this;
            config = config || {};
            Ext.applyIf(config, {
                height: 120,
                width: 300,
                boxMaxWidth: 300, // for chrome, safari
                modal: true,
                plain: true,
                closeAction: 'hide',
                listeners: {
                    show: function(win) {
                        var form = win.addForm;
                        form.newId.setValue('');
                    }
                },
                items:{
                    xtype:'form',
                    ref: 'addForm',
                    listeners: {
                        validitychange: function(form, isValid) {
                            me.query('button')[0].setDisabled(!isValid);
                        }
                    },
                    buttonAlign: 'left',
                    fieldDefaults: {
                        labelWidth: 40
                    },
                    items:[{
                        xtype: 'idfield',
                        name: 'newId',
                        context: '/zport/dmd/Triggers',
                        ref: 'newId',
                        allowBlank: false,
                        vtype: 'alphanum',
                        width:280,
                        fieldLabel: _t('Id')
                    }],
                    buttons:[{
                        xtype: 'button',
                        ui: 'dialog-dark',
                        text: _t('Submit'),
                        ref: '../../submitButton',
                        formBind: true,
                        /*
                         * This dialogue is used to generically add objects for
                         * triggers, notifications and schedule windows. For
                         * triggers and notifications, do the normal thing, but
                         * for schedules, let the config pass in a handler
                         * since creating a window requires slightly different
                         * context.
                         */
                        handler: function(button) {
                            // prevent further clicking
                            button.setDisabled(true);
                            if (config.submitHandler) {
                                config.submitHandler(button);
                            } else {
                                var params = {
                                    newId: button.refOwner.addForm.newId.getValue()
                                };
                                config.directFn(params, function(){
                                    config.reloadFn();
                                });
                            }
                            me.hide();
                        }
                    },{
                        xtype: 'button',
                        ui: 'dialog-dark',
                        ref: '../../cancelButton',
                        text: _t('Cancel'),
                        handler: function() {
                            me.hide();
                        }
                    }]}
            });
            this.callParent(arguments);
        }
    });



    /**
     * NOTIFICATIONS
     **/

    notificationPanelConfig = {
        id: 'notification_panel',
        invalidateScrollerOnRefresh: false
    };

    schedulesPanelConfig = {
        id: 'schedules_panel',
        invalidateScrollerOnRefresh: false
    };

    disableTabContents = function(tab) {
        // disable everything in this tab, but then re-enable the tab itself so
        // that we can still view its contents.
        tab.cascade(function(){
            if (Ext.isFunction(this.disable)) {
                this.disable();
                if (this.xtype === 'panel') {
                    this.addCls('x-item-disabled');
                }
            }
        });
        tab.setDisabled(false);
    };

    var enableTabContents = function(tab) {
        tab.cascade(function() {
            if (Ext.isFunction(this.enable)) {
                this.enable();
            }
        });
        tab.setDisabled(false);
    };

    reloadNotificationGrid = function() {
        Ext.getCmp(notificationPanelConfig.id).getStore().load();
    };


    reloadScheduleGrid = function() {
        var panel = Ext.getCmp(notificationPanelConfig.id),
            row = panel.getSelectionModel().getSelected();
        if (row) {
            Ext.getCmp(schedulesPanelConfig.id).getStore().load({
                params: {
                    uid:row.data.uid
                }
            });
        }
    };

    displayScheduleEditDialogue = function(data) {
        var dialogue = Ext.getCmp(editScheduleDialogueConfig.id);
        dialogue.setTitle(Ext.String.format('{0} - {1}', editScheduleDialogueConfig.title, data['newId']));
        dialogue.loadData(data);
        dialogue.show();
    };

    editScheduleDialogueConfig = {
        id: 'edit_schedule_dialogue',
        xtype: 'editscheduledialogue',
        title: _t('Edit Notification Schedule'),
        directFn: router.updateWindow,
        reloadFn: reloadScheduleGrid
    };

    addScheduleDialogueConfig = {
        id: 'add_schedule_dialogue',
        xtype: 'addialogue',
        title: _t('Add Schedule Window'),
        directFn: router.addWindow,
        submitHandler: function(button) {
            var panel = Ext.getCmp(notificationPanelConfig.id),
                row = panel.getSelectionModel().getSelected(),
                params = {
                    newId: button.refOwner.addForm.newId.getValue(),
                    contextUid: row.data.uid
                };

            router.addWindow(params, function(){
                reloadScheduleGrid();
            });
        }
    };

    /**
     * @class Zenoss.triggers.PermissionGridModel
     * @extends Ext.data.Model
     **/
    Ext.define('Zenoss.triggers.PermissionGridModel',  {
        extend: 'Ext.data.Model',
        idProperty: 'value',
        fields: [
            { name:'type'},
            { name:'label'},
            { name:'value'},
            { name: 'write', type: 'bool'},
            { name: 'manage', type: 'bool'}
        ]
    });
    Ext.define("Zenoss.model.UsersComboStore", {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: ['type', 'label', 'value']
    });

Ext.define('Zenoss.triggers.UsersPermissionGrid', {
        extend: 'Ext.grid.Panel',
        alias: ['widget.usersPermissionGrid'],
        constructor: function(config) {
            var me = this;
            config = config || {};
            this.allowManualEntry = config.allowManualEntry || false;
            Ext.applyIf(config, {
                ref: 'users_grid',
                title: config.title,
                height: 200,
                autoHeight: true,
                keys: [{
                    key: [Ext.EventObject.ENTER],
                    handler: function() {
                        me.addValueFromCombo();
                    }
                }],
                viewConfig: {
                    loadMask: false
                },
                tbar: [{
                        xtype: 'combo',
                        ref: 'usersCombo',
                        typeAhead: true,
                        triggerAction: 'all',
                        lazyRender:true,
                        queryMode: 'local',
                        id: 'usersCombo',
                        store: Ext.create('Zenoss.NonPaginatedStore', {
                            root: 'data',
                            autoLoad: true,
                            model: 'Zenoss.model.UsersComboStore',
                            directFn: router.getRecipientOptions
                        }),
                        valueField: 'value',
                        displayField: 'label'
                    },{
                        xtype: 'button',
                        text: 'Add',
                        ref: 'add_button',
                        id: 'userperm_add_user_button',
                        handler: function() {
                            me.addValueFromCombo();
                        }
                    },{
                        xtype: 'button',
                        ref: 'delete_button',
                        id: 'userperm_delete_user_button',
                        iconCls: 'delete',
                        handler: function() {
                            var rows = me.getSelectionModel().getSelection();
                            if (rows.length){
                                var row = rows[0];
                                me.getStore().remove(row);
                                me.getView().refresh();
                            }
                        }
                    }
                ],
                store: new Ext.data.JsonStore({
                    model: 'Zenoss.triggers.PermissionGridModel',
                    storeId: 'users_combo_store',
                    autoLoad: true,
                    data: []
                }),
                columns: [
                    {
                        header: _t('Type'),
                        dataIndex: 'type',
                        width: 120,
                        sortable: true
                    },{
                        header: config.title,
                        dataIndex: 'label',
                        width: 120,
                        flex: 1,
                        sortable: true
                    },{
                        header: _t('Write'),
                        dataIndex: 'write',
                        listeners:{
                            click: function(e, f, rowi, coli, event){
                                var newVal = event.target.checked;
                                me.getView().getSelectionModel().getSelected().data.write = newVal;
                                me.reconfigure();

                            }
                        },
                        renderer: function(val, e, record, rowIndex){
                            var checked = val ? "checked": "";
                            return '<input '+checked+' id="write_'+rowIndex+'" name="write_'+rowIndex+'" type="checkbox" value="'+val+'">';
                        }
                    }, {
                        header: _t('Manage'),
                        dataIndex: 'manage',
                        listeners:{
                            click: function(e, f, rowi, coli, event){
                                var newVal = event.target.checked;
                                me.getView().getSelectionModel().getSelected().data.manage = newVal;
                                me.reconfigure();

                            }
                        },
                        renderer: function(val, e, record, rowIndex){
                            var checked = val ? "checked": "";
                            return '<input '+checked+' id="manage_'+rowIndex+'" name="manage_'+rowIndex+'" type="checkbox" value="'+val+'">';
                        }
                    }
                ],
                selModel: new Zenoss.SingleRowSelectionModel({})
            });
            this.callParent(arguments);
        },
        addValueFromCombo: function() {
            var cb = Ext.getCmp('usersCombo');

            var val = cb.getValue(),
                idx = cb.store.find('value', val),
                row,
                type = 'manual',
                label;
            if (idx !== -1) {
                row = cb.store.getAt(idx);
            }

            if (row) {
                type = row.data.type;
                label = row.data.label;
            }
            else {
                val = cb.getRawValue();
                label = val;
            }


            if (!this.allowManualEntry && type === 'manual') {
                Zenoss.message.error(_t('Manual entry not permitted.'));
            }
            else {
                var existingIndex = this.getStore().findExact('value', val);

                if (!Ext.isEmpty(val) && existingIndex === -1) {
                    var record = new Zenoss.triggers.PermissionGridModel({
                        type:type,
                        value:val,
                        label:label,
                        write:false,
                        manage: false
                    });
                    this.getStore().add(record);
                    cb.clearValue();
                }
                else if (existingIndex !== -1) {
                    Zenoss.message.error(_t('Duplicate items not permitted.'));
                }

            }

        },
        loadData: function(data) {
            this.getStore().loadData(data.users);
        }
    });


    var NotificationTabContent = Ext.extend(Ext.Panel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                forceLayout: true,
                autoScroll: true,
                resizable: false,
                height: bigWindowHeight-110,
                maxHeight: bigWindowHeight-110,
                width: bigWindowWidth,
                minWidth: bigWindowWidth
            });
            NotificationTabContent.superclass.constructor.apply(this, arguments);
        }
    });

    var NotificationTabPanel = Ext.extend(Ext.TabPanel, {
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                ref: '../tabPanel',
                activeTab: 0,
                activeIndex: 0,
                forceLayout: true,
                frame: false,
                style:{'left':'2px'},
                loadData: function(data) {
                    Ext.each(this.items.items, function(item) {
                        item.loadData(data);
                    });
                }
            });
            NotificationTabPanel.superclass.constructor.apply(this, arguments);
        }
    });

    displayNotificationEditDialogue = function(data) {
        var tab_notification, tab_content;

        tab_content = new NotificationTabContent({
            layout: 'anchor',
            padding: panelPadding,
            title: _t('Content'),
            id: 'notification_content',
            defaults: {
                padding: 0
            },
            listeners: {
                render: function() {
                    if (!this.userWrite) {
                        disableTabContents(this);
                    }
                }
            },
            loadData: function(data) {
                this.userWrite = data['userWrite'] || false;
                this.add(data.content);
            }
        });

        tab_notification = new NotificationTabContent({
            title: _t('Notification'),
            ref: 'notification_tab',
        listeners: {
            render: function(){
                if(Zenoss.SELENIUM){
                    Ext.getDom(this.tab.btnEl.id).id = "notifications_notification_tab_button";
                    Ext.getDom(this.tab.tabBar.items.items[1].btnEl.id).id = "notifications_content_tab_button";
                    Ext.getDom(this.tab.tabBar.items.items[2].btnEl.id).id = "notifications_subscribers_tab_button";
                 }
            }
        },
            items: [
                {
                    xtype: 'panel',
                    layout: 'column',
                    //padding: panelPadding,
                    defaults: {
                        layout: 'anchor',
                        padding: 10,
                        height:95,
                        columnWidth: 0.49
                    },
                    items: [
                        {
                            xtype: 'fieldset',
                            header: false,
                            defaults: {anchor: '100%', labelWidth: 190 },
                            items: [
                                {
                                    xtype: 'hidden',
                                    name: 'uid',
                                    ref: '../../uid'
                                },{
                                    xtype: 'checkbox',
                                    name: 'enabled',
                                    id: 'notifications_enabled_checkbox',
                                    ref: '../../enabled',
                                    fieldLabel: _t('Enabled')
                                },{
                                    xtype: 'checkbox',
                                    name: 'send_clear',
                                    id: 'notifications_sendclear_checkbox',
                                    ref: '../../send_clear',
                                    fieldLabel: _t('Send Clear')
                                },{
                                    xtype: 'checkbox',
                                    name: 'send_initial_occurrence',
                                    id: 'notifications_sendinitial_checkbox',
                                    ref: '../../send_initial_occurrence',
                                    fieldLabel: _t('Send only on Initial Occurrence?')
                                }
                            ]
                        },
                        {
                            xtype: 'fieldset',
                            header: false,
                            items: [
                                {
                                    xtype: 'numberfield',
                                    name: 'delay_seconds',
                                    allowNegative: false,
                                    allowBlank: false,
                                    id: 'notifications_delay_numberfield',
                                    ref: '../../delay_seconds',
                                    fieldLabel: _t('Delay (seconds)')
                                },{
                                    xtype: 'numberfield',
                                    allowNegative: false,
                                    allowBlank: false,
                                    id: 'notifications_repeat_numberfield',
                                    name: 'repeat_seconds',
                                    ref: '../../repeat_seconds',
                                    fieldLabel: _t('Repeat (seconds)')
                                }
                            ]
                        }
                    ]
                },
                {
                    xtype: 'triggersSubscriptions',
                    ref: 'subscriptions'
                }
            ],
            loadData: function(data) {
                this.uid.setValue(data.uid);
                this.enabled.setValue(data.enabled);
                this.delay_seconds.setValue(data.delay_seconds);
                this.send_clear.setValue(data.send_clear);
                this.repeat_seconds.setValue(data.repeat_seconds);
                this.subscriptions.loadData(data.subscriptions);
                this.send_initial_occurrence.setValue(data.send_initial_occurrence);
            }
        });

        if (!data['userWrite']) {
            disableTabContents(tab_notification);
        }


        var tab_recipients = new NotificationTabContent({
            title: _t('Subscribers'),
            ref: 'recipients_tab',
            items: [{
                xtype: 'panel',
                layout: 'anchor',
                title: _t('Local Notification Permissions'),
                items: [
                    {
                        xtype:'checkbox',
                        name: 'notification_globalRead',
                        id: 'notifications_recipients_globalread_checkbox',
                        ref: '../globalRead',
                        boxLabel: _t('Everyone can view'),
                        hideLabel: true
                    },
                    {
                        xtype:'checkbox',
                        name: 'notification_globalWrite',
                        id: 'notifications_recipients_globalwrite_checkbox',
                        ref: '../globalWrite',
                        boxLabel: _t('Everyone can edit content'),
                        hideLabel: true
                    },
                    {
                        xtype:'checkbox',
                        name: 'notification_globalManage',
                        id: 'notifications_recipients_globalmanage_checkbox',
                        ref: '../globalManage',
                        boxLabel: _t('Everyone can manage subscriptions'),
                        hideLabel: true
                    }
                ]
            },{
                xtype: 'usersPermissionGrid',
                title: _t('Subscribers'),
                allowManualEntry: true,
                width: Ext.IsIE ? bigWindowWidth-50 : 'auto',
                ref: 'recipients_grid'
            }
            ],
            loadData: function(data) {
                this.recipients_grid.getStore().loadData(data.recipients);
                this.globalRead.setValue(data.globalRead);
                this.globalWrite.setValue(data.globalWrite);
                this.globalManage.setValue(data.globalManage);
            }
        });

        if (!data['userManage']) {
            disableTabContents(tab_recipients);
        }

        var tab_panel = new NotificationTabPanel({
            // the following width dance is to make IE, FF and Chrome behave.
            // Each browser was responding differently to the following params.
            width: bigWindowWidth-10,
            minWidth: bigWindowWidth-15,
            maxWidth: bigWindowWidth,
            items: [
                // NOTIFICATION INFO
                tab_notification,

                // CONTENT TAB
                tab_content,

                // RECIPIENTS
                tab_recipients
            ]
        });

        var reloadNotificationGridFn = function() {
            reloadNotificationGrid.apply(this, arguments);
            schedules_panel.getStore().removeAll();
        };

        var dialogue =  Ext.create('Zenoss.triggers.EditNotificationDialogue', {
            title: _t('Edit Notification'),
            directFn: router.updateNotification,
            reloadFn: reloadNotificationGridFn,
            tabPanel: tab_panel
        });

        dialogue.title = Ext.String.format("{0} - {1} ({2})", dialogue.title, data['newId'], data['action']);
        dialogue.loadData(data);
        dialogue.show();
    };

    var displayNotificationAddDialogue = function() {
        var typesCombo = new Ext.form.ComboBox({
            store: Ext.create('Zenoss.NonPaginatedStore', {
                autoLoad: true,
                directFn: router.getNotificationTypes,
                model: 'Zenoss.model.IdName'
            }),
            name:'action',
            id: 'notification_types_combo',
            ref: 'action_combo',
            allowBlank:false,
            required:true,
            editable:false,
            displayField:'name',
            valueField:'id',
            fieldLabel: _t('Action'),
            triggerAction: 'all'
        });
        typesCombo.store.on('load', function(){
            typesCombo.setValue('email');
        });
        var dialogue = new Zenoss.dialog.BaseWindow({
            title: _t('Add Notification'),
            height: 140,
            width: 300,
            modal: true,
            plain: true,
            items: [{
                xtype:'form',
                ref: '../addForm',
                listeners: {
                    validitychange: function(form, isValid) {
                        dialogue.query('DialogButton')[0].setDisabled(!isValid);
                    }
                },
                buttonAlign: 'left',
                fieldDefaults: {
                    labelWidth: 40
                },
                items:[
                    {
                        xtype: 'textfield',
                        name: 'newId',
                        ref: '../newId',
                        id: 'add_notification_textfield',
                        allowBlank: false,
                        vtype: 'alphanum',
                        width:280,
                        fieldLabel: _t('Id')
                    },
                    typesCombo
                ],
                buttons:[
                    {
                        xtype: 'DialogButton',
                        ref: 'submitButton',
                        id: 'submit_new_notification_button',
                        text: _t('Submit'),
                        handler: function(button) {
                            var form = button.refOwner.ownerCt,
                                params = form.getForm().getValues();


                            button.setDisabled(true);

                            router.addNotification(params, function(){
                                reloadNotificationGrid();
                            });
                        }
                    },{
                        xtype: 'DialogButton',
                        id: 'cancel_new_notification_button',
                        ref: 'cancelButton',
                        text: _t('Cancel')
                    }
                ]
            }]
        });
        dialogue.show();
    };

    Ext.define("Zenoss.triggers.EditNotificationDialogue", {
        alias:['widget.editnotificationdialogue'],
        extend:"Zenoss.dialog.BaseWindow",
        constructor: function(config) {
            var me = this;
            config = config || {};
            Ext.applyIf(config, {
                plain: true,
                cls: 'white-background-panel',
                autoScroll: true,
                constrain: true,
                modal: true,
                resizable: false,
                width: bigWindowWidth+8,
                height: bigWindowHeight,
                minWidth: bigWindowWidth,
                minHeight: bigWindowHeight,
                stateful: false,
                layout: 'fit',
                forceLayout: true,
                items: [{
                    xtype:'form',
                    ref: 'editForm',
                    buttonAlign: 'left',
                    listeners: {
                        validitychange: function(form, isValid) {
                            me.query('DialogButton')[0].setDisabled(!isValid);
                        }
                    },
                    items:[config.tabPanel],
                    buttons:[{
                        xtype: 'DialogButton',
                        text: _t('Submit'),
                        id: 'notifications_edit_submit_button',
                        ref: '../../submitButton',
                        handler: function(button) {
                            var params = button.refOwner.editForm.getForm().getValues();
                            params.recipients = [];
                            params.subscriptions = [];
                            Ext.each(
                                button.refOwner.tabPanel.notification_tab.subscriptions.getStore().getRange(),
                                function(item) {
                                    params.subscriptions.push(item.data.uuid);
                                }
                            );
                            Ext.each(
                                button.refOwner.tabPanel.recipients_tab.recipients_grid.getStore().getRange(),
                                function(item){
                                    params.recipients.push(item.data);
                                }
                            );
                            config.directFn(params, function(){
                                config.reloadFn();
                            });
                            me.hide();
                        }
                    },{
                        xtype: 'DialogButton',
                        ref: '../../cancelButton',
                        id: 'notifications_edit_cancel_button',
                        text: _t('Cancel'),
                        handler: function(){
                            me.hide();
                        }
                    }]
                }]
            });
            this.callParent(arguments);
        },
        loadData: function(data) {
            this.tabPanel.loadData(data);
        }
    });



    Ext.define("Zenoss.triggers.EditScheduleDialogue", {
        alias:['widget.editscheduledialogue'],
        extend:"Zenoss.dialog.BaseWindow",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                modal: true,
                plain: true,
                autoHeight: true,
                minHeight: 100,
                autoWidth: true,
                minWidth: 250,
                closeAction: 'hide',
                items:{
                    xtype:'form',
                    ref: 'editForm',
                    buttonAlign: 'left',
                    listeners: {
                        validitychange: function(form, isValid) {
                            this.query('button')[0].setDisabled(!isValid);
                        },
                        scope: this
                    },
                    items:[{
                        xtype: 'hidden',
                        name: 'uid',
                        ref: 'uid'
                    },{
                        xtype: 'checkbox',
                        name: 'enabled',
                        id: 'edit_notification_schedule_enabled_checkbox',
                        fieldLabel: _t('Enabled')
                    },{
                        xtype: 'zendatetimefield',
                        name: 'start_ts',
                        id: 'edit_notification_schedule_start_datefield',
                        allowBlank: false,
                        fieldLabel: _t('Start Date')
                    },
                    new Ext.form.ComboBox({
                        store: new Ext.data.ArrayStore({
                            model: 'Zenoss.model.Name',
                            id: 0,
                            data: [
                                ['Never'],
                                ['Daily'],
                                ['Every Weekday'],
                                ['Weekly'],
                                ['Monthly'],
                                ['First Sunday of the Month']
                            ]
                        }),
                        queryMode: 'local',
                        name: 'repeat',
                        id: 'edit_notification_schedule_repeat_checkbox',
                        allowBlank: false,
                        required: true,
                        editable: false,
                        displayField: 'name',
                        valueField: 'name',
                        triggerAction: 'all',
                        fieldLabel: _t('Repeat')
                    }),{
                        xtype: 'numberfield',
                        allowNegative: false,
                        allowDecimals: false,
                        id: 'edit_notification_schedule_duration_numberfield',
                        name: 'duration',
                        ref: 'duration',
                        fieldLabel: _t('Duration (minutes)')
                    }],
                    buttons:[{
                        xtype: 'button',
                        ui: 'dialog-dark',
                        text: _t('Submit'),
                        ref: '../../submitButton',
                        id: 'edit_notification_schedule_submit_button',
                        handler: function(button) {
                            if (config.submitHandler) {
                                config.submitHandler(button);
                            } else {
                                var params = button.refOwner.editForm.getForm().getValues();
                                console.log(params);
                                config.directFn(params, function(){
                                    config.reloadFn();
                                    button.refOwner.hide();
                                });
                            }
                        }
                    },{
                        xtype: 'button',
                        ui: 'dialog-dark',
                        ref: '../../cancelButton',
                        id: 'edit_notification_schedule_cancel_button',
                        text: _t('Cancel'),
                        handler: function(button) {
                            button.refOwner.hide();
                        }
                    }]
                }
            });
            Zenoss.triggers.EditScheduleDialogue.superclass.constructor.apply(this, arguments);
        },
        loadData: function(data) {
            Ext.each(this.editForm.items.items, function(item) {
                item.setValue(data[item.name]);
            });
        }
    });


    editScheduleDialogue = new Zenoss.triggers.EditScheduleDialogue(editScheduleDialogueConfig);
    addScheduleDialogue = new Zenoss.trigger.AddDialogue(addScheduleDialogueConfig);

    /**
     * @class Zenoss.triggers.NotificationModel
     * @extends Ext.data.Model
     * Field definitions for the notifications
     **/
    Ext.define('Zenoss.triggers.NotificationModel',  {
        extend: 'Ext.data.Model',
        idProperty: 'uuid',
        fields: [
            { name:'uid'},
            { name:'newId'},
            { name:'enabled'},
            { name:'action'},
            { name:'delay_seconds'},
            { name:'send_clear'},
            { name:'send_initial_occurrence'},
            { name:'repeat_seconds'},
            { name:'content'},
            { name:'recipients'},
            { name:'subscriptions'},
            { name:'globalRead'},
            { name:'globalWrite'},
            { name:'globalManage'},
            { name:'userRead'},
            { name:'userWrite'},
            { name:'userManage'}
        ]
    });

    /**
     * @class Zenoss.triggers.NotificationStore
     * @extend Zenoss.DirectStore
     * Direct store for loading notifications
     */
    Ext.define("Zenoss.triggers.NotificationStore", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.triggers.NotificationModel',
                directFn: router.getNotifications,
                initialSortColumn: 'newId',
                initialSortDirection: 'ASC',
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.triggers.NotificationSubscriptions", {
        alias:['widget.notificationsubscriptions'],
        extend:"Ext.grid.GridPanel",
        constructor: function(config) {
            var me = this;
            config = config || {};
            Ext.applyIf(config, {
                autoScroll: true,
                minHeight: 400, // force IE to show something
                region: 'center',
                title: _t('Notifications'),
                viewConfig: {
                    forceFit: true
                },
                listeners: {
                    itemdblclick: function(grid){
                        var row = grid.getSelectionModel().getSelected();
                        if (row) {
                            displayNotificationEditDialogue(row.data);
                        }
                    }
                },
                selModel: new Zenoss.SingleRowSelectionModel({
                    listeners: {
                        select: function(sm) {
                            var rows = sm.getSelection(),
                                row,
                                panel = Ext.getCmp(schedulesPanelConfig.id);
                            if (!rows.length) {
                                return;
                            }
                            row = rows[0];
                            panel.setContext(row.data.uid, row.data);
                            me.deleteButton.setDisabled(!row.data.userWrite);
                            me.customizeButton.setDisabled(false);
                        },
                        deselect: function() {
                            Ext.getCmp(schedulesPanelConfig.id).disableButtons(true);
                            me.deleteButton.setDisabled(true);
                            me.customizeButton.setDisabled(true);
                        }
                    },
                    scope: this
                }),
                store: Ext.create('Zenoss.triggers.NotificationStore', {}),
                columns: [{
                    xtype: 'booleancolumn',
                    trueText: _t('Yes'),
                    falseText: _t('No'),
                    dataIndex: 'enabled',
                    header: _t('Enabled'),
                    sortable: true
                },{
                    dataIndex: 'newId',
                    header: _t('ID'),
                    flex: 1,
                    sortable: true
                },{
                    dataIndex: 'subscriptions',
                    header: _t('Trigger'),
                    sortable: true,
                    // use a fancy renderer that get's it's display value
                    // from the store that already has the triggers.
                    renderer: function(value) {
                        var triggerList = [];
                        Ext.each(
                            value,
                            function(item) {
                                if (item) {
                                    triggerList.push(item.name);
                                }
                            }
                        );
                        return triggerList.join(', ');
                    }
                },{
                    dataIndex: 'action',
                    header: _t('Action'),
                    sortable: true
                },{
                    dataIndex: 'recipients',
                    header: _t('Subscribers'),
                    sortable: true,
                    renderer: function(value, metaData, record) {
                        return record.data.recipients.length || 0;
                    }
                }],
                tbar:[{
                    xtype: 'button',
                    iconCls: 'add',
                    ref: '../addButton',
                    id: 'notifications_panel_add_button',
                    disabled: Zenoss.Security.doesNotHavePermission("Update Notification"),
                    handler: function() {
                        displayNotificationAddDialogue();
                    }
                },{
                    xtype: 'button',
                    iconCls: 'delete',
                    id: 'notifications_panel_delete_button',
                    ref: '../deleteButton',
                    disabled: true,
                    handler: function(button) {
                        var rows = button.refOwner.getSelectionModel().getSelection(),
                            row,
                            uid,
                            params,
                            callback;
                        if (rows.length) {
                            row = rows[0];
                        }
                        if (row){
                            uid = row.data.uid;
                            // show a confirmation
                            new Zenoss.dialog.SimpleMessageDialog({
                                message: Ext.String.format(_t('Are you sure you want to delete the selected {0}?'), row.data.newId),
                                title: _t('Delete Notification Subscription'),
                                buttons: [{
                                    xtype: 'DialogButton',
                                    text: _t('OK'),
                                    handler: function() {
                                        params = {
                                            uid:uid
                                        };
                                        callback = function(){
                                            var panel = Ext.getCmp(schedulesPanelConfig.id);
                                            panel.getStore().removeAll();
                                            panel.disableButtons(true);
                                            Ext.getCmp(notificationPanelConfig.id).customizeButton.setDisabled(true);
                                            reloadNotificationGrid();
                                        };
                                        router.removeNotification(params, callback);
                                    }
                                }, {
                                    xtype: 'DialogButton',
                                    text: _t('Cancel')
                                }]
                            }).show();
                        }
                    }
                },{
                    xtype: 'button',
                    iconCls: 'customize',
                    id: 'notifications_panel_customize_button',
                    disabled:true,
                    ref: '../customizeButton',
                    handler: function(button){
                        var row = button.refOwner.getSelectionModel().getSelected();
                        if (row) {
                            displayNotificationEditDialogue(row.data);
                        }
                    }
                }]
            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            // notification subscriptions are not context specific
            this.uid = uid;
            this.getStore().load();
            this.deleteButton.setDisabled(true);
            this.customizeButton.setDisabled(true);
            Ext.getCmp('schedules_panel_add_button').disable();
            Ext.getCmp('schedules_panel_delete_button').disable();
            Ext.getCmp('schedules_panel_customize_button').disable();
        }
    });


    /**
     * @class Zenoss.triggers.TriggersStore
     * @extend Zenoss.NonPaginatedStore
     * Direct store for loading ip addresses
     */
    Ext.define("Zenoss.triggers.TriggersStore", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                autoLoad: true,
                model: 'Zenoss.triggers.TriggersModel',
                initialSortColumn: "name",
                directFn: router.getTriggers,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.triggers.TriggersGridPanel", {
        alias:['widget.TriggersGridPanel'],
        extend:"Ext.grid.GridPanel",
        constructor: function(config) {
            var me = this;
            Ext.applyIf(config, {
                columns: [
                    {
                        id: 'enabled',
                        dataIndex: 'enabled',
                        header: _t('Enabled'),
                        xtype: 'booleancolumn',
                        trueText: _t('Yes'),
                        falseText: _t('No'),
                        width: 70,
                        sortable: true,
                        menuDisabled: true
                    }, {
                        id: 'name',
                        flex: 1,
                        dataIndex: 'name',
                        header: _t('Name'),
                        width: 200,
                        sortable: true,
                        menuDisabled: true
                    }
                ],
                title: _t('Triggers'),
                store: Ext.create('Zenoss.triggers.TriggersStore', {}),
                selModel: new Zenoss.SingleRowSelectionModel({
                    listeners: {
                        select: function(record) {
                            // enable/disabled the edit button
                            me.deleteButton.setDisabled(!record.lastSelected.data.userWrite);
                            me.customizeButton.setDisabled(false);
                        },
                        deselect: function() {
                            me.deleteButton.setDisabled(true);
                            me.customizeButton.setDisabled(true);
                        }
                    }
                }),
                listeners: {
                    afterrender: function(t){
                        if(Zenoss.SELENIUM){
                            Ext.defer(function(){
                               var table = Ext.get(t.getView().el.id).query('table');
                               table[0].id = "trigger_grid_table";
                            }, 1000);
                         }
                    },
                    itemdblclick: function(grid) {
                        var rows = grid.getSelectionModel().getSelection();
                        if (rows.length) {
                            displayEditTriggerDialogue(rows[0].data);
                        }
                    }
                },
                tbar:[
                    {
                        xtype: 'button',
                        iconCls: 'add',
                        id: 'add__new_trigger_button',
                        disabled: Zenoss.Security.doesNotHavePermission('Manage Trigger'),
                        ref: '../addButton',
                        handler: function() {
                            addTriggerDialogue.show();
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'delete',
                        id: 'delete_old_trigger_button',
                        disabled: true,
                        ref: '../deleteButton',
                        handler: function() {
                            var rows = me.getSelectionModel().getSelection(),
                                row,
                                uuid, params, callback;
                            if (rows){
                                row = rows[0];
                                uuid = row.data.uuid;
                                // show a confirmation
                                 new Zenoss.dialog.SimpleMessageDialog({
                                        message: Ext.String.format(_t('Are you sure you want to delete the selected {0}?'), row.data.name),
                                        title: _t('Delete Trigger'),
                                        buttons: [{
                                            xtype: 'DialogButton',
                                            text: _t('OK'),
                                            id: 'delete_trigger_button',
                                            handler: function() {
                                                params= {
                                                    uuid:uuid
                                                };
                                                callback = function(){
                                                    // item removed, reload grid.
                                                    me.deleteButton.setDisabled(true);
                                                    me.customizeButton.setDisabled(true);
                                                    reloadTriggersGrid();
                                                    reloadNotificationGrid();
                                                };
                                                router.removeTrigger(params, callback);
                                            }
                                        }, {
                                            xtype: 'DialogButton',
                                            id: 'cancel_delete_trigger_button',
                                            text: _t('Cancel')
                                        }]
                                    }).show();
                            }
                        }
                    },{
                        xtype: 'button',
                        iconCls: 'customize',
                        id: 'trigger_gear_btn',
                        disabled:true,
                        ref: '../customizeButton',
                        handler: function(){
                            var rows = me.getSelectionModel().getSelection();
                            if (rows.length) {
                                displayEditTriggerDialogue(rows[0].data);
                            }
                        }
                    }
                ]
            });
            this.callParent(arguments);
        },
        setContext: function() {
            // triggers are not context aware.
            this.getStore().load();
        }
    });

    notification_panel = Ext.create('Zenoss.triggers.NotificationSubscriptions', notificationPanelConfig);


    /**
     * @class Zenoss.triggers.ScheduleModel
     * @extends Ext.data.Model
     * Field definitions for the schedules
     **/
    Ext.define('Zenoss.triggers.ScheduleModel',  {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: [
            {name: 'uid'},
            {name: 'newId'},
            {name: 'enabled'},
            {name: 'start_ts'},
            {name: 'start'},
            {name: 'starttime'},
            {name: 'repeat'},
            {name: 'duration'}
        ]
    });

    /**
     * @class Zenoss.triggers.ScheduleStore
     * @extend Zenoss.DirectStore
     * Direct store loading schedules
     */
    Ext.define("Zenoss.triggers.ScheduleStore", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.triggers.ScheduleModel',
                initialSortColumn: "uid",
                directFn: router.getWindows,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.triggers.SchedulesPanel", {
        alias:['widget.schedulespanel'],
        extend:"Ext.grid.GridPanel",
        constructor: function(config) {
            var me = this;
            config = config || {};
            Ext.applyIf(config, {
                autoScroll: true,
                height: "100%",
                minHeight: 400, // force IE to show something
                viewConfig: {
                    forceFit: true
                },
                listeners: {
                    itemdblclick: function(grid){
                        var row = grid.getSelectionModel().getSelected();
                        if (row) {
                            displayScheduleEditDialogue(row.data);
                        }
                    },
                    viewready: function(t){
                        if(Zenoss.SELENIUM){
                            Ext.defer(function(){
                               var table = Ext.get(t.getView().el.id).query('table');
                               table[0].id = "schedules_panel_grid_table";
                            }, 1000);
                            t.getStore().on('datachanged', function(){
                                Ext.defer(function(){
                                    var table = Ext.get(t.getView().el.id).query('table');
                                    table[0].id = "schedules_panel_grid_table";
                                }, 1000);
                            });
                        }
                    }
                },
                selModel: new Zenoss.SingleRowSelectionModel({
                    listeners: {
                        select: function() {
                            var disable = !me.parent.userManage;
                            me.deleteButton.setDisabled(disable);
                            me.customizeButton.setDisabled(disable);
                        },
                        deselect: function() {
                            me.deleteButton.setDisabled(true);
                            me.customizeButton.setDisabled(true);
                        }
                    }
                }),
                store: Ext.create('Zenoss.triggers.ScheduleStore', {}),
                columns: [{
                    xtype: 'booleancolumn',
                    trueText: _t('Yes'),
                    falseText: _t('No'),
                    dataIndex: 'enabled',
                    header: _t('Enabled'),
                    width: 60,
                    sortable: true
                },{
                    dataIndex: 'newId',
                    header: _t('ID'),
                    flex: 1,
                    sortable: true
                },{
                    dataIndex: 'start_ts',
                    header: _t('Start'),
                    width: 200,
                    sortable: true,
                    renderer: Zenoss.date.renderDateColumn()
                }],

                tbar:[{
                    xtype: 'button',
                    iconCls: 'add',
                    ref: '../addButton',
                    id: 'schedules_panel_add_button',
                    disabled: true,
                    handler: function() {
                        addScheduleDialogue.show();
                    }
                },{
                    xtype: 'button',
                    iconCls: 'delete',
                    id: 'schedules_panel_delete_button',
                    ref: '../deleteButton',
                    disabled: true,
                    handler: function(button) {
                        var row = button.refOwner.getSelectionModel().getSelected(),
                            uid,
                            params;
                        if (row){
                            uid = row.data.uid;
                            // show a confirmation
                            new Zenoss.dialog.SimpleMessageDialog({
                                message: Ext.String.format(_t('Are you sure you want to delete the selected {0}?'), row.data.newId),
                                title: _t('Delete Schedule'),
                                buttons: [{
                                    xtype: 'DialogButton',
                                    text: _t('OK'),
                                    handler: function() {
                                        params = {
                                            uid:uid
                                        };
                                        router.removeWindow(params, reloadScheduleGrid);
                                    }
                                }, {
                                    xtype: 'DialogButton',
                                    text: _t('Cancel')
                                }]
                            }).show();
                        }
                    }
                },{
                    xtype: 'button',
                    iconCls: 'customize',
                    id: 'schedules_panel_customize_button',
                    disabled:true,
                    ref: '../customizeButton',
                    handler: function(button){
                        var row = button.refOwner.getSelectionModel().getSelected();
                        if (row) {
                            displayScheduleEditDialogue(row.data);
                        }
                    }
                }]

            });
            this.callParent(arguments);
        },
        setContext: function(uid, parent){
            this.uid = uid;
            this.parent = parent;
            this.getStore().load({
                params: {
                    uid: uid
                }
            });
            this.addButton.setDisabled(!this.parent.userManage);
            this.disableButtons(true);
        },
        disableButtons: function(bool){
            var noLocalUserManage = !this.parent.userManage;
            this.deleteButton.setDisabled(bool || noLocalUserManage);
            this.customizeButton.setDisabled(bool || noLocalUserManage);
        }
    });


    schedules_panel = Ext.create('Zenoss.triggers.SchedulesPanel', schedulesPanelConfig);


    Ext.define("Zenoss.triggers.NotificationPageLayout", {
        alias: ['widget.notificationpagelayout'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = config || {};

            Ext.applyIf(config, {
                id: 'notification_subscription_panel',
                layout:'border',
                defaults: {
                    collapsible: false,
                    split: true
                },
                items: [config.notificationPanel,{
                    title: _t('Notification Schedules'),
                    region: 'east',
                    width: 375,
                    minSize: 100,
                    maxSize: 375,
                    items: [config.schedulePanel]

                }]
            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            notification_panel.setContext(uid);
        }
    });

    notificationsPanelConfig = {
        id: 'notifications_panel',
        schedulePanel: schedules_panel,
        notificationPanel: notification_panel
    };

    /***
     * TRIGGERS
     **/

    triggersPanelConfig = {
        id: 'triggers_grid_panel',
        xtype: 'TriggersGridPanel',
        invalidateScrollerOnRefresh: false
    };

    detailPanelConfig = {
        id: 'triggers_detail_panel',
        xtype: 'contextcardpanel',
        split: true,
        region: 'center',
        layout: 'card',
        activeItem: 0,
        items: [Ext.create('Zenoss.triggers.TriggersGridPanel', triggersPanelConfig),
                Ext.create('Zenoss.triggers.NotificationPageLayout', notificationsPanelConfig)]
    };

    navSelectionModel = new Zenoss.TreeSelectionModel({
        listeners: {
            selectionchange: function (sm, newnodes) {
                if (!newnodes.length) {
                    return;
                }
                var newnode = newnodes[0];
                var p = Ext.getCmp(detailPanelConfig.id);
                p.layout.setActiveItem(newnode.data.index);
                p.setContext(newnode.data.target);
            }
        }
    });

    masterPanelTreeStore = Ext.create('Ext.data.TreeStore', {
        model: 'Zenoss.model.Tree',
        root: {
            text: 'Trigger Navigation',
            draggable: false,
            id: 'trigger_root',
            expanded: true,
            children: [
                {
                    target: triggersPanelConfig.id,
                    text: 'Triggers',
                    leaf: true,
                    iconCls: 'no-icon'

                }, {
                    target: notificationsPanelConfig.id,
                    text: 'Notifications',
                    leaf: true,
                    iconCls: 'no-icon'
                }
            ]
        }

    });

    masterPanelConfig = {
        id: 'trigger-master_panel',
        region: 'west',
        split: 'true',
        width: 275,
        maxWidth: 275,
        autoScroll: false,
        items: [
            {
                id: 'trigger-master_panel_navigation',
                xtype: 'treepanel',
                region: 'west',
                split: 'true',
                width: 275,
                height: 500,
                autoScroll: true,
                rootVisible: false,
                selModel: navSelectionModel,
                layout: 'fit',
                bodyStyle: { 'margin-top' : 10 },
                listeners: {
                    render: function(f){
                        f.getView().getSelectionModel().select(0);
                        if(Zenoss.SELENIUM){
                            Ext.defer(function(){
                                var nodes = f.getView().getNodes();
                                Ext.each(nodes, function(item, index) {
                                    item.id = "trigger_tree_tr_"+index;
                                    Ext.get(item.id).query('div')[0].id = 'trigger_tree_tr_div_'+index;
                                });
                            }, 1000);
                         }
                    }
                },
                store: masterPanelTreeStore
            }
        ]
    };

    var prod_state_rule = Ext.applyIf({
        text: _t('Device Production State'),
        value: 'dev.production_state'
        },
        ZFR.PRODUCTIONSTATE
    );
    var dev_priority_rule = Ext.applyIf(
        {
        text: _t('Device Priority'),
        value: 'dev.priority'
        },
        ZFR.DEVICEPRIORITY
    );

    var trigger_tab_subjects = [
        dev_priority_rule,
        prod_state_rule,
        {
            text: _t('Device (Element)'),
            value: 'elem.name',
            comparisons: STRINGCMPS
        },{
            text: _t('Component (Sub-Element)'),
            value: 'sub_elem.name',
            comparisons: STRINGCMPS
        },{
            text: _t('Element Type'),
            value: 'elem.type',
            comparisons: ZFR.IDENTITYCOMPARISONS,
            field: {
                xtype: 'combo',
                queryMode: 'local',
                valueField: 'name',
                displayField: 'name',
                typeAhead: false,
                forceSelection: true,
                triggerAction: 'all',
                listConfig: {
                    maxWidth:200
                },
                store: new Ext.data.ArrayStore({
                    model: 'Zenoss.model.Name',
                    data: [[
                        'COMPONENT'
                    ],[
                        'DEVICE'
                    ],[
                        'SERVICE'
                    ],[
                        'ORGANIZER'
                    ]]
                })
            }
        },{
            text: _t('Sub Element Type'),
            value: 'sub_elem.type',
            comparisons: ZFR.IDENTITYCOMPARISONS,
            field: {
                xtype: 'combo',
                queryMode: 'local',
                valueField: 'name',
                displayField: 'name',
                typeAhead: false,
                forceSelection: true,
                triggerAction: 'all',
                listConfig: {
                    maxWidth:200
                },
                store: new Ext.data.ArrayStore({
                    model: 'Zenoss.model.Name',
                    data: [[
                        'COMPONENT'
                    ],[
                        'DEVICE'
                    ],[
                        'SERVICE'
                    ],[
                        'ORGANIZER'
                    ]]
                })
            }
        }, {
            text: _t('Event Class'),
            value: 'evt.event_class',
            comparisons: STRINGCMPS,
            field: {
                xtype: 'eventclass'
            }
        },{
            text: _t('Event Key'),
            value: 'evt.event_key',
            comparisons: STRINGCMPS
        },{
            text: _t('Summary'),
            value: 'evt.summary',
            comparisons: STRINGCMPS
        },{
            text: _t('Message'),
            value: 'evt.message',
            comparisons: STRINGCMPS
        },{
            text: _t('Severity'),
            value: 'evt.severity',
            comparisons: NUMCMPS,
            field: {
                xtype: 'combo',
                queryMode: 'local',
                valueField: 'value',
                displayField: 'name',
                typeAhead: false,
                forceSelection: true,
                triggerAction: 'all',
                listConfig: {
                    maxWidth:200
                },
                store: new Ext.data.ArrayStore({
                    model: 'Zenoss.model.NameValue',
                    data: [[
                        _t('Critical'), 5
                    ],[
                        _t('Error'), 4
                    ],[
                        _t('Warning'), 3
                    ],[
                        _t('Info'), 2
                    ],[
                        _t('Debug'), 1
                    ],[
                        _t('Clear'), 0
                    ]]
                })
            }
        },{
            text: _t('Fingerprint'),
            value: 'evt.fingerprint',
            comparisons: STRINGCMPS
        },{
            text: _t('Agent'),
            value: 'evt.agent',
            comparisons: STRINGCMPS
        },{
            text: _t('Monitor'),
            value: 'evt.monitor',
            comparisons: STRINGCMPS
        },{
            text: _t('Count'),
            value: 'evt.count',
            comparisons: NUMCMPS,
            field: {
                xtype: 'numberfield'
            }
        },{
            text: _t('Status'),
            value: 'evt.status',
            comparisons: NUMCMPS,
            field: {
                xtype: 'combo',
                queryMode: 'local',
                valueField: 'value',
                displayField: 'name',
                typeAhead: false,
                forceSelection: true,
                triggerAction: 'all',
                listConfig: {
                    maxWidth:200
                },
                store: new Ext.data.ArrayStore({
                    model: 'Zenoss.model.NameValue',
                    data: [[
                        _t('New'), Zenoss.STATUS_NEW
                    ],[
                        _t('Acknowledged'), Zenoss.STATUS_ACKNOWLEDGED
                    ],[
                        _t('Suppressed'), Zenoss.STATUS_SUPPRESSED
                    ]]
                })
            }
        },{
            text: _t('Event Class Key'),
            value: 'evt.event_class_key',
            comparisons: STRINGCMPS
        },{
            text: _t('Syslog Priority'),
            value: 'evt.syslog_priority',
            comparisons: NUMCMPS,
            field: {
                xtype: 'combo',
                queryMode: 'local',
                valueField: 'value',
                displayField: 'name',
                typeAhead: false,
                forceSelection: true,
                triggerAction: 'all',
                listConfig: {
                    maxWidth:200
                },
                store: new Ext.data.ArrayStore({
                    model: 'Zenoss.model.NameValue',
                    data: [[
                        _t('Emergency'), 0
                    ],[
                        _t('Alert'), 1
                    ],[
                        _t('Critical'), 2
                    ],[
                        _t('Error'), 3
                    ],[
                        _t('Warning'), 4
                    ],[
                        _t('Notice'), 5
                    ],[
                        _t('Info'), 6
                    ],[
                        _t('Debug'), 7
                    ]]
                })
            }
        },{
            text: _t('Location'),
            value: 'dev.location',
            comparisons: STRINGCMPS
        },
        ZFR.DEVICECLASS,
        {
            text: _t('Syslog Facility'),
            value: 'evt.syslog_facility',
            comparisons: NUMCMPS,
            field: {
                xtype: 'numberfield'
            }
        },{
            text: _t('NT Event Code'),
            value: 'evt.nt_event_code',
            comparisons: NUMCMPS,
            field: {
                xtype: 'numberfield'
            }
        },{
            text: _t('IP Address'),
            value: 'dev.ip_address',
            comparisons: STRINGCMPS
        },
        ZFR.SYSTEMS,
        ZFR.DEVICEGROUPS,
        {
            text: _t('Owner'),
            value: 'evt.current_user_name',
            comparisons: STRINGCMPS
        }
    ];

    // Details added by zenpacks. Replace '.'' for '_' (if any). zep will do the same
    // when evaluating the trigger. We also add a prefix. When zep creates the trigger context
    // will have to create a dict whose name matches Zenoss.env.ZP_DETAILS_TRIGGER_PREFIX
    zp_details = Zenoss.env.ZP_DETAILS;
    Ext.each(zp_details,
                function(detail){
                        detail.value =  Zenoss.env.ZP_DETAILS_TRIGGER_PREFIX + '.' + detail.value.split(".").join("_");
                }
    );

    trigger_tab_subjects = trigger_tab_subjects.concat(zp_details);

    var trigger_tab_content = {
        xtype:'panel',
        ref: '../../tab_content',
        height: bigWindowHeight-110,
        autoScroll: true,
        width: bigWindowWidth+225,

        // make firefox draw correctly.
        minWidth: bigWindowWidth+225,
        boxMinWidth: bigWindowWidth+225,
        layout: 'anchor',
        title: _t('Trigger'),
        listeners: {
            render: function(){
                if(Zenoss.SELENIUM){
                    Ext.getDom(this.tab.btnEl.id).id = "trigger_tab_button";
                    Ext.getDom(this.tab.tabBar.items.items[1].btnEl.id).id = "users_tab_button";
                }
            }
        },
        padding: 10,
        fieldDefaults: {
            labelWidth: 75
        },
        items:[
            {
                xtype: 'hidden',
                name: 'uuid',
                ref: 'uuid'
            },{
                xtype: 'textfield',
                name: 'name',
                ref: 'name',
                id: 'trigger_tab_content_name_textfield',
                allowBlank: false,
                fieldLabel: _t('Name')
            },{
                xtype: 'checkbox',
                name: 'enabled',
                ref: 'enabled',
                id: 'trigger_tab_content_enabled_checkbox',
                fieldLabel: _t('Enabled')
            },{
                xtype: 'rulebuilder',
                fieldLabel: _t('Rule'),
                labelWidth: 96,
                margin:'0 0 0 5px',
                name: 'criteria',
                ref: 'rule',
                id: 'triggerRule',
                subjects: trigger_tab_subjects
            }
        ]
    };

    var trigger_tab_users = {
        xtype: 'panel',
        ref: '../../tab_users',
        id: 'users_rule',
        title: _t('Users'),
        autoScroll: true,
        height: bigWindowHeight-110,
        items: [
            {
                xtype: 'panel',
                title: _t('Local Trigger Permissions'),
                items: [
                    {
                        xtype:'checkbox',
                        name: 'trigger_globalRead',
                        ref: '../globalRead',
                        boxLabel: _t('Everyone can view'),
                        hideLabel: true
                    },
                    {
                        xtype:'checkbox',
                        name: 'trigger_globalWrite',
                        ref: '../globalWrite',
                        boxLabel: _t('Everyone can edit content'),
                        hideLabel: true
                    },
                    {
                        xtype:'checkbox',
                        name: 'trigger_globalManage',
                        ref: '../globalManage',
                        boxLabel: _t('Everyone can manage users'),
                        hideLabel: true
                    }
                ]
            },{
                xtype: 'usersPermissionGrid',
                ref: 'users_grid',
                title: _t('Users'),
                allowManualEntry: false
            }
        ]
    };


    Ext.define("Zenoss.trigger.EditTriggerDialogue", {
        alias:['widget.edittriggerdialogue'],
        extend:"Zenoss.dialog.BaseWindow",
        constructor: function(config) {
            config = config || {};

            Ext.applyIf(config, {
                plain: true,
                cls: 'white-background-panel',
                autoScroll: false,
                constrain: true,
                resizable: true,
                modal: true,
                height: bigWindowHeight,
                width: bigWindowWidth+235,
                boxMaxWidth: bigWindowWidth+235, // for chrome, safari
                closeAction: 'hide',
                layout: 'fit',
                listeners: {
                    hide: function() {
                        // This makes sure the DOM elements for the clauses are destroyed to prevent
                        // confusion when the window is reopened (because this is a closeAction:'hide'
                        // instead of 'destroy'
                        this.removeAll();
                    },
                    scope: this
                },
                items: [
                    {
                        xtype:'form',
                        ref: 'wrapping_form',
                        buttonAlign: 'left',
                        layout: 'fit',
                        listeners: {
                            validitychange: function(form, isValid) {
                                this.query('DialogButton')[0].setDisabled(!isValid);
                            },
                            scope: this
                        },
                        items: [
                            {
                                xtype: 'tabpanel',
                                ref: '../tabs',
                                activeTab: 0,
                                activeIndex: 0,
                                defaults: {
                                    height: bigWindowHeight,
                                    width: bigWindowWidth+225,
                                    autoScroll: true,
                                    frame: false
                                },
                                items: [
                                    trigger_tab_content,
                                    trigger_tab_users
                                ]
                            }
                        ],
                        buttons:[
                            {
                                xtype: 'DialogButton',
                                text: _t('Submit'),
                                ref: '../../submitButton',
                                id: 'edit_trigger_submit_button',
                                handler: function(button) {
                                    var tab_content = button.refOwner.tab_content,
                                        tab_users = button.refOwner.tab_users;

                                    var params = {
                                        uuid: tab_content.uuid.getValue(),
                                        enabled: tab_content.enabled.getValue(),
                                        name: tab_content.name.getValue(),
                                        rule: {
                                            source: tab_content.rule.getValue()
                                        },

                                        // tab_users
                                        globalRead: tab_users.globalRead.getValue(),
                                        globalWrite: tab_users.globalWrite.getValue(),
                                        globalManage: tab_users.globalManage.getValue(),

                                        users: []
                                    };

                                    Ext.each(
                                        tab_users.users_grid.getStore().getRange(),
                                        function(item){
                                            params.users.push(item.data);
                                        }
                                    );

                                    config.directFn(params, function(){
                                        reloadTriggersGrid();
                                    });
                                }
                            },{
                                xtype: 'DialogButton',
                                ref: '../../cancelButton',
                                text: _t('Cancel'),
                                id: 'edit_trigger_cancel_button',
                                handler: function(button) {
                                    button.refOwner.hide();
                                }
                            }
                        ]
                    }
                ]
            });
            this.callParent([config]);
        },
        loadData: function(data) {
            // set content stuff.
            this.tab_content.uuid.setValue(data.uuid);
            this.tab_content.enabled.setValue(data.enabled);
            this.tab_content.name.setValue(data.name);
            this.tab_content.rule.setValue(data.rule.source);

            // set users information (permissions and such)
            this.tab_users.globalRead.setValue(data.globalRead);
            this.tab_users.globalWrite.setValue(data.globalWrite);
            this.tab_users.globalManage.setValue(data.globalManage);


            this.tab_users.users_grid.getStore().loadData(data.users);

        }
    });



    reloadTriggersGrid = function() {
        Ext.getCmp(triggersPanelConfig.id).getStore().load();
    };

    displayEditTriggerDialogue = function(data) {

        editTriggerDialogue = Ext.create('Zenoss.trigger.EditTriggerDialogue', {
            title: Ext.String.format("{0} - {1}", _t('Edit Trigger'), data['name']),
            directFn: router.updateTrigger,
            reloadFn: reloadTriggersGrid,
            validateFn: router.parseFilter
        });

        editTriggerDialogue.loadData(data);
        editTriggerDialogue.show();

        if (!data['userWrite']) {
            disableTabContents(editTriggerDialogue.tab_content);
        } else {
            enableTabContents(editTriggerDialogue.tab_content);
        }

        if (!data['userManage']) {
            disableTabContents(editTriggerDialogue.tab_users);
        } else {
            enableTabContents(editTriggerDialogue.tab_users);
        }

    };

    addTriggerDialogue = Ext.create('Zenoss.trigger.AddDialogue', {
        title: _t('Add Trigger'),
        id:'triggeradd',
        directFn: router.addTrigger,
        reloadFn: reloadTriggersGrid
    });

    Ext.getCmp('center_panel').add({
        id: 'center_panel_container',
        layout: 'border',
        defaults: {
            'border':false
        },
        items: [
            masterPanelConfig,  // navigation
            detailPanelConfig   // content panel
        ]
    });

});
