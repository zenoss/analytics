/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2013, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function () {
    Ext.ns('Zenoss');
    var ZC = Ext.ns('Zenoss.component');

    ZC.renderMap = {};

    /**
     * Register a custom handler for displaying graphs.
     **/
    ZC.registerComponentGraphRenderer = function (meta_type, fn, scope) {
        if (scope) {
            ZC.renderMap[meta_type] = Ext.bind(fn, scope);
        } else {
            ZC.renderMap[meta_type] = fn;
        }
    };

    /**
     * Grabs the registered graph renderer based on the meta_type of the
     * component. If a custom renderer is not found the 'default' one is
     * returned.
     **/
    ZC.getComponentGraphRenderer = function (meta_type) {
        return ZC.renderMap[meta_type] || ZC.renderMap['default'];
    };

    /**
     * The default graph renderer. This simply displays
     * a europa graph for each result returned.
     **/
    ZC.registerComponentGraphRenderer('default',
        function (meta_type, uid, graphId, allOnSame, data) {
            var id, graph, graphTitle, i, graphs = [];
            for (i = 0; i < data.length; i++) {
                graph = data[i];
                graphTitle = graph.contextTitle || graph.title;
                delete graph.title;
                id = Ext.id();
                graphs.push(Ext.applyIf(graph, {
                    xtype: 'europagraph',
                    uid: uid,
                    graphId: id,
                    allOnSame: allOnSame,
                    graphTitle: graphTitle,
                    ref: id,
                    height: 500
                }));
            }
            return graphs;
        });

    var CURRENT_TIME = "0s-ago",
        DATE_RANGES = [
            ["1h-ago", _t('Last Hour')],
            ["1d-ago", _t('Last 24 Hours')],
            ["7d-ago", _t('Last Week')],
            ["30d-ago", _t('Last 30 days')],
            ["1y-ago", _t('Last Year')]
        ],
        RANGE_TO_MILLISECONDS = {
            '1h-ago': 3600000,
            '1d-ago': 86400000,
            '7d-ago': 604800000,
            '30d-ago': 2419200000,
            '1y-ago': 31536000000
        };

        /*
         * If a given request is over GRAPHPAGESIZE then
         * the results will be paginated.
         * Lower the number of graphs that are displayed for IE
         * since it dramatically speeds up the rendering speed.
         **/
        GRAPHPAGESIZE = Ext.isIE ? 25 : 50;
        /**
         * An example of using a custom renderer to show stacked graphs
         * for processes if you are viewing the memory or cpu and
         * viewing all the graphs on the same page.
         * Notice that it uses the default renderer to actually
         * construct the graphs.
         **/
        ZC.registerComponentGraphRenderer('OSProcess',
            function (meta_type, uid, graphId, allOnSame, data) {
                var fn = ZC.getComponentGraphRenderer('default'), graphs, i;
                for (i = 0; i < data.length; i++) {
                    if (allOnSame && (graphId === 'Memory' || graphId === 'CPU Utilization')) {
                        data[i].type = 'area';
                    }
                }

                graphs = fn(meta_type, uid, graphId, allOnSame, data);
                return graphs;
            });

    var tbarCmpGrphConfig = [
        '->',
        "-",
        {
            xtype: 'drangeselector',
            cls: 'drange_select',
            labelWidth: 40,
            labelAlign: "right",
            listeners: {
                select: function (self, records, index) {
                    var value = records[0].data.id,
                        panel = self.up("componentgraphpanel");

                    // if value is "custom", then reveal the date
                    // picker container
                    if (value === "custom") {
                        panel.showDatePicker();

                        // if user selected the separator, select custom
                    } else if (value === 0) {
                        self.setValue("custom");
                        panel.showDatePicker();

                        // otherwise, update graphs
                    } else {
                        // all ranges are relative to now, so set
                        // end to current time
                        panel.setEndToNow();
                        panel.hideDatePicker();
                        // update drange and start values based
                        // on the new end value
                        panel.setDrange(value);
                    }
                }
            }
        },
        {
            xtype: "container",
            layout: "hbox",
            cls: "date_picker_container",
            padding: "0 10 0 0",
            items: [
                {
                    xtype: 'utcdatefield',
                    cls: 'start_date',
                    width: 175,
                    fieldLabel: _t('Start'),
                    labelWidth: 40,
                    labelAlign: "right",
                    format: 'Y-m-d H:i:s',
                    displayTZ: Zenoss.USER_TIMEZONE,
                    listeners: {
                        change: function (self, val) {
                            var panel = self.up("componentgraphpanel");
                            //update graphpanel.start with *UTC time*
                            //NOTE: panel.start should *always* be UTC!
                            panel.start = moment.utc(self.getValue());
                            panel.refresh();
                        }
                    }
                }, {
                    xtype: 'utcdatefield',
                    cls: 'end_date',
                    width: 175,
                    fieldLabel: _t('End'),
                    labelWidth: 40,
                    labelAlign: "right",
                    disabled: true,
                    format: 'Y-m-d H:i:s',
                    displayTZ: Zenoss.USER_TIMEZONE,
                    listeners: {
                        change: function (self, val) {
                            var panel = self.up("componentgraphpanel");
                            //update graphpanel.end with *UTC time*
                            //NOTE: panel.end should *always* be UTC!
                            panel.end = moment.utc(self.getValue());
                            panel.refresh();
                        }
                    }
                }, {
                    xtype: 'checkbox',
                    cls: 'checkbox_now',
                    fieldLabel: _t('Now'),
                    labelWidth: 40,
                    labelAlign: "right",
                    checked: true,
                    listeners: {
                        change: function (self, val) {
                            var panel = self.up("componentgraphpanel");
                            panel.query("datefield[cls='end_date']")[0].setDisabled(val);

                            // if it should be now, update it
                            if (val) {
                                panel.setEndToNow();
                                panel.refresh();
                            }
                        }
                    }
                }
            ]
        },
        '-',
        {
            xtype: 'compgraphrefreshbutton',
            ref: '../refreshmenu',
            iconCls: 'refresh',
            handler: function (button) {
                var panel = button.up("componentgraphpanel");
                if (panel && panel.isVisible()) {
                    panel.refresh();
                }
            }
        },
        '-',
        {
            xtype: 'button',
            ref: '../newwindow',
            iconCls: 'newwindow',
            hidden: false,
            handler: function (btn) {
                var panel = btn.refOwner;
                var config = panel.initialConfig,
                    win = Ext.create('Zenoss.dialog.BaseWindow', {
                        cls: 'white-background-panel',
                        layout: 'fit',
                        items: [Ext.apply(config, {
                            id: 'component_graphs_window',
                            xtype: 'componentgraphpanel',
                            ref: 'componentgraphPanel',
                            uid: panel.uid,
                            newWindowButton: false
                        })],
                        maximized: true
                    });
                win.show();
                win.componentgraphPanel.setContext(panel.uid);
            }
        }
    ];


    Ext.define("Zenoss.form.ComponentGraphPanel", {
        alias: ['widget.componentgraphpanel'],
        extend: "Ext.Panel",

        cls: 'compgraphpanel',
        layout: 'column',
        pan_factor: 1.25,

        constructor: function (config) {
            config = config || {};
            var me = this,
                ZSDTR = Zenoss.settings.defaultTimeRange || 0;
            // var userColumns = Zenoss.settings.graphColumns || 1;
            Ext.applyIf(config, {
                drange: DATE_RANGES[ZSDTR][0],
                newWindowButton: true,
                bodyStyle: {
                    overflow: 'auto',
                    paddingTop: '15px'
                },
                tbar: [{
                    xtype: 'combo',
                    queryMode: 'local',
                    fieldLabel: _t('Component'),
                    displayField: 'name',
                    valueField: 'value',
                    ref: '../component',
                    labelWidth: 80,
                    width: 200,
                    listConfig: {
                        minWidth: 115
                    },
                    matchFieldWidth: false,
                    listeners: {
                        scope: me,
                        select: me.onSelectComponentType
                    }
                },{
                    xtype: 'combo',
                    disabled: true,
                    queryMode: 'local',
                    labelAlign: 'left',
                    labelWidth: 45,
                    ref: '../graphTypes',
                    fieldLabel: _t('Graph'),
                    displayField: 'name',
                    valueField: 'name',
                    matchFieldWidth: false,
                    width: 200,
                    listConfig: {
                        minWidth: 150
                    },
                    listeners: {
                        scope: me,
                        select: me.onSelectGraph
                    }
                },{
                    xtype: 'textfield',
                    name: 'graphsOnSame',
                    ref: '../graphsOnSame',
                    fieldLabel: 'Amount',
                    allowBlank: false,
                    width: 90,
                    value: 50,
                    labelSeparator: "",
                    labelWidth: 60,
                },{
                    xtype: 'checkbox',
                    baseCls: 'zencheckbox_allonsame',
                    boxLabel: _t('on same graph'),
                    boxLabelAlign: 'before',
                    labelAlign: 'right',
                    margin: '0 10 0 20',
                    ref: '../allOnSame',
                    listeners: {
                         change: function () {
                             me.updateGraphs(0)
                         },
                         scope: me
                    }
                },{
                    xtype: 'button',
                    text: '&lt;',
                    width: 40,
                    handler: function (btn, e) {
                        panel = btn.up("componentgraphpanel");
                        panel.panLeft();
                    },
                    scope: me
                }, {
                    xtype: 'button',
                    text: _t('Zoom In'),
                    handler: function (btn, e) {
                        panel = btn.up("componentgraphpanel");
                        panel.zoomIn();
                    },
                    scope: me
                }, {
                    xtype: 'button',
                    text: _t('Zoom Out'),
                    handler: function (btn, e) {
                        panel = btn.up("componentgraphpanel");
                        panel.zoomOut();
                    },
                    scope: me
                }, {
                    xtype: 'button',
                    text: '&gt;',
                    width: 40,
                    handler: function (btn, e) {
                        panel = btn.up("componentgraphpanel");
                        panel.panRight();
                    },
                    scope: me
                }, {
                    xtype: 'aggregationbutton',
                    margin: '0 10 0 10',
                    stateId: config.id,
                    ref: '../aggregationMenu',
                    text: _t('Avg'),
                    aggregation: 'avg',
                    menuHandler: me.aggregationOnChange,
                    scope: me
                }].concat(tbarCmpGrphConfig)
            });

            Zenoss.form.ComponentGraphPanel.superclass.constructor.call(this, config);
            me.refreshTbarConfigs();
        },
        refreshTbarConfigs: function() {
            this.toolbar = this.getDockedItems()[0];

            this.startDatePicker = this.toolbar.down("utcdatefield[cls='start_date']");
            this.endDatePicker = this.toolbar.down("utcdatefield[cls='end_date']");
            this.nowCheck = this.toolbar.down("checkbox[cls='checkbox_now']");
            this.startDatePicker.setDisplayTimezone(Zenoss.USER_TIMEZONE);
            this.endDatePicker.setDisplayTimezone(Zenoss.USER_TIMEZONE);

            // grab default timerange value from user settings
            this.toolbar.down("drangeselector[cls='drange_select']").setValue(this.drange);
            this.drange = this.rangeToMilliseconds(this.drange);

            // default start and end values in UTC time
            // NOTE: do not apply timezone adjustments to these values!
            this.start = moment.utc().subtract(this.drange, "ms");
            this.setEndToNow();

            // set start and end dates
            this.updateStartDatePicker();
            this.updateEndDatePicker();

            this.hideDatePicker();

            if (this.hideToolbar) {
                this.toolbar.hide();
            }
        },

        aggregationOnChange: function(t, e) {
            Ext.each(this.getGraphs(), function(g) {
                g.aggregationOnChange(t);
            });
            t.up('button').setText(t.text);
            this.aggregationMenu.aggregation = t.itemId;
            this.aggregationMenu.fireEvent('change');
        },

        setContext: function (uid) {
            this.uid = uid;
            if (this.newwindow) {
                if (this.newWindowButton) {
                    this.newwindow.show();
                } else {
                    this.newwindow.hide();
                }
            }
            Zenoss.remote.DeviceRouter.getGraphDefintionsForComponents({
                uid: this.uid
            }, this.updateComboStores, this);
        },
        updateComboStores: function (response) {
            if (response.success) {
                this.componentGraphs = response.data;

                // create the component drop down store
                var data = [], componentType;
                for (componentType in this.componentGraphs) {
                    if (this.componentGraphs.hasOwnProperty(componentType) && this.componentGraphs[componentType].length) {
                        data.push([Zenoss.component.displayName(componentType)[0],
                            componentType]);
                    }

                }
                var store = Ext.create('Ext.data.Store', {
                    model: 'Zenoss.model.NameValue',
                    data: data
                });
                this.component.bindStore(store, true);
                if (data.length) {
                    this.component.select(data[0][0]);
                    this.onSelectComponentType(this.component, [
                        this.component.store.getAt(0)
                    ]);
                }
            }
        },
        onSelectComponentType: function (combo, selected) {
            this.compType = selected[0].get('value');
            var store, i, graphIds = this.componentGraphs[this.compType], data = [];
            // set lastShown 0 to reset pagination limits
            this.lastShown = 0;
            for (i = 0; i < graphIds.length; i++) {
                data.push([
                    graphIds[i]
                ]);
            }
            store = Ext.create('Ext.data.Store', {
                model: 'Zenoss.model.Name',
                data: data
            });
            this.graphTypes.bindStore(store, true);
            if (!data.length) {
                this.graphTypes.disable();
            } else {
                this.graphTypes.enable();
                this.graphTypes.select(data[0][0]);
                // go ahead and show the graphs for the first
                // selected option
                this.onSelectGraph(this.graphTypes,
                    [this.graphTypes.store.getAt(0)]
                );
            }
        },
        onSelectGraph: function (combo, selected) {
            // go to the server and return a list of graph configs
            // from which we can create EuropaGraphs from
            var graphId = selected[0].get('name');
            this.lastShown = 0;
            this.graphId = graphId;
            this.updateGraphs();

        },
        updateGraphs: function (lastShown) {
            var meta_type = this.compType, uid = this.uid,
                graphId = this.graphId, allOnSame = this.allOnSame.checked,
                graphsOnSame = parseInt(this.graphsOnSame.getValue()),
                me = this,
                start = lastShown === undefined ? this.lastShown : lastShown,
                end = start + GRAPHPAGESIZE;
                if (isNaN(graphsOnSame)){
                    // set to default value
                    graphsOnSame = 50
                }

                if (graphId !== undefined) {
                    Zenoss.remote.DeviceRouter.getComponentGraphs({
                        uid: uid,
                        meta_type: meta_type,
                        graphId: graphId,
                        graphsOnSame: graphsOnSame,
                        allOnSame: allOnSame,
                        limit: {'start': start, 'end': end},
                    }, function (response) {
                        if (response.success) {
                            var graphs = [], fn;
                            fn = ZC.getComponentGraphRenderer(meta_type);
                            graphs = fn(meta_type, uid, graphId, allOnSame, response.data);
                            this.removeAll();

                            // grab user-specified column count
                            var colCount = Zenoss.settings.graphColumns || 1;

                            if (Zenoss.settings.graphColumns === 0) {
                                // if setting is Auto then choose columns based on screen width
                                // on load/reload, only center_panel is present
                                var centerPanel = Ext.getCmp('center_panel').getEl().getWidth() - 277;
                                // on resize, query panel directly -- sidebar may not be 277px
                                var extra_column_threshold = 1000;
                                var componentGraphsPnl = this.getEl().getWidth();
                                var panelWidth = componentGraphsPnl ? componentGraphsPnl : centerPanel;
                                colCount = panelWidth > extra_column_threshold ? 2 : 1;
                            }

                            // reduce column count if graphs would not fill columns
                            colCount = Math.min(graphs.length, colCount);

                            var grCols = [], i, c;
                            for (i = 0; i < colCount; i++) {
                                grCols.push({
                                    xtype: 'container',
                                    items: [],
                                    columnWidth: 1 / colCount
                                });
                            }

                        // set up for the next page
                        this.lastShown = end;

                        var gp = {
                            'drange': this.rangeToMilliseconds(this.drange),
                            'end': this.end.valueOf(),
                            'start': this.start.valueOf()
                        };

                        // push graphs into appropriate column
                        for (i = 0; i < graphs.length; i++) {
                            c = i % colCount;
                            graphs[i].graph_params = gp;
                            graphs[i].aggregation = this.aggregationMenu.aggregation;
                            graphs[i].aggregationText = this.aggregationMenu.getText();
                            grCols[c].items.push(graphs[i]);
                        }
                        // if we have more to show, add a button
                        if ((response.data_length - end) > 0) {
                            grCols[c].items.push({
                                xtype: 'button',
                                text: _t('Show more results...'),
                                handler: function(t) {
                                    t.hide();
                                    // will show the next page by looking at this.lastShown
                                    me.updateGraphs()
                                }
                            })
                        }
                        this.add(grCols);
                    }
                }, this);
            }
        },
        rangeToMilliseconds: function (range) {
            if (RANGE_TO_MILLISECONDS[range]) {
                return RANGE_TO_MILLISECONDS[range];
            }
            return range;
        },
        setLimits: function (start, end) {
            // TODO - validate end is greater than start
            this.start = moment.utc(start);
            this.end = moment.utc(end);

            // these limits require a custom date range
            this.drange = end - start;

            // set the range combo to custom
            this.toolbar.query("drangeselector[cls='drange_select']")[0].setValue("custom");

            // uncheck `now` checkbox since we're using a custom range
            this.nowCheck.setValue(false);

            this.showDatePicker();

            //  set the start and end dates to the selected range.
            this.updateStartDatePicker();
            this.updateEndDatePicker();
        },
        setEndToNow: function () {
            this.end = moment.utc();
            this.updateEndDatePicker();

            // if the "now" checkbox is set and range isn't custom, start time should be updated as well
            if (this.nowCheck.getValue() && this.toolbar.query("drangeselector")[0].getValue() !== "custom") {
                this.start = this.end.clone().subtract(this.drange, "ms");
                this.updateStartDatePicker();
            }
        },
        updateStartDatePicker: function () {
            this.startDatePicker.suspendEvents();
            this.startDatePicker.setValue(this.start.valueOf(), false);
            this.startDatePicker.resumeEvents(false);
        },
        updateEndDatePicker: function () {
            this.endDatePicker.suspendEvents();
            this.endDatePicker.setValue(this.end.valueOf(), false);
            this.endDatePicker.resumeEvents(false);
        },
        hideDatePicker: function () {
            // hide date picker stuff
            this.toolbar.query("container[cls='date_picker_container']")[0].hide();
        },
        showDatePicker: function () {
            // show date picker stuff
            this.toolbar.query("container[cls='date_picker_container']")[0].show();
        },
        setDrange: function (drange) {
            this.drange = drange || this.drange;

            // if drange is relative measurement, convert to ms
            if (!Ext.isNumeric(this.drange)) {
                this.drange = this.rangeToMilliseconds(this.drange);
            }

            // check `now` checkbox since drange is always set from now
            this.nowCheck.setValue(true);

            // update start to reflect new range
            this.start = this.end.clone().subtract(this.drange, "ms");

            this.refresh();
        },
        refresh: function () {
            // if end should be set to `now`, set it
            if (this.nowCheck.getValue()) {
                this.setEndToNow();
            }

            var graphConfig = {
                drange: this.drange,
                // start and end are moments so they need to be
                // converted to millisecond values
                start: this.start.valueOf(),
                end: this.end.valueOf()
            };

            // if we are rendered but not visible do not refresh
            if (this.isVisible()) {
                var gs = this.getGraphs();
                Ext.each(this.getGraphs(), function (g) {
                    g.fireEvent("updateimage", graphConfig, this);
                });
            }
            this.updateStartDatePicker();
            this.updateEndDatePicker();
        },
        getGraphs: function () {
            return this.query('europagraph');
        },
        panLeft: function () {
            var curRange = this.rangeToMilliseconds(this.drange);
            var panAmt = Math.round(curRange - curRange / this.pan_factor);
            var newstart = this.start + panAmt > 0 ? this.start - panAmt : 0;
            var newend = parseInt(newstart + curRange);

            this.setLimits(newstart, newend);
            this.refresh();
        },
        panRight: function () {
            var curRange = this.rangeToMilliseconds(this.drange);
            var panAmt = Math.round(curRange - curRange / this.pan_factor);
            var newstart = this.start + panAmt > 0 ? this.start + panAmt : 0;
            var newend = parseInt(newstart + curRange);

            this.setLimits(newstart, newend);
            this.refresh();
        },
        zoomIn: function () {
            var curRange = this.rangeToMilliseconds(this.drange);
            var zoomedRange = Math.round(curRange / this.pan_factor);
            var delta = Math.floor((curRange - zoomedRange));
            var newstart = this.start + delta > 0 ? this.start + delta : this.start;
            var newend = parseInt(newstart + zoomedRange);

            this.setLimits(newstart, newend);
            this.refresh();
        },
        zoomOut: function () {
            var curRange = this.rangeToMilliseconds(this.drange);
            var zoomedRange = Math.round(curRange * this.pan_factor);
            var delta = Math.floor((zoomedRange - curRange));
            var newstart = this.start - delta > 0 ? this.start - delta : this.start;
            var newend = parseInt(newstart + zoomedRange);

            this.setLimits(newstart, newend);
            this.refresh();
        },
        convertStartToAbsoluteTime: function (start) {
            if (Ext.isNumber(start)) {
                return start;
            }
            return parseInt(new Date() - this.rangeToMilliseconds(start));
        },
        convertEndToAbsolute: function (end) {
            if (end === CURRENT_TIME) {
                return now();
            }
            return end;
        },
        rangeToMilliseconds: function (range) {
            if (RANGE_TO_MILLISECONDS[range]) {
                return RANGE_TO_MILLISECONDS[range];
            }
            return range;
        },
        zoomUpdate: function (gp) {
            this.setLimits(gp.start, gp.end);
            this.refresh();
        }

    });

    Ext.define("Zenoss.form.CompGraphRefreshButton", {
        alias: ['widget.compgraphrefreshbutton'],
        extend: "Zenoss.RefreshMenuButton",
        constructor: function (config) {
            config = config || {};
            var menu = {
                xtype: 'statefulrefreshmenu',
                id: config.stateId || Ext.id(),
                trigger: this,
                items: [{
                    cls: 'refreshevery',
                    text: _t('Refresh every')
                }, {
                    xtype: 'menucheckitem',
                    text: _t('1 minute'),
                    value: 60,
                    group: 'refreshgroup'
                }, {
                    xtype: 'menucheckitem',
                    text: _t('5 minutes'),
                    value: 300,
                    group: 'refreshgroup'
                }, {
                    xtype: 'menucheckitem',
                    text: _t('10 Minutes'),
                    value: 600,
                    group: 'refreshgroup'
                }, {
                    xtype: 'menucheckitem',
                    text: _t('30 Minutes'),
                    checked: true,
                    value: 1800,
                    group: 'refreshgroup'
                }, {
                    xtype: 'menucheckitem',
                    text: _t('1 Hour'),
                    value: 3600,
                    group: 'refreshgroup'
                }, {
                    xtype: 'menucheckitem',
                    text: _t('Manually'),
                    value: -1,
                    group: 'refreshgroup'
                }]
            };
            Ext.apply(config, {
                menu: menu
            });
            this.callParent(arguments);
        }
    });

}());
