(function() { // Local scope

Ext.namespace('Zenoss.inspector');


/**
 * Manages inspector windows to ensure that only one window matching
 * `uid` is active at a time.
 */
Zenoss.inspector.SingleInstanceManager = Ext.extend(Object, {
    _instances: null,
    constructor: function() {
        this._instances = {};
    },
    register: function(uid, instance) {
        this.remove(uid);
        this._instances[uid] = instance;
        instance.on('destroy', function() { delete
        this._instances[uid]; }, this);
    },
    get: function(uid) {
        return this._instances[uid];
    },
    remove: function(uid) {
        Ext.destroyMembers(this._instances, uid);
    }
});


/**
 * Represents a single item in the inspector panel.
 *
 * config:
 * - valueTpl An XTemplate that can be used to render the field. Will
 *            be passed the data that is passed to the inspector.
 */
Ext.define('Zenoss.inspector.InspectorProperty', {
    alias: ['widget.inspectorprop'],
    extend: 'Ext.Container',
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            cls: 'inspector-property',
            layout: 'anchor',
            items: [
                {
                    cls: 'inspector-property-label',
                    ref: 'labelItem',
                    xtype: 'label',
                    text: config.label ? config.label + ':' : ''
                },
                {
                    cls: 'inspector-property-value',
                    ref: 'valueItem',
                    text: config.value || '',
                    xtype: 'panel',
                    tpl: config.valueTpl || '{.}'
                }
            ]
        });
        this.callParent(arguments);
    },
    setValue: function(t) {
        this.valueItem.update(t);
    },
    setLabel: function(t) {
        this.labelItem.setText(t + ':');
    }
});


Ext.define('Zenoss.inspector.BaseInspector', {
    extend: 'Ext.Panel',
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            defaultType: 'container',
            layout: 'anchor',
            bodyBorder: false,
            items: [],
            titleTpl: '<div class="name">{name}</div>'
        });

        config.items = [
            {
                layout: 'hbox',
                cls: 'inspector-header',
                ref: 'headerItem',
                items: [
                    {
                        cls: 'header-icon-wrapper',
                        ref: 'iconItem',
                        xtype: 'container',
                        layout: 'fit'
                    },
                    {
                        cls: 'header-title',
                        ref: 'titleItem',
                        xtype: 'container',
                        tpl: config.titleTpl,
                        layout: 'fit'
                    }
                ]
            },
            {
                xtype: 'container',
                cls: 'inspector-body',
                autoEl: 'div',
                layout: 'anchor',
                ref: 'bodyItem',
                defaultType: 'inspectorprop',
                items: config.items
            }
        ];

        this.callParent(arguments);
    },
    setIcon: function(url) {
        if (this.headerItem.iconItem.getEl()) {
            this.headerItem.iconItem.getEl().setStyle(
                'background-image', 'url(' + url + ')'
            );
        } else {
            this.headerItem.iconItem.update(Ext.String.format('<img class="header-icon" src="{0}" alt="" />', url));
        }
    },
    /**
     * Overwrite to add any properties dynamically from the data. Must
     * return true if added any.
     */
    addNewDataItems: function() {
        return false;
    },
    update: function(data) {

        if (this.addNewDataItems(data)) {
            this.doLayout();
        }

        // update all the children that have templates
        var self = this;
        this.cascade(function(item) {
            if (item !== self && item.tpl) {
                item.data = data;
                item.update(data);
            }

            return true;
        });
        if (data.icon) {
            this.setIcon(data.icon);
        }

        if (this.ownerCt) {
            this.ownerCt.doLayout();
        }
        else {
            this.doLayout();
        }

    },
    /**
     * Add a property to the inspector panel for display.
     *@param {string} label
     *@param {string} id The key from the data to display.
     */
    addProperty: function(label, id) {
        this.addPropertyTpl(label, '{[values.' + id + ' || ""]}');
    },
    /**
     * Add a property to the inspector panel using a template to display.
     * @param {string} label label of template.
     * @param {string} tpl A string in XTemplate format to display
     * this property. Data values are in `values`.
     */
    addPropertyTpl: function(label, tpl) {
        this.bodyItem.add({
            xtype: 'inspectorprop',
            label: label,
            valueTpl: tpl
        });
    }
});

/**
 * An inspector that gets its data via a directFn remote call.
 */
