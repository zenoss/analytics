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

Ext.define("Zenoss.ContextMenu", {
    alias:['widget.ContextMenu'],
    extend:"Ext.Button",
    /**
     * onSetContext abstract function called when the context for the menu is
     * potentially changed
     */
    onSetContext: Ext.emptyFn,
    /**
     * The object id for which the context menu belongs to
     */
    contextUid: null,
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            id: 'context-configure-menu',
            iconCls: 'customize'
        });
        Zenoss.ContextMenu.superclass.constructor.call(this, config);
    },
    setContext: function(uid) {
        this.contextUid = uid;
    }
});




Ext.define("Zenoss.ContextConfigureMenu", {
    alias:['widget.ContextConfigureMenu'],
    extend:"Zenoss.ContextMenu",
    /**
     * onGetMenuItems abstract function; hook to provide
     * more menu items based on context
     * @param {string} uid; item to get menu items for
     */
    onGetMenuItems: function(uid){ return []; },
    /**
     * Called when an item in the menu is selected
     * @param {object} this, the ContextConfigureMenu
     * @param {object} the menu item selection
     */
    onSelectionChange: Ext.emptyFn,
    /**
     * Filter out menu items;  Return true if it should be kept, false otherwise
     * @param {ContextConfigureMenu}
     * @param {Object} itemConfig
     */
    filterMenu: function(contextMenu, config) {return true;},
     /**
     * Menu ids used to get dialog menus that will be used in context menu;
     * Empty or null if no items from old menu items is desired
     */
    menuIds: ['More','Manage','Edit', 'Actions','Add','TopLevel'],
    menu: {items:[]},
    disabled: true,
    /**
     * @cfg {array} menutItems
     * items that should always be included in the menu
     */
    menuItems: [],
    /**
     * set the UID, menus for the corresponding object will be determined and
     * set
     * @param {Object} uid
     */
    setContext: function(uid) {
        this.disable();
        this.onSetContext(uid);
        this.contextUid = uid;
        var menu = this.menu;
        menu.removeAll();
        this.getMenuItems(uid);
    },
    /**
     * private
     * handler for add to zenpack menu item; displays dialog
     * @param {Object} uid
     */
     addToZenPackHandler: function(e) {
        var dialog = Ext.create('Zenoss.AddToZenPackWindow', {});
        dialog.setTarget(this.contextUid);
        dialog.show();
    },
    /**
     * private
     * gets the menu items to be displayed
     * @param {Object} uid
     */
    getMenuItems: function(uid){
        var callback = function(provider, response){
            var menuItems = [], visibleMenuCount = 0;
            //get statically defined menu items
            if (this.menuItems.length !== 0) {
                menuItems = menuItems.concat(this.menuItems);
            }
            //get any context specific menus if defined
            var moreMenuItems = this.onGetMenuItems(this.contextUid);
            if (moreMenuItems !== null || moreMenuItems.length > 0){
                menuItems = menuItems.concat(moreMenuItems);
            }
            //menus from router
            var itemConfigs = response.result.menuItems;
            var filterFn = function(val) {
                return this.filterMenu(this, val);
            };
            itemConfigs = Zenoss.util.filter(itemConfigs, filterFn, this);
            if (itemConfigs){
                menuItems = menuItems.concat(itemConfigs);
            }
            //add all menus and set handlers if needed
            Ext.each(menuItems, function(item){
                //add to zenpack has a different/new handler
                if (item.id === 'addtozenpack'){
                    item.handler = Ext.bind(this.addToZenPackHandler, this);
                }
                if (!Ext.isDefined(item.handler)) {
                    item.handler = Ext.bind(this.defaultHandler, this);
                }

                // do now show as enabled if we only have hidden items (or spacers)
                if (!item.hidden && item !== '-') {
                    visibleMenuCount += 1;
                }
                this.menu.add(item);
            }, this);

            // if we have stuff then enable this control
            if(this.menu.items.length !== 0 && visibleMenuCount){
                this.enable();
            }
        };
        var args = {
            'uid': uid
        };
        if (this.menuIds !== null && this.menuIds.length >= 1){
            args.menuIds = this.menuIds;
        }

        Zenoss.remote.DetailNavRouter.getContextMenus(args, callback, this);
    },

    /**
     * private
     * handler used if a menu item does not have a handler defined
     * @param {Object} button
     */
    defaultHandler: function(button) {
        var dialog = new Zenoss.dialog.DynamicDialog();
        dialog.setTitle(_t(button.text.replace(/\.\.\./g, '')));
        dialog.show();
        dialog.body.load({
            scripts: true,
            url: this.contextUid + '/' + button.viewName
        });
    }
});



})();
