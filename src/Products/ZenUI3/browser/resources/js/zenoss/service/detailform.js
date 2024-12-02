/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.onReady( function() {

    /**********************************************************************
     *
     * Service Panel Functionality
     *
     */

    var zsf = Ext.ns('Zenoss.Service.DetailForm');

    zsf.actioncompleteHandler = function(form, action) {
        form = Ext.getCmp('serviceForm');

        var isClass = (form.contextUid.indexOf('serviceclasses') > 0),
            isRoot = form.contextUid === Ext.getCmp('navTree').getRootNode().data.uid;


        if (action.type === 'directload') {
            form.isLoadInProgress = false;
            Ext.each(zsf.hiddenFieldIdsForOrganizer, function(i){
                    var o = Ext.getCmp(i);
                    // make sure comp exists
                    if (!o){
                        return;
                    }
                    o.setVisible(isClass);
                    if (o.label) {
                        o.label.setVisible(isClass);
                    }
                    o.setDisabled(!isClass);
                });
            Ext.getCmp('nameTextField2').setDisabled(isRoot);
        }
        else if (action.type === 'directsubmit') {

            if (Ext.getCmp('monitoredStartModes')) {
                Ext.getCmp('monitoredStartModes').refresh();
            }

            if (isClass) {
                // Update the record in the navigation grid.
                var navGrid = Ext.getCmp('navGrid'),
                    navGridModel = navGrid.getSelectionModel(),
                    navGridRecord = navGridModel.getSelected();

                if (navGridRecord) {
                    Zenoss.util.applyNotIf(navGridRecord.data, form.form.getValues());
                    navGrid.view.refreshNode(navGridRecord.index);
                    Ext.getCmp('detail_panel').detailCardPanel.setContext(navGridRecord.data.uid);
                }
            } else {
                // Update the record in the navigation tree.
                var treeSM = Ext.getCmp('navTree').getSelectionModel(),
                    treeSNode = treeSM.getSelectedNode();

                treeSNode.data.text.text = form.form.getValues().name;
                treeSNode.set('text', treeSNode.data.text);
                Ext.getCmp('detail_panel').detailCardPanel.setContext(treeSNode.data.uid);
            }


        }
    };

    zsf.nameTextField = {
        xtype: 'textfield',
        id: 'nameTextField2',
        fieldLabel: _t('Name'),
        name: 'name',
        anchor: '95%',
        allowBlank: false
    };

    zsf.descriptionTextField = {
        xtype: 'textfield',
        id: 'descriptionTextField',
        fieldLabel: _t('Description'),
        anchor: '95%',
        name: 'description'
    };

    zsf.sendStringTextField = {
        xtype: 'textfield',
        id: 'sendStringTextField',
        fieldLabel: _t('Send String'),
        anchor: '95%',
        name: 'sendString'
    };

    zsf.expectRegexTextField = {
        xtype: 'textfield',
        id: 'expectRegexTextField',
        fieldLabel: _t('Expect Regex'),
        anchor: '95%',
        name: 'expectRegex'
    };

    zsf.serviceKeysTextField = {
        xtype: 'textarea',
        id: 'serviceKeysTextField',
        fieldLabel: _t('Service Keys'),
        anchor: '95%',
        name: 'serviceKeys'
    };

    zsf.zMonitor = {
        xtype: 'zprop',
        ref: '../../zMonitor',
        title: _t('Enable Monitoring? (zMonitor)'),
        name: 'zMonitor',
        localField: {
            xtype: 'select',
            queryMode: 'local',
            store: [[true, 'Yes'], [false, 'No']]
        }
    };

    zsf.zFailSeverity = {
        xtype: 'zprop',
        ref: '../../zFailSeverity',
        title: _t('Failure Event Severity (zFailSeverity)'),
        name: 'zFailSeverity',
        localField: {
            xtype: 'select',
            queryMode: 'local',
            store: Zenoss.env.SEVERITIES.slice(0, 5)
        }
    };

    zsf.formItems = {
        layout: 'column',
        defaults: {
            layout: 'anchor',
            bodyStyle: 'padding: 15px',
            columnWidth: 0.5
        }
        // items is set in winservice.js and ipservice.js
    };

    zsf.hiddenFieldIdsForOrganizer = [
        zsf.serviceKeysTextField.id
    ];

    zsf.formConfig = {
        xtype: 'basedetailform',
        id: 'serviceForm',
        region: 'center',
        items: zsf.formItems,
        permission: 'Manage DMD',
        trackResetOnLoad: true,
        router: Zenoss.remote.ServiceRouter
    };

    zsf.initForm = function() {
        Ext.getCmp('serviceForm').on('actioncomplete', zsf.actioncompleteHandler);
    };
});
