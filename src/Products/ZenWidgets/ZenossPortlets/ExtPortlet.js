var NS = Ext.ns('Zenoss.portlets');

var $portletId = Subclass.create(YAHOO.zenoss.portlet.Portlet);
$portletId.prototype = {
    __class__:"YAHOO.zenoss.portlet.$portletId",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args ? args.id : getUID('extgeneric');
        datasource = 'datasource' in args ? args.datasource :
            new YAHOO.zenoss.portlet.ExtDatasource({portletId: '$portletId'});
        bodyHeight = 'bodyHeight' in args ? args.bodyHeight : $portletHeight;
        title = 'title' in args ? args.title : "$portletTitle";
        refreshTime = 'refreshTime' in args ? args.refreshTime : 60;
        this.superclass.__init__({id: id, title: title, datasource: datasource,
                                 refreshTime: refreshTime, bodyHeight: bodyHeight});

        var thisPortlet = this,
            settingsSlot = this.settingsSlot;

        var task = {
            run: function() {
                if (thisPortlet.datasource.extPortlet) {
                    Ext.TaskManager.stop(task);
                    var extP = thisPortlet.extPortlet = thisPortlet.datasource.extPortlet;
                    delete thisPortlet.datasource.extPortlet;

                    if (!thisPortlet.datasource.extSettings) {
                        thisPortlet.datasource.extSettings =
                            extP.portlet_settings_defaults();
                    }

                    if (extP.portlet_settings_render) {
                        extP.portlet_settings_render(settingsSlot,
                                                     thisPortlet.datasource.extSettings);
                    }

                    extP.portlet_render();
                }
            },
            interval: 100
        };
        Ext.TaskManager.start(task);
    },
    startRefresh: function(firsttime) {
        this.stopRefresh();
        if (!firsttime) {
            if (this.extPortlet.portlet_refresh)
                this.extPortlet.portlet_refresh();
        }
        if (this.refreshTime>0)
            this.calllater = callLater(this.refreshTime, this.startRefresh);
    },
    saveSettings: function(settings) {
        settings.extSettings = this.extPortlet.portlet_settings_save();
        this.refreshTime = settings['refreshTime'];
        this.title = settings['title'];
        this.setTitleText(this.title);
        for (setting in settings) {
            this.datasource[setting] = settings[setting];
        }
        this.PortletContainer.isDirty = true;
        this.PortletContainer.save();
        this.startRefresh(true);
    }
}
YAHOO.zenoss.portlet.$portletId = $portletId;
