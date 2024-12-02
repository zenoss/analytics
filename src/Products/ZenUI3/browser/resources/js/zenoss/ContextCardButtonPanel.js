/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

Ext.ns('Zenoss');


Ext.override(Ext.layout.CardLayout, {
    // store old functionality to have acces to it from other app parts;
    oldInitEvents: Ext.layout.CardLayout.prototype.initEvents,
    oldSetActiveItem: Ext.layout.CardLayout.prototype.setActiveItem,
    initEvents: function() {
        oldInitEvents.apply(this, arguments);
        this.owner.addEvents('cardchange');
    },
    setActiveItem: function(item) {
        var result = this.oldSetActiveItem.apply(this, arguments);
        this.owner.fireEvent('cardchange', this.owner, item);
        // we need to return result from old "setActiveItem" to avoid conflicts in layout owner on card change;
        return result;
    }
});

Ext.define("Zenoss.ContextCardPanel", {
    extend:"Ext.Panel",
    alias: ['widget.contextcardpanel'],
    contextUid: null,
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: {
                type: 'card',
                deferredRender: true
            }
        });
        Zenoss.ContextCardPanel.superclass.constructor.call(this, config);
        this.on('cardchange', this.cardChangeHandler, this);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.cardChangeHandler(this.layout.activeItem);
    },
    cardChangeHandler: function(panel) {
        if (panel!==this && panel.setContext) {
            panel.setContext(this.contextUid);
        }
    }

});




})();
