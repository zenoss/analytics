//var DEBUG_MODE = true;
if (typeof(DEBUG_MODE)=='undefined') var DEBUG_MODE = false;
if (typeof(VERSION_ID)=='undefined') var VERSION_ID = '';
var DEBUG_MODE = false;

// Graceful degradation of Firebug console object
// via http://ajaxian.com/archives/graceful-degradation-of-firebug-console-object
if (! ("console" in window)) {

    var names = ["log", "debug", "info", "warn", "error", "assert",
                 "dir", "dirxml", "group", "groupEnd", "time", "timeEnd",
                 "count", "trace", "profile", "profileEnd"];
    window.console = {};
    for (var i = 0; i <names.length; ++i) window.console[names[i]] = function() {};}

// alias MochiKit to $MK to make way for jquery
var $MK = $;

// Set up the Javascript loader
function getLoader(withtests) {
    /**
    * Get a YAHOO.util.YUILoader configured to load Zenoss-specific skins and
    * scripts. Optionally register test modules with the loader.
    */
    var withtests = withtests || false;
    configObj = {
        onFailure: function(msg, xhrreq) {
            console.warn('FAILURE: ' + msg)
        }
    };
    if (DEBUG_MODE) configObj.filter = 'DEBUG';
    else {
        configObj.filter = {
            'searchExp': "\\.js",
            'replaceStr': ".js?_dc=" + VERSION_ID
        }
    }
    loader = new YAHOO.util.YUILoader(configObj);
    loader.base = '/zport/dmd/yui/';

    // Register zenoss scripts
    loader.addModule({
        name: "datatablesamskin",
        type: "css",
        fullpath: "/zport/dmd/yui/datatable/assets/skins/sam/datatable.css"
    });
    loader.addModule({
        name: "autocompleteskin",
        type: "css",
        fullpath: "/zport/dmd/yui/autocomplete/assets/skins/sam/autocomplete.css"
    });
    loader.addModule({
        name: "zenautocomplete",
        type: "js",
        fullpath: "/zport/dmd/javascript/zenautocomplete.js",
        requires: ["datasource", "autocomplete", "animation",
                   "autocompleteskin","zenossutils"]
    });
    loader.addModule({
        name: "portlet",
        type: "js",
        fullpath: "/zport/dmd/javascript/portlet.js",
        requires: ["dragdrop", "event", "dom", "animation",
                   "datasource", "datatable", "datatablesamskin",
                   "container", "button","zenautocomplete", "zenossutils"]
    });
    loader.addModule({
        name: "portletsource",
        type: "js",
        fullpath: "/zport/ZenPortletManager/get_source",
        requires: ["portlet"]
    });
    loader.addModule({
        name: "zenossutils",
        type: "js",
        fullpath: "/zport/javascript/zenoss-utils.js",
        requires: ['dom', 'event']
    });
    loader.addModule({
        name: "devicezengrid",
        type: "js",
        fullpath: "/zport/dmd/javascript/devicezengrid.js",
        requires: ['zenossutils']
    });
    loader.addModule({
        name: "eventzengrid",
        type: "js",
        fullpath: "/zport/dmd/javascript/zengrid.js",
        requires: ['zenossutils']
    });
    loader.addModule({
        name: 'geomap',
        type: 'js',
        fullpath: '/zport/dmd/javascript/geomap.js',
        requires: ['zenossutils', 'container', 'json']
    });
    loader.addModule({
        name: 'swoopygraphs',
        type: 'js',
        fullpath: '/zport/dmd/zenrrdzoom.js',
        requires: ['zenossutils']
    });
    loader.addModule({
        name: 'yowl-base',
        type: 'js',
        fullpath: '/zport/dmd/yowl/yowl.js',
        requires: ['event', 'animation', 'container']
    });
    loader.addModule({
        name: 'yowl',
        type: 'js',
        fullpath: '/zport/dmd/yowl/display-yui.js',
        requires: ['yowl-base', 'yowl-style']
    });
    loader.addModule({
        name: 'yowl-style',
        type: 'css',
        fullpath: '/zport/dmd/yowl/yowl.css'
    });

    if (withtests) {
        loader.addModule({
            name: 'test_example',
            type: 'js',
            fullpath: '/zport/dmd/javascript/tests/test_example.js',
            requires: ['yuitest']
        });
    }
    return loader;
}

//Declare the Zenoss namespace
YAHOO.namespace("zenoss");

// Put the loader somewhere accessible
YAHOO.zenoss.getLoader = getLoader;

if (DEBUG_MODE) {
    loader = getLoader();
    loader.require(['logger']);
    loader.insert({onSuccess:function(){YAHOO.widget.Logger.enableBrowserConsole()}})
}

function runtests(pkg) {
    /**
    * Run tests associated with a package.
    *
    * Test package must be included in the getLoader function, above, and must
    * include TestSuites and/or TestCases that register themselves with
    * YAHOO.tool.TestRunner. See tests/test_example.js for an example.
    */
    loader = getLoader(true);
    loader.require(['logger', 'yuitest', 'test_'+pkg])
    loader.insert({
        onSuccess: function(){
            var oLogger = new YAHOO.tool.TestLogger();
            YAHOO.tool.TestRunner.run();
        },
        onFailure: function(o) {
            console.log(o.msg);
        }
    });
}
