/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

Ext.onReady(function(){

    var dataSourcesId = 'dataSourceTreeGrid';
    var thresholdsId = Zenoss.templates.thresholdsId;
    var graphsId = 'graphGrid';
    var updateDataSources, updateThresholds, updateGraphs;
    updateDataSources = function(uid) {
        var treeGrid = Ext.getCmp(dataSourcesId);
        if (!treeGrid) {
            Ext.getCmp('center_detail_panel').add({
                xtype: 'DataSourceTreeGrid',
                uid: uid,
                root: {
                    id: uid,
                    uid: uid
                }
            });
        } else {
            treeGrid.setContext(uid);
        }
    };

    updateThresholds = function(uid) {
        var panel;
        panel = Ext.getCmp('top_detail_panel');

        if ( ! Ext.getCmp(thresholdsId) ) {
            panel.add({id: thresholdsId, xtype:'thresholddatagrid'});
            panel.doLayout();
        }
        Ext.getCmp(thresholdsId).setContext(uid);
    };

    updateGraphs = function(uid) {
        var panel;
        panel = Ext.getCmp('bottom_detail_panel');
        if ( ! Ext.getCmp(graphsId) ) {
            panel.add({
                xtype: 'graphgrid',
                id: graphsId
            });
            panel.doLayout();
        }
        Ext.getCmp(graphsId).setContext(uid);
    };

    var selModel = new Zenoss.TreeSelectionModel({
        listeners: {
            selectionchange: function(sm, nodes) {
                var node = nodes[0];
                updateDataSources(node.data.uid);
                updateThresholds(node.data.uid);
                updateGraphs(node.data.uid);
                Zenoss.env.PARENT_CONTEXT = node.data.uid;
            }
        }
    });
    Ext.getCmp('master_panel').add({
        items:[{
            xtype: 'TemplateTreePanel',
            selModel: selModel,
            enableDragDrop: false,
            directFn: Zenoss.remote.TemplateRouter.getCollectorTemplate
        }]
    });

}); // Ext. OnReady
