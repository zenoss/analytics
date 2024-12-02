(function(){

Ext.ns('Zenoss');

function makeIpAddress(val) {
    var octets = val.split('.');
    if(octets.length>4) {
        return false;
    }
    while(octets.length < 4) {
        octets.push('0');
    }
    for(var i=0;i<octets.length;i++) {
        var octet=parseInt(octets[i], 10);
        if (!octet && octet!==0) {
            return false;
        }
        try {
            if (octet>255) {
                return false;
            }
        } catch(e) {
            return false;
        }
        octets[i] = octet.toString();
    }
    return octets.join('.');
}


/**
 * @class Zenoss.IpAddressField
 * @extends Ext.form.TextField
 * @constructor
 */
Ext.define("Zenoss.IpAddressField", {
    alias:['widget.ipaddressfield'],
    extend:"Ext.form.TextField",
    constructor: function(config){
        config.maskRe = true;
        Zenoss.IpAddressField.superclass.constructor.call(this, config);
    },
    filterKeys: function(e, dom) {
        if(e.ctrlKey || e.isSpecialKey()){
            return;
        }
        e.stopEvent();
        var result, newoctet,
            cursor = dom.selectionStart,
            selend = dom.selectionEnd,
            beg = dom.value.substring(0, cursor),
            end = dom.value.substring(selend),
            s = String.fromCharCode(e.getCharCode());
        if (s==='.') {
            result = beg + end;
            cursor += end.indexOf('.');
            newoctet = end.split('.')[1];
            if (selend===cursor+1) {
                cursor++;
            }
            if(newoctet) {
                dom.setSelectionRange(cursor+1, cursor+newoctet.length+1);
            }
        } else {
            result = makeIpAddress(beg + s + end);
            if (result) {
                cursor++;
                dom.value = result;
                dom.setSelectionRange(cursor, cursor);
            }
        }
    }

}); // Ext.extend



})();
