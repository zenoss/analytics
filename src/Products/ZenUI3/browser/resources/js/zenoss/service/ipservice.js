/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.ns('Zenoss.IpService');

Ext.onReady( function() {

    var zsn = Zenoss.Service.Nav;
    var zsf = Zenoss.Service.DetailForm;

    var portTextField = {
        xtype: 'numberfield',
        fieldLabel: _t('Port'),
        name: 'port',
        width: "100%",
        id: 'portTextField',
        allowBlank: false,
        allowDecimals: false,
        allowNegative: false,
        maxValue: 65535,
        minValue: 1
    };

    zsf.formItems.items = [{
        items: [
            zsf.nameTextField,
            zsf.descriptionTextField,
            portTextField,
            zsf.sendStringTextField,
            zsf.expectRegexTextField,
            zsf.serviceKeysTextField
        ]
    }, {
        items: [
            zsf.zMonitor,
            zsf.zFailSeverity
        ]
    }];

    zsn.columns = [
        {
            dataIndex: 'name',
            header: _t('Name'),
            id: 'name',
            menuDisabled: true,
            flex: 1
        },
        {
            dataIndex: 'port',
            header: _t('Port'),
            id: 'port',
            width: 50,
            filter: false,
            menuDisabled: true
        },
        {
            dataIndex: 'count',
            header: _t('Count'),
            id: 'count',
            width: 50,
            filter: false,
            menuDisabled: true
        }
    ];


    zsf.hiddenFieldIdsForOrganizer.push('portTextField');
    zsf.hiddenFieldIdsForOrganizer.push(zsf.sendStringTextField.id);
    zsf.hiddenFieldIdsForOrganizer.push(zsf.expectRegexTextField.id);

    zsn.initNav('/zport/dmd/Services/IpService');
    zsf.initForm();
});
