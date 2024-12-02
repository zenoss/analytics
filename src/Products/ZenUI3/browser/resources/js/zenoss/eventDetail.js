Ext.onReady(function() {
    Ext.ns('Zenoss.eventdetail');

    /**
     * This property is used by ZenPacks and other things to specify custom
     * renderers for fields in the detail panel before the panel has
     * instantiated. Once instantiated, the panel will apply any renderers
     * found here.
     */
    if (!Zenoss.hasOwnProperty('event_detail_custom_renderers')) {
        Zenoss.event_detail_custom_renderers = {};
    }

    /**
     * This property is by ZenPacks and other things to specify custom sections
     * for the detail panel before the panel has been instantiated. The section
     * config must specify a `section_class` property which is the string name
     * of a section class ('Section', 'RepeatedSection', etc.).
     *
     * A section config may also specify `renderers` which will specify a custom
     * renderer for a field. This will override the renderer for that field for
     * the entire detail panel.
     *
     * If a section config specifies a `title` property, the title will be used
     * to toggle display of the section.
     */
    if (!Zenoss.hasOwnProperty('event_detail_custom_sections')) {
        Zenoss.event_detail_custom_sections = {};
    }


    /**
     * The header used for the top of the event detail pane.
     * WAS Zenoss.eventdetail.detail_table_template
     */
    Zenoss.eventdetail.detail_header_template = ['<table width="99%" id="evdetail_props_table">',
        '<tr><td class="dt">',_t('Resource:'),'</td>',
            '<td>',
                '<tpl if="device">',
                    '{device}',
                '</tpl>',
            '</td>',
        '</tr>',
        '<tr><td class="dt">',_t('Component:'),'</td>',
            '<td>',
                '<tpl if="component">',
                    '{component}',
                '</tpl>',
            '</td>',
        '</tr>',
        '<tr><td class="dt">',_t('Event Class:'),'</td>',
            '<td>',
                '<tpl if="eventClass">',
                    '{eventClass}',
                '</tpl>',
            '</td>',
        '</tr>',
        '<tr><td class="dt">',_t('Status:'),'</td> <td>{eventState}</td></tr>',
        '<tr><td class="dt" valign="top">',_t('Message:'),'</td> <td id="event_details_event_message"><div class="event_message">{message}</div></td></tr>',
    '</table><div style="clear:both;"></div>'];

    /**
     * The template used for regular event properties.
     * WAS: Zenoss.eventdetail.fullprop_table_template
     */
    Zenoss.eventdetail.detail_data_template = ['<table class="proptable" width="100%">',
        '<tpl for="properties">',
        '<tr class=\'{[xindex % 2 === 0 ? "even" : "odd"]}\'>',
        '<td class="proptable_key">{key}</td>',
        '<td class="proptable_value"><div>{value}</div></td></tr>',
        '</tpl>',
        '</table>'];

    /**
     * Template for log messages.
     * WAS: Zenoss.eventdetail.log_table_template
     */
    Zenoss.eventdetail.detail_log_template = ['<table>',
        '<tpl for="log">',
        '<tr><td class="time">{0} {1}: </td>',
            '<td class="message">{2}</td></tr>',
        '</tpl>',
        '</table>'];


    /**
     * This class will generate HTML based on a template that simply uses named
     * properties:
     *
     *      "<p>{my_key}</p>"
     *
     */
    Zenoss.eventdetail.Section = Ext.extend(Object, {
        constructor: function(config){
            Ext.applyIf(config || {}, {
                template: Zenoss.eventdetail.detail_data_template
            });
            Ext.apply(this, config);

            Zenoss.eventdetail.Section.superclass.constructor.apply(this, arguments);
        },

        /**
         * A section is asked to generate its own HTML using this method.
         *
         * @param renderedData This is the event data after each field has been
         *                     rendered according to any renderers specified.
         *                     This contains all rendered data, not just the data
         *                     for the keys specified in this section.
         * @param eventData This is the raw event data. This is made available to
         *                  the section so that it may use it for whatever it wants.
         */
        generateHtml: function(renderedData, eventData) {
            var template = new Ext.XTemplate(this.template),
                props = {};
            Ext.each(this.keys, function(key) {
                props[key] = renderedData[key];
            });
            return template.apply(props);
        }
    });


    /**
     * This class will generate HTML based on a template that utilizes 'for'
     * and iterates over data on the 'properties' property:
     *
     *  "<tpl for="properties">
     *      <p>{key}: {value}</p>
     *   </tpl>"
     *
     */
    Zenoss.eventdetail.RepeatedSection = Ext.extend(Zenoss.eventdetail.Section, {
        constructor: function(config) {
            Ext.applyIf(config || {} , {
                generateHtml: function(renderedData, eventData) {
                    var template = new Ext.XTemplate(this.template),
                        props = {
                            properties: []
                        };
                    Ext.each(this.keys, function(key) {
                        props.properties.push({
                            key: key,
                            value: renderedData[key]
                        });
                    });
                    return template.apply(props);
                }
            });
            Zenoss.eventdetail.RepeatedSection.superclass.constructor.apply(this, arguments);
        }
    });


    /**
     * This special details section knows how to iterate over event details. Any
     * keys specified will be looked for in an event's details data.
     */
    Zenoss.eventdetail.DetailsSection = Ext.extend(Zenoss.eventdetail.RepeatedSection, {
        constructor: function(config) {
            Ext.applyIf(config || {} , {
                generateHtml: function(renderedData, eventData) {
                    var template = new Ext.XTemplate(this.template),
                        props = {
                            properties: renderedData.details
                        },
                        details = [];

                    if (this.hasOwnProperty('keys')) {
                        Ext.each(this.keys, function(key) {
                            Ext.each(renderedData.details, function(detail) {
                                if (detail.key === key) {
                                    details.push(detail);
                                }
                            }, this);
                        }, this);
                        props.properties = details;
                    }

                    return template.apply(props);
                }
            });
            Zenoss.eventdetail.DetailsSection.superclass.constructor.apply(this, arguments);
        }
    });


    /**
     * This panel represents the event detail panel. An initial "zenoss" config
     * is automatically loaded during instantiation in the `init` method.
     */
    Ext.define("Zenoss.DetailPanel", {
        extend:"Ext.Panel",
        alias: "widget.detailpanel",
        isHistory: false,
        layout: 'border',
        constructor: function(config){
            this.sections = [];
            this.renderers = {};
            config.onDetailHide = config.onDetailHide || Ext.emptyFn;
            config.items = [
                // Details Toolbar
                {
                    id: 'evdetail_hd',
                    region: 'north',
                    layout: 'border',
                    height: 50,
                    cls: 'evdetail_hd',
                    items: [{
                        region: 'west',
                        width: 77,
                        height:47,
                        defaults:{height:47},
                        layout: 'hbox',
                        items: [{
                            id: 'severity-icon',
                            cls: 'severity-icon'
                        },{
                            id: 'evdetail-sep',
                            cls: 'evdetail-sep'
                        }]
                    }, {
                        region: 'center',
                        id: 'evdetail-summary',
                        html: ''
                    },{
                        region: 'east',
                        id: 'evdetail-tools',
                        layout: 'hbox',
                        width: 57,
                        items: [{
                            id: 'evdetail-popout',
                            cls: 'evdetail-popout'
                        },{
                            id: 'evdetail_tool_close',
                            cls: 'evdetail_close'
                        }]
                    }]
                },

                // Details Body
                {
                    id: 'evdetail_bd',
                    region: 'center',
                    width: "90%",
                    autoScroll: true,
                    cls: 'evdetail_bd',
                    items: [   {
                        xtype:'toolbar',
                        width: "105%",
                        style: {
                            position: "relative",
                            top: -1
                        },
                        hidden: !config.showActions,
                        id: 'actiontoolbar',
                        items:[ {
                                xtype: 'tbtext',
                                text: _t('Event Actions:')
                            },
                            Zenoss.events.EventPanelToolbarActions.acknowledge,
                            Zenoss.events.EventPanelToolbarActions.close,
                            Zenoss.events.EventPanelToolbarActions.reopen,
                            Zenoss.events.EventPanelToolbarActions.unclose

                        ]
                    },
                    {
                        id: 'event_detail_properties',
                        frame: false,
                        defaults: {
                            frame: false
                        },
                        layout: {
                            type: 'table',
                            columns: 1,
                            tableAttrs: {
                                style: {
                                    width: '90%'
                                }
                            }
                        }
                    },

                    // Event Log Header
                    {
                        id: 'evdetail-log-header',
                        cls: 'evdetail-log-header',
                        hidden: false,
                        html: '<'+'hr/><'+'h2>LOG<'+'/h2>'
                    },

                    // Event Audit Form
                    {
                        xtype: 'form',
                        id: 'log-container',
                        width: '90%',
                        layout: {
                            type: 'table',
                            columns: 1
                        },
                        style: {'margin-left':'3em'},
                        hidden: false,
                        fieldDefaults: {
                            labelWidth: 1
                        },
                        items: [{
                            id: 'detail-logform-evid',
                            xtype: 'hidden',
                            name: 'evid'
                        },{
                            style: 'margin:0.75em',
                            width: 300,
                            xtype: 'textfield',
                            name: 'message',
                            listeners: {
                                specialkey: function(formEl, e){
                                    if (e.getCharCode() == Ext.EventObject.ENTER) {
                                        this.up('form').down('button').handler()
                                    }
                                }
                            },
                            hidden: Zenoss.Security.doesNotHavePermission('Manage Events'),
                            id: 'detail-logform-message'
                        },{
                            xtype: 'button',
                            type: 'submit',
                            name: 'add',
                            hidden: Zenoss.Security.doesNotHavePermission('Manage Events'),
                            text: 'Add',
                            handler: function(btn, e) {
                                var form = Ext.getCmp('log-container'),
                                vals = form.getForm().getValues(),
                                params = {
                                    evid: Ext.getCmp('')
                                };
                                Ext.apply(params, vals);
                                Zenoss.remote.EventsRouter.write_log(
                                    params,
                                    function(provider, response){
                                        Ext.getCmp(
                                            'detail-logform-message').setRawValue('');
                                        Ext.getCmp(config.id).refresh();
                                    });
                            }
                        }]
                    },

                    // Event Log Content
                    {
                        id: 'evdetail_log',
                        cls: 'log-content',
                        hidden: false,
                        autoScroll: true,
                        height: 200
                    }
                    ]
                }

            ];

            this.callParent([config]);
            this.init();
        },
        init: function() {
            var default_renderers = {
                device: function(value, sourceData) {
                    var val = sourceData.device_title;
                    if (sourceData.device_url) {
                        val = Zenoss.render.default_uid_renderer(
                            sourceData.device_url,
                            sourceData.device_title);
                    }
                    return val;
                },
                component: function(value, sourceData) {
                    var val = Ext.htmlEncode(sourceData.component_title);
                    if (sourceData.component_url) {
                        val = Zenoss.render.default_uid_renderer(
                            sourceData.component_url,
                            sourceData.component_title);
                    }
                    return val;
                },
                eventClass: function(value, sourceData) {
                    return  Zenoss.render.EventClass(
                        sourceData.eventClass_url,
                        sourceData.eventClass
                    );
                },
                eventClassMapping: function(value, sourceData) {
                    if (sourceData.eventClassMapping_url) {
                        return Zenoss.render.link(null,
                            sourceData.eventClassMapping_url,
                            sourceData.eventClassMapping
                        );
                    }
                },
                Systems: function(value, sourceData) {
                    return Zenoss.render.LinkFromGridUidGroup(value);
                },


                /* We don't totally control what the source looks like, so escape any HTML*/
                eventState: function(value, sourceData) {
                    return Ext.htmlEncode(value);
                },
                summary: function(value, sourceData) {
                    return Zenoss.render.conditionalEscaping(value);
                },
                dedupid: function(value, sourceData) {
                    return Ext.htmlEncode(value);
                },
                message: function(value, sourceData) {
                    return Zenoss.render.conditionalEscaping(value);
                },
                eventClassKey: function(value, sourceData) {
                    return Ext.htmlEncode(value);
                },
                DeviceGroups: function(value, sourceData) {
                    return Zenoss.render.LinkFromGridUidGroup(value);
                },
                DeviceClass: function(value, sourceData) {
                    return Zenoss.render.LinkFromGridUidGroup(value);
                },
                Location: function(value, sourceData) {
                    return Zenoss.render.LinkFromGridUidGroup(value);
                }

            };
            Ext.apply(this.renderers, default_renderers);

            var eventInfoSection = new Zenoss.eventdetail.Section({
                id: "evdetail_props",
                cls: 'evdetail_props',
                template: Zenoss.eventdetail.detail_header_template,
                keys: ['device', 'component', 'eventClass', 'eventState', 'message']
            });
            this.addSection(eventInfoSection);

            var eventManagementSection = new Zenoss.eventdetail.RepeatedSection({
                id: "event_detail_management_section",
                title: _t("Event Management"),
                template: Zenoss.eventdetail.detail_data_template,
                keys: [ 'agent', 'component', 'dedupid', 'eventClass', 'eventClassKey',
                        'eventClassMapping', 'eventGroup', 'eventKey', 'eventState', 'evid',
                        'facility', 'message', 'ntevid', 'priority', 'severity', 'summary'
                ]
            });
            this.addSection(eventManagementSection);

            var deviceStateSection = new Zenoss.eventdetail.RepeatedSection({
                id: 'event_detail_device_state_section',
                title: _t('Device State'),
                template: Zenoss.eventdetail.detail_data_template,
                keys: [
                    'DeviceClass', 'DeviceGroups', 'DevicePriority',
                    'Location', 'Systems', 'device', 'ipAddress',
                    'monitor', 'prodState'
                ]
            });
            this.addSection(deviceStateSection);

            var eventMetaSection = new Zenoss.eventdetail.RepeatedSection({
                id: 'event_detail_meta_section',
                title: _t('Event Data'),
                template: Zenoss.eventdetail.detail_data_template,
                keys: [
                    'clearid', 'count', 'firstTime', 'lastTime',
                    'ownerid', 'stateChange'
                ]
            });
            this.addSection(eventMetaSection);

            var eventDetailsSection = new Zenoss.eventdetail.DetailsSection({
                id: 'event_detail_details_section',
                title: _t('Event Details'),
                template: Zenoss.eventdetail.detail_data_template
            });
            this.addSection(eventDetailsSection);

            this.checkCustomizations();
            Zenoss.Security.onPermissionsChange(this.updateEventActions, this);
        },

        checkCustomizations: function() {
            // Apply any custom renderers that were registered before we loaded
            // the 'stock' sections and renderers.
            Ext.apply(this.renderers, Zenoss.event_detail_custom_renderers);

            // Add any sections that were registered before we loaded completely.
            Ext.each(Zenoss.event_detail_custom_sections, function(section) {
                if (section.hasOwnProperty('section_class')) {
                    this.addSection(section);
                }
            }, this);

            this.doLayout();
        },

        getBody: function() {
            return Ext.getCmp('event_detail_properties');
        },

        addSection: function(section) {
            if (section.hasOwnProperty('renderers')) {
                Ext.apply(this.renderers, section.renderers);
            }

            this.sections.push(section);

            if (section.hasOwnProperty('title')) {
                var section_title_config = {
                    id: section.id + '_title',
                    html: "<a href='#'>" + section.title + '...' + "</a>",
                    cls: 'show_details',
                    height: 30,
                    toggleFn: Ext.bind(this.toggleSection, this, [section.id])
                };
                this.getBody().add(section_title_config);
            }



            var content_cls = 'full_event_props';
            if (section.hasOwnProperty('cls')) {
                content_cls = section.cls;
            }
            var section_content_config = {
                layout: 'fit',
                id: section.id,
                hidden: false,
                cls: content_cls,
                // dummy html
                html: ''
            };
            this.getBody().add(section_content_config);
        },

        removeSection: function(section_id) {
            var remove_idx;
            Ext.each(this.sections, function(item, idx, sections) {
                if (item.id === section_id) {
                    remove_idx = idx;
                }
            });
            this.sections.splice(remove_idx, 1);

            Ext.getCmp(section_id).destroy();
            Ext.getCmp(section_id+'_title').destroy();
        },

        hideSection: function(section_id) {
            Ext.getCmp(section_id).hide();
        },

        showSection: function(section_id) {
            Ext.getCmp(section_id).show();
        },

        toggleSection: function(section_id) {
            var state = Ext.state.Manager.get("evDetailSectionsState", {});
            var cmp = Ext.getCmp(section_id), el = cmp.getEl();
            // workaround IE not hiding/showing sections by explicitly setting the style on the dom nodes
            if (el.dom.style.display === "none") {
                el.dom.style.display = "block";
                state[section_id] = true;
            }
            else {
                el.dom.style.display = "none";
                state[section_id] = false;
            }
            Ext.state.Manager.set("evDetailSectionsState", state);
            this.getBody().doLayout();
        },

        findSection: function(section_id) {
            var section;
            Ext.each(this.sections, function(item) {
                if (item.id === section_id) {
                    section = item;
                }
            });
            return section;
        },

        /**
         * This method will iterate over every property of the raw event data
         * and call extractData for that key.
         *
         * @param eventData The raw event data.
         */
        renderData: function(eventData) {
            var renderedData = {};
            Ext.iterate(eventData, function(key) {
                if (key === 'details') {
                    var detailsData = [];
                    Ext.each(eventData[key], function(item) {
                        var val = this.extractData(item.key, item.value, eventData);
                        detailsData.push({
                            key: item.key,
                            value: val
                        });
                    }, this);
                    renderedData[key] = detailsData;
                }
                else {
                    renderedData[key] = this.extractData(key, eventData[key], eventData);
                }
            }, this);

            return renderedData;
        },

        /**
         * Extract rendered data from raw event data. Handles the case where a
         * key does not have a specified renderer as well as the case where
         * the value is null or undefined.
         *
         * @param key The key to use for looking up a renderer.
         * @param value The value to be rendered.
         * @param sourceData All event data.
         */
        extractData: function(key, value, sourceData) {
            var data;
            if (this.renderers.hasOwnProperty(key)) {
                data = this.renderers[key](value, sourceData);
            }
            else if (value || typeof(value) == 'number') {
                data = value;
            }
            else {
                data = '';
            }
            return data;
        },

        setSummary: function(summary){
            var panel = Ext.getCmp('evdetail-summary');
            if (panel && panel.el){
                panel.update(summary);
            }
        },

        setSeverityIcon: function(severity){
            var panel = Ext.getCmp('severity-icon');
            this.clearSeverityIcon();
            panel.addCls(severity);
        },

        clearSeverityIcon: function() {
            var panel = Ext.getCmp('severity-icon');
            Ext.each(Zenoss.env.SEVERITIES, function(sev) {
                sev = sev[1];
                panel.removeCls(sev.toLowerCase());
            });
        },

        update: function(eventData) {
            this.eventData = eventData;
            // render event data
            eventData.firstTime = Zenoss.date.renderWithTimeZone(eventData.firstTime);
            eventData.lastTime = Zenoss.date.renderWithTimeZone(eventData.lastTime);
            eventData.stateChange = Zenoss.date.renderWithTimeZone(eventData.stateChange);
            // Convert log timestamps to localized dates
            eventData.log = eventData.log.map(
                function(item) {
                    item[1] = Zenoss.date.renderWithTimeZone(item[1]/1000);
                    return item;
                }
            )

            var renderedData = this.renderData(eventData);

            this.setSummary(renderedData.summary);
            this.setSeverityIcon(Zenoss.util.convertSeverity(eventData.severity));

            // Save the evid for popping out. This is also used when submitting
            // the log form.
            Ext.getCmp('detail-logform-evid').setValue(eventData.evid);

            var state = Ext.state.Manager.get("evDetailSectionsState", {});
            // Update the data sections
            Ext.each(this.sections, function(section) {
                var cmp = Ext.getCmp(section.id),
                    html, el = cmp.getEl();
                html = section.generateHtml(renderedData, eventData);
                cmp.update(html);
                var section_state = (section.id in state) ? state[section.id] : false;
                if (el) {
                   if (section_state) {
                       el.dom.style.display = "block";
                   } else {
                       el.dom.style.display = "none";
                   }
               }
            }, this);

            // Update Logs
            var logTemplate = new Ext.XTemplate(Zenoss.eventdetail.detail_log_template),
                logHtml;
            logHtml = logTemplate.apply(eventData);
            Ext.getCmp('evdetail_log').update(logHtml);
            this.doLayout();
            if (this.showActions) {
                if (!_has_global_roles()) {
                    var deviceClass = eventData.DeviceClass[0]['uid'],
                    device = eventData.device,
                    context = deviceClass+'/devices/'+device;
                    Zenoss.Security.setContext(context);
                } else { 
                    this.updateEventActions();
                }
            }
        },
        updateEventActions: function() {
            var eventData = this.eventData;
            if (!this.showActions) return;
            Zenoss.EventActionManager.configure({
                onFinishAction: Ext.bind(this.refresh, this),

                findParams: function() {
                    var params = {
                            evids: [eventData.evid]
                        };
                    return params;
                }
            });
            var actiontoolbar = Ext.getCmp('actiontoolbar'),
                ackButton = actiontoolbar.query("button[iconCls='acknowledge']")[0],
                closeButton = actiontoolbar.query("button[iconCls='close']")[0],
                unAckButton = actiontoolbar.query("button[iconCls='unacknowledge']")[0],
                reopenButton = actiontoolbar.query("button[iconCls='reopen']")[0],
                state = eventData.eventState.toLowerCase();

            // disable all buttons
            ackButton.disable();
            closeButton.disable();
            unAckButton.disable();
            reopenButton.disable();

            // enable based on state (i.e. Which state can I go to from my current?)
            if (Zenoss.Security.hasPermission('Manage Events')) {
                if (state === "new") {
                    ackButton.enable();
                    closeButton.enable();
                } else if (state === "acknowledged") {
                    unAckButton.enable();
                    closeButton.enable();
                } else if ((state === "closed") || (state === "cleared"))  {
                    reopenButton.enable();
                }
            }

        },
        bind: function() {
            var close_btn = Ext.getCmp('evdetail_tool_close').getEl(),
                pop = Ext.getCmp('evdetail-popout').getEl();

            Ext.each(this.sections, function(section) {
                var cmp = Ext.getCmp(section.id+'_title');

                // A section may opt to not have a title, in which case
                // we can't provide auto-collapsing.
                if (cmp) {
                    // We remove this first because we don't want to keep
                    // adding listeners for the same event each time a new
                    // event is loaded.
                    cmp.getEl().un('click', cmp.toggleFn);
                    cmp.getEl().on('click', cmp.toggleFn);
                }

            }, this);

            if (close_btn) {
                // The 'onDetailHide' property is set by the config
                // during instantiation.
                close_btn.un('click', this.onDetailHide);
                close_btn.on('click', this.onDetailHide);
            }

            if (pop) {
                pop.un('click', this.popout, this);
                pop.on('click', this.popout, this);
            }
        },

        popout: function(){
            var evid = Ext.getCmp('detail-logform-evid').getValue(),
                url = this.isHistory ? 'viewHistoryDetail' : 'viewDetail';
            url = url +'?evid='+evid;
            window.open(url, evid.replace(/-/g,'_'),
                        "status=1,width=600,height=500,resizable=1,name=EventDetails");
        },
        wipe: function() {
            // hook to perform clean up actions when the panel is closed
        },
        load: function(event_id) {
            if (event_id !== this.event_id) {
                this.event_id = event_id;
                this.refresh();
            }
        },
        refresh: function() {
            Zenoss.remote.EventsRouter.detail({
                evid: this.event_id
            }, function(result) {
                var event = result.event[0];
                this.update(event);
                this.bind();
                this.show();
            }, this);
        }
    });
});
