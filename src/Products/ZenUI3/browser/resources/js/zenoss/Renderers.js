/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, 2012, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

Ext.ns('Zenoss.render');

// templates for the events renderer
var iconTemplate = new Ext.Template(
    '<td class="severity-icon-small {severity} {cssclass}" title="{severity:uppercase()}: {acked} out of {total} events acknowledged">{total}</td>');
iconTemplate.compile();

var rainbowTemplate = new Ext.Template(
    '<table class="eventrainbow eventrainbow_cols_{count}"><tr>{cells}</tr></table>');
rainbowTemplate.compile();

var upDownTemplate = new Ext.Template(
    '<span class="status-{0}{2}">{1}</span>');
upDownTemplate.compile();

var ipInterfaceStatusTemplate = new Ext.Template(
    '<span title="Administrative / Operational">{adminStatus} / {operStatus}</span>');
ipInterfaceStatusTemplate.compile();

function convertToUnits(num, divby, unitstr, places){
    unitstr = unitstr || "B";
    places = Ext.isDefined(places) ? places : 2;
    divby = divby || 1024.0;
    var units = [];
    Ext.each(['', 'K', 'M', 'G', 'T', 'P'], function(p){
        units.push(p+unitstr);
    });
    var sign = 1;
    if (num < 0) {
        num = Math.abs(num);
        sign = -1;
    }
    var i;
    for (i=0;i<units.length;i++) {
        if (num<divby) {
            break;
        }
        num = num/divby;
    }
    return (num*sign).toFixed(places) + units[i];
}

function pingStatusBase(bool) {
    /*
     * The "bool" variable can be null, undefined, a string, or a boolean.
     * We need to handle all cases and also make sure they are
     * handled in proper order.
     */
    if (bool === null || !Ext.isDefined(bool)) {
        return 'Unknown';
    }

    if(Ext.isString(bool)){
        if(bool.toLowerCase() === "none"){
            return 'Unknown';
        }else{
            bool = bool.toLowerCase() === 'up';
        }
    }

    var str = bool ? 'Up' : 'Down';
    return str;
}