Zenoss.inspector.DirectInspector = Ext.extend(Zenoss.inspector.BaseInspector, {
    _contextUid: null,
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            directFn: Ext.emptyFn
        });

        Zenoss.inspector.DirectInspector.superclass.constructor.call(this, config);
    },
    initComponent: function() {
        Zenoss.inspector.DirectInspector.superclass.initComponent.call(this);
        this.addEvents('contextchange');
        this.on('contextchange', this._onContextChange, this);
    },
    refresh: function() {
        this.load();
    },
    load: function() {
        if (this._contextUid) {
            this.directFn(
                { uid: this._contextUid, keys: this.keys },
                function(result) {
                    if (result.success) {
                        this.fireEvent('contextchange', result.data, this);
                    }
                },
                this
            );
        }
    },
    setContext: function(uid, load) {
        this._contextUid = uid;
        load = Ext.isDefined(load) ? load : true;

        if (load) {
            this.load();
        }
    },
    _onContextChange: function(data) {
        this.onData(data);
    },
    onData: function(data) {
        this.update(data);
    }
});

Ext.define('Zenoss.inspector.DeviceInspector', {
    alias: ['widget.deviceinspector'],
    extend: 'Zenoss.inspector.DirectInspector',
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            directFn: Zenoss.remote.DeviceRouter.getInfo,
            keys: ['ipAddress', 'device', 'deviceClass'],
            cls: 'inspector',
            titleTpl: '<div class="name"><a href="{uid}" target="_top">{name}</a></div><div class="info">{[Zenoss.render.DeviceClass(values.deviceClass.uid)]}</div><div class="info">{[Zenoss.render.ipAddress(values.ipAddress)]}</div>'
        });
        this.callParent(arguments);

        var url = "{uid}/devicedetail?filter=default#deviceDetailNav:device_events";
        this.addPropertyTpl(_t('Events'), '<div onclick="location.href=\''+url+'\';">{[Zenoss.render.events(values.events, 4)]}</div>');
        this.addPropertyTpl(_t('Device Status'), '{[Zenoss.render.pingStatus(values.status)]}');
        this.addProperty(_t('Production State'), 'productionState');
        this.addPropertyTpl(_t('Location'), '{[(values.location && values.location.name) || ""]}');
    }
});


Ext.define('Zenoss.inspector.ComponentInspector', {
    alias: ['widget.componentinspector'],
    extend: 'Zenoss.inspector.DirectInspector',
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            directFn: Zenoss.remote.DeviceRouter.getInfo,
            keys: ['ipAddress', 'device'],
            cls: 'inspector',
            titleTpl: '<div class="name"><a href="{uid}" target="_top">{name}</a></div><div class="info"><a href="{[values.device.uid]}" target="_top">{[values.device.name]}</a></div><div class="info">{[Zenoss.render.ipAddress(values.ipAddress)]}</div>'
        });

        config.items = [(
            {
                label: _t('Events'),
                valueTpl: '{[Zenoss.render.events(values.events, 4)]}'
            }
        )];

        this.callParent(arguments);
    },
    update: function(data) {
        // our template relies on a device being present
        if (!data.device) {
            data.device = { };
        }
        this.callParent(arguments);
    }
});

var windowManager = new Zenoss.inspector.SingleInstanceManager();
Zenoss.inspector.createWindow = function(uid, xtype, x, y) {

    var win = new Ext.Window({
        x: (x || 0),
        y: (y || 0),
        cls: 'inspector-window',
        plain: true,
        frame: false,
        constrain: true,
        model: false,
        layout: 'fit',
        width: 300,
        items: [{
            xtype: xtype,
            ref: 'panelItem'
        }]
    });

    windowManager.register(uid, win);
    return win;
};

Zenoss.inspector.registeredInspectors = {
    device: 'deviceinspector'
};

Zenoss.inspector.registerInspector = function(inspector_type, inspector_xtype) {
    Zenoss.inspector.registeredInspectors[inspector_type.toLowerCase()] = inspector_xtype;
};

Zenoss.inspector.show = function(uid, x, y) {
    Zenoss.remote.DeviceRouter.getInfo({ uid: uid }, function(result) {
        if (result.success) {
            // Grasping at straws but assume it's a component unless otherwise stated
            var xtype = 'componentinspector';

            var itype = result.data.inspector_type || result.data.meta_type;
            if (itype) {
                itype = itype.toLowerCase();
                if (Zenoss.inspector.registeredInspectors[itype]) {
                    xtype = Zenoss.inspector.registeredInspectors[itype];
                }
            }
            var win = Zenoss.inspector.createWindow(uid, xtype, x, y);
            win.panelItem.setContext(uid, false);
            win.panelItem.update(result.data);
            win.show();
            win.toFront();
        }
    });
};

})();
