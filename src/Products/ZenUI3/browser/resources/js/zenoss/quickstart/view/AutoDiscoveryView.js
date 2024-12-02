/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    var router = Zenoss.remote.JobsRouter;

    /**
     * Checks to make sure this is a valid IPv4 range or network.
     **/
    function isIpRangeOrNetwork(val) {
        var pieces = val.split("."), i, block;
        if (pieces.length !== 4) {
            return false;
        }

        // go through each octet and make sure it is either
        // a number or a number with a / or a .
        for (i=0; i<pieces.length; i++) {
            block = pieces[i];
            block = block.replace("/", "");
            block = block.replace("-", "");
            if (!Ext.isNumeric(block)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Add a vtype for ip range
     **/
    Ext.apply(Ext.form.VTypes, {
        /**
         * Verify that at least one network or ip range has been entered
         * by splitting the input.
         * returns true if any token in the input is valid.
         **/
        ipRange: function(val) {
            var values, i;
            values = val.split(",");
            values = values.concat(val.split("\n"));
            values = Ext.Array.unique(values);
            for (i=0; i<values.length;i++) {
                if (isIpRangeOrNetwork(values[i])) {
                    return true;
                }
            }
            return false;
        },
        ipRangeText: _t("You must enter at least one network or ip range.")
    });

    function addErrorToolTip(metadata, record) {
        if (record.get('errors')) {
            var msg = record.get('errors');
            msg = Ext.htmlEncode(msg);
            msg = "<pre style='white-space:normal;'>" + msg + "</pre>";
            msg = msg.replace(/\"/g, '&quot;');
            metadata.tdAttr = 'data-qtip="' + msg + '"';
        }
    }

    /**
     * @class Zenoss.quickstart.Wizard.view.AutoDiscoveryView
     * @extends Ext.panel.Panel
     * @constructor
     *
     */
    Ext.define('Zenoss.quickstart.Wizard.view.DiscoveryGrid', {
        extend: 'Ext.grid.Panel',
        alias: ['widget.discoverygrid'],
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                columns: [{
                    dataIndex: 'status',
                    header: _t('Status'),
                    renderer: function(val, metadata, record) {
                        // if there are errors show them in a tooltip
                        addErrorToolTip(metadata, record);
                        switch (val) {
                          case "STARTED":
                            return Ext.String.format("<img src='{0}' alt='{1}' />", "/++resource++zenui/img/ext4/icon/circle_arrows_ani.gif", status);
                          case "PENDING":
                          case "RETRY":
                            return Ext.String.format("<img src='{0}' alt='{1}' />", "/++resource++zenui/img/ext4/icon/circle_arrows_still.png", status);
                          case "ABORTED":
                            return "<span class=\"tree-severity-icon-small-warning\" style=\"padding-left:18px;padding-top:2px;\">Aborted</span>";
                          case "SUCCESS":
                            return "<span class=\"tree-severity-icon-small-clear\" style=\"padding-left:18px;padding-top:2px;\">Success</span>";
                          case "FAILURE":
                            return "<span class=\"tree-severity-icon-small-critical\" style=\"padding-left:18px;padding-top:2px;\">Failure</span>";
                        }
                        return val;
                    }
                }, {
                    dataIndex: 'networks',
                    header: _t('Networks'),
                    flex: 1,
                    renderer: function(val, metadata, record) {
                        addErrorToolTip(metadata, record);
                        return val;
                    }
                },{
                    dataIndex: 'zProperties',
                    header: _t('Credentials'),
                    renderer: function(props, metadata, record) {
                        addErrorToolTip(metadata, record);
                        var values = [], key;
                        for (key in props) {
                            if (key.indexOf('Password') === -1) {
                                values.push(props[key]);
                            }
                        }
                        return values.join(",");
                    }
                }, {
                    dataIndex: 'collector',
                    header: _t('Collector'),
                    hidden: Zenoss.env.COLLECTORS.length === 1 ? true:  false
                },{
                    dataIndex: 'duration',
                    header: _t('Duration'),
                    renderer: function(value, metadata, record) {
                        addErrorToolTip(metadata, record);
                        if (value) {
                            return Ext.String.format("{0} {1}", value, _t('seconds'));
                        }
                        return "--";
                    }
                }, {
                    dataIndex: 'logfile',
                    header: _t('Job Log'),
                    renderer: function(val, metadata, record) {
                        addErrorToolTip(metadata, record);
                        if (!val) {
                            return "--";
                        }
                        return Ext.String.format(
                            "<a href=\"{0}\" onClick=\"{1}\">{2}</a>",
                            "javascript:",
                            Ext.String.format(
                                "Zenoss.quickstart.Wizard.openJobLogFile('{0}', '{1}')",
                                record.get('uuid'),
                                record.get('networks')
                            ),
                            val.replace("/opt/zenoss/log/jobs/", "")
                        );
                    }
                }, {
                    xtype: 'actioncolumn',
                    width: 75,
                    handler: function(grid, rowIndex){
                        // get the record and tell the database to delete the job
                        var store = grid.getStore(), record = store.getAt(rowIndex);
                        if (record.get('pendingDelete')) {
                            return;
                        }
                        record.set('pendingDelete', true);
                        router.deleteJobs({
                            jobids: [record.get('uuid')]
                        }, function(response) {
                            if (response.success) {
                                store.remove(record);
                            }
                        });
                    },
                    text: _t('Remove'),
                    icon: "/++resource++extjs/examples/restful/images/delete.png",
                    altText: _t('Remove')

                }],
                store: Ext.create('Zenoss.quickstart.Wizard.DiscoveryStore', {})

            });
            this.callParent([config]);
        }
    });

    /**
     * @class Zenoss.quickstart.Wizard.view.AutoDiscoveryView
     * @extends Ext.panel.Panel
     * @constructor
     *
     */
    Ext.define('Zenoss.quickstart.Wizard.view.AutoDiscoveryView', {
        extend: 'Ext.form.Panel',
        alias: 'widget.wizardautodiscoveryview',
        stepTitle: _t('Network Discovery'),
        stepId: 'discover-network',
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                layout: "vbox",
                items:[{
                    region: 'north',
                    height: 30,
                    cls: 'wizard_subtitle',
                    html: '<h2><em>' + _t('Devices found via Discovery will be placed in the /Discovered Device Class') + '</em></h2>'
                },{
                    xtype: 'form',
                    region: 'center',
                    layout: 'hbox',
                    width: "100%",
                    defaults: {
                        height: 175,
                        flex: 1,
                        cls: "wizardColumn",
                        overflowY: "auto"
                    },
                    defaultType: "fieldset",
                    items: [{
                        title: _t('Networks/Range'),
                        defaults: {
                            width: "100%"
                        },
                        items:[{
                            xtype: 'textarea',
                            name: 'ip_ranges',
                            vtype: 'ipRange',
                            fieldLabel: _t("Enter one or more networks (such " + "as 10.0.0.0/24) or " + "IP ranges " + "(such as 10.0.0.1-50)"),
                            tabIndex: 2,
                            labelAlign: 'top',
                            id: 'wizard_ip_ranges',
                            allowBlank: false,
                        }, {
                            xtype: 'combo',
                            // only show if we have multiple collectors
                            hidden: Zenoss.env.COLLECTORS.length === 1,
                            // if visible give it a good tabindex
                            tabIndex: (Zenoss.env.COLLECTORS.length === 1) ? 100: 2,
                            labelAlign: 'top',
                            fieldLabel: 'Collector',
                            queryMode: 'local',
                            store: new Ext.data.ArrayStore({
                                data: Zenoss.env.COLLECTORS,
                                fields: ['name']
                            }),
                            valueField: 'name',
                            value: 'localhost',
                            name: 'collector',
                            displayField: 'name',
                            forceSelection: true,
                            editable: false,
                            allowBlank: false,
                            triggerAction: 'all'
                        }, {
                            xtype: 'button',
                            itemId: 'discoverButton',
                            anchor: "40%",
                            formBind: true,
                            tabIndex: 3,
                            text: _t('Discover')
                        }]
                    }, {
                        title: _t('SNMP'),
                        defaults: {
                            width: "100%",
                            labelAlign: 'top',
                        },
                        items: [{
                            xtype: 'textarea',
                            id: 'wizard_snmp_communities',
                            inputAttrTpl: Ext.String.format(" data-qtip='{0}' ", _t("Zenoss will try each of these community strings in turn when connecting to the device.")),
                            tabIndex: 2,
                            allowBlank: false,
                            fieldLabel: _t('Community Strings'),
                            name: 'zSnmpCommunities'
                        }]
                    },{
                        title: _t('SSH Authentication'),
                        defaults: {
                            width: "100%",
                            labelAlign: 'top',
                        },
                        items: [{
                            xtype: 'textfield',
                            tabIndex: 2,
                            fieldLabel: 'Username',
                            name: 'zCommandUsername'
                        },{
                            xtype: 'textfield',
                            tabIndex: 2,
                            fieldLabel: 'Password',
                            inputType: 'password',
                            name: 'zCommandPassword'
                        }]
                    },{
                        style: {
                            border: "none !important",
                            paddingRight: 0
                        },
                        title: _t('Windows Authentication'),
                        defaults: {
                            width: "100%",
                            labelAlign: 'top',
                        },
                        items: [{
                            xtype: 'textfield',
                            tabIndex: 2,
                            inputAttrTpl: Ext.String.format(" data-qtip='{0}' ", _t("This user must be a member of the Local Administrators group..")),
                            fieldLabel: 'Administrator Username',
                            name: 'zWinRMUser'
                        },{
                            xtype: 'textfield',
                            tabIndex: 2,
                            fieldLabel: 'Password',
                            inputType: 'password',
                            name: 'zWinRMPassword'
                        }]
                    }]
                }, {
                    region: 'south',
                    xtype: 'fieldset',
                    width: "100%",
                    title: _t('Discoveries'),
                    items: [{
                        xtype: 'discoverygrid',
                        height: 150,
                        autoScroll: true,
                        emptyText: _t('Add network discoveries using the above form'),
                        emptyCls: "empty-grid-text"
                    }]
                }]
            });
            this.callParent([config]);
        }
    });



})();
