Ext.onReady(function () {

// If there is no searchbox-container, then we will not attempt to render
// the searchbox.  No context windows such as the event detail popout have
// no searchbox-container

    if (Ext.get('searchbox-container') === null) {
        return;
    } else {
        /**
         * So we do indeed want the search.
         * But we almost want two different searches:
         * 1.  Free form text entry search for anything out there.
         * 2.  Drop down listing of saved searches.
         *
         * In the ExtJS land, both of these would be served by
         * a ComboBox.  So we would kinda want two combo boxes
         * to be melded into one.  To accomplish this, we will
         * have one combo box and just swap out the Store and the display
         * for the picker  when the user does stuff.
         */

        var router = Zenoss.remote.SearchRouter;
        var ManageSavedSearchDialog;

        // Create two pickers to be swapped out.  (A picker is the drop down box)
        var savedSearchPicker;
        var freeSearchPicker;
        // Create two variables to hold the store ids
        var storedSearchesDataStoreID = "storedSearchesDataStoreID";
        var  freeSearchDataStoreID = "freeSearchDataStoreID";

        // Custom rendering Template for the Free Search Results
        // this defines the way the picker (drop down box) will look
        var resultTpl = new Ext.XTemplate(
            '<tpl for=".">',
            '<table class="search-result"><tr class="x-combo-list-item">',
            '<th><tpl if="values.category && (xindex == 1 || parent[xindex - 2].category != values.category)"',
            '>{category}</tpl></th>',
            '<td colspan="2" class="x-boundlist-item">{content}</td>',
            '</tpl>');

        // create an input field that everything hangs off of.
        var searchfield = new Zenoss.SearchField({
            black:true,
            id:'searchbox-query',
            fieldClass:'searchbox-query',
            name:'query',
            width:150,
            renderTo:'searchbox-container'
        });
        /**
         * @class Zenoss.search.FreeSearchModel
         * @extends Ext.data.Model
         * Field definitions for free search
         **/
        Ext.define('Zenoss.search.FreeSearchModel', {
            extend:'Ext.data.Model',
            idProperty:'url',
            fields:[
                {name:'url'},
                {name:'content'},
                {name:'popout'},
                {name:'category'}
            ]
        });

        // Create the Store for the Free Search
        var freeSearchDataStore = Ext.create('Zenoss.NonPaginatedStore', {
            storeId:freeSearchDataStoreID,
            directFn:Zenoss.remote.SearchRouter.getLiveResults,
            model: 'Zenoss.search.FreeSearchModel',
            root:'results'
        });

        /**
         * @class Zenoss.search.SavedSearchModel
         * @extends Ext.data.Model
         * Field definitions for saved search
         **/
        Ext.define('Zenoss.search.SavedSearchModel', {
            extend:'Ext.data.Model',
            idProperty:'uid',
            fields:[
                {name:'id'},
                {name:'name'},
                {name:'uid'},
                {name:'createor'},
                {name:'query'}
            ]
        });

        /**
         * @class Zenoss.search.SavedSearchStore
         * @extend Zenoss.NonPaginatedStore
         * Direct store for loading saved searches
         */
        Ext.define("Zenoss.search.SavedSearchStore", {
            extend:"Zenoss.NonPaginatedStore",
            constructor:function (config) {
                config = config || {};
                Ext.applyIf(config, {
                    model:'Zenoss.search.SavedSearchModel',
                    directFn:Zenoss.remote.SearchRouter.getAllSavedSearches,
                    root:'data'
                });
                this.callParent(arguments);
            }
        });

        // Create the Store for the saved searches
        var storedSearchesDataStore = Ext.create('Zenoss.search.SavedSearchStore', {
            storeId:storedSearchesDataStoreID,
            listeners:{
                beforeload:function () {
                    this.setBaseParam('addManageSavedSearch', true);
                },
                scope:this.savedSearchCombo
            }
        });

        function getSearchApplyTo(targetEl) {
            var target = Ext.get(targetEl);
            if (target) {
                var parent = target.parent();
                target.remove();
                return parent;
            }
            return targetEl;
        }

        // Create a searchable Combo Box and apply it to the Search Field that we defined above.
        var theSearchBox = new Ext.form.ComboBox({
            store:freeSearchDataStore,
            typeAhead:false,
            triggerAction:'all',
            width:148,
            maxWidth:375,
            pageSize:0,
            // delay all requests by one second
            delayQuery:1000,
            minChars:3,
            hideTrigger:false,
            renderTo: getSearchApplyTo(searchfield.getEl()),
            queryMode:'remote',
            listConfig: {
                cls:'search-result',
                loadingText:_t('Searching..'),
                resizable:true
            },
            matchFieldWidth:false,
            displayField:'name',
            valueField:'url',
            listConfig:{
                emptyText:_t('No Results'),
                tpl:resultTpl,
                minWidth:375
            },

            /**
             * Override the get picker method to switch pickers based on the store.
             * @return {Ext.Component} The picker component
             */
            getPicker: function() {
                var me = this;
                // Which picker should we return????
                if(this.store.storeId == storedSearchesDataStoreID ){
                    // We want the Saved Searches.
                    // flip the template for the drop down box
                    this.listConfig.tpl =  null;
                    // return the correct picker, create it first if you have to
                    return savedSearchPicker || (savedSearchPicker = me.createPicker());
                }
                else{
                    // We want the Free Text Entry Search
                    // flip the template for the drop down box
                    this.listConfig.tpl =  resultTpl;
                    // return the correct picker, create it first if you have to
                    return freeSearchPicker || (freeSearchPicker = me.createPicker());
                }
            },

            /**
             * Override the align picker method to make sure that
             * the width of the picker is 375, which is different than the width of the input
             **/
            alignPicker:function () {
                var me = this;
                var picker;
                if (me.isExpanded) {
                    picker = me.getPicker();
                    // Auto the height (it will be constrained by min and max width) unless there are no records to display.
                    picker.setSize(375, picker.store && picker.store.getCount() ? null : 20);
                    if (picker.isFloating()) {
                        me.doAlign();
                    }
                }
            },
            // Override the on click event to switch the store over to the Saved Searches
            onTriggerClick:function () {
                if (theSearchBox.store.storeId != storedSearchesDataStoreID) {
                    // load the data into it.
                    storedSearchesDataStore.load();
                    theSearchBox.store = storedSearchesDataStore;
                }
                if (!this.isExpanded) {
                    this.expand();
                }
            },

            listeners:{
                // Fire this off when they just select away and the drop down box is closed
                // we want to make sure that the store is returned to the free search
                collapse:function(){
                    theSearchBox.store = freeSearchDataStore;
                    // sometimes EXT forgets to actually hide the pickers
                    if(savedSearchPicker ){savedSearchPicker.hide();}
                    if(freeSearchPicker){ freeSearchPicker.hide();}

                },
                // Fire this off when a selection is made
                select:function (box, records) {
                    // Which selection box was active at the time????
                    if (theSearchBox.store.storeId != storedSearchesDataStoreID) {
                        // We are looking at a free search.
                        var record = records[0];
                        if (record.get('url') !== '') {
                            // IE only supports these window names: _blank _media _parent _search _self _top
                            var windowname = Ext.isIE ? '_blank' : record.data.url;
                            if (record.get('popout')) {
                                window.open(Ext.String.format('{0}', record.data.url),
                                    windowname, 'status=1,width=600,height=500');
                            }
                            else {
                                window.location =
                                    Ext.String.format('{0}', record.data.url);
                            }
                        }
                    } else {
                        // we are looking at a saved search
                        var record = records[0];
                        // magic string that means the user wishes to manage
                        // their saved searches
                        if (record.get("id") == 'manage_saved_search') {
                            var decodedUrl = Ext.urlDecode(location.search.substring(1, location.search.length)),
                                searchId = decodedUrl.search,
                                win = Ext.create('Zenoss.search.ManageSavedSearchDialog', {
                                    xtype:'managesavedsearchdialog',
                                    id:'manageSavedSearchesDialog',
                                    searchId:searchId
                                });
                            win.show();
                            // Make sure that we reset the store to be saved search
                            theSearchBox.store = freeSearchDataStore;
                            // and clear out the typed in search box
                            theSearchBox.clearValue();

                        } else {
                            // otherwise go to the selected search results page
                            window.location = Ext.String.format('/zport/dmd/search?search={0}', record.get("id"));
                        }
                    }
                }
            }
        });

        // Now set the combo box to the env
        Zenoss.env.search = theSearchBox;

        // =================================================================================
        // Managed Search floating dialog box.
        Ext.define("Zenoss.search.ManageSavedSearchDialog", {
            extend:"Ext.Window",
            alias:['managesavedsearchdialog'],
            constructor:function (config) {
                config = config || {};
                var searchId = config.searchId,
                    me = this;
                Ext.apply(config, {
                    title:_t('Manage Saved Searches'),
                    layout: 'anchor',
                    stateful: false,
                    autoHeight:true,
                    width:460,
                    modal:true,
                    items:[{
                            ref:'savedSearchGrid',
                            xtype:'grid',
                            autoScroll:true,
                            border:false,
                            autoHeight:true,
                            sortableColumns:false,
                            enableColumnHide:false,
                            viewConfig: {
                                striperows: true,
                                style:{cursor: 'pointer'},
                                listeners: {
                                    itemdblclick: function(gridview,rowrecord,rowhtml,rowindex,e) {
                                        window.location = "/zport/dmd/search?search="+rowrecord.data.name;
                                    }
                                }
                            },
                            dockedItems: [{
                                xtype: 'toolbar',
                                dock: 'top',
                                height:30,
                                items: [{
                                        xtype:'button',
                                        ref:'../deleteButton',
                                        iconCls:'delete',
                                        tooltip:_t('Delete the selected saved search'),
                                        handler:function (button, e) {
                                            var grid = button.refOwner,
                                                selectedRow = grid.getSelectionModel().getSelected(),
                                                params = {
                                                    searchName:selectedRow.data.name
                                                };
                                            router.removeSavedSearch(params, Ext.bind(me.reloadGrid, me));
                                            if(selectedRow.data.name == searchId) window.location = "/zport/dmd/search";
                                    }
                                }]
                            }],
                            selModel:new Zenoss.SingleRowSelectionModel({
                                singleSelect:true
                            }),
                            columns:[
                                {dataIndex:'name', header:_t('Name'), width:225},
                                {dataIndex:'query', header:_t('Query'), width:225}
                            ],
                            store:Ext.create('Zenoss.search.SavedSearchStore', {
                                autoLoad:true
                            })
                        }
                    ],

                    buttons:[
                        {
                            xtype:'DialogButton',
                            text:_t('Close'),
                            handler:function () {
                                me.hide();
                                me.destroy();
                            }
                        }
                    ]
                });
                this.callParent(arguments);
            },
            reloadGrid:function () {
                this.savedSearchGrid.getStore().load();
            }
        });

    }
});
