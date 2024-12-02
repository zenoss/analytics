/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

Ext.onReady(function(){
    Ext.ns('Zenoss.eventclasses');

   Ext.define('Zenoss.sequencegrid.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: [
            {name: 'id'},
            {name: 'uid'},
            {name: 'eventClass'},
            {name: 'sequence'},
            {name: 'eventClassKey'},
            {name: 'eval'}
        ]
    });

    Ext.define("Zenoss.sequencegrid.Store", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.sequencegrid.Model',
                remoteSort: true,
                initialSortColumn: 'sequence',
                lockedOrder: 'asc',
                directFn: Zenoss.remote.EventClassesRouter.getSequence,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.sequencegrid.SequenceGrid", {
        alias: ['widget.sequencegrid'],
        extend:"Zenoss.BaseGridPanel",
        constructor: function(config) {
            config = config || {};
            var me = this;
            Ext.applyIf(config, {
                stateId: 'mapping_sequence_grid',
                id: 'mapping_sequence_grid',
                sm: Ext.create('Zenoss.SingleRowSelectionModel', {}),
                stateful: true,
                store: Ext.create('Zenoss.sequencegrid.Store', {}),
                enableDragDrop: true,
                ddGroup: 'sequencegriddd',
                viewConfig: {
                    forcefit: true,
                    markDirty:false,
                    plugins: {
                        ptype: 'gridviewdragdrop',
                        dragGroup: 'sequencegriddd',
                        dropGroup: 'sequencegriddd'
                    },
                    listeners: {
                        /**
                         * Updates the graph order when the user drags and drops them
                         **/
                        drop: function() {
                            var records = me.store.getRange();
                            var uids = Ext.pluck(Ext.pluck(records, 'data'), 'uid');
                            Zenoss.remote.EventClassesRouter.resequence({'uids':uids}, function(response){
                                if (response.success) {
                                    // redraw the sequences cells with the new numbers:
                                    Zenoss.message.info(_t('Saved new sequence.'));
                                    me.getSelectionModel().deselectAll();
                                    for (var i = 0; records.length > i; i++){
                                        records[i].set("sequence", i);
                                        if(records[i].get("uid") === Ext.getCmp('mappingDialog').contextUid){
                                            Ext.getCmp('sequence_text_id').setText('Sequence: '+i);
                                        }
                                    }
                                }
                            });
                        }
                    }
                },
                columns: [{
                        header: _t('Seq'),
                        id: 'seq_seq_id',
                        dataIndex: 'sequence',
                        width: 30,
                        sortable: false
                    },{
                        header: _t('ID'),
                        id: 'map_seq_id',
                        dataIndex: 'id',
                        renderer: function(value, metaData, record){
                            if(record.get("uid") === Ext.getCmp('mappingDialog').contextUid){
                                return '<b>* '+value+'</b>';
                            }
                            return value;
                        },
                        flex: 1,
                        sortable: false
                    },{
                        header: _t("Event Class"),
                        id: 'class_seq_id',
                        dataIndex: 'eventClass',
                        width: 200,
                        sortable: false
                    },{
                        header: _t("EventClass Key"),
                        id: 'key_seq_id',
                        dataIndex: 'eventClassKey',
                        flex: 1,
                        sortable: false
                    },{
                        header: _t("Evaluation"),
                        id: 'eval_seq_id',
                        dataIndex: 'eval',
                        flex: 1,
                        sortable: false
                    }]
            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            this.uid = uid;
            // load the grid's store
            this.callParent(arguments);
        }
    });


// ----------------------------------------------------------------- DIALOGS
    Zenoss.eventclasses.mappingDialog = function(grid, data) {
        if(!Ext.isDefined(data)) {
            data = "";
        }
        var addhandler, config, dialog, newEntry;
        newEntry = (data === "");
        var xtraData = {};
        addhandler = function() {
            var c = dialog.getForm().getForm().getValues();
            var save_xform = Ext.getCmp('xform_mapping_panel').getLastInChainValue() !== false ? Ext.getCmp('xform_mapping_panel').getLastInChainValue() : xtraData.transform;
            var params = {
                evclass:                Zenoss.env.contextUid,
                uid:                    xtraData.uid,
                instanceName:           c.instanceName,
                newName:                c.name, // if they change the name of this mapping
                eventClassKey:          c.eventclasskey,
                example:                Ext.getCmp('example_panel').getValue(),
                explanation:            Ext.getCmp('explanation_panel').getValue(),
                regex:                  Ext.getCmp('regex_panel').getValue(),
                rule:                   Ext.getCmp('rule_panel').getValue(),
                resolution:             Ext.getCmp('resolution_panel').getValue(),
                transform:              save_xform
            };
            var isTrans = (save_xform !== "");
            if(newEntry){
                Zenoss.remote.EventClassesRouter.addNewInstance({'params':params}, function(response){
                    if (response.success) {
                        // get the uid from the created instance so we can
                        // save the properties
                        params.uid = response.data.uid;
                        Zenoss.remote.EventClassesRouter.editInstance({'params':params}, function(response){
                            if (response.success) {
                                Ext.getCmp('classes').setTransIcon(isTrans);
                            }
                        });
                    }
                });
            }else{
                Zenoss.remote.EventClassesRouter.editInstance({'params':params}, function(response){
                    if (response.success) {
                        if(grid){
                            Ext.getCmp('classes').setTransIcon(isTrans);
                        }
                    }
                });
            }
        };

        // form config
        config = {
            submitHandler: addhandler,
            height:Ext.getBody().getViewSize().height,
            width:Ext.getBody().getViewSize().width*0.8, //80%
            id: 'mappingDialog',
            contextUid: null,
            title: _t("Add New Event Class Mapping"),
            listeners: {
                'hide': function(){
                    if (grid) {
                        grid.refresh();
                    }
                },
                'close':function(){
                    if (grid) {
                        grid.refresh();
                    }
                },
                'afterrender': function(e){
                    if(!newEntry){
                        // this window will be used to EDIT the values instead of create from scratch
                        // grab extra data from server to populate code boxes:

                       Zenoss.remote.EventClassesRouter.getInstanceData({'uid':data.uid}, function(response){
                            if(response.success){
                                xtraData = response.data[0];
                                Ext.getCmp('mappingDialog').contextUid = xtraData.uid;
                                var titleloc = xtraData.uid.split('/instances').join('').substring(10);
                                e.setTitle(_t("Edit Event Class Mapping")+" for: "+titleloc);
                                var fields = e.getForm().getForm().getFields();
                                Ext.getCmp('sequence_text_id').setText('Sequence: '+xtraData.sequence);
                                fields.findBy(
                                    function(record){
                                        switch(record.getName()){
                                            case "name"             : record.setValue(xtraData.id);  break;
                                            case "instanceName"     : record.setValue(xtraData.id);  break;
                                            case "eventclasskey"    : record.setValue(xtraData.eventClassKey);  break;
                                            case "rule_panel"       :
                                                record.setValue(xtraData.rule);
                                                // collapse or expand this panel depending on "" content
                                                if(xtraData.rule !== "") {
                                                    record.ownerCt.toggleCollapse();
                                                }
                                                break;
                                            case "regex_panel"      :
                                                record.setValue(xtraData.regex);
                                                // collapse or expand this panel depending on "" content
                                                if(xtraData.regex !== "") {
                                                    record.ownerCt.toggleCollapse();
                                                }
                                                break;
                                            case "example_panel"    : record.setValue(xtraData.example); break;
                                            //case "transform_panel"  : record.setValue(xtraData.transform); break;
                                            case "explanation_panel": record.setValue(xtraData.evaluation); break;
                                            case "resolution_panel" : record.setValue(xtraData.resolution); break;
                                        }
                                    }
                                );
                            }
                        });
                    }
                }
            },
            items: [
                {
                    xtype: 'label',
                    name: 'sequence',
                    id: 'sequence_text_id',
                    style: 'color:white;padding:5px 5px 3px 5px;position:absolute;top:-16px;left:600px;',
                    margin: '13 0 0 0',
                    width:100
                },{
                    xtype: 'tabpanel',
                    id: 'blackTabs',
                    listeners: {
                        'afterrender': function(p){
                            if(data.whichPanel === 'sequence'){
                                p.setActiveTab(3);
                            }
                        }
                    },
                    bodyStyle: {
                        padding: '10 0 10 0'
                    },
                        items: [
                            {
                                title: 'Matching',
                                items:[
                                {
                                    xtype: 'panel',
                                    layout: 'hbox',
                                    margin: '0 0 30px 0',
                                    items: [
                                        {
                                            xtype: 'textfield',
                                            name: 'name',
                                            fieldLabel: _t('Instance Name'),
                                            margin: '0 10px 0 0',
                                            width:320,
                                            regex: Zenoss.env.textMasks.allowedNameTextDashDot,
                                            regexText: Zenoss.env.textMasks.allowedNameTextFeedbackDashDot,
                                            allowBlank: false
                                        },{
                                            xtype: 'hidden',
                                            name: 'instanceName'
                                        },{
                                            xtype: 'textfield',
                                            name: 'eventclasskey',
                                            margin: '0 40px 0 0',
                                            fieldLabel: _t('Event Class Key'),
                                            regex: Zenoss.env.textMasks.allowedNameTextDashDot,
                                            regexText: Zenoss.env.textMasks.allowedNameTextFeedbackDashDot,
                                            width:320
                                        }
                                    ]

                                },{
                                    xtype: 'panel',
                                    items:[
                                        {
                                            xtype: 'minieditorpanel',
                                            title: 'Example',
                                            id: 'example_panel',
                                            name: 'example_panel',
                                            margin: '0 20 20 0'
                                        },{
                                            xtype: 'minieditorpanel',
                                            name: 'rule_panel',
                                            id: 'rule_panel',
                                            margin: '0 20 20 0',
                                            title: 'Rule (Single line Python Expression)',
                                            tools:[{
                                                type: 'save',
                                                tooltip: 'Test this Rule',
                                                handler:  function(event, html, button){
                                                    var value = button.ownerCt.items.items[0].getValue();
                                                    Zenoss.remote.EventClassesRouter.testRule({'rule':value}, function(response){
                                                        if(response.success){
                                                            Zenoss.message.info(_t('Rule compiles without error'));
                                                        }
                                                    });
                                                }
                                            }],
                                            collapsed: true,
                                            listeners:{
                                                expand: function(){
                                                    var regex_panel = Ext.getCmp('regex_panel');
                                                    if(regex_panel.getValue() !== ""){
                                                        Ext.getCmp('rule_panel').collapse();
                                                        new Zenoss.dialog.SimpleMessageDialog({
                                                            title: _t('Regex panel is not empty'),
                                                            message: _t("Please clear the regex panel to continue. You cannot have both a rule and a regex at the same time."),
                                                            buttons: [{
                                                                xtype: 'DialogButton',
                                                                text: _t('OK')
                                                            }]
                                                        }).show();
                                                    }else{
                                                        regex_panel.collapse();
                                                    }
                                                }
                                            }
                                        },
                                        {
                                            xtype: 'minieditorpanel',
                                            name: 'regex_panel',
                                            id: 'regex_panel',
                                            title: 'Regex (Can only have a rule, or regex, not both)',
                                            tools:[{
                                                type: 'save',
                                                tooltip: 'Test this Regex',
                                                handler:  function(event, html, button){
                                                    var value = button.ownerCt.items.items[0].getValue();
                                                    var ex = Ext.getCmp('example_panel').items.items[0].getValue();
                                                    Zenoss.remote.EventClassesRouter.testRegex({'regex':value, 'example':ex}, function(response){
                                                        if(response.success){
                                                            Zenoss.message.info(_t('Regex works with example'));
                                                        }
                                                    });
                                                }
                                            }],
                                            margin: '0 20 20 0',
                                            collapsed: true,
                                            listeners:{
                                                expand: function(){
                                                    var rule_panel = Ext.getCmp('rule_panel');
                                                    if(rule_panel.getValue() !== ""){
                                                        Ext.getCmp('regex_panel').collapse();
                                                        new Zenoss.dialog.SimpleMessageDialog({
                                                            title: _t('Rule panel is not empty'),
                                                            message: _t("Please clear the rule panel to continue. You cannot have both a rule and a regex at the same time."),
                                                            buttons: [{
                                                                xtype: 'DialogButton',
                                                                text: _t('OK')
                                                                }]
                                                        }).show();
                                                    }else{
                                                        rule_panel.collapse();
                                                    }
                                                }
                                            }
                                        },{
                                            xtype: 'minieditorpanel',
                                            title: 'Explanation',
                                            name: 'explanation_panel',
                                            id: 'explanation_panel',
                                            margin: '0 20 20 0'
                                        },{
                                            xtype: 'minieditorpanel',
                                            title: 'Resolution',
                                            name: 'resolution_panel',
                                            id: 'resolution_panel',
                                            margin: '0 20 20 0'
                                        }
                                    ]
                                } ]
                              },{
                                title:'Transforms',
                                hidden: newEntry,
                                items:[
                                    {
                                        xtype: 'xformmasterpanel',
                                        id: 'xform_mapping_panel',
                                        autoScroll: false,
                                        listeners: {
                                            beforerender: function(g){
                                                g.setContext(data.uid);
                                            }
                                        }
                                    }
                                ]
                              },{
                                title:'Configuration Properties',
                                hidden: newEntry,
                                items:[
                                    {
                                        xtype: 'configpropertypanel',
                                        style: 'background: #fff',
                                        listeners: {
                                            beforerender: function(g){
                                                g.setHeight(Ext.getCmp('mappingDialog').height-150);
                                                g.setContext(data.uid);
                                            }
                                        }
                                    }
                                ]
                              },{
                                title: 'Sequence',
                                hidden: newEntry,
                                items:[
                                    {
                                        xtype: 'sequencegrid',
                                        listeners: {
                                            beforerender: function(g){
                                                g.setContext(data.uid);
                                            }
                                        }
                                    }
                                ]
                              }
                            ]

                }
            ],
            // explicitly do not allow enter to submit the dialog
            keys: {}
        };


        if (Zenoss.Security.hasPermission('Manage Device')) {
            dialog = new Zenoss.SmartFormDialog(config);
            dialog.show();
        }else{ return false; }
    };    // end edit mapping dialog

   Ext.define('Zenoss.classesgrid.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: [
            {name: 'hasTransform'},
            {name: 'id'},
            {name: 'uid'},
            {name: 'eventClassKey'},
            {name: 'eval'}
        ]
    });

    Ext.define("Zenoss.classesgrid.Store", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.classesgrid.Model',
                initialSortColumn: "id",
                directFn: Zenoss.remote.EventClassesRouter.getInstances,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.eventclasses.ClassesGrid", {
        alias: ['widget.classesgrid'],
        extend:"Zenoss.FilterGridPanel",
        constructor: function(config) {
            config = config || {};
            var me = this;
            Ext.applyIf(config, {
                stateId: 'classes_mapping_grid',
                id: 'classes_mapping_grid',
                stateful: false,
                multiSelect: true,
                dockedItems:[
                    {
                        xtype: 'largetoolbar',
                        id: 'mapping_toolbar',
                        itemId: 'mapping_toolbar',
                        dock: 'top',
                        height: 45,
                        disabled: true,
                        items: [
                            {
                                xtype: 'button',
                                iconCls: 'add',
                                hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                                tooltip: _t('Add new Event Class Mapping Instance'),
                                handler: function() {
                                    var grid = Ext.getCmp("classesgrid_id");
                                    Zenoss.eventclasses.mappingDialog(grid);
                                }
                            },{
                                xtype: 'button',
                                iconCls: 'delete',
                                hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                                tooltip: _t('Delete selected items'),
                                handler: function() {
                                    var grid = Ext.getCmp("classesgrid_id"),
                                        data = [],
                                        selected = grid.getSelectionModel().getSelection();
                                    if (Ext.isEmpty(selected)) {
                                        return;
                                    }
                                    for (var i=0; selected.length > i; i++){
                                        data.push({'context':selected[i].data.uid.split('/instances/')[0], 'id':selected[i].data.id});
                                    }
                                    new Zenoss.dialog.SimpleMessageDialog({
                                        title: _t('Delete Instance'),
                                        message: _t("Are you sure you want to delete the selected instances?"),
                                        buttons: [{
                                            xtype: 'DialogButton',
                                            text: _t('OK'),
                                            handler: function() {
                                                Zenoss.remote.EventClassesRouter.removeInstance({'instances':data}, function(response){
                                                    if (response.success) {
                                                        grid.refresh();
                                                        var bar = Ext.getCmp('mapping_toolbar');
                                                        bar.items.items[2].setDisabled(false);
                                                        bar.items.items[3].setDisabled(false);
                                                    }
                                                });
                                            }
                                        }, {
                                            xtype: 'DialogButton',
                                            text: _t('Cancel')
                                        }]
                                    }).show();
                                }
                            },{
                                xtype: 'button',
                                iconCls: 'customize',
                                tooltip: _t('View and/or Edit selected Event Class Mapping Instance'),
                                handler: function() {
                                    var grid = Ext.getCmp("classesgrid_id"),
                                        data,
                                        selected = grid.getSelectionModel().getSelection();

                                    if (Ext.isEmpty(selected)) {
                                        return;
                                    }
                                    // single selection
                                    data = selected[0].data;
                                    data.whichPanel = 'default';
                                    Zenoss.eventclasses.mappingDialog(grid, data);
                                }
                            },{
                                xtype: 'button',
                                iconCls: 'set',
                                hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                                tooltip: _t('Use a drag-drop grid to resequence the weights of Instance Maps'),
                                handler: function() {
                                    var grid = Ext.getCmp("classesgrid_id");
                                    var data, selected = grid.getSelectionModel().getSelection();
                                    if (!selected[0]) {
                                        return;
                                    }
                                    data = selected[0].data;
                                    data.whichPanel = 'sequence';
                                    Zenoss.eventclasses.mappingDialog(grid, data);
                                }
                            }, {
                                iconCls: 'adddevice',
                                xtype: 'button',
                                tooptip: _t('Add To ZenPack'),
                                hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                                handler: function() {
                                    var addtozenpack = new Zenoss.AddToZenPackWindow(),
                                        records = me.getSelectionModel().getSelection();
                                    if (records.length) {
                                        var targets = Ext.Array.pluck(Ext.Array.pluck(records, "data"), "uid");
                                        addtozenpack.setTarget(targets);
                                        addtozenpack.show();
                                    }
                                }
                            }]
                        }
                ],
                store: Ext.create('Zenoss.classesgrid.Store', {}),
                listeners: {
                    afterrender: function(e){
                        e.getStore().on('load', function(){
                            Ext.getCmp('mapping_toolbar').setDisabled(false);
                        });
                    },
                    select: function(e){
                            var bar = Ext.getCmp('mapping_toolbar');
                        if(e.getCount() > 1){
                            bar.items.items[2].setDisabled(true);
                            bar.items.items[3].setDisabled(true);
                        }else{
                            bar.items.items[2].setDisabled(false);
                            bar.items.items[3].setDisabled(false);
                        }
                    }
                },
                columns: [
                    {
                        header: _t('xForm'),
                        id: 'xForm',
                        dataIndex: 'hasTransform',
                        width:45,
                        sortable: true,
                        renderer: function(value){
                            var cls = (Ext.isIE) ? 'ie_xforms_grid': 'xforms_grid';
                            if(value){
                                return '<span class="'+cls+'"><img src="/++resource++zenui/img/xtheme-zenoss/icon/is-transform.png" />&nbsp;</span>';
                            }
                            return '<span class="'+cls+'"><img src="/++resource++zenui/img/xtheme-zenoss/icon/no-transform.png" />&nbsp;</span>';
                        },
                        filter:false
                    },{
                        header: _t('ID'),
                        id: 'map_id',
                        dataIndex: 'id',
                        flex: 1,
                        sortable: true,
                        filter: true
                    },{
                        header: _t("EventClass Key"),
                        id: 'key_id',
                        dataIndex: 'eventClassKey',
                        width: 200,
                        sortable: true,
                        filter: true
                    },{
                        header: _t("Explanation"),
                        id: 'eval_id',
                        dataIndex: 'eval',
                        flex: 1,
                        sortable: true,
                        filter: false
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
            data.whichPanel = 'default';
            Zenoss.eventclasses.mappingDialog(this, data);
        }
    });


    Ext.define('Zenoss.eventclasses.CodeEditorField', {
        extend: 'Ext.form.field.TextArea',
        alias: 'widget.codeeditorfield',
        cls: 'codemirror-field',
        originalValue: "",
        initComponent: function() {
            var me = this;
            Ext.applyIf(me, {
                listeners: {
                    render: {
                        fn: me.onCodeeditorfieldRender,
                        scope: me
                    }
                }
            });
            this.callParent(arguments);
        },
        onCodeeditorfieldRender: function(abstractcomponent) {
            var me = this;
            var element = document.getElementById(abstractcomponent.getInputId());
            this.editor = CodeMirror.fromTextArea(element, {'lineNumbers':true});
            this.editor.on('cursorActivity', function(){
                if (me.getValue() !== me.originalValue){
                    me.ownerCt.getDockedItems()[0].addCls('edited_feedback');
                }else{
                    me.ownerCt.getDockedItems()[0].removeCls('edited_feedback');
                }
            });
        },
        focus: function() {
            this.editor.focus();
        },
        onFocus: function() {
            this.fireEvent('focus', this);
        },
        destroy: function() {
            this.editor.toTextArea();
            this.callParent(arguments);
        },
        getValue: function() {
            this.editor.save();
            return this.callParent(arguments);
        },
        setValue: function(value) {
            if (this.editor) {
                this.editor.setValue(value);
                this.originalValue = value;
                this.ownerCt.getDockedItems()[0].removeCls('edited_feedback');
            }
            return this.callParent(arguments);
        }
    });

    Ext.define('Zenoss.eventclasses.MiniEditorPanel', {
        extend: 'Ext.panel.Panel',
        alias: 'widget.minieditorpanel',
        layout: {
            type: 'fit'
        },
        collapsible: true,
        titleCollapse: true,
        resizable: {
            handles: 's',
            pinned: true
        },
        height:200,
        style: 'background:white',
        initComponent: function() {
            var me = this;
            Ext.applyIf(me, {
                items: [
                    {
                        xtype: 'codeeditorfield',
                        name: me.name
                    }
                ]
            });

            this.callParent(arguments);
        },
        focus: function() {
            this.down('codeeditorfield').focus();
        },
        getValue: function() {
            return this.down('codeeditorfield').getValue();
        },
        setValue: function(value) {
            this.down('codeeditorfield').setValue(value);
        },
        reset: function() {
            this.down('codeeditorfield').setValue('');
        }
    });

    Ext.define('Zenoss.eventclass.XformMasterPanel', {
        extend: 'Ext.panel.Panel',
        alias: 'widget.xformmasterpanel',
        autoScroll: true,
        initComponent: function() {
            this.callParent(arguments);
        },
        getLastInChainValue: function(){
            var items = this.items.items;
            if(items[items.length-1]){
                return items[items.length-1].getValue();
            }else{
                return false;
            }
        },
        setContext: function(uid){
            var me = this;

            Zenoss.remote.EventClassesRouter.getTransformTree({'uid':uid}, function(response){
                if(response.success){
                    var data = response.data;
                    me.removeAll(true);
                    if(data.length > 1){
                        me.add({
                            xtype: 'label',
                            cls: 'transform-headers',
                            text: 'Inherited Transforms: (All Transforms are multi-line Python code)'
                        });
                    }

                    for(var i=0; data.length-1 > i; i++){
                        // add the inheritance chain:
                        me.add({
                                xtype: 'xformeditorpanel',
                                name: 'maintransformseditor'+i,
                                collapsed: true,
                                cls: 'inherited_transforms',
                                listeners:{
                                    afterrender: function(p){
                                        p.setValue(data[i]);
                                    }
                                }
                        });
                    }
                    me.add({
                        xtype: 'label',
                        cls: 'transform-headers',
                        text: 'Current Transform:'
                    });
                    me.add({
                        xtype: 'panel',
                        region:'left',
                        hidden: true,
                        margin: '0 0 5 5',
                        layout: {
                            type: 'hbox',
                            align: 'middle',
                            pack: 'left'
                        },
                        listeners : {
                            beforerender: function(el) {
                                if(Zenoss.Security.doesNotHavePermission('Manage DMD') === false) {
                                    Zenoss.remote.EventClassesRouter.isTransformEnabled({'uid':uid}, function(response){
                                        if(response.success){
                                            if(response.data === false){
                                                el.setVisible(true);
                                            }
                                        }
                                    });
                                }
                            }
                        },
                        items: [{
                            xtype: 'label',
                            text: 'Transformation is currently disabled due to several failed tries to apply it.'
                        },{
                            xtype: 'button',
                            text: 'Re-activate transform',
                            margin: '0 0 0 5',
                            handler : function(el) {
                                if(!el.disabled){
                                    Zenoss.remote.EventClassesRouter.setTransformEnabled({'uid':uid, 'enabled': true}, function(response){
                                         if(response.success){
                                             if(response.data === true){
                                                 Zenoss.message.info(_t('State changed. Transform is now enabled.'));
                                                 var panel = el.findParentByType('panel');
                                                 panel.setVisible(false)
                                             }
                                             else{
                                                 Zenoss.message.info(_t('State not changed. Transform is still disabled. Try again.'));
                                             }
                                         }
                                    });
                                }
                            }
                        }]
                    });
                    // add the current context transform
                    me.add({
                            xtype: 'xformeditorpanel',
                            name: 'maintransformseditor'+(data.length-1),
                            cls: 'main_transform',
                            listeners:{
                                afterrender: function(p){
                                    p.setValue(data[data.length-1]);
                                }
                            }
                    });
                }
            });
        }
    });

    Ext.define('Zenoss.eventclasses.XformEditorPanel', {
        extend: 'Ext.panel.Panel',
        alias: 'widget.xformeditorpanel',
        collapsible: true,
        titleCollapse: true,
        uid: null,
        resizable: {
            handles: 's',
            pinned: true
        },
        autoHeight: true,
        layout: 'fit',
        initComponent: function() {
            var me = this;
            Ext.applyIf(me, {
                tools:[{
                    type: 'save',
                    hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    tooltip: _t('Save and compile this Transform only'),
                    handler:  function(){
                        var value = me.items.items[0].getValue();
                        var uid = me.uid;
                        Zenoss.remote.EventClassesRouter.setTransform({'uid':uid, 'transform':value}, function(response){
                            if(response.success){
                                Zenoss.message.info(_t('One Transform compiled and saved'));
                                var isTrans = (value !== "");
                                Ext.getCmp('classes').setTransIcon(isTrans);
                            }
                        });
                    }
                },{
                    type: 'refresh',
                    tooltip: _t('Reset this Transform back to the last save'),
                    hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler:  function(){
                        var uid = me.uid;
                        Zenoss.remote.EventClassesRouter.getTransform({'uid':uid}, function(response){
                            if(response.success){
                                var str = me.getDefaultString(response.data)
                                me.items.items[0].setValue(str);
                            }
                        });
                    }
                },{
                    type: 'expand',
                    tooltip: _t('Expand all edit boxes on this page'),
                    handler:  function(){
                        // find all boxes on the page:
                        var items = this.ownerCt.ownerCt.ownerCt.items.items;
                        for (var i=0; items.length > i; i++){
                            // swollow when something doesn't have ability to 'expand'
                            try{ items[i].expand(); }catch(e){}
                        }
                    }
                }],
                items: [
                    {
                        xtype: 'codeeditorfield',
                        name: me.name
                    }
                ]
            });

            this.callParent(arguments);
        },
        focus: function() {
            this.down('codeeditorfield').focus();
        },
        getValue: function() {
            return this.down('codeeditorfield').getValue();
        },
        setValue: function(value) {
            this.setTitle(_t("Transform for")+": "+value.transid);
            this.uid = "/zport/dmd"+value.transid;
            var str = this.getDefaultString(value.trans)
            this.down('codeeditorfield').setValue(str);
        },
        reset: function() {
            this.down('codeeditorfield').setValue('');
        },
        getDefaultString: function(str){
            if (str == '') {
               return '\n'.repeat(10);
            }
            return str;
        }
    });

});
