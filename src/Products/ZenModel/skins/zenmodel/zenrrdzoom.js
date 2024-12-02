/*global RefreshManager */
/*
#####################################################
#
# ZenRRDZoom - Pan & Zoom for Zenoss RRDTool graphs
# 2006-12-29
#
#####################################################
*/

Date.prototype.minus = function(secs) {
    return new Date(this.valueOf()-(secs*1000));
}

Date.prototype.toPretty = function() {
    return toISOTimestamp(this);
}

function fixBase64Padding(s) {
    s = s.split('=',1)[0];
    var a = [s];
    for (var i = 0; i <= 4 - (s.length % 4); i++) {
        a.push('=');
    }
    return a.join('');
}

var ZenGraphs = ZenGraphs || {},
    zoom_factor = 1.5,
    pan_factor = 3,
    end_re = /now-([0-9]*)s/,
    start_re = /end-([0-9]*)s/;

Ext.ns('Zenoss');

Zenoss.SWOOPIES = [];
Zenoss.SWOOP_CALLBACKS = {};

Zenoss.SwoopyGraph = Ext.extend(Ext.Panel, {
    constructor: function(config) {
        var cls = Ext.isGecko ? '-moz-zoom-in' :
                  Ext.isWebKit ? '-webkit-zoom-in' :
                  'crosshair';
        config = Ext.applyIf(config||{}, {

            html: {
                tag: 'img',
                src: config.graphUrl,
                id: config.graphId,
                style: 'cursor:' + cls
            },
            tbar: {
                items: [{
                    xtype: 'tbtext',
                    text: config.graphTitle
                },'->',{
                    text: '&lt;',
                    width: 67,
                    handler: Ext.bind(function(btn, e) {
                        this.onPanLeft(this);
                    },this)
                },{
                    text: 'Zoom In',
                    enableToggle: true,
                    pressed: true,
                    itemId: 'zoomin',
                    handler: Ext.bind(function(btn, e) {
                        this.fireEventsToAll("zoommodechange", this, !btn.pressed);
                    }, this)
                },{
                    text: 'Zoom Out',
                    itemId: 'zoomout',
                    enableToggle: true,
                    handler: Ext.bind(function(btn, e) {
                        this.fireEventsToAll("zoommodechange", this, btn.pressed);
                    }, this)
                },{
                    text: '&gt;',
                    width: 67,
                    handler: Ext.bind(function(btn, e) {
                        this.onPanRight(this);
                    }, this)
                }]
            }
        });
        Zenoss.SwoopyGraph.superclass.constructor.call(this, config);
        this.linkcheck = Ext.get('linkcheck');
        this.mustUseImageUri = Ext.isIE;
        
        //as of extJS 4 the ref property was removed, so we need this to handle 
        //zoom in and zoom out buttons 
        this.zoomin = this.down("[itemId='zoomin']"); 
        this.zoomout = this.down("[itemId='zoomout']");
     	
        Zenoss.SWOOPIES.push(this);
    },
    initEvents: function() {
        this.addEvents("zoommodechange", "updateimage");
        Zenoss.SwoopyGraph.superclass.initEvents.call(this);
        this.on("zoommodechange", this.onZoomModeChange, this);
        this.on("updateimage", this.updateImage, this);
        this.graphEl = Ext.get(this.graphId);
        this.graphEl.on('click', this.onGraphClick, this);
        this.graphEl.on('load', function(){
            var size = this.graphEl.getSize();
            this.setWidth(size.width);
            if (!size.width || !size.height){
                this.showFailure();
            } else {
                this.parseGraphParams();
            }
        }, this, {single:true});
    },
    showFailure: function() {
        this.failureMask = this.failureMask || Ext.DomHelper.insertAfter(this.graphEl, {
            tag: 'div',
            html: "There was a problem rendering this graph. Either the file does not exist or an error has occurred.  Initial graph creation can take up to 5 minutes.  If the graph still does not appear, look in the Zope log file $ZENHOME/log/event.log for errors."
        });
        var el = Ext.fly(this.failureMask);
        var size = this.graphEl.getSize();
        if (!size.width || !size.height) {
            size = {height:150, width:500};
        }
        el.setSize(size);
        Ext.fly(this.failureMask).setDisplayed(true);
        this.graphEl.setDisplayed(false);
    },
    hideFailure: function() {
        if (this.failureMask) {
            this.graphEl.setDisplayed(true);
            Ext.fly(this.failureMask).setDisplayed(false);
        }
    },
    parseGraphParams: function(url) {
        url = url || this.graphEl.dom.src;
        var href = url.split('?'),
            gp = Ext.apply({url:href[0]}, Ext.urlDecode(href[1]));
        // Encoding can screw with the '=' padding at the end of gopts, so
        // strip and recreate it
        gp.gopts = fixBase64Padding(gp.gopts);
        gp.width = Number(gp.width);
        gp.drange = Number(gp.drange);
        gp.start = Ext.isDefined(gp.start) ? Number(start_re.exec(gp.start)[1]) : gp.drange;
        gp.end = Ext.isDefined(gp.end) ? Number(end_re.exec(gp.end)[1]) : 0;
        this.graph_params = gp;
    },
    getComment: function(start, end) {
        var now = new Date(),
            endDate = now.minus(end).toPretty(),
            startDate = now.minus(start + end).toPretty();
        var com_ctr = "\\t\\t to \\t\\t";
        var comment = startDate + com_ctr + endDate;
        comment = comment.replace(/:/g, '\\:');
        return comment;
    },
    fireEventsToAll: function() {
        if (this.linked()) {
            var args = arguments;
            Ext.each(Zenoss.SWOOPIES, function(g) {
                g.fireEvent.apply(g, args);
            });
        } else {
            this.fireEvent.apply(this, arguments);
        }
    },
    linked: function() {
        return Ext.get('linkcheck').dom.checked;
    },
    updateImage: function(params) {
        /*
        * params should look like:
        * {drange:n, start:n, end:n}
        */
        var gp = Ext.apply({}, params, this.graph_params);
        gp.comment = this.getComment(gp.start, gp.end);
        gp.end = 'now-' + gp.end + 's';
        gp.start = 'end-' + gp.start + 's';
        this.sendRequest(gp);
    },
    sendRequest: function(params) {
        var url = params.url;
        delete params.url;        params.getImage = null;
        if (this.mustUseImageUri === true) {
            params.getImage = true;
        }

        var now = new Date().getTime();
        var graphid = now + '_' + this.graphId;
        params.graphid = graphid;

        var fullurl = Ext.urlAppend(url, Ext.urlEncode(params));

        if (this.mustUseImageUri === true) {
            // IE 6 and 7 Cannoy display data:image stuff in image
            // src. If it's one of those browsers,
            // skip the SWOOP stuff and just set the image src.
            this.graphEl.dom.src = fullurl;
            this.parseGraphParams(fullurl);
        }
        else {
            Zenoss.SWOOP_CALLBACKS[graphid] = Ext.bind(function(packet) {
                var ob = Ext.decode(packet);
                if (ob.success) {
                    this.hideFailure();
                    this.graphEl.dom.src = "data:image/png;base64," + ob.data;
                    this.parseGraphParams(fullurl);
                } else {
                    this.showFailure();
                }
                // Clean up callbacks and script tags
                delete Zenoss.SWOOP_CALLBACKS[graphid];
                Ext.get(graphid).remove();
            }, this);
            var sc = Ext.DomHelper.createDom({
                tag: 'script',
                id: graphid,
                type: 'text/javascript',
                src: fullurl
            });
            Ext.getDoc().dom.getElementsByTagName('head')[0].appendChild(sc);
        }

    },
    onPanLeft: function(graph) {
        var gp = this.graph_params;
        var delta = Math.round(gp.drange/pan_factor);
        var newend = gp.end + delta > 0 ? gp.end + delta : 0;
        this.fireEventsToAll("updateimage", {end:newend});
    },
    onPanRight: function(graph) {
        var gp = this.graph_params;
        var delta = Math.round(gp.drange/pan_factor);
        var newend = gp.end - delta > 0 ? gp.end - delta : 0;
        this.fireEventsToAll("updateimage", {end:newend});
    },
    onZoomModeChange: function(graph, zoomOut) {
        this.zoomout.toggle(zoomOut);
        this.zoomin.toggle(!zoomOut);
        var dir = zoomOut ? 'out' : 'in',
            cls = Ext.isGecko ? '-moz-zoom-'+dir :
                 (Ext.isWebKit ? '-webkit-zoom-'+dir : 'crosshair');
        this.graphEl.setStyle({'cursor': cls});
    },
    doZoom: function(xpos, factor) {
        var gp = this.graph_params;
        if (xpos < 0 || xpos > gp.width) {
            return;
        }
        var drange = Math.round(gp.drange/factor),
            delta = ((gp.width/2) - xpos) * (gp.drange/gp.width) + (gp.drange - drange)/2,
            end = Math.round(gp.end + delta >= 0 ? gp.end + delta : 0);
        this.fireEventsToAll("updateimage", {
            drange: drange,
            start: drange,
            end: end
        });
    },
    onGraphClick: function(e) {
        var graph = e.getTarget(null, null, true),
            x = e.getPageX() - graph.getX() - 67,
            func = this.zoomin.pressed ? this.onZoomIn : this.onZoomOut;
        func.call(this, this, x);
    },
    onZoomIn: function(graph, xpos) {
        this.doZoom(xpos, zoom_factor);
    },
    onZoomOut: function(graph, xpos) {
        this.doZoom(xpos, 1/zoom_factor);
    }
});

