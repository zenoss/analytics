/* global _managed_objects:true */
/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


Ext.ns('Zenoss.ui.EvConsole');

Ext.onReady(function(){
var stateProvider = Ext.state.Manager.getProvider();
// wait until state is ready;
stateProvider.onStateReady(function() {
    // Get references to the panels
    var detail_panel = Ext.getCmp('detail_panel');
    var master_panel = Ext.getCmp('master_panel');
    detail_panel.collapse();
    master_panel.layout = 'border';

    // Make this instance of the detail panel use a unique state ID so
    // it doesn't interfere with the state of other instances of this panel.
    detail_panel.stateId = 'Zenoss.ui.EvConsole.detail_panel';

    // Get the container surrounding master/detail, for adding the toolbar
    var container = Ext.getCmp('center_panel_container');

    // Add a CSS class to scope some styles that affect other parts of the UI
    container.on('render', function(){container.el.addClass('zenui3');});
    // update the document title based on the number of open events (includes filters)
    var originalTitle = document.title;
    function updateTitle(store) {
        if (store.totalCount) {
            document.title = Ext.String.format("({0}) {1}", store.totalCount, originalTitle);
        } else {
            document.title = originalTitle;
        }
    }

    // Selection model
    var console_selection_model = Ext.create('Zenoss.EventPanelSelectionModel', {
        gridId: 'events_grid'
    });

    var createEventConsoleGrid = function() {
        var console_store = Ext.create('Zenoss.events.Store', {});
        if (!Zenoss.settings.enableInfiniteGridForEvents) {
            console_store.buffered = false;
        }

        console_store.on('afterguaranteedrange', updateTitle);
        console_store.on('load', updateTitle);

        var master_panel = Ext.getCmp('master_panel');
        var grid = Ext.create('Zenoss.events.Grid', {
            region: 'center',
            tbar: Ext.create('Zenoss.EventConsoleTBar', {
                region: 'north',
                gridId: 'events_grid',
                hideDisplayCombo: true,
                newwindowBtn: false
            }),
            appendGlob: true,
            defaultFilters: {
                severity: [Zenoss.SEVERITY_CRITICAL, Zenoss.SEVERITY_ERROR, Zenoss.SEVERITY_WARNING, Zenoss.SEVERITY_INFO],
                eventState: [Zenoss.STATUS_NEW, Zenoss.STATUS_ACKNOWLEDGED],
                // _managed_objects is a global function sent from the server, see ZenUI3/security/security.py
                tags: _managed_objects()
            },
            id: 'events_grid',
            stateId: Zenoss.env.EVENTSGRID_STATEID,
            enableDragDrop: false,
            stateful: true,
            rowSelectorDepth: 5,
            store: console_store, // defined above
            // Zenoss.env.COLUMN_DEFINITIONS comes from the server, and depends on
            // the resultFields associated with the context.
            columns: Zenoss.env.getColumnDefinitionsToRender(Zenoss.env.EVENTSGRID_STATEID),
            enableColumnHide: false,
            displayTotal: false,
            // Map some other keys
            keys: [{
                // Enter to pop open the detail panel
                key: Ext.EventObject.ENTER,
                fn: toggleEventDetailContent
            }],
            selModel: console_selection_model, // defined above
            enableTextSelection: true
        });
        console_selection_model.grid = grid;

        // Add it to the layout

        master_panel.add(grid);

        // stats is not used -- REMOVE??
        if (Zenoss.settings.showPageStatistics){
            // this will render the page loading time button
            Ext.create('Zenoss.stats.Events');
        }

        Zenoss.util.callWhenReady('events_grid', function(){
            Ext.getCmp('events_grid').uid = Zenoss.env.PARENT_CONTEXT;
        });
        var pageParameters = Ext.urlDecode(window.location.search.substring(1));
        if (pageParameters.filter === "default") {
            // reset eventconsole filters to the default
            grid.resetGrid();
        }

        grid.on("itemdblclick", toggleEventDetailContent);

        grid.on('recreateGrid', function (grid) {
            var container_panel = Ext.getCmp('master_panel');
            container_panel.remove(grid.id, true);
            var new_grid = createEventConsoleGrid();
            new_grid.on('afterrender', master_panel.fireEvent('events_grid_reloaded'));
        });

        hideEventDetail();

        return grid;
    };


    /*
     * THE GRID ITSELF!
     */
    var grid = createEventConsoleGrid();

    /*
     * DETAIL PANEL STUFF
     */
    // Pop open the event detail, depending on the number of rows selected
    function toggleEventDetailContent(){
        var selections = console_selection_model.getSelection();
        if (selections.length) {
            showEventDetail(selections[0]);
        } else {
            wipeEventDetail();
        }
    }

    // Pop open the event detail pane and populate it with the appropriate data
    // and switch triggers (single select repopulates detail, esc to close)
    function showEventDetail(r) {
        Ext.getCmp('dpanelcontainer').load(r.data.evid);
        var grid = Ext.getCmp('events_grid');
        grid.un('itemdblclick', toggleEventDetailContent);

        detail_panel.expand();
        detail_panel.show();
        esckeymap.enable();
    }

    // Wipe event detail values
    function wipeEventDetail() {
        Ext.getCmp('dpanelcontainer').wipe();
    }

    // Collapse the event detail pane and switch triggers (double select
    // repopulates detail, esc no longer closes)
    function hideEventDetail() {
        detail_panel.collapse();
        detail_panel.hide();
    }

    function eventDetailCollapsed(){
        var grid = Ext.getCmp('events_grid');
        wipeEventDetail();
        grid.on('itemdblclick', toggleEventDetailContent);
        esckeymap.disable();
    }
    // Finally, add the detail panel (have to do it after function defs to hook
    // up the hide callback)
    detail_panel.add({
        xtype:'detailpanel',
        id: 'dpanelcontainer',
        onDetailHide: hideEventDetail
    });
    // Make the detail panel collapsible
    detail_panel.animCollapse = false;

    // render so that the detail panel has html elements


    detail_panel.on('collapse', function() {
        eventDetailCollapsed();
    });


    // Detail pane should pop open when double-click on event
    grid.on("itemdblclick", toggleEventDetailContent);
    console_selection_model.on("select", function(){
        if(!detail_panel.collapsed){
            toggleEventDetailContent();
        }
    });

    // When multiple events are selected, detail pane should blank
    console_selection_model.on('rangeselect', wipeEventDetail);

    // Key mapping for ESC to close detail pane
    var esckeymap = new Ext.KeyMap(document, {
        key: Ext.EventObject.ESC,
        fn: hideEventDetail
    });
    // Start disabled since pane is collapsed
    esckeymap.disable();


    // if there is a state apply it now
    if (window.location.search) {
        grid.restoreURLState();
    }

    // ZEN-26417
    grid.on("selectionchange", updateEventContext);
    function updateEventContext() {
        var selectionModel = this.getSelectionModel()
        var selection = selectionModel.getSelection()
        selection.forEach(function(sel) {
            Zenoss.Security.setContext(sel.data.device.uid)
            });
    }

    // ZEN-28542: memory leak, unclear if it's from our extensions to
    // Ext or Ext itself. Set up activity listeners and reload the page
    // after 1 hour of inactivity.
    var timeoutID;
    var body = Ext.getBody();
    body.on('mousemove', resetInactive);
    body.on('keydown', resetInactive);

    function resetInactive() {
        clearTimeout(timeoutID);
        startInactive();
    }

    function startInactive() {
        timeoutID = setTimeout(doReload, 1000 * 60 * 60);
    }

    function doReload() {
        grid.destroy();
        window.location.reload();
    }

    startInactive();
}); // stateProvider.onStateReady
});
