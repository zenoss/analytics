// Set up the namespace
YAHOO.namespace('zenoss.portlet');

// Cache internally
var YZP = YAHOO.zenoss.portlet;

// A registry for portlets to make themselves known.
YZP.Registry = [];
function register_portlet(klass, name) {
    if (klass in YZP) {
        var constructor = YZP[klass];
        if (Zenoss.PortletManager.fireEvent('beforeregister', name)) {
            YZP.Registry.push([constructor, name]);
        }
    }
}
YZP.register_portlet = register_portlet;

YZP.DEFAULT_SITEWINDOW_URL = YZP.DEFAULT_SITEWINDOW_URL ||
                             "https://help.zenoss.com/zsd#main-contant";

var isIE/*@cc_on=1@*/;

var purge = YAHOO.zenoss.purge;
var setInnerHTML = YAHOO.zenoss.setInnerHTML;

var DDM = YAHOO.util.DragDropMgr;

var Portlet = Class.create();
var PortletContainer = Class.create();
var PortletColumn = Class.create();
var XHRDatasource = Class.create();
var StaticDatasource = Class.create();
var IFrameDatasource = Class.create();
var ExtDatasource = Class.create();
var TableDatasource = Class.create();

var pc_layouts = {
    '1col':   [1, 'yui-b' ],
    '2coleq': [2, 'yui-g' ],
    '2colbs': [2, 'yui-gc'],
    '2colsb': [2, 'yui-gd'],
    '3col':   [3, 'yui-gb']
};

YAHOO.namespace('zenoss.globalPortletContainer');

function getUID(base) {
    return base + new Date().getTime();
}

PortletColumn.prototype = {
    __init__: function(domel, container) {
        this.domel = domel;
        this.container = container;
        new YAHOO.util.DDTarget(this.domel, 'PortletProxy');
        setStyle(this.domel, {'height':'400px'});
    },
    addPortlet: function(portlet, toTop) {
        this.container.portlets[portlet.id] = portlet;
        portlet.PortletContainer = this.container;
        if (toTop) {
            ports = this.getPortlets();
            if (ports.length) {
                first = this.getPortlets()[0];
                insertSiblingNodesBefore(first.container, portlet.render());
            } else {
                appendChildNodes(this.domel, portlet.render());
            }
        } else {
            appendChildNodes(this.domel, portlet.render());
        }
        if (!isIE) new YAHOO.zenoss.DDResize(portlet);
        j = new YZP.PortletProxy(portlet.id, this);
        j.addInvalidHandleId(portlet.resizehandle.id);
        j.addInvalidHandleClass('nodrag');
        this.container.setContainerHeight();
        if (isIE) new YAHOO.zenoss.DDResize(portlet);
    },
    getPortlets: function() {
        els = getElementsByTagAndClassName('div', 'zenoss-portlet', this.domel);
        var portlets = [];
        for (var i=0;i<els.length;i++) {
            var id = els[i].id;
            var portlet = this.container.portlets[id];
            portlets.push(portlet);
        }
        return portlets;
    },
    serialize: function() {
        var portlets = this.getPortlets();
        return map(function(x){return x.serialize()}, portlets);
    }
}

