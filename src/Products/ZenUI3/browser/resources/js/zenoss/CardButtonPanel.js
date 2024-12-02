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

/**
 * @class Zenoss.ViewButton
 * @extends Ext.Button
 * A button that toggles between cards in a panel with a card layout.
 * @constructor
 */
Ext.define("Zenoss.ViewButton", {
    extend:"Ext.Button",
    alias: ['widget.ViewButton'],

    constructor: function(userConfig) {

        var baseConfig = {
            enableToggle: true,
            toggleGroup: 'CardButtonPanel',
            allowDepress: false
        };

        var config = Ext.apply(baseConfig, userConfig);
        Zenoss.ViewButton.superclass.constructor.call(this, config);
    }

});



/**
 * @class Zenoss.CardButtonPanel
 * @extends Ext.Button
 * A Panel with a card layout and toolbar buttons for switching between the
 * cards.
 * @constructor
 */
Ext.define("Zenoss.CardButtonPanel", {
    extend:"Ext.Panel",
    alias: ['widget.CardButtonPanel'],

    constructor: function(config) {
        // Inner secret closure function to create the handler
        function createToggleHandler(cardPanel, panel) {
            return function(button, pressed) {
                if (pressed) {
                    cardPanel.fireEvent('cardchange', panel);
                    cardPanel.getLayout().setActiveItem(panel.id);
                }
            };
        }

        function syncButtons(me) {
            var tb = me.getDockedItems('toolbar')[0];
            for (var idx=0; idx < me.items.getCount(); ++idx) {
                var newComponent = me.items.get(idx);

                if (newComponent instanceof Ext.Panel) {
                    tb.add({
                        xtype: 'ViewButton',
                        id: 'button_' + newComponent.id,
                        text: Ext.clean(newComponent.buttonTitle,
                                        newComponent.title, 'Undefined'),
                        pressed: (newComponent === me.layout.activeItem),
                        iconCls: newComponent.iconCls,
                        toggleHandler: createToggleHandler(me, newComponent)
                    });
                }
            }
        }

        Ext.applyIf(config, {
            id: 'cardPanel',
            layout: 'card',
            activeItem: 0
        });

        Ext.apply(config, {
            header: false,
            tbar: [{
                xtype: 'tbtext',
                text: _t('View: ')
            }]
        });

        this.addEvents('cardchange');
        this.on('afterrender', syncButtons, this);
        this.listeners = config.listeners;
        Zenoss.CardButtonPanel.superclass.constructor.call(this, config);
    }
});



})();
