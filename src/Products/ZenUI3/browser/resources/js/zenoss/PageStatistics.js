(function(){

    /**
     * Classes for determining when the page is completely loaded. Since this
     * is set per page encapsulate the logic here.
     *
     **/
    Ext.define("Zenoss.stats.ResultsWindow", {
        extend: "Zenoss.dialog.BaseDialog",
        constructor: function(config) {
            var finalTime = config.finalTime,
                loadingTime = config.loadingTime;


            Ext.applyIf(config, {
                title: _t('Page Load Time'),
                defaults: {
                    xtype: 'displayfield'
                },
                items: [{
                    value: Ext.String.format(_t("{0} seconds until the page is ready to use."), loadingTime)
                }, {
                    value: Ext.String.format(_t("{0} seconds in layout and rendering on the client."), (finalTime - Zenoss._pageStartTime).toFixed(2))
                }, {
                    value: Ext.String.format(_t("{0} seconds since ExtJs start time."), (finalTime - (Ext._startTime/1000)).toFixed(2))
                },{
                    value: Ext.String.format(_t("{0} seconds spent in Ajax requests."), (config.ajaxTime).toFixed(2))
                }]

            });
            this.callParent([config]);
        }


    });

    Ext.define("Zenoss.stats.Infrastructure", {
        pageName: 'Infrastructure',
        constructor: function() {
            this.addHooks();
        },
        addHooks: function() {
            // the Infrastructure page is loaded when the both the trees
            // and grid stores are loaded and rendered. Since
            // we don't really load the store until after the Devices tree is rendered
            // we can assume the page is fully loaded when the Device grid has finished loading
            // its store.
            Ext.getCmp('device_grid').getStore().on('load', this.checkReady, this, {single:true});
        },
        getTiming: function() {
            var perf = window.performance || {};
            var fn = perf.now || perf.mozNow || perf.webkitNow || perf.msNow || perf.oNow;
            return fn ? fn.bind(perf) : Ext.emptyFn;
        },
        checkReady: function() {
            // convert from milliseconds to seconds
            var finalTime = new Date().getTime() / 1000.0,
                loadingTime = this.getTiming()(),
                ajaxTime = Ext.Array.sum(Ext.pluck(completedRequests, 'time'));
            // perf data is unavailable, display nothing
            if (!loadingTime) {
                return;
            }

            loadingTime = (loadingTime / 1000.00).toFixed(2);
            Zenoss.remote.DetailNavRouter.recordPageLoadTime({
                page: this.pageName,
                time: loadingTime
            });
            // do not listen to ajax requests anymore
            Ext.Ajax.un('beforerequest', beforeAjaxRequest);
            Ext.Ajax.un('requestcomplete', afterAjaxRequest);
            Ext.getCmp('footer_bar').add(['-', {
                xtype: 'button',
                text: Ext.String.format(_t("{0} seconds"), loadingTime),
                handler: function(){
                    Ext.create('Zenoss.stats.ResultsWindow', {
                        finalTime: finalTime,
                        loadingTime: loadingTime,
                        ajaxTime: ajaxTime
                    }).show();
                }
            }]);
        }


    });

    Ext.define("Zenoss.stats.Events", {
        extend: "Zenoss.stats.Infrastructure",
        pageName: 'EventConsole',
        addHooks: function() {
            Ext.getCmp('events_grid').getStore().on('load', this.checkReady, this, {single:true});
        }

    });

    Ext.define("Zenoss.stats.DeviceDetail", {
        extend: "Zenoss.stats.Infrastructure",
        pageName: 'DeviceDetails',
        addHooks: function() {
            var detailnav = Ext.getCmp('deviceDetailNav');
            detailnav.on('componenttreeloaded', this.checkReady, this, {single:true});
        }

    });

    var openRequests = {}, completedRequests=[];

    /**
     * Uniquely identify each ajax request so that
     * we can match it up when the results come back from the server.
     **/
    function getTransactionId(transaction) {
        if (!transaction) {
            return null;
        }

        if (Ext.isArray(transaction)) {
            var ids = Ext.pluck(transaction, "id");
            return ids.join(" ");
        }
        return transaction.id;
    }

    /**
     * Log the start time and Url of each ajax request that has a transaction
     * associated with it.
     **/
    function beforeAjaxRequest(conn, options) {
        var url = options.url, transactionId = getTransactionId(options.transaction);
        if (transactionId) {
            openRequests[transactionId] = {
                url: url,
                starttime: new Date().getTime()
            };
        }
    }

    /**
     * Log the end time so we can get the total time spent in ajax requests.
     **/
    function afterAjaxRequest(conn, response, options) {
        var url = options.url, endtime = new Date().getTime(), transactionId = getTransactionId(options.transaction);
        if (openRequests[transactionId]) {
            completedRequests.push({
                url: url,
                time: (endtime - openRequests[transactionId].starttime) / 1000.00
            });
            delete openRequests[transactionId];
        }
    }

    Ext.onReady(function() {
        if (Zenoss.settings.showPageStatistics) {
            Ext.Ajax.on('beforerequest', beforeAjaxRequest);
            Ext.Ajax.on('requestcomplete', afterAjaxRequest);
        }
    });
}());