Portlet.prototype = {
    __class__: "YAHOO.zenoss.portlet.Portlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id:"";
        datasource = 'datasource' in args? args.datasource:{};
        title = 'title' in args? args.title:"My Portlet";
        bodyHeight = 'bodyHeight' in args? args.bodyHeight:200;
        refreshTime = 'refreshTime' in args? args.refreshTime:60;
        if (!bodyHeight) bodyHeight = 50;
        this.bodyHeight = bodyHeight;
        this.refreshTime = refreshTime;
        this.PortletContainer = null;
        this.id = id;
        this.handleid = id+'_handle';
        this.isDirty = true;
        this.title = title;
        this.render();
        this.setTitleText(title);
        this.setDatasource(datasource);
        this.calllater = null;
        this.startRefresh(true);
    },
    setDatasource: function(datasource) {
        if (datasource) {
            this.datasource = null;
            this.datasource = datasource;
            if (datasource.__class__=='YAHOO.zenoss.portlet.TableDatasource') {
                this.datasource.get(this.fillTable);
            } else {
                this.datasource.get(this.fill);
            }
        }
    },
    setTitleText: function(text) {
        if (this.titlecont) {
            if (!text) text = "My Portlet";
            setInnerHTML(this.titlecont, text);
            this.title = text;
        }
    },
    empty: function() {
        var els = this.body.childNodes;
        map(purge, els);
        replaceChildNodes(this.body, '');
    },
    fill: function(contents) {
        if (this.body) {
            if (contents.responseText) {
                contents = contents.responseText;
            }
            this.empty();
            setInnerHTML(this.body, contents);
        }
    },
    fillTable: function(contents) {
        var columnDefs = contents.columnDefs;
        var dataSource = contents.dataSource;
        var oConfigs = {};
        if (this.dataTable) {
            oRequest = {'results':dataSource.liveData}
            this.dataTable.onDataReturnInitializeTable(null, oRequest);
        } else {
            addElementClass(this.body, 'yui-skin-sam');
            this.dataTable = new YAHOO.widget.DataTable(
                this.body.id, columnDefs, dataSource, oConfigs);
        }
    },
    toggleSettings: function(state) {
        var show = method(this, function() {
            //this.body.style.marginTop = '-1px';
            showElement(this.settingsPane);
            this.PortletContainer.setContainerHeight();
        });
        var hide = method(this, function() {
            hideElement(this.settingsPane);
            //this.body.style.marginTop = '0';
            this.PortletContainer.setContainerHeight();
        });
        if (state=='hide') hide();
        else if (state=='show') show();
        else if (this.settingsPane.style.display=='none') show();
        else if (this.settingsPane.style.display=='block') hide();
    },
    saveSettings: function(settings) {
        this.refreshTime = settings['refreshTime'];
        this.title = settings['title'];
        this.setTitleText(this.title);
        for (setting in settings) {
            this.datasource[setting] = settings[setting];
        }
        this.setDatasource(this.datasource);
        this.PortletContainer.isDirty = true;
        this.PortletContainer.save();
        this.startRefresh(true);
    },
    submitSettings: function(e, settings) {
        settings = settings || {};
        settings['refreshTime'] = this.refreshRateInput.value || 60;
        settings['title'] = this.titleInput.value;
        this.saveSettings(settings);
        this.toggleSettings('hide');
    },
    destroy: function(suppressSave) {
        this.stopRefresh();
        if ('datatable' in this) this.datatable.destroy();
        purge(this.container);
        removeElement(this.container);
        delete this.PortletContainer.portlets[this.id];
        this.PortletContainer.isDirty = true;
        if (suppressSave!=true)
            this.PortletContainer.save();
    },
    render: function() {
        if (this.isDirty) {
            this.body = DIV({'class':'portlet-body','id':this.id+'_body'},
                            "Portlet Content");
            this.resizehandle = DIV(
                {'class':'resize-handle','id':this.id+'_resizer'}, null);
            this.titlecont = SPAN({'class':'nodrag'}, null);
            this.settingsToggle = DIV({'class':'portlet-settings-toggle'}, null);
            connect(this.settingsToggle, 'onclick', this.toggleSettings);
            this.refreshRateInput = INPUT({'value':this.refreshTime}, null);
            this.titleInput = INPUT({'value':this.title}, null);
            this.settingsSlot = DIV({'id':this.id+'_customsettings',
                'class':'settings-controls'},
               [
                DIV({'class':'portlet-settings-control'}, [
                DIV({'class':'control-label'}, 'Title'),
                 this.titleInput
               ]),
               DIV({'class':'portlet-settings-control'}, [
                DIV({'class':'control-label'}, 'Refresh Rate'),
                 this.refreshRateInput
               ])]);
            this.destroybutton = A(
                {'class':'portlet-settings-control'}, 'Remove Portlet');
            this.savesettingsbutton = BUTTON(
                {'class':'portlet-settings-control'}, 'Save Settings');
            connect(this.savesettingsbutton, 'onclick', this.submitSettings);
            connect(this.destroybutton, 'onclick', this.destroy);
            this.buttonsSlot = DIV({'id':this.id+'_buttonslot',
                'class':'settings-controls buttonslot'},
                    [this.destroybutton, this.savesettingsbutton]);
            this.settingsPane = DIV({'id':this.id+'_settings',
                'class':'portlet-settings'},
                [DIV({'class':'settings-controls'},
                    [this.settingsSlot, this.buttonsSlot]),
                    DIV({'style':'clear:both'}, '')]);
            this.container = DIV({'class':'zenoss-portlet','id':this.id},
               DIV({'class':'zenportlet'},
                [
                 DIV({'class':'portlet-header'},
                  DIV({'class':'tabletitle-container','id':this.handleid},
                   DIV({'class':'tabletitle-left'},
                    DIV({'class':'tabletitle-right'},
                     DIV({'class':'tabletitle-center'},
                     [this.titlecont,this.settingsToggle]
                 ))))),
                DIV(null, this.settingsPane),
                DIV({'class':'portlet-body-outer'},
                    [this.body,this.resizehandle])
                ]));
            this.isDirty = false;
            setStyle(this.body, {'height':this.bodyHeight+'px'});
            hideElement(this.settingsPane);
        }
        return this.container;
    },
    serialize: function() {
        portobj = {
            id: this.id,
            title: this.title,
            datasource: this.datasource,
            bodyHeight: this.bodyHeight,
            refreshTime: this.refreshTime,
            __class__: this.__class__
        };
        return portobj;
    },
    startRefresh: function(firsttime) {
        this.stopRefresh();
        if (!firsttime) this.setDatasource(this.datasource);
        if (this.refreshTime>0)
            this.calllater = callLater(this.refreshTime, this.startRefresh);
    },
    stopRefresh: function() {
        if (this.calllater) {
            this.calllater.cancel();
            this.calllater = null;
        }
    },
    disable: function() {
        this.enable();
        this.cover = DIV({'style':'position:absolute;top:0;left:0;height:100%;width:100%;'},
                    null);
        setStyle(this.body, {'position':'relative'});
        appendChildNodes(this.body, this.cover);
    },
    enable: function() {
        if ('cover' in this) {
            try {
                removeElement(this.cover);
            } catch(e) {
                noop();
            }
        }
        this.cover = null;
    }
}

