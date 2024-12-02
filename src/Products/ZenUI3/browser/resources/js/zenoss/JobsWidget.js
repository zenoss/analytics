/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2012, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function () {

Ext.ns('Zenoss');

var REMOTE = Zenoss.remote.JobsRouter;

function lengthOrZero(o) {
    if (o) {
        return o;
    }
    return 0;
}

function isObjectEmpty(o) {
    for (var i in o) {
        if (o.hasOwnProperty(i)) {
             return false;
        }
    }
    return true;
}

function jobLinkRenderer(value, metadata, record) {
    var job = record.data,
    description = job.description;
    description = description.length > 58 ? description.substring(0, 55) + '...' : description;
    // Not htmlEncod()ing the 'description' below, as it's already coming to use encoded
    return "<a href='/zport/dmd/joblist#jobs:" + job.uuid + "'>" + description + "</a>";
}

function readableRenderer(value, metadata, record) {
    var adjective,
        job = record.data,
        date = new Date(0);
    switch (job.status) {
        case "SUCCESS":
            adjective = _t("Finished");
            break;
        case "STARTED":
            adjective = _t("Started");
            break;
        case "PENDING":
            adjective = _t("Scheduled");
            break;
    }
    date.setUTCSeconds(value);
    return adjective + " " + date.readable(1);
}

Ext.define("Zenoss.model.Job", {
    extend: 'Ext.data.Model',
    idProperty: 'uuid',
    fields: [
        'uuid',
        'type',
        'description',
        'scheduled',
        'started',
        'finished',
        'status',
        'user'
    ]
});

var runningJobsStore = Ext.create('Ext.data.Store', {
    model: 'Zenoss.model.Job',
    initialSortColumn: 'running'
});

var pendingJobsStore = Ext.create('Ext.data.Store', {
    model: 'Zenoss.model.Job',
    initialSortColumn: 'pending'
});

var finishedJobsStore = Ext.create('Ext.data.Store', {
    model: 'Zenoss.model.Job',
    initialSortColumn: 'finished'
});

Ext.define("Zenoss.JobsWidget", {
    alias: ['widget.jobswidget'],
    extend: "Ext.Button",
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            menuAlign: 'br-tr?',
            menu: {
                layout: 'fit',
                plain: true,
                bodyStyle: 'background:transparent;padding:0;border:0',
                style: 'background:transparent;padding:0;border:0',
                items: [{
                    xtype: 'container',
                    width: 425,
                    style: {
                        border: '1px solid #444',
                        '-webkit-border-radius': 5,
                        '-moz-border-radius': 5,
                        '-ms-border-radius': 5,
                        borderRadius: 5
                    },
                    items: [{
                        id: 'nojobspanel',
                        xtype: 'panel',
                        bodyStyle: 'padding:4px',
                        hidden: true,
                        html: _t('No jobs')
                    },{
                        id: 'jobs-grid-running',
                        xtype: 'grid',
                        hideHeaders: true,
                        forceFit: true,
                        stateful: false,
                        disableSelection: true,
                        title: _t('Running jobs'),
                        store: runningJobsStore,
                        columns: [{
                            header: 'description',
                            dataIndex: 'description',
                            renderer: jobLinkRenderer
                        }, {
                            header: 'started',
                            dataIndex: 'started',
                            renderer: readableRenderer,
                            width: 150
                        }]
                    },{
                        id: 'jobs-grid-retry',
                        xtype: 'grid',
                        hideHeaders: true,
                        forceFit: true,
                        stateful: false,
                        disableSelection: true,
                        title: _t('Retry jobs'),
                        store: pendingJobsStore,
                        columns: [{
                            header: 'description',
                            dataIndex: 'description',
                            renderer: jobLinkRenderer
                        }, {
                            header: 'scheduled',
                            dataIndex: 'scheduled',
                            renderer: readableRenderer,
                            width: 150
                        }]
                    },{
                        id: 'jobs-grid-pending',
                        xtype: 'grid',
                        hideHeaders: true,
                        forceFit: true,
                        stateful: false,
                        disableSelection: true,
                        title: _t('Pending jobs'),
                        store: pendingJobsStore,
                        columns: [{
                            header: 'description',
                            dataIndex: 'description',
                            renderer: jobLinkRenderer
                        }, {
                            header: 'scheduled',
                            dataIndex: 'scheduled',
                            renderer: readableRenderer,
                            width: 150
                        }]
                    },{
                        id: 'jobs-grid-finished',
                        xtype: 'grid',
                        hideHeaders: true,
                        forceFit: true,
                        stateful: false,
                        disableSelection: true,
                        title: _t('Finished jobs'),
                        store: finishedJobsStore,
                        columns: [{
                            header: 'description',
                            dataIndex: 'description',
                            renderer: jobLinkRenderer,
                            width:60,
                            flex: 1
                        }, {
                            header: 'finished',
                            dataIndex: 'finished',
                            renderer: readableRenderer,
                            width: 150
                        }]
                    },{
                        xtype: 'panel',
                        id: 'more-jobs-link',
                        bodyStyle: 'font-size:11px; padding:3px; padding-left: 5px',
                        html: '<a href="/zport/dmd/joblist">More...</a>'
                    }]
                }]
            }
        });
        this.lastchecked = 0;
        this.callParent([config]);
        this.on('beforerender', this.on_render, this, {single:true});
        this.pollTask = new Ext.util.DelayedTask(this.poll, this);
    },
    initComponent: function() {
        this.lastchecked = Ext.util.Cookies.get('jobswidget_update') || 0;
        this.callParent(arguments);
    },
    on_render: function() {
        this.menucontainer = this.menu.items.items[0];
        this.init_tip();
        // initially delay before rending the jobs widget so that
        // other, more important, router requests have time to complete.
        this.pollTask.delay(2000);
    },
    initEvents: function() {
        this.callParent(arguments);
        this.addEvents('update');
        // Listen to Direct requests for job results
        Ext.Direct.on('event', function(e) {
            if (Ext.isDefined(e.result) && e.result && Ext.isDefined(e.result.new_jobs)) {
                Ext.each(e.result.new_jobs, function(job) {
                    this.alert_new(job);
                }, this);
            }
        }, this);
    },
    init_tip: function() {
        var me = this,
            klass = Ext.ClassManager.getByAlias("widget.tooltip"),
            tip = this.tip = Ext.create('Ext.tip.ToolTip', {
                target: this,
                dismissDelay: 9000,
                show: function() {
                    klass.prototype.show.call(this);
                    this.triggerElement = me.el;
                    this.clearTimer('hide');
                    this.targetXY = this.el.getAlignToXY(me.el, 'br-tr', [-15, -18]);
                    klass.prototype.show.call(this);
                }
            });
        tip.mun(this, 'mouseover', tip.onTargetOver, tip);
        tip.mun(this, 'mouseout', tip.onTargetOut, tip);
        tip.mun(this, 'mousemove', tip.onMouseMove, tip);
    },
    alert: function(msg) {
        if (this.tip.isVisible()) {
            msg = this.tip.body.dom.innerHTML + '<br/><br/>' + msg;
        }
        this.tip.update(msg);
        this.tip.show();
    },
    alert_new: function(job) {
        this.alert("<b>New job</b>: " + Ext.htmlEncode(job.description));
    },
    alert_finished: function(job) {
        this.alert("<b>Finished job</b>: " + Ext.htmlEncode(job.description));
    },
    poll: function() {
        this.update();
        this.pollTask.delay(Zenoss.settings.zenjobsRefreshInterval * 1000);
    },
    pause: function() {
        this.pollTask.cancel();
    },
    check_for_recently_finished: function(jobs) {
        if (Ext.isDefined(jobs.SUCCESS)) {
            Ext.each(jobs.SUCCESS, function(job) {
                if (job.finished >= this.lastchecked) {
                    this.alert_finished(job);
                }
            }, this);
        }
        this.set_lastchecked();
    },
    update_button: function(totals) {
        var pending = lengthOrZero(totals.PENDING),
            retry = lengthOrZero(totals.RETRY),
            running = lengthOrZero(totals.STARTED),
            text, cl, jobText;
        if (!pending && !running) {
            text = _t("0 Jobs");
            cl = 'circle_arrows_still';
        } else {
            if (running > 1 ) {
                jobText = " Jobs";
            }else {
                jobText = " Job";
            }
            unfinished = pending + retry;
            unfinished_text = (retry == 0) ? " Pending" : " Pending/Retry";
            text = running + jobText + " ("+ unfinished + unfinished_text + ")";
            cl = 'circle_arrows_ani';
        }
        this.setIconCls(cl);
        this.setText(text);
    },
    update_menu: function(jobs) {
        if (!isObjectEmpty(jobs)) {
            Ext.getCmp('nojobspanel').hide();
            Ext.getCmp('jobs-grid-running').setVisible(jobs.STARTED);
            if (jobs.STARTED) {
                runningJobsStore.loadData(jobs.STARTED);
            }
            Ext.getCmp('jobs-grid-retry').setVisible(jobs.RETRY);
            if (jobs.RETRY) {
                pendingJobsStore.loadData(jobs.RETRY);
            }
            Ext.getCmp('jobs-grid-pending').setVisible(jobs.PENDING);
            if (jobs.PENDING) {
                pendingJobsStore.loadData(jobs.PENDING);
            }
            Ext.getCmp('jobs-grid-finished').setVisible(jobs.SUCCESS);
            if (jobs.SUCCESS) {
                finishedJobsStore.loadData(jobs.SUCCESS);
            }
            Ext.getCmp('more-jobs-link').show();
        } else {
            Ext.getCmp('nojobspanel').show();
            Ext.getCmp('jobs-grid-running').hide();
            Ext.getCmp('jobs-grid-retry').hide();
            Ext.getCmp('jobs-grid-pending').hide();
            Ext.getCmp('jobs-grid-finished').hide();
            Ext.getCmp('more-jobs-link').hide();
        }
    },
    set_lastchecked: function() {
        // expires two weeks from now
        var cookieExpires = Ext.Date.add(new Date(), Ext.Date.DAY, 14);
        this.lastchecked = (new Date().getTime()/1000);
        Ext.util.Cookies.set('jobswidget_update', this.lastchecked, cookieExpires);
    },
    update: function() {
        if (!Zenoss.Security.doesNotHavePermission('Manage DMD') && Zenoss.settings.zenjobsRefreshInterval) {
            REMOTE.userjobs({}, function(result){
                if (result && result.jobs) {
                    var jobs = result.jobs;
                    this.update_button(result.totals);
                    this.update_menu(jobs);
                    this.check_for_recently_finished(jobs);
                }

            }, this);
        }
    }
});

})(); // End local namespace
