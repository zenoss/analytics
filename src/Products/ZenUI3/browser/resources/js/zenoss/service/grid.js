
/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

    var zs = Ext.ns('Zenoss.Service.Nav');



    // handles the SelectionModel's rowselect event
    zs.rowselectHandler = function(sm, dataRecord, rowIndex) {
        var token, tokenParts, detail, panel;
        Ext.getCmp('serviceForm').setContext(dataRecord.data.uid);
        detail = Ext.getCmp('detail_panel');
        panel = detail.detailCardPanel;

        if (panel.collapsed) {
            panel.on('expand', function(p){
                p.setHeight(250).doLayout();
                Ext.getCmp('detail_panel').doLayout();
                panel.setContext(dataRecord.data.uid);
            }, this, {single: true});
            panel.expand();
        } else {
            panel.setContext(dataRecord.data.uid);
        }

        Ext.getCmp('footer_bar').buttonDelete.setDisabled(false);
        token = Ext.History.getToken();
        if ( ! token ) {
            token = 'navTree:' + Ext.getCmp('navTree').getRootNode().data.uid.replace(/\//g, '.');
        }
        tokenParts = token.split('.serviceclasses.');
        if ( tokenParts[1] !== dataRecord.data.name ) {
            Ext.History.add( tokenParts[0] + '.serviceclasses.' + dataRecord.data.name);
        }
    };

    /**
     * @class Zenoss.Service.Nav.Model
     * @extends Ext.data.Model
     * Field definitions for the services
     **/
    Ext.define('Zenoss.Service.Nav.Model',  {
        extend: 'Ext.data.Model',
        idProperty: 'uid',
        fields: [
            {name:'name', type:'string'},
            {name:'description', type:'string'},
            {name:'port', type:'int'},
            {name:'count', type:'int', sortDir: 'DESC'},
            {name:'uid', type:'string'}
        ]
    });

    /**
     * @class Zenoss.Service.Nav.Store
     * @extend Zenoss.DirectStore
     * Direct store for the nav services
     */
    Ext.define("Zenoss.Service.Nav.Store", {
        extend: "Zenoss.DirectStore",
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                model: 'Zenoss.Service.Nav.Model',
                pageSize: 200,
                initialSortColumn: "name",
                directFn: Zenoss.remote.ServiceRouter.query,
                root: 'services'
            });
            this.callParent(arguments);
        }
    });
    zs.columns = [
        {
            dataIndex : 'name',
            header : _t('Name'),
            flex: 1,
            menuDisabled: false,
            id : 'name'
        }, {
            dataIndex : 'count',
            header : _t('Count'),
            id : 'count',
            width : 50,
            menuDisabled: false,
            filter : false
        }
    ];

    /**
     * @class Zenoss.Service.Nav.GridPanel
     * @extends Zenoss.FilterGridPanel
     * Grid that is on the left hand side of the sevices page. Shows the
     * service class as well as the instance count
     **/

    Ext.define("Zenoss.Service.Nav.GridPanel", {
        extend:"Zenoss.FilterGridPanel",
        alias: ['widget.servicegridpanel'],

        constructor: function(config) {
            Ext.applyIf(config, {
                id: 'navGrid',
                flex: 3,
                stateId: 'servicesNavGridState',

                viewConfig: {
                    plugins: {
                        ptype: 'gridviewdragdrop',
                        ddGroup: 'serviceDragDrop',
                        enableDrag: true,
                        enableDrop: false
                    }
                },
                stateful: true,
                columns: zs.columns,
                rowSelectorDepth: 5,
                loadMask: true
            });
            this.callParent(arguments);
        },

        filterAndSelectRow: function(serviceClassName) {
            var selections, selectedRecord;
            if (serviceClassName) {
                // the token includes a ServiceClass. Filter the grid
                // using the name of the ServiceClass and select the
                // correct row.
                selections = this.getSelectionModel().getSelection();
                if (selections.length) {
                    selectedRecord = selections[0];
                }

                if ( ! selectedRecord || selectedRecord.data.name !== serviceClassName ) {
                    this.serviceClassName = serviceClassName;
                    this.getStore().on('datachanged', this.filterGrid, this, {single: true});
                }
            }else{
                this.setFilter('name', '');
            }
        },

        filterGrid: function() {
            var me = this,
                serviceClassName = this.serviceClassName;
            if (!serviceClassName) {
                return;
            }
            // look for it in our current store
            function selectrow() {
                var found = false;
                me.getStore().each(function(record){
                    if (record.get("name") === serviceClassName) {
                        me.getSelectionModel().select(record);
                        found = true;
                    }
                });
                return found;
            }
            if (!selectrow()) {
                // otherwise filter for it and find the service then
                this.setFilter('name', serviceClassName);
                this.getStore().on('datachanged', selectrow, this, {single: true});
            }
        }

    });

})();