PortletContainer.prototype = {
    __init__: function(target) {
        this.container = $MK(target);
        this.columns = [];
        this.portlets = {};
        this.columnContainer = null;
        this.isDirty = false;
    },
    goodConnection: function() {
        setInnerHTML($MK('connectionmessage'),
                'Last updated ' + getServerTimestamp() + '.');
    },
    brokenConnection: function() {
        setInnerHTML($MK('connectionmessage'), 'Lost connection to the server.');
    },
    setContainerHeight: function() {
        var heights = [];
        for (var i=0;i<this.columns.length;i++) {
            col = this.columns[i];
            ports = col.getPortlets();
            lastp = ports[ports.length-1]
            if (lastp) {
                cont = lastp.container;
                p = getElementPosition(cont).y;
                h = getElementDimensions(cont).h;
                heights.push(p+h);
            }
        }
        highest = listMax(heights);
        newHeight = highest - 80;
        if (newHeight!=getElementDimensions(this.container).h) {
            setStyle(this.container, {'height':newHeight + 'px'});
            map(function(x){setStyle(x.domel, {'height':newHeight+'px'})},
                this.columns);
        }
    },
    getColumnsAsDisplayed: function() {
        // Due to the CSS, columns are displayed out of order in
        // the 33-33-33 format.
        if (this.numCols()==3) {
            return [this.columns[0], this.columns[1], this.columns[2]];
        } else {
            return this.columns;
        }
    },
    columnElements: function() {
        return map(function(x){return x.domel}, this.columns);
    },
    numCols: function() {
        return this.columns.length;
    },
    leftCol: function() {
        return this.columns[0];
    },
    middleCol: function() {
        if (this.numCols()==3) {
            return this.columns[1];
        } else {
            return this.rightCol();
        }
    },
    rightCol: function() {
        return this.columns[this.columns.length-1];
    },
    addPortlet: function(klass, args) {
        try {
            var portlet = new klass(args);
            this.rightCol().addPortlet(portlet, true);
            this.isDirty = true;
            this.save();
        } catch (e) { noop() }
    },
    fillColumns: function(oldcols) {
        // Passed in an array of arrays of portlets,
        // distribute among current columns.
        // This works because this.middleCol on 2-column
        // layouts returns this.rightCol
        var fillfuncs = [this.leftCol, this.middleCol, this.rightCol];
        for (i=0;i<oldcols.length;i++) {
            var col = fillfuncs[i]();
            var oldcol = oldcols[i];
            for (k=0;k<oldcol.length;k++) {
                col.addPortlet(oldcol[k]);
            }
        }
    },
    getColumnState: function() {
        var curcols = this.getColumnsAsDisplayed();
        var curstate = map(function(x){return x.getPortlets()}, curcols);
        return curstate;
    },
    showLayoutDialog: function() {
        if (!this.configDialog) {
            configDialog = new YAHOO.widget.SimpleDialog("configureDialog",
                { width: "188px",
                  fixedcenter: true,
                  modal: false,
                  visible: false,
                  draggable:true });
            configDialog.setHeader("Column Layout");
            this.configDialog = configDialog;
            var threecol = bind(function(){this.setLayout('3col', true)},this);
            var onecol   = bind(function(){this.setLayout('1col', true)},this);
            var twocoleq = bind(function(){this.setLayout('2coleq', true)},this);
            var twocolsb = bind(function(){this.setLayout('2colsb', true)},this);
            var twocolbs = bind(function(){this.setLayout('2colbs', true)},this);
            var hidedialog = bind(function(){
                //this.configDialog.hide();
                this.configDialog.destroy();
                this.configDialog = null;
            }, this);
            var getImage = function(type) {
                el = DIV({'class':'column-layout-button',
                          'style':'background-image:url(img/icons/'+type+'.png)'
                         }, null);
                var imagehtml = toHTML(el);
                if (isIE) {
                    imagehtml = imagehtml.replace(
                        'align',
                        'style="background-image:url(img/icons/'+type+
                            '.png)" align');
                }
                return imagehtml;
            }
            var mybuttons = [ { text:getImage("1col"),handler:onecol},
                              { text:getImage("2coleq"),handler:twocoleq},
                              { text:getImage("2colsb"),handler:twocolsb},
                              { text:getImage("2colbs"),handler:twocolbs},
                              { text:getImage("3col"),handler:threecol}
                            ];
            configDialog.cfg.queueProperty("buttons", mybuttons);
            addElementClass(this.container, 'yui-skin-sam');
            configDialog.render(this.container);
        }
        this.configDialog.show();
    },
    setLayout: function(layout, makeDirty) {
        if (makeDirty) this.isDirty = true;
        layinfo = pc_layouts[layout];
        colsnum = layinfo[0];
        colsclass = layinfo[1];
        var curstate = this.getColumnState();
        this.columns = [];
        for (var i=0; i<colsnum; i++) {
            var unique = new Date().getTime();
            var unitclass = 'yui-u';
            if (i==0) unitclass += ' first';
            var col = new PortletColumn(DIV({'class':unitclass}, null), this);
            this.columns.push(col);
        }
        this.resetLink = A({'class':"tinylink"}, "Reset Portlets...");
        this.dialogLink = A({'class':"tinylink"}, "Configure layout...");
        this.portDialogLink = A({'class':"tinylink"}, "Add portlet...");
        this.doRefresh = A({'class':"tinylink"}, "Stop Refresh");

        messagebox = DIV({'class':'msgbox', 'id':'connectionmessage'},
            'Last updated ' + getServerTimestamp() + '.');
        connect(this.resetLink, "onclick", this.promptRestoreDefaults);
        connect(this.dialogLink, "onclick", this.showLayoutDialog);
        connect(this.portDialogLink, "onclick", this.showAddPortletDialog);
        connect(this.doRefresh, "onclick", this.stopRefresh);
        var newContainer = DIV({'class':colsclass},
            [DIV({'class':'tinylink-container'}, [
                messagebox,
                 this.doRefresh, this.portDialogLink, this.dialogLink, this.resetLink]),
             this.columnElements()]);
        if (!this.columnContainer) {
            this.columnContainer = newContainer;
            appendChildNodes(this.container, newContainer);
        } else {
            this.columnContainer = swapDOM(
                this.columnContainer, newContainer);
        }
        this.layout = layout;
        if (curstate) this.fillColumns(curstate);
        this.relayout();
        this.save();
    },
    relayout: function() {
        // relayout ext portlets
        Ext.each(this.columns, function(col){
            var i, portlets = col.getPortlets(), fly;
            Ext.suspendLayouts();
            for(i=0;i<portlets.length;i++) {
                if (portlets[i].extPortlet) {
                    fly = Ext.fly(portlets[i].body);
                    portlets[i].extPortlet.setHeight(fly.getHeight() - 5);
                    portlets[i].extPortlet.setWidth(fly.getWidth() - 5);
                }
            }
            Ext.resumeLayouts(true);
        });
    },
    serialize: function() {
        var cols = this.getColumnState();
        var columns = map(
                function(x){
                    return map(function(y){return y.serialize()}, x)
                },
                cols
        );
        var settingsObject = {
            layout: this.layout,
            columns: columns
        };

        var json = serializeJSON(settingsObject);
        return json;
    },
    save: function() {
        if (this.isDirty) {
            var setUrl='/zport/dmd/ZenUsers/setDashboardState';
            doXHR(setUrl, {
                method: 'POST',
                sendContent: this.serialize()
            });
            this.isDirty = false;
        }
    },
    restore: function(state) {
        this.isDirty = false;
        var layout = state.layout;
        var columns = state.columns;
        var newcolumns = [];
        this.setLayout(layout);
        forEach (columns, function(portlets) {
            var thiscolumn = [];
            forEach (portlets, function(portsettings) {
                var dssettings = portsettings.datasource;
                var dsklass = eval(dssettings.__class__);
                var datasource = new dsklass(dssettings);
                portsettings.datasource = datasource;
                var portklass = eval(portsettings.__class__);
                if (portklass) {
                    var p = new portklass(portsettings);
                    thiscolumn.push(p);
                }
            });
            newcolumns.push(thiscolumn);
        });
        this.fillColumns(newcolumns);
    },
    startRefresh: function() {
        for (portlet in this.portlets) {
            p = this.portlets[portlet];
            p.startRefresh(true);
        }
        setInnerHTML(this.doRefresh, "Stop Refresh");
        disconnectAll(this.doRefresh, 'onclick');
        connect(this.doRefresh, 'onclick', this.stopRefresh);
    },
    stopRefresh: function() {
        for (portlet in this.portlets) {
            p = this.portlets[portlet];
            p.stopRefresh();
        }
        setInnerHTML(this.doRefresh, "Start Refresh");
        disconnectAll(this.doRefresh, 'onclick');
        connect(this.doRefresh, 'onclick', this.startRefresh);
    },
    showAddPortletDialog: function() {
        var registry = YZP.Registry,
        i, portletNames = [], me = this;
        for (i=0; i<registry.length; i++) {
            portletNames.push(registry[i][1]);
        }
        portletNames = portletNames.sort();
        var win = Ext.create('Zenoss.dialog.BaseWindow', {
            title: _t('Add Portlet'),
            height: 150,
            width: 250,
            items: [{
                xtype: 'combo',
                labelAlign: 'top',
                ref: 'portlet',
                fieldLabel: _t('Portlet'),
                emptyText: _t('Select One...'),
                store: portletNames
            }],
            buttons: [{
                xtype: 'DialogButton',
                ui: 'dialog-dark',
                text: _t('Add Portlet'),
                handler: function(btn){
                    var portletName = win.portlet.getValue();
                    for (i=0; i<registry.length; i++) {
                        if(registry[i][1] == portletName) {
                            me.addPortlet(registry[i][0]);
                            break;
                        }
                    }
                }
            },{
                xtype: 'DialogButton',
                ui: 'dialog-dark',
                text: _t('Close')
            }]
        });
        win.show();
    },
    promptRestoreDefaults: function() {
        var me = this,
            msg = _t('Are you sure you want restore the default portlets?'),
            win = new Zenoss.dialog.SimpleMessageDialog({
                    message: msg,
                    title: _t('Restore Default Portlets'),
                    buttons: [{
                        xtype: 'DialogButton',
                        text: _t('OK'),
                        handler: function() {
                            me.restoreDefaults();
                        }
                    }, {
                        xtype: 'DialogButton',
                        text: _t('Cancel')
                    }]
                });
        win.show();
    },
    restoreDefaults: function() {
        if (YZP.PortletEvents.fireEvent('restoredefaults', this) === false) {
            return;
        }
        forEach(values(this.portlets), function(p){
            p.destroy(true);
        });
        p1 = new YZP.SiteWindowPortlet({
                id:'welcome',
                title:'Welcome',
                url: YZP.DEFAULT_SITEWINDOW_URL,
                bodyHeight: 500
             });
        //p1 = new YZP.ProdStatePortlet({id:'prodstates'});
        p2 = new YZP.DeviceIssuesPortlet({
                id:'devissues',
                bodyHeight: 150
            });
        //p3 = new YZP.WatchListPortlet({id:'watchlist'});
        p4 = new YZP.GoogleMapsPortlet({
                id:'googlemaps',
                bodyHeight: 310
            });
        //p4 = new YZP.UserMsgsPortlet({id:'usermsgs'});
        this.leftCol().addPortlet(p1);
        //this.leftCol().addPortlet(p2);
        this.middleCol().addPortlet(p2);
        this.rightCol().addPortlet(p4);
        this.save();
    },
    disablePortlets: function() {
        forEach(values(this.portlets), method(this, function(x) {
            x.disable();
        }));
    },
    enablePortlets: function() {
        forEach(values(this.portlets), method(this, function(x) {
            x.enable();
        }));
    }
}

