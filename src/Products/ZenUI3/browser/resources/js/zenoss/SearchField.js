Ext.ns('Zenoss');

/**
 * @class Zenoss.SearchField
 * @extends Ext.form.TextField
 * @constructor
 */
Ext.define("Zenoss.SearchField", {
    extend: "Ext.form.TextField",
    alias: ['widget.searchfield'],
    constructor: function(config){
        config = Ext.applyIf(config||{}, {
            validationDelay: 500,
            selectOnFocus: true
        });
        config.cls += ' x-field-search';
        Zenoss.SearchField.superclass.constructor.apply(this, arguments);
    },
    getClass: function(){
        var cls = this.altCls ? this.altCls : 'searchfield';
        return this.black ? cls + '-black' : cls;
    },
    onRender: function() {
        Zenoss.SearchField.superclass.onRender.apply(this, arguments);
        this.wrap = this.el.boxWrap(this.getClass());
        if (this.bodyStyle) {
            this.wrap.setStyle(this.bodyStyle);
        }
        this.resizeEl = this.positionEl = this.wrap;
        this.syncSize();
    },
    syncSize: function(){
        this.el.setBox(this.el.parent().getBox());
    }

}); // Ext.extend


