
var ContextMenu = function() {

    var idseed = 0;

    var menu = function(ds) {
        var attach = this;

        // Create the menu items
        var menu = {};
        for (var i = 0; i < ds.length; i++) {
            var item = ds[i];
            var itemname = name.call(this, item);
            menu[itemname] = {
                "click": menuClick(attach, item, i),
                "mouseover": menuMouseOver(attach, item, i),
                "mouseout": menuMouseOut(attach, item, i)
            };
        }

        // Set the options
        var options = {
            "disable_native_context_menu": true,
            "showMenu": function() { handlers.open.call(attach, ds); },
            "hideMenu": function() { handlers.close.call(attach, ds); }
        }

        // Attach the context menu to this element
        $(attach).contextMenu('context-menu'+(idseed++), menu, options);
    }

    // Stupid javascript
    var menuClick = function(attach,d, i) {
        return function() {
            handlers.click.call(attach, d, i);
        }
    }

    // Stupid stupid javascript
    var menuMouseOver = function(attach, d, i) {
        return function() {
            handlers.mouseover.call(attach, d, i);
        }
    }

    // Stupid stupid stupid javascript
    var menuMouseOut = function(attach, d, i) {
        return function() {
            handlers.mouseout.call(attach, d, i);
        }
    }

    var name = function(d) { return d.name; }

    var handlers = {
        "click": function() {},
        "open": function() {},
        "close": function() {},
        "mouseover": function() {},
        "mouseout": function() {}
    }


    menu.name = function(_) { if (arguments.length==0) return name; name = _; return menu; }
    menu.on = function(event, _) {
        if (!handlers[event]) return menu;
        if (arguments.length==1) return handlers[event];
        handlers[event] = _;
        return menu;
    }


    return menu;
}