StaticDatasource.prototype = {
    __class__: "YAHOO.zenoss.portlet.StaticDatasource",
    __init__: function(settings) {
        this.settings = settings;
        this.html = settings.html;
    },
    get: function(callback) {
        this.callback = callback;
        r = {responseText:this.html};
        callback(r);
    }
}

XHRDatasource.prototype = {
    __class__: "YAHOO.zenoss.portlet.XHRDatasource",
    __init__: function(settings) {
        this.url = settings.url;
    },
    get: function(callback) {
        this.callback = callback;
        var d = doXHR(this.url);
        d.addCallback(function(r){
            YAHOO.zenoss.globalPortletContainer.goodConnection();
            callback(r);
        });
        d.addErrback(function(){
            YAHOO.zenoss.globalPortletContainer.brokenConnection();
        });
        return d;
    }
}

IFrameDatasource.prototype = {
    __class__: "YAHOO.zenoss.portlet.IFrameDatasource",
    __init__: function(settings) {
        this.url = settings.url;
    },
    get: function(callback) {
        this.callback = callback;
        html = '<iframe src="' + this.url + '" ' +
               'style="border:medium none;margin:0;padding:0;'+
               'width:100%;height:100%;"/>';
        callback({responseText:html});
    }
}

ExtDatasource.prototype = {
    __class__: "YAHOO.zenoss.portlet.ExtDatasource",
    __init__: function(settings) {
        this.extSettings = settings.extSettings || null;
        this.portletId = settings.portletId;
    },
    get: function(callback) {
        var randomId = 'extportlet' + Math.floor(Math.random()*1000000),
            thisPortlet = Zenoss.portlets[this.portletId],
            ds = this;

        html = '<div id="' + randomId + '"' +
               'style="border:medium none;margin:0;padding:0;' +
               'width:100%;height:100%;"></>';
        callback({responseText:html});

        var task = {
            run: function() {
                if (Ext.get(randomId)) {
                    Ext.TaskManager.stop(task);
                    ds.extPortlet = new Ext.Panel(thisPortlet);
                    ds.extPortlet.render(randomId);
                }
            },
            interval: 100
        };
        Ext.TaskManager.start(task);
    }
}

