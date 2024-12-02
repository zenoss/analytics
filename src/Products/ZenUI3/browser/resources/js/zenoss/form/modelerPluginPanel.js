/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){
    var router = Zenoss.remote.PropertiesRouter,
        ZPROP_NAME = 'zCollectorPlugins';
    Ext.define("Zenoss.form.ModelerPluginForm", {
        extend:"Ext.form.FormPanel",
        alias: "widget:modelerpluginform",
        constructor: function(config) {
            var me = this;
            config = config || {};
            Ext.apply(config, {
                fieldDefaults: {
                    labelAlign: 'top'
                },
                paramsAsHash: true,
                frame: false,
                autoScroll: 'y',
                defaults: {
                    labelStyle: 'font-size: 13px; color: #5a5a5a',
                    anchor: '100%'
                },
                items: [{
                    xtype: 'displayfield',
                    name: 'path',
                    id: 'modeler-plugin-path',
                    fieldLabel: _t('Path')
                },{
                    xtype: 'displayfield',
                    id: 'modeler-plugin-doc',
                    name: 'doc',
                    height: 65,
                    autoScroll: true,
                    ref: 'doc',
                    tooltip: 'Select a single plugin to see the docs',
                    fieldLabel: _t('Plugin Documentation')
                }],
                buttonAlign: 'left',
                buttons: [{
                    text: _t('Save'),
                    ref: 'savebtn',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function(btn){
                        var values = me.modelerPlugins.getValue(),
                            panel = me,
                            uid = me.uid;
                        router.setZenProperty({uid:uid,
                                               zProperty: ZPROP_NAME,
                                               value:values},
                                              function(response){
                                                  if (response.success){
                                                      Zenoss.message.info('Updated Modeler Plugins');
                                                      Ext.getCmp('modeler-plugin-path').setValue(response.data.path);
                                                      panel.toggleDeleteButton(response.data.path);
                                                  }

                                              });
                    }
                },{
                    text: _t('Cancel'),
                    ref: 'cancelbtn',
                    handler: function() {
                        if (me.uid) {
                            me.setContext(me.uid);
                        }
                    }
                },{
                    text: _t('Delete Local Copy'),
                    ref: 'deleteBtn',
                    hidden: true,
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    handler: function(btn) {
                        var panel = me;
                        // show a confirmation
                        new Zenoss.dialog.SimpleMessageDialog({
                            title: _t('Delete zProperty'),
                            msg: _t("Are you sure you want to delete the local copy of zCollectorPlugin?"),
                            buttons: [{
                                xtype: 'DialogButton',
                                text: _t('OK'),
                                handler: function() {
                                    if (panel.uid) {
                                        router.deleteZenProperty({
                                            uid: panel.uid,
                                            zProperty: ZPROP_NAME
                                        }, function(response){
                                            panel.setContext(panel.uid);
                                        });
                                    }
                                }
                            }, {
                                xtype: 'DialogButton',
                                text: _t('Cancel')
                            }]
                        }).show();
                    }
                }],
                cls: 'device-overview-form-wrapper',
                bodyCls: 'device-overview-form'
            });
            this.callParent(arguments);
        },
        setContext: function(uid) {
            if (this.modelerPlugins) {
                this.modelerPlugins.destroy();
            }
            if(this.pluginsHeader){
                this.pluginsHeader.destroy();
            }
            if(this.panelHeaders){
                this.panelHeaders.destroy();
            }
            Ext.getCmp('modeler-plugin-doc').setValue('');
            this.uid = uid;
            // get the modeler plugins
            router.getZenProperty({
                uid: uid,
                zProperty: ZPROP_NAME
            }, Ext.bind(this.loadData, this));

            Zenoss.remote.DeviceRouter.getModelerPluginDocStrings({
                uid: uid
            }, Ext.bind(this.loadDocs, this));

        },
        toggleDeleteButton: function(path){
            // show the delete button if locally defined
            var localPath = this.uid.replace('/zport/dmd/Devices', ''),
                deleteBtn = this.getButton("deleteBtn");

            // can't delete the root
            if (path === '/') {
                deleteBtn.hide();
                return;
            }
            if (localPath === path) {
                deleteBtn.show();
            }else{
                deleteBtn.hide();
            }
        },
        getButton: function(ref) {
            return this.query(Ext.String.format("button[ref='{0}']", ref))[0];
        },
        loadData: function(response) {
            if (response.success) {
                var data = response.data,
                    clickHandler,
                    panel = this;

                Ext.getCmp('modeler-plugin-path').setValue(data.path);
                this.toggleDeleteButton(data.path);
                clickHandler = function(select, record) {
                    // display the docs for the record clicked
                    var value = record.data.name;
                    panel.showDocFor(value);
                };
                var store = [];
                Ext.each(data.options, function(item) {
                    store.push([item]);
                });
                // add the multi select
                this.add({
                        xtype:'label',
                        text: 'Modeler Plugins:',
                        ref: 'pluginsHeader',
                        style: {'color':'#5A5A5A', 'fontWeight':'bold', 'display':'block', 'padding':'0 0 8px 0'}
                });
                this.add({
                    xtype: 'panel',
                    width: 800,
                    layout:'column',
                    ref: 'panelHeaders',
                    items: [
                    {
                        xtype:'label',
                        columnWidth: 0.515,
                        text: 'Available',
                        style: {'color':'#5A5A5A'}
                    },{
                        xtype: 'label',
                        columnWidth: 0.485,
                        text: 'Selected',
                        style: {'color':'#5A5A5A'}
                    }]
                });
                this.add({
                    name: 'modelerPlugins',
                    ref: 'modelerPlugins',
                    xtype: 'itemselector',
                    imagePath: "/++resource++zenui/img/xtheme-zenoss/icon",
                    height: 250,
                    drawUpIcon: true,
                    drawDownIcon: true,
                    drawTopIcon: true,
                    drawBotIcon: true,
                    displayField: 'name',
                    valueField: 'name',
                    store:  Ext.create('Ext.data.ArrayStore', {
                        model: 'Zenoss.model.Name',
                        data: store
                    }),
                    value: data.value,
                    listeners: {
                        afterrender: function() {
                            // HACK: have to go into the internals of MultiSelect to properly register a click
                            // handler
                            this.modelerPlugins.fromField.boundList.on('itemclick', clickHandler);
                            this.modelerPlugins.toField.boundList.on('itemclick', clickHandler);
                        },
                        scope: this
                    }
                });
                this.doLayout();

            }
        },
        showDocFor: function(plugin) {
            if (plugin && this.docs && this.docs[plugin]) {
                this.doc.setValue(this.docs[plugin]);
            }else{
                this.doc.setValue(Ext.String.format(_t('No documentation found for {0}'), plugin));
            }
        },
        loadDocs: function(response) {
            if (response.success) {
                this.docs = response.data;
            }
        }
    });


    /**
     * Place the form inside a panel for sizing
     **/
    Ext.define("Zenoss.form.ModelerPluginPanel", {
        alias:['widget.modelerpluginpanel'],
        extend:"Ext.Panel",
        constructor: function(config) {
            config = config || {};
            var form = Ext.create("Zenoss.form.ModelerPluginForm", {});
            Ext.applyIf(config, {
                layout: 'fit',
                width: 800,
                autoScroll: 'auto',
                items: [form]
            });
            this.callParent(arguments);
            this.form = form;
        },
        setContext: function(uid) {
            this.form.setContext(uid);
        }
    });




})();
