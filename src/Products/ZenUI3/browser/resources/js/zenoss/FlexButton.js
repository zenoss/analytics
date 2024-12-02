/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function () {
Ext.ns('Zenoss');

Ext.define("Zenoss.FlexButton", {
    extend: "Ext.button.Button",
    alias: ['widget.FlexButton'],
    constructor: function(config) {
        if ( config.menu && config.menu.items && config.menu.items.length === 1 ) {
            // Only has one menu item, lets just not have it display a menu
            config.originalMenu = Ext.apply({}, config.menu);

            // probably don't want to inherit the text
            var menuConfig = config.menu.items[0];
            Ext.apply(config, {listeners: menuConfig.listeners});
            Ext.destroyMembers(config, 'menu');
        }

        Zenoss.FlexButton.superclass.constructor.call(this, config);
    },
    add: function(config) {
        if ( !this.menu ) {
            // this button does not have a menu yet so we need to initialize it
            // update the config with things that may have changed since creation
            var menuConfig = {};
            if ( this.initialConfig.originalMenu ) {
                // originally had a menu, just use it
                Ext.apply(menuConfig, this.initialConfig.originalMenu);

            }
            else {
                // Have to generate a menu config from the original button
                menuConfig.items = [{
                    text: this.getText() ? this.getText() : this.tooltip,
                    listeners: this.initialConfig.listeners
                }];

            }

            this.split = true;
            // remove the old click handler
            var oldClick = this.initialConfig.listeners.click;
            this.un('click', oldClick);

            // Clear out properties that should be handled by the menu item
            this.on('render', function() {
                this.events['click'].clearListeners();
            }); // *TODO* This code makes me feel dirty; there must be a better way
            this.clearTip();

            this.menu = Ext.menu.MenuMgr.get(menuConfig);
            this.up('panel').doLayout();
        }

        return this.menu.add(config);
    }
});

})();
