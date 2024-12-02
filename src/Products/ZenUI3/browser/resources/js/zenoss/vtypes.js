(function(){
    Ext.ns('Zenoss.VTypes');

    var ipv4_regex = new RegExp("^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$");
    var ipv6_regex = new RegExp("^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?\s*$");
    var ip_with_netmask_regex = new RegExp("^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(/[0-9]+)$");
    var ipv6_with_netmask_regex = new RegExp("^\s*((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?(/[0-9]+)$");
    var hex_regex = new RegExp("^#?([a-f]|[A-F]|[0-9]){3}(([a-f]|[A-F]|[0-9]){3,5})?$");
    var numcmp_regex = new RegExp("^(\>=|\<=|\>|\<|=)?\s*([0-9]+)$");
    var numrange_regex = new RegExp("^(-?[0-9]+)?:?(-?[0-9]+)?$");
    var range_regex = new RegExp("^([^:]*):?([^:]*)$");
    var alpha_num_space = new RegExp(/[a-z_\s\d]/i);
    var hostname_or_ip_regex = new RegExp(/[a-zA-Z0-9-_.\(\)\/:]/);

    /**
     * These are the custom validators defined for
     * our zenoss forms. The xtype/vtype custom is to have the
     * name of the vtype all lower case with no word separator.
     *
     **/
    var vtypes = {
        /**
         * Allows int comparisons like 4,>2,<=5
         */
        numcmp: function(val) {
            return numcmp_regex.test(val);
        },
        numcmpText: _t('Enter a valid comparison (ex: 4, <2, >=1)'),

        numrange: function(val) {
            var result, from, to;
            result = numrange_regex.exec(val);
            if (!result) {
                return false;
            }
            from = result[1];
            to = result[2];
            if (from && to) {
                return parseInt(from) <= parseInt(to);
            }
            return true;
        },
        numrangeText: _t('Enter a valid numeric range (ex: 2, 5:, 6:8, :9)'),

        floatrange: function(val) {
            var result, from, to;
            result = range_regex.exec(val);
            if (!result) {
                return false;
            }
            from = result[1];
            to = result[2];
            if (from && to) {
                from = parseFloat(from);
                to = parseFloat(to);
                return !isNaN(from) && !isNaN(to) && from <= to;
            }
            if (from) {
                return !isNaN(parseFloat(from));
            }
            if (to) {
                return !isNaN(parseFloat(to));
            }
            return true;
        },
        floatrangeText: _t('Enter a valid floating point range (ex: 1, 2.5:5.5, 2.5:, :9.5'),

        /**
         * The number must be greater than zero. Designed for us in NumberFields
         **/
        positive: function(val) {
            return (val >= 0);
        },
        positiveText: _t('Must be greater than or equal to 0'),

        /**
         * Between 0 and 1 (for float types)
         **/
        betweenzeroandone: function(val) {
            return (val >= 0 && val <=1);
        },
        betweenzeroandoneText: _t('Must be between 0 and 1'),
        ipaddress: function(val) {
            return ipv4_regex.test(val) || ipv6_regex.test(val);
        },
        ipv6address: function(val) {
            return ipv6_regex.test(val);
        },
        ipaddressText: _t('Invalid IP address'),

        ipaddresswithnetmask: function(val) {
            return ip_with_netmask_regex.test(val) || ipv6_with_netmask_regex.test(val);
        },
        ipaddresswithnetmaskText: _t('You must enter a valid IP address with netmask.'),

        /**
         * Hex Number (for colors etc)
         **/
        hexnumber: function(val) {
            return hex_regex.test(val);
        },
        hexnumberText: _t('Must be a 6 or 8 digit hexadecimal value.'),

        /**
         * Modifies alpha number to allow spaces
         **/
        alphanumspace: function(val) {
            return alpha_num_space.test(val);
        },
        alphanumspaceText: _t('Must be an alphanumeric value or a space '),
        alphanumspaceMask: alpha_num_space,

        hostnameorIP: function(val) {
            return hostname_or_ip_regex.test(val);
        },
        hostnameorIPText: _t('Must be a valid hostname or IP address '),
        hostnameorIPMask: hostname_or_ip_regex
    };

    Ext.apply(Ext.form.VTypes, vtypes);
}());