TableDatasource.prototype = {
    __class__: "YAHOO.zenoss.portlet.TableDatasource",
    __init__: function(settings) {
        this.url = settings.url;
        this.queryArguments = 'queryArguments' in settings?
            settings.queryArguments:{};
        this.postContent = 'postContent' in settings?
            settings.postContent:'';
        this.method = 'method' in settings? settings.method:'POST';
        this.useRandomParameter = 'useRandomParameter' in settings?
            settings.useRandomParameter:true;
    },
    get: function(callback) {
        queryarguments = this.queryArguments;
        if ('ms' in queryarguments) delete queryarguments['ms'];
        if (this.useRandomParameter) {
            if ('_dc' in queryarguments) { delete queryarguments['_dc']; }
        } else {
            queryarguments['_dc'] = String(new Date().getTime());
        }
        /*
          doXHR on IE will add post content to queryargs which get passed
          as keyword parameters to backend. We need to get rid of _dc stuff
          altogether and use response headers. For now, we detect if we have
          any query args other that dc and if we are using POST. If so, don't
          add queryargs string to doXHR call. Server side user @nocache
          decorator.
        */
        var d;
        var has_args_other_than_dc = false;
        for (key in queryarguments) {
            if (key != '_dc') {
                has_args_other_than_dc = true;
                break;
            }
        }
        if ((this.method == 'POST') && (has_args_other_than_dc == false)) {
            d = doXHR(this.url, {
                method: this.method,
                sendContent: serializeJSON(this.postContent)
            });
        } else {
            d = doXHR(this.url, {
                method: this.method,
                queryString: queryarguments,
                sendContent: serializeJSON(this.postContent)
            });
        }
        d.addCallback(bind(function(r){
            YAHOO.zenoss.globalPortletContainer.goodConnection();
            this.parseResponse(r, callback)},this));
        d.addErrback(function(){
            YAHOO.zenoss.globalPortletContainer.brokenConnection();
        });
    },
    parseResponse: function(response, callback) {
        response = evalJSONRequest(response);
        var columns = response.columns;
        var colwidths = {};
        forEach(columns, method(this, function(x) {
            if ('widths' in this) {
              if (x in this.widths) colwidths[x] = this.widths[x];
              else if (x=='Events') colwidths[x] = '50px';
              else colwidths[x] = '';
            } else if (x=='Events') {
                colwidths[x] = '50px';
            } else {
                colwidths[x] = '';
            }
        }));
        var mycolumndefs = map(function(x){
            return {key:x,sortable:true,resizeable:true,
                    width:x=colwidths[x]}}, columns);
        var data = response.data;
        if ('datasource' in this) {
            this.datasource.liveData = data;
        } else {
            this.datasource = new YAHOO.util.DataSource(data);
        }
        this.datasource.responseType = YAHOO.util.DataSource.TYPE_JSARRAY;
        this.datasource.responseSchema = {fields:columns};
        callback({columnDefs:mycolumndefs,dataSource:this.datasource});
    },
    __json__: function() {
        queryarguments = this.queryArguments;
        if ('ms' in queryarguments) delete queryarguments['ms'];
        if (this.useRandomParameter && ('_dc' in queryarguments)) {
            delete queryarguments['_dc'];
        } else {
            queryarguments['_dc'] = String(new Date().getTime());
        }
        return {url:this.url, queryArguments:queryarguments,
                postContent: this.postContent, method:this.method,
                __class__:this.__class__}
    }
}


