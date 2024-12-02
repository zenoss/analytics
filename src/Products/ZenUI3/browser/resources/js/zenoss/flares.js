(function() {
    Ext.namespace('Zenoss.flares');

    /**
     * An invisible layer that contains all the Flares.
     * Must be the highest layer in order for Flares to show up.
     */
    Ext.define('Zenoss.flares.Container', {
        extend: 'Ext.Container',
        _layoutDelay: null,
        constructor: function(config) {
            config = Ext.applyIf(config || {}, {
                id: 'flare-container',
                baseCls: 'x-flare-container',
                alignment: 't-t',
                width: '100%',
                zindex: 400000,
                items: []
            });

            this.callParent([config]);
        },
        onRender: function(ct) {
            this.el = ct.createChild({
                cls: this.baseCls + '-layer',
                children: [{
                    cls: this.baseCls + '-body'
                }]
            });
            this.body = this.el.child('.' + this.baseCls + '-body');
            this.el = new Ext.Layer({ zindex: this.zindex }, this.el);
            Zenoss.flares.Container.superclass.onRender.apply(this, arguments);
            this.el.alignTo(document, this.alignment);
        },
        getLayoutTarget: function() {
            return this.body;
        },
        onShow: function() {
            this.el.show();
            Zenoss.flares.Container.superclass.onShow.apply(this, arguments);
        },
        onRemove: function() {
            // Move the sticky items back to the top. Wait a few microseconds to do it in case more items are
            // being removed at the same time.
            if ( !this._layoutDelay ) {
                this._layoutDelay = new Ext.util.DelayedTask(this.doLayout, this);
            }
            this._layoutDelay.delay(500);
        },
        show: function() {
            if ( !this.rendered ) {
                this.render(Ext.getBody());
            }
            Zenoss.flares.Container.superclass.show.apply(this, arguments);
        },
        onLayout: function() {
            Ext.each(this.items.items, function(item, index, items) {
                if ( item.canLayout() ) {
                    if ( index === 0 ) {
                        item.anchorTo(this.el, this.alignment);
                    }
                    else {
                        item.anchorTo(items[index - 1].el, 'tl');
                    }
                }
            }, this);
            Zenoss.flares.Container.superclass.onLayout.apply(this, arguments);
        }
    });

    /**
     * The UI manager for flares.
     */
    Zenoss.flares.Manager = {
        container: Ext.create('Zenoss.flares.Container', {}),
        INFO: 'x-flare-info',
        ERROR: 'x-flare-error',
        WARNING: 'x-flare-warning',
        DEBUG: 'x-flare-debug',
        SUCCESS: 'x-flare-success',
        CRITICAL: 'x-flare-critical',
        _visibleFlares: new Ext.util.MixedCollection(false, function(flare) {
            return flare._bodyHtml;
        }),

        /**
         * Add the flare to the container and show it.
         *
         * @param flare Zenoss.flares.Flare
         */
        flare: function(flare) {
            var otherFlare = Zenoss.flares.Manager._visibleFlares.last();
            Zenoss.flares.Manager._visibleFlares.add(flare._bodyHtml, flare);

            flare.on('afterrender', function() {
                /**
                 * Checks whether a message is longer than a flare.
                 * If so, sets new styles for a message to set it properly in a flare.
                 * (reduces width and line-height of a message)
                 **/
                 var dom_message = Ext.dom.Query.select('.x-flare-message');
                 var message = Ext.get(dom_message[dom_message.length-1]);
                 var documentWidth = Ext.getBody().getViewSize().width;

                 if (message.getWidth() >= documentWidth-15) {
                     var dom_flare = Ext.dom.Query.select('.x-flare');
                     var dom_close = Ext.dom.Query.select('.x-tool-close');
                     var flare = Ext.get(dom_flare[dom_flare.length-1]);
                     var close =  Ext.get(dom_close[dom_close.length-1]);

                     flare.setStyle('line-height', '16px');
                     message.setStyle('width', '92%');
                     close.setStyle('border-top', '2px solid transparent');
                 }
             });

            // if we have other flares, make sure this one renders to the bottom of the
            // previous flares
            if (otherFlare) {
                flare.on('afterrender', function(fl){
                    fl.alignTo(otherFlare.getEl(), 'bl-bl', [0, 32]);
                });
            }else {
                flare.on('afterrender', function(fl){
                    fl.alignTo(Ext.getBody(), 'tl-tl');
                });
            }
            if(Ext.isIE){
                flare.on('afterrender', function(fl){
                // ie isn't calc width correct. must set after render to known width
                       fl.setWidth(fl.getWidth());
                });
            }
            if(Zenoss.SELENIUM){
                flare.on('afterrender', function(fl){
                    fl.getEl().query('.x-flare-message')[0].id = "flare-message-span";
                });
            }
            Zenoss.flares.Manager.container.add(flare);
            Zenoss.flares.Manager.container.doLayout();
            flare.show();
        },
        removeFlare: function(flare) {
            Zenoss.flares.Manager._visibleFlares.removeAtKey(flare._bodyHtml);
            Zenoss.flares.Manager.adjustFlares();
        },
        /**
         * Adjusts the locations of the flares, when one
         * is deleted it iterates through all the existing flares
         * and realigns their position
         **/
        adjustFlares: function() {
            var flares = Zenoss.flares.Manager._visibleFlares;
            var container = Ext.getBody(), useOffset = false;
            flares.each(function(flare){
                if (!useOffset) {
                    flare.alignTo(container, 'tl-tl');
                    useOffset = true;
                } else {
                    flare.alignTo(container, 'bl-bl', [0, 32]);
                }
                container = flare.getEl();
            });
        },
        /**
         * Format a message and create a Flare.
         *
         * @param message string A message template
         * @param type string One of the status types assigned to this class (ex: INFO, ERROR)
         * @param args array Optional orguments to fill in the message template
         */
        _formatFlare: function(message, type, args) {
            args = Array.prototype.slice.call(args, 1);
            // in case if message has some encoded html returned from server;
            message = Ext.htmlDecode(message);
            var flare = new Zenoss.flares.Flare(message, args, {
                iconCls: type,
                animateTarget: Zenoss.flares.Manager.container.el
            });

            var existingFlare = Zenoss.flares.Manager._visibleFlares.get(flare._bodyHtml);
            if (!Ext.isDefined(existingFlare)) {
                Zenoss.flares.Manager.flare(flare);
                return flare;
            }
            flare.destroy();
            return existingFlare;
        },
        /**
         * Show a Flare with the info status.
         *
         * @param message string A message template
         * @param args mixed Optional orguments to fill in the message template
         */
        info: function(message) {
            return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.INFO, arguments);
        },
        error: function(message) {
            return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.ERROR, arguments);
        },
        warning: function(message) {
            return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.WARNING, arguments);
        },
        debug: function(message) {
            return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.DEBUG, arguments);
        },
        critical: function(message) {
            return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.CRITICAL, arguments);
        },
        success: function(message) {
            return Zenoss.flares.Manager._formatFlare(message, Zenoss.flares.Manager.SUCCESS, arguments);
        }
    };

    /**
     * Flares are growl like flash messages. Used for transient notifications. Flares are
     * managed by Zenoss.flares.Manager.
     *
     * Example:
     *
     * Zenoss.flares.Manager.info('{0} was saved as {1}.', itemName, newItemName);
     */
    Ext.define('Zenoss.flares.Flare', {
        extend: 'Ext.Window',
        _bodyHtml: null,
        _task: null,
        _closing: false,
        focus: Ext.emptyFn,
        constructor: function(message, params, config) {
            if ( Ext.isArray(message) ) {
                var children = [];
                Ext.each(message, function(m) {
                    children.push({ tag: 'li', html: m });
                });

                message = Ext.DomHelper.markup({
                    tag: 'ul',
                    children: children
                });
            }

            var template =  new Ext.Template(message, { compiled: true } );
            this._bodyHtml = template.apply(params);

            Ext.applyIf(config, {
                headerAsText: false,
                bodyCls: config.iconCls || 'x-flare-info',
                baseCls: 'x-flare',
                plain: false,
                draggable: false,
                shadow: false,
                closable: true,
                resizable: false,
                delay: 5000, // How long to show the message for
                alignment: 't-t',
                duration: 0.2, // How long to do the opening slide in
                hideDuration: 1, // How long to do the closing fade out
                template: template,
                cls: 'x-flare-body',
                height: '32',
                dismissOnClick: true,
                listeners: {
                    show: function() {
                        if ( this._task ) {
                            this._task.delay(this.delay);
                        }
                    },
                    hide: function() {
                        Zenoss.flares.Manager.removeFlare(this);
                    },
                    scope: this
                },
                items: {
                    html: "<div class='x-flare-icon'></div><span class='x-flare-message'>" + this._bodyHtml + "</span>"
                }
            });
            this.callParent([config]);

        },
        initEvents: function() {
            this.callParent(arguments);
            this.mon(this.el, 'mouseover', function(){
                this.sticky();
            }, this);
            this.mon(this.el, 'mouseout', function(){
                Ext.defer(function(){
                    if ( !this.sticky ) {
                        this.hide();
                    }
                }, 1000, this);
            }, this);
            if ( this.dismissOnClick ) {
                this.mon(this.el, 'click', function() {
                    this.hide();
                }, this);
            }
        },
        initComponent: function() {
            if ( this.delay ) {
                this._task = new Ext.util.DelayedTask(this.hide, this);
            }
            this.callParent(arguments);
        },
        /**
         * Make this Flare "stick". It will not fade away and must manually be dismissed by the user.
         */
        sticky: function() {
            if ( this._task ) {
                this._task.cancel();
                delete this._task;
            }
        },
        animShow: function() {
            this.el.slideIn('t', {
                duration: this.duration,
                callback: this._afterShow,
                scope: this
            });
        },
        close: function() {
            Zenoss.flares.Manager._visibleFlares.removeAtKey(this._bodyHtml);
            this.hide();
        },
        animHide: function() {
            Zenoss.flares.Manager._visibleFlares.removeAtKey(this._bodyHtml);
            this._closing = true;
            this.el.ghost("t", {
                duration: this.hideDuration,
                remove: false,
                callback : Ext.bind(function () {
                    this.destroy();
                }, this)
            });
        },
        canLayout: function() {
            if ( !this._closing ) {
                // Only move if it's not already closing
                return Zenoss.flares.Flare.superclass.canLayout.apply(this, arguments);
            }
        }
    });

    Ext.namespace('Zenoss.messaging');
    /**
     * Message for Zenoss.messaging.Messenger. This is for back-compat and should not be used directly.
     */
    Ext.define('Zenoss.messaging.Message',  {
        INFO: 0,        // Same as in messaging.py
        WARNING: 1,     // Same as in messaging.py
        CRITICAL: 2,    // Same as in messaging.py
        constructor: function(config) {
            config = Ext.applyIf(config || {}, {
                body: '',
                priority: this.INFO,
                sticky: false
            });
            Ext.apply(this, config);
        }
    });

    /**
     * An interface to the old messaging API. This is for back-compat and should not be used directly.
     */
    Ext.define('Zenoss.messaging.Messenger', {
        extend: 'Ext.util.Observable',
        constructor: function(config) {
            config = Ext.applyIf(config || {}, {
                interval: 30000
            });
            Ext.apply(this, config);
            this.callParent([config]);
            this.addEvents('message');
        },
        init: function() {
            this._task = new Ext.util.DelayedTask(function(){
                this.checkMessages();
            }, this);
            this._task.delay(this.interval);
            this.checkMessages();
        },
        checkMessages: function() {
            Zenoss.remote.MessagingRouter.getUserMessages({}, function(results) {
                Ext.each(results.messages, function(m) {
                    this.send(m);
                }, this);
            }, this);
        },
        send: function(msgConfig) {
            var message = new Zenoss.messaging.Message(msgConfig);
            this.fireEvent('message', this, message);

            var flare;
            if ( message.priority  === message.WARNING ) {
                flare = Zenoss.flares.Manager.warning(message.body);
            }
            else if ( message.priority  === message.CRITICAL ) {
                flare = Zenoss.flares.Manager.critical(message.body);
            }
            else {
                flare = Zenoss.flares.Manager.info(message.body);
            }

            if ( message.sticky ) {
                flare.sticky();
            }
        }
    });

    Zenoss.messenger = Ext.create('Zenoss.messaging.Messenger', {});

    Ext.onReady(function() {
        Zenoss.flares.Manager.container.show();
        Zenoss.messenger.init();
    });

    /**
     * Inform the user with a message. This is usually represented with a Flare. Use
     * this interface to alert users.
     */
    Zenoss.message = {
        /**
         * Show a message with the info status.
         *
         * @param message string A message template
         * @param args mixed Optional orguments to fill in the message template
         */
        info: function() {
            return Zenoss.flares.Manager.info.apply(null, arguments);
        },
        error: function() {
            return Zenoss.flares.Manager.error.apply(null, arguments);
        },
        warning: function() {
            return Zenoss.flares.Manager.warning.apply(null, arguments);
        },
        debug: function() {
            return Zenoss.flares.Manager.debug.apply(null, arguments);
        },
        /**
         * These messages have a critical error icon and stay until dismissed by the user.
         */
        critical: function() {
            var flare = Zenoss.flares.Manager.critical.apply(null, arguments);
            flare.sticky();
            return flare;
        },
        success: function() {
            return Zenoss.flares.Manager.success.apply(null, arguments);
        }
    };

}());
