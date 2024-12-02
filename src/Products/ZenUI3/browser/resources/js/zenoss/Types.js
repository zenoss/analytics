(function(){

var _tm = {
    'IpAddress':        ["^/zport/dmd/.*/ipaddresses/[^/]*/?$"],
    'IpInterface':      ["^/zport/dmd/Devices/.*/devices/.*/os/interfaces/.*"],
    'Device':           ["^/zport/dmd/.*/devices/[^/]*/?$"],
    'DeviceLocation':   ["^/zport/dmd/Locations/"],
    'DeviceSystem':     ["^/zport/dmd/Systems/"],
    'DeviceGroup':      ["^/zport/dmd/Groups/"],
    'DeviceClass':      ["^/zport/dmd/Devices(/(?!devices)[^/]+)*/?$"],
    'EventClass':       ["^/zport/dmd/Events(/[A-Za-z][^/]*)*/?$"],
    'Network':          ["^/zport/dmd/Networks(/(?!ipaddresses)[^/]+)*/?$"],
    'Process':          ["^/zport/dmd/Processes(.*)$"],
    'HyperlinkTag':     ["href=[\"\'](.*?)[\"\']"]
};

var T = Ext.ns('Zenoss.types');

Ext.apply(T, {

    TYPES: {},

    getAllTypes: function() {
        var result = [];
        for (var k in T.TYPES) {
            if (true) {
                result.push(k);
            }
        }
        return result;
    }, // getAllTypes

    type: function(uid) {
        var _f;
        for (var type in T.TYPES) {
            if (T.TYPES[type]) {
                _f = true;
                Ext.each(T.TYPES[type], function(test) {
                    if (!_f) {
                        return;
                    }
                    _f = test.test(uid);
                });
                if (_f) {
                    return type;
                }
            }
        }
        return null;
    }, // getType

    register: function(config) {
        function addRegex(k, t) {
            var types = T.TYPES[k] = T.TYPES[k] || [];
            if (!(t instanceof RegExp)) {
                t = new RegExp(t);
            }
            if (!(t in types)) {
                types.push(t);
            }
        }
        for (var k in config) {
            var t = config[k];
            if (Ext.isString(t)) {
                addRegex(k, t);
            } else if (Ext.isArray(t)) {
                Ext.each(t, function(r) {
                    addRegex(k, r);
                });
            }

        }
    } // register

}); // Ext.apply

T.register(_tm);

})(); // End local scope