// Portlet drag stuffz
YZP.PortletProxy = function(id, portlet) {
    sGroup = 'PortletProxy';
    config = null;
    YZP.PortletProxy.superclass.constructor.call(
        this, id, sGroup, config);
    var el = this.getDragEl();
    YAHOO.util.Dom.setStyle(el, "opacity", 0.67);
    YAHOO.util.Dom.setStyle(el, "z-index", 10000);
    this.portlet = portlet;
    this.container = portlet.container;
    this.goingUp = false;
    this.lastY = 0;
    this.setHandleElId(id+'_handle');
    this.addInvalidHandleClass('nodrag');
}

YAHOO.extend(YZP.PortletProxy, YAHOO.util.DDProxy, {

    startDrag: function(x, y) {
        var dragEl = this.getDragEl();
        var clickEl = this.getEl();
        setStyle(clickEl, {'visibility':'hidden'});
        nodes = clickEl.childNodes;
        setInnerHTML(dragEl, clickEl.innerHTML);
        this.container.disablePortlets();
    },
    endDrag: function(e) {
        var srcEl = this.getEl();
        var proxy = this.getDragEl();
        setStyle(proxy, {"visibility":""});
        var a = new YAHOO.util.Motion(
            proxy, {
                points: {
                    to: YAHOO.util.Dom.getXY(srcEl)
                }
            },
            0.2,
            YAHOO.util.Easing.easeOut
        )
        var proxyid = proxy.id;
        var thisid = this.id;
        a.onComplete.subscribe(function() {
            YAHOO.util.Dom.setStyle(proxyid, "visibility", "hidden");
            YAHOO.util.Dom.setStyle(thisid, "visibility", "");
        });
        a.animate();
        this.container.enablePortlets();
    },
    onDragDrop: function(e, id) {
        if (DDM.interactionInfo.drop.length === 1) {
            var pt = DDM.interactionInfo.point;
            var region = DDM.interactionInfo.sourceRegion;
            if (!region.intersect(pt)) {
                var destEl = $MK(id);
                var destDD = DDM.getDDById(id);
                destEl.appendChild(this.getEl());
                destDD.isEmpty = false;
                this.container.isDirty = true;
                DDM.refreshCache();
            }
        }
        this.container.setContainerHeight();
        this.container.save();

        // relayout the extjs portlets
        this.container.relayout();
        if (this.container.doRefresh.innerHTML=='Stop Refresh')
            this.container.startRefresh();
    },
    onDrag: function(e) {
        var y = YAHOO.util.Event.getPageY(e);
        if (y<this.lastY) {
            this.goingUp = true;
        } else if (y > this.lastY) {
            this.goingUp = false;
        }
        this.lastY = y;
    },
    onDragOver: function(e, id) {
        var srcEl = this.getEl();
        var destEl = $MK(id);
        if (destEl.className.toLowerCase() == 'zenoss-portlet') {
            var orig_p = srcEl.parentNode;
            var p = destEl.parentNode;
            if (this.goingUp) {
                p.insertBefore(srcEl, destEl);
            } else {
                p.insertBefore(srcEl, destEl.nextSibling);
            }
            DDM.refreshCache();
            this.container.setContainerHeight();
            this.container.isDirty = true;
        }
    }
});

