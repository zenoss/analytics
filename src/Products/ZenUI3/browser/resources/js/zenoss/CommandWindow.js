/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


(function(){

/**********************************************************************
 *
 * Command Panel
 *
 */
var formTpl = new Ext.Template(
    '<form name="commandform" method="POST" action="{target}">',
    '<textarea style="visibility:hidden" name="data">',
    '{data}',
    '</textarea>',
    '</form>');
formTpl.compile();

Ext.define("Zenoss.CommandPanel", {
    alias:['widget.commandpanel'],
    extend:"Zenoss.IFramePanel",
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            ignoreClassName: true
        });
        Zenoss.CommandPanel.superclass.constructor.call(this, config);
        this.on('frameload', this.injectForm, this, {single:true});
    },
    injectForm: function(win){
        var doc = this.getDocument(),
            form = formTpl.apply({
                data: Ext.encode(this.data),
                target: this.target
            });
        this.getBody().innerHTML = form;
        this.getFrame().setAttribute("allowtransparency", "true");   
        doc.commandform.submit();
        this.parentWindow.setSize(this.parentWindow.getSize());
    }
});



/**********************************************************************
 *
 *  Command Window
 *
 */
Ext.define("Zenoss.CommandWindow", {
    alias:['widget.commandwindow'],
    extend:"Ext.Window",
    constructor: function(config) {
        this.cpanel = Ext.id();
        this.commandData = config.data ||
            { uids: config.uids, command: config.command };
        this.target = config.target;
        config = Ext.applyIf(config || {}, {
            layout: 'fit',
            title: config.command || config.title,
            cls: 'streaming-window',
            constrain: true,
            closable:true,
            plain: true,
            items: {
                id: this.cpanel,
                xtype: config.panel || 'commandpanel', //default to commandpanel
                data: this.commandData,
                target: config.target,
                autoLoad: config.autoLoad,
                parentWindow: this
            },
            fbar: {
                buttonAlign: 'left',
                id:'window_footer_toolbar',
                items: [
                    {
                        xtype: 'button',
                        text: _t('Copy to clipboard'),
                        handler: Ext.bind(function(c){
                            this.copyToClipboard();
                            }, this)
                    }, '-',
                    {
                    xtype: 'checkbox',
                    checked: true,
                    boxLabel: '<span style="color:white">Autoscroll</span>',
                    handler: Ext.bind(function(c){
                        if (c.checked) {
                            this.startScrolling();
                        } else {
                            this.stopScrolling();
                        }}, this)
                    },
                ]
            }
        });
        Zenoss.CommandWindow.superclass.constructor.call(this, config);
        this.task = new Ext.util.DelayedTask(this.scrollToBottom, this);
        this.on('afterrender', this.startScrolling, this);
        this.on('afterrender', this.resizeOnRender, this);
        this.on('afterlayout', function(){this.center();}, this, {single:true});
        this.on('close', this.stopScrolling, this);
            this.on('close', function() {
                if(Ext.isDefined(config.redirectTarget)){
                        this.closeAndRedirect();
                }
            });
    },
    resizeOnRender: function() {
        var vsize = Ext.getBody().getViewSize();
        this.setSize({width:vsize.width*0.95, height:vsize.height*0.95});
    },
    getCommandPanel: function() {
        if (Ext.isString(this.cpanel)) {
            this.cpanel = Ext.getCmp(this.cpanel);
        }
        return this.cpanel;
    },
    startScrolling: function() {
        this.task.delay(250);
    },
    stopScrolling: function() {
        this.task.cancel();
    },
    scrollToBottom: function() {
        try {
            var win = this.getCommandPanel().getWindow(),
                body = this.getCommandPanel().getBody();
            Zenoss.env.BODY = body;
            win.scrollBy(0, body.scrollHeight);
        } catch(e) {
            Ext.emptyFn();
        }

        if (Ext.get('window_footer_toolbar')) {
            Ext.get('window_footer_toolbar').focus();
            this.task.delay(250);
        }
    },
    copyToClipboard: function() {
        var body = this.getCommandPanel().getBody().innerText;
        // maybe a better Ext-y way to do this, but the below works well.
        var tempText = document.createElement("textarea");
        tempText.value = body;
        document.body.appendChild(tempText);
      
        function afterTextareaAppending() {
            tempText.focus();
            tempText.select();
            try {
                if (document.execCommand('copy')) {
                    Zenoss.flares.Manager.success('Copied command output to clipboard');
                }
            } catch (err) {
                console.error("Failed to copy command output to clipboard", err);
            } finally {
                document.body.removeChild(tempText);
            }
        }

        if (Ext.isChrome) {
            setTimeout(afterTextareaAppending);
        } else {
            afterTextareaAppending();
        }
    },
    closeAndRedirect: function() {
        window.top.location = this.redirectTarget;
        this.destroy();
    }
});



})();
