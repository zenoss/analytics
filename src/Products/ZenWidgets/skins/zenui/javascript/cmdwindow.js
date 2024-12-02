var Class = YAHOO.zenoss.Class;

var PollingDialog = Class.create();
PollingDialog.prototype = {
    __init__: function(title, url, refreshRate) {
        bindMethods(this);
        this.showDialog(title, url, refreshRate);
    },
    fetch: function(did, url) {
        var d = doSimpleXMLHttpRequest(url);
        d.addCallback(bind(function(req){
            this.fill(did, req);
        }, this));
    },
    fill: function(did, request) {
        $MK(did+'_innercontent').innerHTML = request.responseText;
        var elements = getFormElements($MK(did+'_innercontent'));
        var first = elements[0];
        var textboxes = elements[1];
        var submits = elements[2];
        var submt = submits[0];
        var connectTextboxes = function(box) {
            connect(box, 'onkeyup', function(e){
                if (e.key().string=='KEY_ENTER') submt.click();
            });
        }
        if (submits.length==1) map(connectTextboxes, textboxes);
        first.focus();
    },
    makeDialog: function(title) {
        var did = 'dialog'+String(Date.now());
        var mydialog = DIV({
            'id':did,
            'style':'visibility:hidden;position:absolute;top:0;'
        },
            [
                DIV({'class':'x-dlg-hd'}, title),
                DIV({'class':'x-dlg-bd'},
                    DIV({'id':did+'_innercontent'}, null)
                )
            ]
        )
        appendChildNodes($MK('frame'), mydialog);
        return did;
    },
    showDialog: function(title, url, refreshRate){
        var did = this.makeDialog(title);
        this.dialog = new Ext.BasicDialog(did, {
            width:400,
            height:400,
            shadow:true,
            minWidth:300,
            minHeight:250,
            proxyDrag:true
        });
        var killdialog = bind(function() {
            this.destroy(did, this.dialog);
        }, this);
        this.dialog.addKeyListener(27, killdialog, did, this.dialog);
        this.dialog.addButton('Close', killdialog, did, this.dialog);
        this.dialog.on('hide', killdialog);
        this.dialog.show();
        this.fetch(did, url);
        refreshRate = parseInt(refreshRate);
        if (refreshRate>0)
            this.startRepeat(this.dialog, did, url, refreshRate);
    },
    startRepeat: function(dialog, did, url, refreshRate){
        dialog.caller = callLater(refreshRate, bind(function(){
            this.fetch(did, url);
            this.startRepeat(dialog, did, url, refreshRate);
        }, this));
    },
    destroy: function(did, dialog){
        if (dialog.caller) dialog.caller.cancel();
        dialog.destroy();
    }

}

