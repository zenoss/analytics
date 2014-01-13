/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

Ext.onReady(function(){
    Ext.ns('Zenoss.manufacturers');

// ----------------------------------------------------------------- DIALOGS

    Zenoss.manufacturers.productsDialog = function(grid, data) {
        var baseid = "";
        var originalManufacturer = "";
        if(typeof(data) === "undefined"){
            data = "";
            baseid = grid.uid ? grid.uid : "";
        }else{
            baseid = data.uid.split("/products/")[0];
        }
        var addhandler, uid, config, dialog, newEntry;
        var labelmargin = '5px 5px 0 0';
        newEntry = (data == "");
        var xtraData = {};
        addhandler = function() {
            var c = dialog.getForm().getForm().getValues(), value;
            var params = {
                uid:                    baseid,
                prodname:               c.name,
                oldname:                c.productname, // if they change the name of this product
                partno:                 c.partNo,
                type:                   c.prodtype,
                prodkeys:               c.keys_panel,
                description:            Ext.getCmp('desc_panel').getValue()
            };
            if (newEntry) {
                Zenoss.remote.ManufacturersRouter.addNewProduct({'params':params}, function(response){
                    if (response.success) {
                        if (grid) {
                            grid.refresh();
                        }
                    }
                });
            } else {
                var mancombo = Ext.getCmp('mansetting');
                Zenoss.remote.ManufacturersRouter.editProduct({'params':params}, function(response){
                    if (response.success) {
                        if (grid) {
                            if(originalManufacturer == mancombo.getValue()){
                                grid.refresh();
                            }
                        }
                    }
                });
                var moveTarget = "/zport/dmd/Manufacturers/"+mancombo.getValue();
                if(originalManufacturer != mancombo.getValue()){
                        var params = {
                            'moveFrom': "/zport/dmd/Manufacturers/"+oldMan,
                            'moveTarget': moveTarget,
                            'ids': [c.name]
                        };
                        Zenoss.remote.ManufacturersRouter.moveProduct(params, function(response){
                            if(response.success) {
                                var tree = Ext.getCmp('manufacturers_tree');
                                tree.refresh();
                                tree.getStore().on('load', function(s){
                                    var nodeId = moveTarget;
                                    var node = tree.getRootNode().findChild("uid", nodeId, true);
                                    tree.getView().select(node);
                                }, this, {single:true});
                            }
                        });
                }

            }
        };

        // form config
        config = {
            submitHandler: addhandler,
            height:Ext.getBody().getViewSize().height,
            width:Ext.getBody().getViewSize().width*0.8, //80%
            id: 'productsDialog',
            contextUid: null,
            title: _t("Add New Product"),
            listeners: {
                'afterrender': function(e){
                    if(!newEntry){
                        // this window will be used to EDIT the values instead of create from scratch
                        // grab extra data from server to populate code boxes:
                       Zenoss.remote.ManufacturersRouter.getProductData({'uid':baseid, 'prodname':data.id}, function(response){
                            if(response.success){
                                xtraData = response.data[0];
                                var instancegrid = Ext.getCmp('instancegrid_id');
                                instancegrid.store.setBaseParam('id', data.id);
                                instancegrid.setContext(baseid);
                                var combo = Ext.getCmp('prodtype');
                                if(data.type == "Hardware"){
                                    combo.store.filter([{
                                        filterFn: function(record) {
                                            return record.get('name') === 'Hardware';
                                        }
                                    }]);
                                }else{
                                    combo.store.filter([{
                                        filterFn: function(record) {
                                            return record.get('name') !== 'Hardware';
                                        }
                                    }]);
                                }
                                Ext.getCmp('productsDialog').contextUid = xtraData.uid;
                                e.setTitle(Ext.String.format(_t("Edit Product Info for: {0}"), data.id));
                                var fields = e.getForm().getForm().getFields();
                                fields.findBy(
                                    function(record, id){
                                        switch(record.getName()){
                                            case "name"             : record.setValue(xtraData.name);  break;
                                            case "productname"      : record.setValue(xtraData.name);  break;
                                            case "partNo"           : record.setValue(xtraData.partno);  break;
                                            case "keys_panel"       : record.setValue(xtraData.prodKeys.toString());  break;
                                            case "desc_panel"       : record.setValue(xtraData.desc);  break;
                                            case "prodtype"         : record.setValue(xtraData.type); break;
                                        }
                                    }
                                );
                            }

                            /*  get list of manufacturers and
                                add them to the combo box
                            */
                                var mancombo = Ext.getCmp('mansetting');
                                originalManufacturer = data.uid.split("/products/")[0].split("/Manufacturers/")[1];
                                var mandata = [];
                                var tree = Ext.getCmp('manufacturers_tree');
                                if (tree){ // if no tree, then dialog is being called from another context
                                    var children = tree.items.items[0].node.childNodes;
                                    for (var i = 0; i < children.length; i++){
                                        mandata.push([children[i].data.text.text]);
                                    }
                                    mancombo.store.loadData(mandata);
                                }else{
                                    Zenoss.remote.ManufacturersRouter.returnTree({'id':'zport/dmd/Manufacturers'}, function(response){
                                        for (var i = 0; i < response.length; i++){
                                            mandata.push([response[i].text.text]);
                                        }
                                        mancombo.store.loadData(mandata);
                                    });
                                }
                                mancombo.setValue(originalManufacturer);
                        });
                    }else{
                            var tree = Ext.getCmp('manufacturers_tree');
                            Ext.getCmp('mansetting').setValue(tree.getSelectionModel().getSelectedNode().data.text.text);
                    }
                }
            },
            items: [
                {
                    xtype: 'tabpanel',
                    id: 'blackTabs',
                    listeners: {
                        'afterrender': function(p){
                            if(data['whichPanel'] == 'configprops'){
                                p.setActiveTab(1);
                            }
                        }
                    },
                    bodyStyle: {
                        padding: '10 0 10 0'
                    },
                    items: [
                        {
                            title: _t('Product Details'),
                            items:[
                                {
                                    xtype: 'panel',
                                    layout: 'hbox',
                                    margin: '0 0 30px 0',
                                    items: [
                                        {
                                            xtype: 'textfield',
                                            name: 'name',
                                            fieldLabel: _t('Product Name'),
                                            margin: '0 10px 0 0',
                                            width:320,
                                            regex: Zenoss.env.textMasks.allowedDescText,
                                            regexText: Zenoss.env.textMasks.allowedDescTextFeedback,
                                            allowBlank: false
                                        },{
                                            xtype: 'hidden',
                                            name: 'productname'
                                        },{
                                            xtype: 'textfield',
                                            name: 'partNo',
                                            margin: '0 20px 0 0',
                                            fieldLabel: _t('Part #'),
                                            regex: Zenoss.env.textMasks.allowedDescText,
                                            regexText: Zenoss.env.textMasks.allowedDescTextFeedback,
                                            width:250
                                        },{
                                            xtype: 'combo',
                                            id: 'prodtype',
                                            name:'prodtype',
                                            displayField: 'name',
                                            editable: false,
                                            typeAhead: false,
                                            allowBlank: false,
                                            fieldLabel: _t('Type'),
                                            store:  Ext.create('Ext.data.ArrayStore', {
                                                 model: 'Zenoss.model.Name',
                                                 data: [[
                                                    _t('Hardware')
                                                ],[
                                                    _t('Software')
                                                ],[
                                                    _t('Operating System')
                                                ]]
                                             })
                                        },{
                                            xtype: 'combo',
                                            id: 'mansetting',
                                            name:'mansetting',
                                            displayField: 'name',
                                            editable: false,
                                            typeAhead: false,
                                            width: 200,
                                            fieldLabel: _t('Manufacturer'),
                                            queryMode: 'local',
                                            store: [ 'none' ]
                                        }
                                    ]

                                },{
                                    xtype: 'panel',
                                    items:[
                                        {
                                            xtype: 'textfield',
                                            fieldLabel: _t('Product Keys (comma delimited)'),
                                            id: 'keys_panel',
                                            name: 'keys_panel',
                                            width: '98.5%',
                                            margin: '0 20 20 0'
                                        },{
                                            xtype: 'minieditorpanel',
                                            name: 'desc_panel',
                                            id: 'desc_panel',
                                            height:100,
                                            width:'98.5%',
                                            margin: '0 20 20 0',
                                            title: _t('Description')
                                        },{
                                            xtype: 'instancepanel',
                                            hidden: newEntry,
                                            title: _t('Instances of this product'),
                                            id: 'instancegrid_id',
                                            width:'98.5%'
                                        }
                                    ]// panel items
                              }
                              ] // product details items
                           },{
                                title: _t('Configuration Properties'),
                                hidden: newEntry,
                                items:[
                                    {
                                        xtype: 'configpropertypanel',
                                        style: 'background: #fff',
                                        listeners: {
                                            beforerender: function(g){
                                                g.setHeight(Ext.getCmp('productsDialog').height-150);
                                                g.setContext(data.uid);
                                            }
                                        }
                                    }
                                ]
                            }
                       ] // tab panel items
                }// tab panel
            ], // config items
            // explicitly do not allow enter to submit the dialog
            keys: {}
        };
        if (Zenoss.Security.hasPermission('Manage Device')) {
            dialog = new Zenoss.SmartFormDialog(config);
            dialog.show();
        }else{ return false; }
    };    // end edit product dialog

   Ext.define('Zenoss.productsgrid.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'id',
        fields: [
            {name: 'count'},
            {name: 'id'},
            {name: 'uid'},
            {name: 'key'},
            {name: 'type'}
        ]
    });

    Ext.define("Zenoss.productsgrid.Store", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.productsgrid.Model',
                initialSortColumn: "id",
                directFn: Zenoss.remote.ManufacturersRouter.getProductsByManufacturer,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.manufacturers.ProductsGrid", {
        alias: ['widget.productsgrid'],
        extend:"Zenoss.FilterGridPanel",
        constructor: function(config) {
            config = config || {};

            Ext.applyIf(config, {
                stateId: 'products_grid',
                id: 'products_grid',
                stateful: false,
                loadMask:true,
                multiSelect: true,
                tbar:[
                    {
                        xtype: 'largetoolbar',
                        id: 'products_toolbar',
                        itemId: 'products_toolbar',
                        height:30,
                        disabled: true,
                        items: [
                            {
                                xtype: 'button',
                                iconCls: 'add',
                                hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                                tooltip: _t('Add a new product to this manufacturer'),
                                handler: function(button) {
                                    var grid = Ext.getCmp("productsgrid_id");
                                    Zenoss.manufacturers.productsDialog(grid);
                                }
                            },{
                                xtype: 'button',
                                iconCls: 'delete',
                                hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                                tooltip: _t('Delete selected items'),
                                handler: function(button) {
                                    var grid = Ext.getCmp("productsgrid_id"),
                                        data = [],
                                        selected = grid.getSelectionModel().getSelection();
                                    if (Ext.isEmpty(selected)) {
                                        return;
                                    }
                                    for (var i=0; selected.length > i; i++){
                                        data.push({'context':selected[i].data.uid.split('/products/')[0], 'id':selected[i].data.id});
                                    }
                                    new Zenoss.dialog.SimpleMessageDialog({
                                        title: _t('Delete Product'),
                                        message: _t("Are you sure you want to delete the selected products?"),
                                        buttons: [{
                                            xtype: 'DialogButton',
                                            text: _t('OK'),
                                            handler: function() {
                                                Zenoss.remote.ManufacturersRouter.removeProducts({'products':data}, function(response){
                                                    if (response.success) {
                                                        grid.refresh();
                                                        var bar = Ext.getCmp('products_toolbar');
                                                        //bar.items.items[2].setDisabled(false);
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
                                tooltip: _t('View and/or Edit selected'),
                                handler: function(button) {
                                    var grid = Ext.getCmp("productsgrid_id"),
                                        data,
                                        selected = grid.getSelectionModel().getSelection();

                                    if (Ext.isEmpty(selected)) {
                                        return;
                                    }
                                    // single selection
                                    data = selected[0].data;
                                    data['whichPanel'] = 'default';
                                    Zenoss.manufacturers.productsDialog(grid, data);
                                }
                            }]
                        }
                ],
                store: Ext.create('Zenoss.productsgrid.Store', {}),
                listeners: {
                    afterrender: function(e){
                        e.getStore().on('load', function(f){
                            Ext.getCmp('products_toolbar').setDisabled(false);
                        });
                    },
                    select: function(e){
                            var bar = Ext.getCmp('products_toolbar');
                        if(e.getCount() > 1){
                            bar.items.items[2].setDisabled(true);
                        }else{
                            bar.items.items[2].setDisabled(false);
                        }
                    }
                },
                columns: [
                    {
                        header: _t('Name'),
                        id: 'prod_id',
                        dataIndex: 'id',
                        flex: 1,
                        sortable: true
                    },{
                        id: 'uid_id',
                        dataIndex: 'uid',
                        hidden: true
                    },{
                        header: _t("Type"),
                        id: 'type_id',
                        dataIndex: 'type',
                        width: 200,
                        sortable: true,
                        filter: []
                    },{
                        header: _t("Product Keys"),
                        id: 'keys_id',
                        dataIndex: 'key',
                        flex: 1,
                        sortable: true,
                        renderer: function(e){
                            return e.toString().replace(",",",  ");
                        },
                        filter: []
                    },{
                        header: _t('Count'),
                        id: 'count_id',
                        dataIndex: 'count',
                        width:70,
                        sortable: true,
                        filter: []
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
        onRowDblClick: function(grid, rowIndex, e) {
            var data,
                selected = this.getSelectionModel().getSelection();
            if (!selected) {
                return;
            }
            data = selected[0].data;
            data['whichPanel'] = 'default';
            Zenoss.manufacturers.productsDialog(this, data);
        }
    });




   Ext.define('Zenoss.instancegrid.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'device',
        fields: [
            {name: 'id'},
            {name: 'device'}
        ]
    });

    Ext.define("Zenoss.instancegrid.Store", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.instancegrid.Model',
                initialSortColumn: "id",
                directFn: Zenoss.remote.ManufacturersRouter.getProductInstances,
                root: 'data'
            });
            this.callParent(arguments);
        }
    });

    Ext.define("Zenoss.manufacturers.InstanceGrid", {
        alias: ['widget.instancepanel'],
        extend:"Zenoss.FilterGridPanel",
        constructor: function(config) {
            config = config || {};

            Ext.applyIf(config, {
                stateId: 'instance_grid',
                id: 'instance_grid',
                stateful: true,
                loadMask:true,
                store: Ext.create('Zenoss.instancegrid.Store', {}),
                columns: [
                    {
                        header: _t("Device"),
                        id: 'device_id',
                        dataIndex: 'device',
                        flex: 1,
                        sortable: true,
                        renderer: function(name, row, record) {
                            return Zenoss.render.Device(record.data.uid, name);
                        }
                    },{
                        header: _t('Name'),
                        id: 'instance_id',
                        dataIndex: 'id',
                        flex: 1,
                        sortable: true,
                        filter: []
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






    Ext.define('Zenoss.manufacturers.CodeEditorField', {
        extend: 'Ext.form.field.TextArea',
        alias: 'widget.codefield',
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
        onCodeeditorfieldRender: function(abstractcomponent, options) {
            var me = this;
            var element = document.getElementById(abstractcomponent.getInputId());
            this.editor = CodeMirror.fromTextArea(element, {'lineNumbers':true});
            this.editor.on('cursorActivity', function(ce){
                if (me.getValue() != me.originalValue){
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

    Ext.define('Zenoss.manufacturers.MiniEditorPanel', {
        extend: 'Ext.panel.Panel',
        alias: 'widget.minieditor',
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
                        xtype: 'codefield',
                        name: me.name,
                        value: me.value
                    }
                ]
            });

            this.callParent(arguments);
        },
        focus: function() {
            this.down('codefield').focus();
        },
        getValue: function() {
            return this.down('codefield').getValue();
        },
        setValue: function(value) {
            this.down('codefield').setValue(value);
        },
        reset: function() {
            this.down('codefield').setValue('');
        }
    });




});