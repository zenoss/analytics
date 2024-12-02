/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2012, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.onReady(function() {

Ext.ns("Zenoss.jobs");

var REMOTE = Zenoss.remote.JobsRouter;

function renderDate(utcseconds) {
    if (utcseconds) {
        var d = new Date(0);
        d.setUTCSeconds(utcseconds);
        return d.readable(1);
    }
    return "--";
}


Ext.getCmp('center_panel').add({
    layout: 'border',
    hidden: Zenoss.Security.doesNotHavePermission('Manage DMD'),
    items: [{
        id: 'jobs',
        region: 'center',
        xtype: 'basegridpanel',
        uid: '/zport/dmd/JobManager',
        stateful: true,
        stateId: 'jobs',
        store: Ext.create('Zenoss.DirectStore', {
            id: 'jobliststore',
            root: 'jobs',
            autoLoad: true,
            pageSize: Zenoss.settings.zenjobsGridBufferSize,
            initialSortColumn: 'scheduled',
            initialSortDirection: 'DESC',
            totalProperty: 'totalCount',
            model: 'Zenoss.model.Job',
            directFn: REMOTE.getJobs,
            listeners: {
                'load': function(store) {
                    store.loaded = true;
                }
            }
        }),
        columns: [{
            id: 'status',
            dataIndex: 'status',
            header: _t('Status'),
            width: 150,
            sortable: true,
            renderer: function(value) {
                var iconCls = "";
                value = Ext.util.Format.capitalize(value.toLowerCase());
                switch (value) {
                    case "Success":
                        iconCls = "tree-severity-icon-small-clear";
                        break;
                    case "Failure":
                        iconCls = "tree-severity-icon-small-critical";
                        break;
                    case "Aborted":
                        iconCls = "tree-severity-icon-small-warning";
                        break;
                    default:
                        break;
                }
                return "<span style='padding-left:18px;padding-top:2px;' class='"+iconCls+"'>"+value+"</span>";
            }
        },{
            id: 'description',
            dataIndex: 'description',
            header: _t('Description'),
            flex: 3,
            sortable: false,
            // Set renderer here to do nothing to kill one of the default renderers
            // (one in ExtOverrides and one in Renderers) and avoid double-encoding
            renderer: function(value) {
                return value;
            }
        },{
            id: 'scheduled',
            dataIndex: 'scheduled',
            header: _t('Scheduled'),
            width: 150,
            sortable: true,
            renderer: renderDate
        },{
            id: 'started',
            dataIndex: 'started',
            header: _t('Started'),
            width: 150,
            sortable: true,
            renderer: renderDate
        },{
            id: 'finished',
            dataIndex: 'finished',
            header: _t('Finished'),
            width: 150,
            sortable: true,
            renderer: renderDate
        },{
            dataIndex: 'user',
            header: _t('Created By'),
            width: 150,
            sortable: true
        }],
        multiSelect: true,
        selectByToken: function(token) {
            var grid = this,
                store = this.getStore(),
                selectToken = function() {
                    var index = store.indexOfId(token);

                    // if we have a job token selected always expand the panel
                    if (index >= 0) {
                        grid.getSelectionModel().select(index);
                        Ext.getCmp('job_detail_panel').expand();
                    }
                };
            if (!store.loaded) {
                store.on('load', selectToken, this, {single:true});
            } else {
                selectToken();
            }
        },
        title: _t('Background Jobs'),
        tbar: {
            id: 'jobs-toolbar',
            items: [{
                id: 'deletejob-button',
                iconCls: 'delete',
                text: _t('Delete'),
                tooltip: _t('Delete Jobs'),
                handler: function() {
                    var grid = Ext.getCmp('jobs'),
                    jobids = [];
                    Ext.each(grid.getSelectionModel().getSelection(), function(row) {
                        jobids.push(row.data.uuid);
                    });

                    REMOTE.deleteJobs({jobids:jobids}, function() {
                        grid.refresh();
                    });

                }
            },{
                id: 'abortjob-button',
                iconCls: 'suppress',
                text: _t('Abort'),
                tooltip: _t("Abort Jobs"),
                disabled: true,
                handler: function() {
                    var grid = Ext.getCmp('jobs'),
                    jobids = [];
                    Ext.each(grid.getSelectionModel().getSelection(), function(row) {

                        switch (row.data.status) {
                            case 'STARTED':
                            case 'PENDING':
                                jobids.push(row.data.uuid);
                        }

                    });
                    REMOTE.abort({jobids:jobids}, function() {
                        grid.refresh();
                    });
                }
            },'->',{
                id: 'refreshjobs-button',
                xtype: 'refreshmenu',
                ref: 'refreshmenu',
                stateId: 'jobsrefresh',
                iconCls: 'refresh',
                text: _t('Refresh'),
                tooltip: _t('Refresh Job List'),
                handler: function() {
                    var grid = Ext.getCmp('jobs');
                    grid.refresh();
                }
            }]
        },
        listeners: {
            selectionchange: function(grid, selected) {
                var detail_panel = Ext.getCmp('job_detail_panel');
                var enableAbort = false;
                var abort_button = Ext.getCmp('abortjob-button');

                for (var i = 0; i < selected.length; i++) {
                    switch(selected[i].data.status) {
                        case 'STARTED':
                        case 'PENDING':
                            enableAbort = true;
                    }

                    if (enableAbort) {
                        break;
                    }
                }
                if (enableAbort) {
                    abort_button.enable();
                } else {
                    abort_button.disable();
                }

                if (selected.length===1) {
                    detail_panel.setJob.call(detail_panel, selected[0]);
                    Ext.History.add('jobs:' + selected[0].data.uuid);
                } else {
                    detail_panel.update('');
                    if (detail_panel.updateTask) {
                        detail_panel.updateTask.cancel();
                    }
                }
            },
            itemdblclick: function() {
                var detail_panel = Ext.getCmp('job_detail_panel');
                detail_panel.expand();
            }
        }
    },{
        id: 'job_detail_panel',
        title: _t('Job Log'),
        region: 'south',
        split: true,
        collapsible: true,
        collapsed: true,
        collapseMode: 'mini',
        stateful: false,
        height: 400,
        autoScroll: true,
        updateTask: null,
        bodyStyle: 'padding:8px;background:#fff',
        listeners: {
            expand: function(panel) {
                var grid = Ext.getCmp('jobs'),
                    view = grid.getView(),
                    selected = grid.getSelectionModel().getSelection();
                if (selected.length === 0){ // nothing is selected, do something about it.
                    try{
                        grid.getSelectionModel().select(0);
                    }catch(e){// couldn't select anything means there's nothing to select, abort
                        return;
                    }
                }
                if (selected.length > 0) {
                    var index = selected[0].index;
                    //view.focusRow(index);
                    // It takes two. I have no idea why nor do I wish to
                    // spend the time to find out. One scrolls the scroller but
                    // does not update the grid. Two makes it all work.
                    //view.focusRow(index);
                    Ext.defer(function(){
                        view.focusRow(index);
                    }, 500);
                }
                panel.poll();
            },
            collapse: function(panel) {
                if (panel.updateTask) {
                    panel.updateTask.cancel();
                }
            }
        },
        refresh: function() {
            if (this.job === null) {
                return;
            }
            REMOTE.detail({jobid:this.jobid}, function(r){
                var msg = _t("[!] Log file too large for job log screen (viewing last 100 lines). To view full log use link above.");
                var html = Ext.String.format(
                    "<b>Log file: <a href='joblog?job={0}'>{1}</a></b><br/><br/>", this.jobid, r.logfile
                );
                if (r.maxLimit) {
                    html += Ext.String.format(
                        "<b style='color:red;padding-bottom:8px;display:block;'>{0}</b>", msg
                    );
                }
                var preTagFmt = Ext.String.format(
                    "<pre style='{0}'>{1}</pre>",
                    [
                        "font-family:Monaco,monospaced",
                        "font-size:12px",
                        "white-space:pre-wrap",
                        "color:{0}"
                    ].join(';') + ";",
                    "{1}"
                );
                for (var i=0; i < r.content.length; i++) {
                    var color = (i % 2) ? '#b58900' : '#657B83';
                    var line = r.content[i];
                    if (line.indexOf("ERROR") > -1) {
                        color = '#ff0000'; // red
                    }
                    html += Ext.String.format(preTagFmt, color, Ext.htmlEncode(line));
                }
                this.update(html);
                var d = this.body.dom;
                d.scrollTop = d.scrollHeight - d.offsetHeight + 16;
            }, this);
        },
        poll: function() {
            if (!this.collapsed) {
                if (!this.updateTask) {
                    this.updateTask = new Ext.util.DelayedTask(this.poll, this);
                }
                this.refresh();
                var status = this.job.get('status');
                switch (status) {
                    case "STARTED":
                    case "PENDING":
                        this.updateTask.delay(1000);
                        break;
                    case "ABORTED":
                        // Might have updates but only a couple, so let's not
                        // spam the server with requests on a dead job
                        this.updateTask.delay(5000);
                        break;
                }
            }
        },
        setJob: function(job) {
            this.job = job;
            this.jobid = job.get('uuid');
            this.poll();
        }
    }]
});

});
