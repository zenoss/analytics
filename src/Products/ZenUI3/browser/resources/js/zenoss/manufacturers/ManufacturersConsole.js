/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

Ext.onReady(function () {

    Ext.ns('Zenoss.manufacturers');
    // page level variables
    var REMOTE = Zenoss.remote.ManufacturersRouter;

    function getOrganizerFields() {
        var items = [
            {
                xtype: 'fieldset',
                margin: '0 15px 20px 0',
                items: [
                    {
                        xtype: 'panel',
                        layout: 'hbox',
                        items: [
                            {
                                xtype: 'textfield',
                                name: 'oldname',
                                hidden: true
                            }, {
                                xtype: 'textfield',
                                name: 'name',
                                fieldLabel: _t('Manufacturer Name'),
                                margin: '0 10px 0 0',
                                width: 320,
                                regex: Zenoss.env.textMasks.allowedDescText,
                                regexText: Zenoss.env.textMasks.allowedDescTextFeedback,
                                allowBlank: false
                            }, {
                                xtype: 'textfield',
                                name: 'phone',
                                fieldLabel: _t('Phone'),
                                margin: '0 10px 0 0',
                                width: 120,
                                regex: /^\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}$|^$/,
                                regexText: "Numbers, - . () only",
                                allowBlank: true
                            }, {
                                xtype: 'textfield',
                                vtype: 'url',
                                name: 'URL',
                                fieldLabel: _t('URL'),
                                width: 420
                            }
                        ]
                    }
                ]
            }, {
                xtype: 'fieldset',
                margin: '0 15px 20px 0',
                items: [
                    {
                        xtype: 'textfield',
                        name: 'address1',
                        fieldLabel: _t('Address 1'),
                        margin: '0 0 10px 0',
                        width: 400
                    }, {
                        xtype: 'textfield',
                        name: 'address2',
                        fieldLabel: _t('Address 2'),
                        width: 400
                    }
                ]
            }, {
                xtype: 'fieldset',
                margin: '0 15px 20px 0',
                items: [
                    {
                        xtype: 'panel',
                        layout: 'hbox',
                        items: [
                            {
                                xtype: 'textfield',
                                name: 'city',
                                fieldLabel: _t('City'),
                                margin: '0 10px 0 0',
                                width: 320,
                                regex: Zenoss.env.textMasks.allowedDescText,
                                regexText: Zenoss.env.textMasks.allowedDescTextFeedback,
                                allowBlank: true
                            }, {
                                xtype: 'combo',
                                name: 'state',
                                margin: '0 10px 0 0',
                                store: Ext.create('Ext.data.Store', {
                                    model: 'Zenoss.manufacturers.state',
                                    data: Zenoss.util.states
                                }),
                                fieldLabel: _t('State/Province'),
                                displayField: 'name',
                                width: 150,
                                queryMode: 'local',
                                typeAhead: true
                            }, {
                                xtype: 'textfield',
                                name: 'zip',
                                fieldLabel: _t('Postal/Zip Code'),
                                margin: '0 10px 0 0',
                                width: 180,
                                regex: Zenoss.env.textMasks.allowedDescText,
                                regexText: Zenoss.env.textMasks.allowedDescTextFeedback,
                                allowBlank: true
                            }, {
                                xtype: 'textfield',
                                name: 'country',
                                fieldLabel: _t('Country'),
                                width: 250,
                                regex: Zenoss.env.textMasks.allowedDescText,
                                regexText: Zenoss.env.textMasks.allowedDescTextFeedback
                            }
                        ]
                    }
                ]
            }, {
                xtype: 'panel',
                items: [
                    {
                        xtype: 'minieditor',
                        title: _t('Regexes (matches for incoming products to manufacturer)'),
                        name: 'regexes_panel',
                        margin: '0 15 0 0'
                    }
                ]
            }

        ];

        return items;
    }

    Ext.define('Zenoss.manufacturers.state', {
        extend: 'Ext.data.Model',
        fields: [
            {type: 'string', name: 'abbr'},
            {type: 'string', name: 'name'},
            {type: 'string', name: 'slogan'}
        ]
    });

    /* Manufacturer Edit Dialog */
    Zenoss.manufacturers.callEditManufacturerDialog = function (name, uid) {
        var manufacturersDialog = new Zenoss.SmartFormDialog({
            title: _t('Edit Manufacturer'),
            formId: 'editManufacturerDialog',
            height: Ext.getBody().getViewSize().height,
            width: Ext.getBody().getViewSize().width * 0.8, //80%
            autoDestroy: true,
            items: getOrganizerFields()
        });
        REMOTE.getManufacturerData({'uid': uid}, function (response) {
            if (response.success) {
                var data = response.data[0];
                var fields = Ext.getCmp('editManufacturerDialog').getForm().getFields();
                for (var i = 0; i < fields.length; i++) {
                    var record = fields.items[i];
                    switch (record.name) {
                        case "oldname"  :
                            record.setValue(data.id);
                            break;
                        case "name"     :
                            record.setValue(name);
                            break;
                        case "URL"      :
                            record.setValue(data.url);
                            break;
                        case "phone"    :
                            record.setValue(data.phone);
                            break;
                        case "address1" :
                            record.setValue(data.address1);
                            break;
                        case "address2" :
                            record.setValue(data.address2);
                            break;
                        case "city"     :
                            record.setValue(data.city);
                            break;
                        case "state"    :
                            record.setValue(data.state);
                            break;
                        case "zip"      :
                            record.setValue(data.zip);
                            break;
                        case "country"  :
                            record.setValue(data.country);
                            break;
                        case "regexes_panel"  :
                            try {
                                record.setValue(data.regexes);
                            } catch (e) {/*swallow codemirror split bug */
                            }
                            break;
                    }
                }
            }
            manufacturersDialog.setSubmitHandler(function (e) {
                var params = {
                    'oldname': e.oldname,
                    'name': e.name,
                    'phone': e.phone,
                    'URL': e.URL,
                    'address1': e.address1,
                    'address2': e.address2,
                    'city': e.city,
                    'zip': e.zip,
                    'state': (e.state || ""),
                    'country': e.country,
                    'regexes': e.regexes_panel
                };
                REMOTE.editManufacturer({'params': params}, function (response) {
                    if (response.success) {
                        var leftGrid = Ext.getCmp('manufacturers_tree');
                        leftGrid.store.load();
                        Zenoss.message.info(_t(e.name) + ' added');
                    }
                });
            });
        });
        manufacturersDialog.show();
    };

    function getSelectedManufacturer() {
        return Ext.getCmp('manufacturers_tree').getSelectionModel().getSelectedNode();
    }

    /* New version of left side menu */
    Ext.define('Zenoss.manufactures.StoreModel', {
        extend: 'Ext.data.Model',
        idProperty: 'uuid',
        fields: [
            {name: 'path'},
            {name: 'text', mapping: 'text.text'},
            {name: 'url', mapping: 'text.url'},
            {name: 'description', mapping: 'text.description'},
            {name: 'uid'},
            {name: 'id'}
        ]
    });
    Ext.define("Zenoss.manufactures.Store", {
        extend: "Zenoss.NonPaginatedStore",
        constructor: function (config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.manufactures.StoreModel',
                directFn: REMOTE.getManufacturerList,
                initialSortColumn: 'text',
                initialSortDirection: 'ASC',
                root: 'data',
                autoLoad: true
            });
            this.callParent(arguments);
        }
    });

    var leftGridPanel = Ext.create('Ext.grid.Panel', {
        id: 'manufacturers_tree',
        store: Ext.create('Zenoss.manufactures.Store', {}),
        columns: [
            {text: 'Name', dataIndex: 'text', flex: 1, sortable: false}
        ],
        getContentPanel: function () {
            return Ext.getCmp('man_center_panel').items.items[Ext.getCmp('nav_combo').getSelectedIndex()];
        },
	selectByToken: function(nodeId){
            if (nodeId) {
                nodeId = decodeURI(nodeId);
                var node = this.store.findRecord("id", nodeId);
                if (node) {
                    this.getSelectionModel().select(node);
                } else {
                    var me = this;
                    this.store.on('load', function() {
                        var node = me.store.findRecord("id", nodeId);
                        if (node) {
                            me.getSelectionModel().select(node);
                        }
                    }, this, {single:true});
                }
            }
        },
        selModel: Ext.create('Zenoss.TreeSelectionModel', {
            listeners: {
                selectionchange: function (sm, newnodes) {
                    if (newnodes.length) {
                        var newnode = newnodes[0];
                        var uid = newnode.data.uid;
                        var data = newnode.data;
                        var contentPanel = leftGridPanel.getContentPanel();
                        var phone = "", url = "";
                        contentPanel.setContext(uid);

                        if (data.description !== "") {
                            phone = " - " + data.description;
                        }
                        if (data.url !== "") {
                            url = " - <a href='" + data.url + "'>" + data.url + "</a>";
                        }
                        Ext.getCmp("manufacturer_info").setText(
                            data.text + phone + url, false);
                        Ext.getCmp('footer_bar').setContext(uid);
                        Zenoss.env.contextUid = uid;
                        // explicitly set the new security context (to update permissions)
                        Zenoss.Security.setContext(uid);
                    }
                }
            }
        }),
        listeners: {
            itemdblclick: function () {
                var node = getSelectedManufacturer();
                if (Zenoss.Security.doesNotHavePermission('Manage DMD')) {
                    return false;
                }
                Zenoss.manufacturers.callEditManufacturerDialog(node.data.text, node.data.uid);
            }
        },
        deleteSelectedNode: function () {
            var node = getSelectedManufacturer();
            REMOTE.deleteManufacturer({'uid': node.data.uid}, function (response) {
                if (response.success) {
                    var leftGrid = Ext.getCmp('manufacturers_tree');
                    leftGrid.store.load();
                }
            });
        }
    });


    Ext.define("Zenoss.eventmanufacturers.NavigtaionCombo", {
        alias: ['widget.NavCombo'],
        extend: "Ext.form.ComboBox",
        constructor: function (config) {
            config = config || {};
            Ext.applyIf(config, {
                id: 'nav_combo',
                width: 240,
                displayField: 'name',
                editable: false,
                typeAhead: false,
                value: _t('Products'),
                listeners: {
                    select: function (combo) {
                        var container = Ext.getCmp('man_center_panel');
                        container.layout.setActiveItem(combo.getSelectedIndex());
                        // set the context for the active item:
                        var contentPanel = leftGridPanel.getContentPanel();
                        contentPanel.setContext(Zenoss.env.contextUid);
                        Zenoss.Security.setContext(Zenoss.env.contextUid);
                    }
                },
                store: Ext.create('Ext.data.ArrayStore', {
                    model: 'Zenoss.model.Name',
                    data: [[
                        _t('Products')
                    ], [
                        _t('Configuration Properties')
                    ]]
                })
            });
            this.callParent(arguments);
        }

    });


    Ext.getCmp('center_panel').add({
        id: 'center_panel_container',
        layout: 'border',
        defaults: {
            split: true
        },
        items: [{
            xtype: 'panel',
            id: 'master_panel',
            cls: 'x-zenoss-master-panel',
            region: 'west',
            width: 275,
            maxWidth: 275,
            layout: 'fit',
            items: [
                leftGridPanel
            ]
        }, {
            xtype: 'contextcardpanel',
            id: 'man_center_panel',
            region: 'center',
            activeItem: 0,
            tbar: {
                cls: 'largetoolbar',
                height: 38,
                items: [
                    {
                        xtype: 'NavCombo'
                    }, {
                        xtype: 'label',
                        id: 'manufacturer_info'
                    }
                ]
            },
            items: [
                {
                    xtype: 'productsgrid',
                    id: 'productsgrid_id'
                }, {
                    xtype: 'configpropertypanel',
                    id: 'configpanel_id'
                }

            ]
        }]
    });


    // Footer bar for the main manufacturers page.
    // This extends Zenoss.footerHelper in FooterBar.js
    /* ------------------------------------------------------------------------------ FOOTER --------------------------------- */
    var footerBar = Ext.getCmp('footer_bar');
    Zenoss.footerHelper(
        '',
        footerBar,
        {
            hasOrganizers: false,
            addToZenPack: false,
            // the message to display when user hits the [-] delete button.
            onGetDeleteMessage: function (itemName) {
                var node = getSelectedManufacturer();
                if (Ext.isEmpty(node)) {
                    return;
                }
                msg = _t('Are you sure you want to delete the {0} {1}? <br/>There is <strong>no</strong> undo.');
                return Ext.String.format(msg, itemName.toLowerCase(), '/' + node.data.path);
            },
            customAddDialog: {
                title: _t('Add New Manufacturer'),
                id: 'addNewManufacturerDialog',
                height: Ext.getBody().getViewSize().height,
                width: Ext.getBody().getViewSize().width * 0.8,
                submitHandler: function (e) {
                    var params = {
                        'name': e.name,
                        'phone': e.phone,
                        'URL': e.URL,
                        'address1': e.address1,
                        'address2': e.address2,
                        'city': e.city,
                        'zip': e.zip,
                        'state': (e.state || ""),
                        'country': e.country,
                        'regexes': e.regexes_panel
                    };
                    REMOTE.addManufacturer({'id': e.name}, function (response) {
                        if (response.success) {
                            REMOTE.editManufacturer({'params': params}, function (response) {
                                if (response.success) {
                                    var leftGrid = Ext.getCmp('manufacturers_tree');
                                    leftGrid.store.load();
                                }
                            });
                        }
                    });
                },
                items: getOrganizerFields()
            },
            buttonContextMenu: {
                xtype: 'ContextConfigureMenu',
                onSetContext: function (uid) {
                    Zenoss.env.PARENT_CONTEXT = uid;
                },
                hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                onGetMenuItems: function () {
                    var menuItems = [];
                    menuItems.push({
                            xtype: 'menuitem',
                            text: _t('Edit'),
                            handler: function () {
                                var node = getSelectedManufacturer();
                                var uid = node.data.uid;
                                Zenoss.manufacturers.callEditManufacturerDialog(node.data.text, uid);
                            }
                        },
                        {
                            xtype: 'menuitem',
                            text: _t('Add to ZenPack'),
                            handler: function () {
                                win = Ext.create('Zenoss.AddToZenPackWindow', {});
                                win.target = getSelectedManufacturer().data.uid;
                                win.show();
                            }
                        });
                    return menuItems;
                }
            }
        }
    );

    footerBar.on('buttonClick', function (actionName, id, values) {
        var leftGrid = Ext.getCmp('manufacturers_tree');
        switch (actionName) {
            case 'addManufacturer':
                leftGrid.addChildNode(Ext.apply(values, {type: 'organizer'}));
                break;
            case 'addOrganizer':
                throw new Ext.Error('Not Implemented');
            case 'delete':
                leftGrid.deleteSelectedNode();
                break;
            default:
                break;
        }
    });


}); // Ext. OnReady