YAHOO.zenoss.DDResize = function(portlet) {
    sGroup = "PortletResize";
    config = {'tickInterval':5};
    panelElId = portlet.id;
    this.portlet = portlet;
    YAHOO.zenoss.DDResize.superclass.constructor.call(
        this, panelElId, sGroup, config);
    this.hasOuterHandles = true;
    this.setOuterHandleElId(portlet.resizehandle.id);
    this.addInvalidHandleId(portlet.handleid);
    this.addInvalidHandleId(portlet.body.id);
    this.addInvalidHandleId(portlet.handleid);
    this.addInvalidHandleId(portlet.container.id);
    this.addInvalidHandleId(portlet.titlecont.id);
    this.addInvalidHandleClass('removelink');
};
YAHOO.extend(YAHOO.zenoss.DDResize, YAHOO.util.DragDrop, {
    onMouseDown: function(e) {
        if (this.portlet.__class__=='YAHOO.zenoss.portlet.GoogleMapsPortlet')
            this.portlet.disable();
        var panel = this.portlet.body;
        this.startWidth = panel.offsetWidth;
        this.startHeight = panel.offsetHeight;
        this.startPos = [YAHOO.util.Event.getPageX(e),
                         YAHOO.util.Event.getPageY(e)];
    },
    onDrag: function(e) {
        if (!this.portlet.cover) this.portlet.disable();
        if (this.portlet.cover) {
            var newPos = [YAHOO.util.Event.getPageX(e),
                          YAHOO.util.Event.getPageY(e)];

            var offsetY = newPos[1] - this.startPos[1];
            var newHeight = Math.max(this.startHeight + offsetY, 10);
            newHeight = newHeight - (Math.abs(newHeight) % 5);
            if (newHeight!=this.portlet.bodyHeight) {
                var panel = this.portlet.body;
                panel.style.height = newHeight + "px";
                this.portlet.bodyHeight = newHeight;
                this.portlet.PortletContainer.setContainerHeight();
                this.portlet.PortletContainer.isDirty = true;
            }
        }
    },
    onDrop: function(e) {
        this.portlet.enable();
    },

    onMouseUp: function(e) {
        this.portlet.enable();
        this.portlet.PortletContainer.save();
        if (this.portlet.extPortlet) {
            var fly = Ext.fly(this.portlet.body);
            this.portlet.extPortlet.setHeight(fly.getHeight() - 5);
        }
    }

});

YZP.PortletContainer = PortletContainer;
YZP.XHRDatasource = XHRDatasource;
YZP.StaticDatasource = StaticDatasource;
YZP.IFrameDatasource = IFrameDatasource;
YZP.ExtDatasource = ExtDatasource;
YZP.TableDatasource = TableDatasource;
YZP.Portlet = Portlet;
YZP.PortletEvents = Ext.create('Ext.util.Observable', {});
YZP.PortletEvents.addEvents('restoredefaults');
// Tell the loader we're all done!
YAHOO.register("portlet", YZP, {});

Zenoss.PortletManager.fireEvent('ready', YZP);