function resetSwoopies(drange) {
    drange = drange || Ext.get('drange_select').dom.value;
    Ext.each(Zenoss.SWOOPIES, function(g) {
        g.fireEventsToAll("updateimage", {
            drange: drange,
            start: drange,
            end: 0
        });
    });
}

function onLinkCheck(e, el) {
    if (el.checked) {
        resetSwoopies();
    }
}

Ext.onReady(function(){
    var graphid;
    Ext.get('linkcheck').on('click', onLinkCheck);
    Ext.get('drange_select').on('change', function(e, el){
        resetSwoopies(el.value);
    });
    var resetButton = Ext.get('graphreset');
    if (resetButton) {
        resetButton.on('click', function(){resetSwoopies();});
    }
    for (graphid in ZenGraphs) {
        var id = Ext.id();
        var graphinfo = ZenGraphs[graphid];
        var x = new Zenoss.SwoopyGraph({
            graphUrl: graphinfo[0],
            graphTitle: graphinfo[1],
            id: id,
            width: 600,
            graphId: graphid
        }).render(Ext.get('td_'+graphid));
        var el = Ext.getCmp(id).el;
    }

    // Old code I don't want to rewrite right now
    var button = Ext.get('refreshButton');
    var refreshMgr;
    function turnRefreshOff () {
        if (refreshMgr) {
            refreshMgr.cancelRefresh();
        }
        button.setStyle({'background-image':'url(img/refresh_on.png)'});
        button.un('click', turnRefreshOff);
        button.on('click', turnRefreshOn);
        button.blur();
    }
    function turnRefreshOn () {
        var refrate = $('refreshRate');
        if (refrate) {
            var rate = refrate.value;
            refreshMgr = new RefreshManager(rate, function(){resetSwoopies();});
            button.setStyle({'background-image':'url(img/refresh_off.png)'});
            button.un('click', turnRefreshOn);
            button.on('click', turnRefreshOff);
            button.blur();
        }
    }
    turnRefreshOn();
});