Ext.apply(Zenoss.render, {

    date: function(date, format) {
        if (!format && typeof format !== "string" && !(format instanceof String)) {
            format = Zenoss.USER_DATE_FORMAT + ' ' + Zenoss.USER_TIME_FORMAT + ' z';
        }
        // timestamp in seconds (UNIX style)
        if (Ext.isNumeric(date)) {
            return moment.unix(date).tz(Zenoss.USER_TIMEZONE).format(format);
        }
        // Ext Datetime object
        if (Ext.isDate(date)) {
            return moment.tz(date, Zenoss.USER_TIMEZONE).format(format);
        }
        return date;
    },

    conditionalEscaping: function(data) {
        if (!Zenoss.settings.enableHtmlInEventFields)
            return Ext.htmlEncode(data);
        else
            return data;
    },

    bytesString: function(num) {
        return num===0 ? '0' :convertToUnits(num, 1024.0, 'B');
    },

    memory: function(mb) {
        return (mb === 0) ? '0' : convertToUnits(mb, 1024.0, 'B', 2);
    },

    link_speed: function(bps) {
      return (bps===0) ? '0': convertToUnits(bps, 1000.0, 'bps', 0);
    },

    cpu_speed: function(speed) {
        if (speed) {
            var n = parseFloat(speed);
            if (isNaN(n)) {
                return speed;
            } else {
                return convertToUnits(n, 1000, 'Hz', 2);
            }
        } else {
            return speed;
        }
    },

    checkbox: function(bool) {
        if (bool) {
            return '<input type="checkbox" checked="true" disabled="true">';
        } else {
            return '<input type="checkbox" disabled="true">';
        }
    },

    pingStatus: function(bool) {
        var str = pingStatusBase(bool);
        return upDownTemplate.apply([str.toLowerCase(), str]);
    },

    pingStatusLarge: function(bool) {
        var str = pingStatusBase(bool);
        return upDownTemplate.apply([str.toLowerCase(), str, '-large']);
    },

    upDownUnknown: function(status,displayString){
        return upDownTemplate.apply([status.toLowerCase(),displayString]);
    },

    upDownUnknownLarge: function(status,displayString){
        return upDownTemplate.apply([status.toLowerCase(),displayString,'-large']);
    },

    ipInterfaceStatus: function(ifStatus) {
        return ipInterfaceStatusTemplate.apply(ifStatus);
    },

    ipAddress: function(ip) {
        if (Ext.isObject(ip)) {
            ip = ip.name;
        }
        if (!ip||ip==='0.0.0.0') {
            return '';
        }
        return Ext.isString(ip) ? ip : Zenoss.util.num2dot(ip);
    },

    severity: function(sev) {
        return '<div class="severity-icon-small '+
            Zenoss.util.convertSeverity(sev) +
            '"'+'><'+'/div>';
    },

    // renders availability as a percentage with 3 digits after decimal point
    availability: function(value) {
        return Ext.util.Format.number(value*100, '0.000%');
    },

    evstatus: function(evstatus) {
        if (!evstatus){
            return '';
        }
        return '<span class="status-icon-small status-icon-small-'+evstatus.toLowerCase()+'"><'+'/span>';
    },

    events: function(value, count) {
        var result = '',
            sevs = ['critical', 'error', 'warning', 'info', 'debug', 'clear'],
            cssclass = '',
            total,
            acked;
        count = count || 3;
        Ext.each(sevs.slice(0, count), function(severity) {
            total = value[severity].count;
            acked = value[severity].acknowledged_count;
            cssclass = (total===0) ? 'no-events' : (total===acked) ? 'acked-events' : '';
            result += iconTemplate.apply({
                severity: severity,
                total: total,
                acked: acked,
                cssclass: cssclass
            });
        });
        return rainbowTemplate.apply({cells: result, count: count});
    },
    worstevents: function(value) {
        var result = '',
            sevs = ['critical', 'error', 'warning', 'info', 'debug', 'clear'],
            cssclass = '',
            total,
            acked;
        Ext.each(sevs, function(severity) {
            if (value[severity] && value[severity].count && !result) {
                total = value[severity].count;
                acked = value[severity].acknowledged_count;
                cssclass = (total===acked) ? 'acked-events' : '';
                result = iconTemplate.apply({
                    severity: severity,
                    total: total,
                    acked: acked,
                    cssclass: cssclass
                });
            }
        });
        return rainbowTemplate.apply({cells: result});
    },

    locking: function(obj) {
        /*
        * Expects an object with keys updates, deletion, events, all boolean
        */
        var from = [];
        if (obj.updates) {
            from.push('updates');
        }
        if (obj.deletion) {
            from.push('deletion');
        }
        if (!Ext.isEmpty(from)) {
            var l = _t('Locked from ') + from.join(_t(' and '));
            if (obj.events) {
                l += "<br/>"+_t("Send event when blocked");
            } else {
                l += "<br/>"+_t("Do not send event when blocked");
            }
            return l;
        } else {
            return _t('Unlocked');
        }
    },

    locking_icons: function(obj) {
        /*
        * Expects an object with keys updates, deletion, events, all boolean
        * Returns images representing locking status.
        */
        var tpl = new Ext.Template(
            '<img border="0" src="locked-{str}-icon.png"',
            'style="vertical-align:middle"/>'),
            result = '';
        tpl.compile();
        if (obj.updates) {
            result += tpl.apply({str:'update'});
        }
        if (obj.deletion) {
            result += tpl.apply({str:'delete'});
        }
        if (obj.events) {
            result += tpl.apply({str:'sendevent'});
        }
        return result;
    },

    /*
     * Given a uid, determines the type of the object and passes rendering
     * off to the appropriate rendering function.
     * e.g. Zenoss.render.link('/zport/dmd/Devices/Server') =>
     * <a href="/zport/dmd/itinfrastructure#devices:/Devices/Server/Linux">...
     *
     * Can also just accept a url and name for wrapping in an anchor tag, by
     * passing in null for the first argument.
     */
    link: function(uid, url, name) {
        if (!url) {
            var dflt = 'default_uid_renderer',
                type = Zenoss.types.type(uid) || dflt,
                renderer = Zenoss.render[type];
            if (renderer) {
                return renderer(uid, name);
            }
        }
        if (url && name) {
            return '<a class="z-entity" href="'+url+'">'+Ext.htmlEncode(name)+'</a>';
        }
        if (url) {
           return url;
        }
    },

    default_uid_renderer: function(uid, name) {
        // Just straight up links to the object.
        var parts,
            vTypes = Ext.form.VTypes;
        // ZEN-29776: do not render ipaddress as link
        // since there is no such object in the system and
        // "192.168.1.1/24" is not an zope uid format.
        if (!uid || vTypes.ipaddress(uid) || vTypes.ipaddresswithnetmask(uid)) {
            return uid;
        }
        if (Ext.isObject(uid)) {
            name = uid.name;
            uid = uid.uid;
        }
        if (!name) {
            parts = uid.split('/');
            name = parts[parts.length-1];
        }
        return Zenoss.render.link(null, uid, name);
    },

    linkFromGrid: function(value) {
        var item;
        if (Ext.isObject(value)) {
            item = value;
            if(item === null){
                return value;
            }else if(item.url) {
                return Zenoss.render.link(null, item.url, item.text);
            }else if(item.uid) {
                // Don't render link to event class page for user without global role as
                // as such user doesn't have access to view such page
                if (!_has_global_roles() && item.uid.includes("/dmd/Events/")) {
                    return item.text
                } else {
                    return Zenoss.render.link(item.uid, null, item.text);
                }
            }
            return Ext.htmlEncode(item.text);
        }
        return Ext.htmlEncode(value);
    },

    LinkFromGridGuidGroup: function(name) {
        if (!name) {
            return name;
        }

        var url, results = [];
        Ext.each(name, function(item){
            url = "/zport/dmd/goto?guid=" + item.uuid;
            results.push(Zenoss.render.link(null, url, item.name));
        });

        return results.join(" | ");
    },

    LinkFromGridUidGroup: function(name) {
        if (!name) {
            return name;
        }

        var results = [];
        Ext.each(name, function(item) {
            results.push(Zenoss.render.default_uid_renderer(item.uid, item.name));
        });

        return results.join(" | ");
    },

    componentLinkFromGrid: function(obj, col, record) {
        if (!obj) {
            return;
        }

        if (typeof(obj) === 'string') {
            obj = record.data;
        }

        if (!obj.title && obj.name) {
            obj.title = obj.name;
        }

        if (this.subComponentGridPanel || this.componentType !== obj.meta_type) {
            return '<a href="javascript:Ext.getCmp(\'component_card\').componentgrid.jumpToEntity(\''+obj.uid+'\', \''+obj.meta_type+'\');">'+obj.title+'</a>';
        }
        return obj.title;
    },

    Device: function(uid, name, fragment) {
        if (!Ext.isString(fragment)) {
            fragment = 'deviceDetailNav:device_overview';
        }
        // For now, link to the old device page
        return Zenoss.render.link(null, uid+'/devicedetail#'+fragment, name);
    },

    DeviceClass: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Devices/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#devices:.zport.dmd.Devices' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) {
            name = value;
        }
        return Zenoss.render.link(null, url, name);
    },

    DeviceLocation: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Locations/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#locs:.zport.dmd.Locations' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) {
            name = value;
        }
        return Zenoss.render.link(null, url, name);
    },

    DeviceGroup: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Groups/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#groups:.zport.dmd.Groups' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) {
            name = value;
        }
        return Zenoss.render.link(null, url, name);
    },
    DeviceSystem: function(uid, name) {
        var value = uid.replace(/^\/zport\/dmd\/Systems/, '');
        value = value.replace(/\/devices\/.*$/, '');
        var url = '/zport/dmd/itinfrastructure#systemsTree:.zport.dmd.Systems' + value.replace(/\//g,'.');
        if (!Ext.isString(name)) {
            name = value;
        }
        return Zenoss.render.link(null, url, name);
    },

    DeviceComponent: function(name, col, record) {
        var item = record.data[col.id];
        if (item.uid){
            // TODO once these pages are built fix the link
            return Zenoss.render.default_uid_renderer(item.uid, item.text);
        }
        return item.text;
    },

    EventClass: function(uid, name) {
        // don't render link to the event class page for user without globa role
        // as such user doesn't have permission to see it
        if (!_has_global_roles()) {
            return name
        } else {
            return Zenoss.render.default_uid_renderer(uid, name);
        }
    },

    IpServiceClass: function(value, metadata, record) {
        // this is intended to set directly as a column renderer instead of
        // using Types.js. See the Ext.grid.ColumnModel.setRenderer
        // documentation
        var uid = record.data.serviceClassUid.replace(/\//g, '.');
        return Zenoss.render.serviceClass('ipservice', uid, value);
    },

    WinServiceClass: function(value, metadata, record) {
        // this is intended to set directly as a column renderer instead of
        // using Types.js. See the Ext.grid.ColumnModel.setRenderer
        // documentation
        var uid = record.data.serviceClassUid.replace(/\//g, '.');
        return Zenoss.render.serviceClass('winservice', uid, value);
    },

    serviceClass: function(page, uid, name) {
        var url = Ext.String.format('/zport/dmd/{0}#navTree:{1}', page, uid);
        return Zenoss.render.link(null, url, name);
    },

    nextHop: function(value){
        var link = "";
        if (value && value.uid && value.id) {
            link += Zenoss.render.IpAddress(value.uid, value.id);
            if (value.device && value.device.uid && value.device.id) {
                link += " (";
                link += Zenoss.render.Device(value.device.uid, value.device.id);
                link += ")";
            }
        }
        return link;
    },

    IpInterface: function(uid, name) {
        var deviceUid = uid.split('/os/interfaces/')[0];
        var url = deviceUid + '/devicedetail#deviceDetailNav:IpInterface:' + uid;
        return Zenoss.render.link(null, url, name);
    },

    IpAddress: function(uid, name) {
        return Zenoss.render.Network(uid, name);
    },

    Network: function(uid, name) {
        var url = '/zport/dmd/networks#networks:' + uid.replace(/\//g, '.');
        if (!name) {
            var parts = uid.split('/');
            name = parts[parts.length-1];
        }
        return Zenoss.render.link(null, url, name);
    },

    Process: function(uid, name) {
        var url = '/zport/dmd/process#processTree:' + uid.replace(/\//g, '.');
        if (!name) {
            var parts = uid.split('/');
            name = parts[parts.length-1];
        }
        return Zenoss.render.link(null, url, name);
    },

    HyperlinkTag : function(uid, name) {
        //When we get hyperlink tag return it back
        return Zenoss.render.link(null, uid, null);
    },

    eventSummaryRow:function (data, metadata, record){
        var msg = record.data.message;
        if (!msg || msg === "None" ) {
            msg = record.data.summary;
        }
        msg = Zenoss.render.conditionalEscaping(msg);
        msg = "<pre style='white-space:normal;'>" + msg + "</pre>";
        msg = msg.replace(/\"/g, '&quot;');
        metadata.tdAttr = 'data-qtip="' + Zenoss.render.conditionalEscaping(msg) + '" data-qwidth="500"';

        data = Zenoss.render.conditionalEscaping(data);
        return data;
    },

    zProperty: function(value, record) {
        // if value is an object or array, it must be stringified via JSON
        if (typeof value === "object") {
            value = JSON.stringify(value);
        }
        var severityFields = ['zEventSeverity', 'zFlappingSeverity'];
        if (severityFields.includes(record.data.id)) {
            if (value === -1) {
                value = 'Default (-1)';
            } else {
                value = Ext.String.format('{0} ({1})', Zenoss.util.convertSeverity(value), value);
                value = value.charAt(0).toUpperCase() + value.slice(1);
            }
        }
        return Ext.htmlEncode(value);
    },

    // Renders the paths of properties by removing the '/zport/dmd/Devices' from the start.
    PropertyPath: function(path) {
        var exclusions = ['zport', 'dmd', 'Devices'],
            exclude = function(v) { return exclusions.indexOf(v) === -1; };
        return '/' + path.split('/').slice(1).filter(exclude).join('/');
    }

}); // Ext.apply

})(); // End local namespace
