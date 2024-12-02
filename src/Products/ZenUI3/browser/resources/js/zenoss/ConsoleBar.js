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

Ext.define("Zenoss.ConsoleBar", {
    alias:['widget.consolebar'],
    extend:"Zenoss.LargeToolbar",
    constructor: function(config) {
        var title = config.title || 'Title';
        delete config.title;
        config = Ext.apply(config||{}, {
            cls: 'largetoolbar consolebar',
            height: 35,
            collapseTitle: 'Instances',

            items: [{
                xtype: 'tbtext',
                text: title
            }].concat(config.leftItems||[]).concat([{
                xtype: 'tbfill'
            }])

        });

        this.callParent(arguments);

    },
    /**
     * Because in our UI we want the console bar visible when the
     * panel is collapse we add ourselves to the "dockedItems" when
     * our expand and collapse button is pressed.
     **/
    toggleDockedItemPosition: function() {
        this.up('panel').removeDocked(this, false);
        if (this.parentPanel.collapsed) {
            this.moveToSouthRegion();
        } else {
            this.moveToCenterRegion();
        }
    },
    _getRegion: function(region) {
        var reg = null;
        Ext.getCmp(this.centerPanel).items.each(function(item){
            if (item.region === region) {
                reg = item;
            }
        });
        return reg;
    },
    moveToSouthRegion: function() {
        this.dock = "top";
        this._getRegion("south").addDocked(this);
        this.parentPanel.setHeight(this.oldHeight);
        this.parentPanel.expand();
    },
    moveToCenterRegion: function() {
        this.dock = "bottom";
        this._getRegion("center").addDocked(this, 0);
        // remember the old height for when we expand
        this.oldHeight = Math.max(this.parentPanel.getEl().getComputedHeight(), this.parentPanel.initialConfig.height);
        this.parentPanel.collapse();
        // set height to 0 so the header bar disappears
        this.parentPanel.setHeight(0);
    }

});

})(); // End local namespace
