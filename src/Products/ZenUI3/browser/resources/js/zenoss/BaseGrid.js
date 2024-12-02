(function () {


    /**
     * Base class for non paginated and paginated stores.
     * @class Zenoss.Store
     */
    Ext.define('Zenoss.Store', {
        extend: 'Ext.data.Store',
        constructor: function (config) {
            this.callParent([config]);
            this.addEvents(
                /**
                 * @event afterguaranteedrange
                 * This fires after the callback from the guaranteerange method.
                 * @param {Zenoss.Store} this
                 */
                'afterguaranteedrange'
            );
        },
        setBaseParam: function (key, value) {
            this.proxy.extraParams[key] = value;
        },
        setParamsParam: function (key, value) {
            if (!this.proxy.extraParams.params) {
                this.proxy.extraParams.params = {};
            }
            this.proxy.extraParams.params[key] = value;
        },
        onGuaranteedRange: function (range, start, end, options) {
            this.callParent(arguments);
            this.fireEvent('afterguaranteedrange', this);
        }
    });



    /**
     * Base Configuration for direct stores
     * @class Zenoss.DirectStore
     */
    Ext.define('Zenoss.DirectStore', {
        extend: 'Zenoss.Store',
        alias: 'store.zendirectstore',
        constructor: function (config) {
            config = config || {};
            var sorters;
            if (config.initialSortColumn) {
                sorters = [
                    {
                        property: config.initialSortColumn,
                        direction: config.initialSortDirection || 'ASC'
                    }
                ];
            }
            Ext.applyIf(config, {
                remoteSort: true,
                pageSize: config.pageSize || 50,
                buffered: true,
                sorters: sorters,
                proxy: {
                    type: 'direct',
                    simpleSortMode: true,
                    directFn: config.directFn,
                    extraParams: config.baseParams || {},
                    reader: {
                        root: config.root || 'data',
                        totalProperty: config.totalProperty || 'totalCount'
                    }
                }
            });
            this.callParent(arguments);
        }
    });

    /**
     * @class Zenoss.NonPaginatedStore
     * @extends Ext.data.Store
     * Direct Store for when you want all of the results on a single
     * grid.
     * Use this if the expected number of rows is always going to be less than
     * a hundred or so since every request will load the entire grid without pagination.
     **/
    Ext.define('Zenoss.NonPaginatedStore', {
        extend: 'Zenoss.Store',
        alias: ['store.directcombo'],
        constructor: function (config) {
            config = config || {};
            Ext.applyIf(config, {
                remoteSort: false,
                buffered: false,
                proxy: {
                    type: 'direct',
                    limitParam: undefined,
                    startParam: undefined,
                    pageParam: undefined,
                    sortParam: undefined,
                    extraParams: config.baseParams || {},
                    directFn: config.directFn,
                    reader: {
                        type: 'json',
                        root: config.root || 'data'
                    }
                }
            });
            if (config.initialSortColumn || config.initialSortDirection) {
                Ext.applyIf(config, {
                    sorters: [{
                        property: config.initialSortColumn || undefined,
                        direction: config.initialSortDirection || 'ASC'
                    }
                    ]
                });
            }
            this.callParent(arguments);
        },
        setContext: function (context) {
            if (this.proxy.extraParams) {
                this.proxy.extraParams.uid = context;
            }
            this.load();
        }
    });

    Ext.define('Ext.ux.grid.FilterRow', {
        extend: 'Ext.util.Observable',

        init: function (grid) {
            this.grid = grid;

            // when column width programmatically changed
            grid.headerCt.on('columnresize', this.resizeFilterField, this);
            grid.headerCt.on('columnshow', this.resetFilterRow, this);
            grid.headerCt.on('columnhide', this.resetFilterRow, this);

            grid.headerCt.on('columnmove', this.resetFilterRow, this);
            grid.on('columnmove', function (col, moved, movedIndex) {
                this.gridColumnMoveWithFilter(col, moved, movedIndex);
            }, this);
            this.view = this.grid.getView();
            this.view.on('bodyscroll', this.onViewScroll, this);
        },
        /**
         * Make sure that when we scroll to the left on the grid that we adjust the
         * filters to scroll as well.
         **/
        onViewScroll: function (e) {
            if (e) {
                var viewScrollLeft = this.view.el.dom.scrollLeft,
                    // need to scroll the inner container for the changes to be noticed
                    innerEl = this.dockedFilter.el.dom.childNodes[0],
                    scrollLeft = innerEl.scrollLeft;
                if (viewScrollLeft !== scrollLeft) {
                    innerEl.scrollLeft = viewScrollLeft;
                }
            }
        },
        gridColumnMoveWithFilter: function (column, moved, movedIndex) {
            var grid = this.grid;
            var me = this;
            var filterBar = me.dockedFilter;
            if (filterBar) {
                me.eachColumn(function (col) {
                    if (Ext.isDefined(col.filterField)) {
                        col.filterField.destroy();
                        delete col.filterField;
                    }
                });

                // remove all the filters
                filterBar.removeAll(true);

                Ext.each(grid.getDockedItems(), function (item) {
                    if (item.id === grid.id + 'docked-filter') {
                        grid.removeDocked(item, true);
                    }
                });

                me.applyTemplate();
                // force the columns to relayout themselves (work around
                // a bug in Chrome where this would be a blank row otherwise)
                me.eachColumn(function (col) {
                    if (col.isVisible() && col.getEl()) {
                        col.setWidth(col.getWidth() + 1);
                        col.setWidth(col.getWidth() - 1);

                    }
                });
                this.view.el.dom.scrollLeft -= 1;
            }

        },
        applyTemplate: function () {
            var searchItems = [];
            // set the default params
            this.eachColumn(function (col) {
                // this is the value we are going to send to the server
                // for this filter
                if (!col.filterKey) {
                    col.filterKey = col.id;
                    if (!col.filterKey || col.filterKey.startswith("gridcolumn")) {
                        col.filterKey = col.dataIndex;
                    }
                }

                var filterDivId = this.getFilterDivId(col.filterKey);

                if (!col.filterField) {
                    if (Ext.isDefined(col.filter) && col.filter === false) {
                        col.filter = {};
                        col.filter.xtype = 'hidden';
                    }
                    if (col.nofilter || Ext.isDefined(col.isCheckerHd)) {
                        col.filter = {};
                    } else if (!col.filter) {
                        col.filter = {};
                        col.filter.xtype = 'textfield';
                    }

                    col.filter = Ext.apply({
                        id: filterDivId,
                        hidden: col.isHidden(),
                        xtype: 'component',
                        baseCls: 'x-grid-filter',
                        width: col.width - 2,
                        enableKeyEvents: true,
                        style: {
                            margin: '1px 1px 1px 1px'
                        },
                        hideLabel: true,
                        value: this.defaultFilters[col.filterKey]
                    }, col.filter);
                    col.filterField = Ext.ComponentManager.create(col.filter);

                } else {
                    if (col.hidden !== col.filterField.hidden) {
                        col.filterField.setVisible(!col.hidden);
                    }
                }
                if (Zenoss.SELENIUM) {
                    col.filterField.on('afterrender', function (e) {
                        if (Ext.getCmp(e.id).inputEl) {
                            /*  add an id to the input element of filters if
                                it has one. If not, don't worry about it.
                                example: events_grid-filter-devices-input
                                -- for selenium automation --
                            */
                            var filterInput = Ext.getCmp(e.id).inputEl;
                            filterInput.dom.id = e.id + "-input";
                        }
                    }, this);
                }

                if (Zenoss.settings.enableLiveSearch) {
                    col.filterField.on('change', this.onChange, this);
                }
                col.filterField.on('keydown', this.onKeyDown, this);
                col.filterField.on('validitychange', this.onInvalidFilter, this);
                col.filterField.on('focus', this.onFocus, this);

                searchItems.push(col.filterField);
            });
            // make sure we send our default filters on the initial load
            if (!Ext.isEmpty(this.defaultFilters)) {
                if (!this.grid.store.proxy.extraParams) {
                    this.grid.store.proxy.extraParams = {};
                }
                Ext.applyIf(this.grid.store.proxy.extraParams.params, this.getSearchValues());
            }

            if (searchItems.length > 0) {
                this.grid.addDocked(this.dockedFilter = Ext.create('Ext.container.Container', {
                    id: this.grid.id + 'docked-filter',
                    weight: 100,
                    dock: 'top',
                    border: false,
                    baseCls: Ext.baseCSSPrefix + 'grid-header-ct',
                    items: searchItems,
                    layout: {
                        type: 'hbox'
                    }
                }));

            }
            this.grid.on('afterrender', function () {
                /* using storeSearch here to force the filters to acknowledge the fact that there
                   may be new filters since the last time the page was visited. This is questionable
                   and probably should be considered temporary until a better solution to filters
                   can be found
                */
                this.storeSearch();
            }, this, { single: true });
        },
        clearFilters: function () {

            /* when using .reset(), it applies setValue(), which in turn applies the
              previous value. In the case of multiselect, it adds duplicates to the list instead of resetting it.
              Hardwiring a reset for each of the changed multiselections here to disallow dupes and firing the onChange manually.
              This only fires if any of the multiselects have been changed, otherwise it only resets the text fields.
            */
            this.eachColumn(function (col) {
                if (Ext.isDefined(col.filterField)) {
                    if (col.filterField.isXType("multiselectmenu")) {
                        var dirty = false;
                        col.filterField.menu.items.each(function (f) {
                            if (f.checked !== f.initialConfig.checked) {
                                f.setChecked(f.initialConfig.checked);
                                dirty = true;
                            }
                        });
                        if (dirty === true) {
                            this.onChange();
                        }
                    } else {
                        col.filterField.reset();
                    }
                }
            });
        },
        getState: function () {
            return this.getSearchValues();
        },
        applyState: function (state) {
            if (Ext.isEmpty(state)) {
                return;
            }
            if (!this.dockedFilter) {
                this.applyTemplate();
            }
            this.eachColumn(function (col) {
                col.filterField.setVisible(!col.isHidden());
                // do not apply a filter to a hidden column (will be confusing for the user)
                if (!col.isHidden() &&
                    Ext.isDefined(state[col.filterKey]) &&
                    !Ext.isEmpty(state[col.filterKey])) {
                    col.filterField.setValue(state[col.filterKey]);
                }
            });
        },
        onChange: function (field, newValue, oldValue) {
            if (!this.onChangeTask) {
                this.onChangeTask = new Ext.util.DelayedTask(function () {
                    this.storeSearch();
                }, this);
            }

            this.onChangeTask.delay(1000);

        },
        onFocus: function (field) {
            /**
             * When search field is in focus, we check its right x coordinate.
             * If this coordinate is bigger than width of a document,
             * we perform horizontal scroll on delta pixels.
             * delta is a difference between right x
             * coordinate of a search field and a document width.
             */

            var documentWidth = Ext.getBody().getViewSize().width;
            var searchFieldRightXPosition = field.getEl().getX() + field.width;
            var delta = searchFieldRightXPosition - documentWidth;
            var shift = 20;

            if (delta > 0) {
                this.view.el.dom.scrollLeft += delta + shift;
            }
            /**
             * check the case when search field right x coordinate is on the
             * edge or very close (20px) to the right side of the window.
             */
            else if (delta > -shift && delta <= 0) {
                this.view.el.dom.scrollLeft += shift;
            }
        },
        onKeyDown: function (field, e) {
            // if they explicitly pressed enter then search now
            if (e.getKey() === e.ENTER) {
                this.onChange();
            }
        },
        /**
         * Determines if the current set of filters are all valid.
         * If any one filter is invalid the set of filters is invalid
         **/
        isValid: function () {
            var isValid = true;
            this.eachFilterColumn(function (col) {
                if (col.filterField.isValid) {
                    isValid = isValid && col.filterField.isValid();
                }
            }, this);

            return isValid;
        },
        /**
         * Flare the user when we have an invalid filter.
         **/
        onInvalidFilter: function (field, isValid) {
            if (!isValid) {
                var error = field.activeError;
                if (error) {
                    Zenoss.message.error(error);
                }
            }
        },
        getSearchValues: function () {
            var values = {},
                visibleColumns = [],
                globbing = (this.appendGlob && (Ext.isDefined(globbing) ? globbing : true));

            this.eachColumn(function (col) {
                visibleColumns.push(col.id);
                var filter = col.filterField, excludeGlobChars = ['*', '"', '?'], query;
                if (filter && filter.xtype !== 'component') {
                    if (!Ext.isEmpty(filter.getValue())) {
                        query = filter.getValue();
                        if (globbing && filter.xtype === 'textfield' && filter.vtype !== 'numcmp' &&
                            filter.vtype !== 'numrange' && filter.vtype !== 'floatrange' &&
                            Ext.Array.indexOf(excludeGlobChars, query.charAt(query.length - 1)) === -1) {
                            query += '*';
                        }
                        values[col.filterKey] = query;
                    }
                }
            });

            // apply default filters if the column is visible
            // and the filter has not already been set
            for (var key in this.defaultFilters) {
                if (Ext.Array.contains(visibleColumns, key) && !values[key]) {
                    values[key] = this.defaultFilters[key];
                }
            }

            // always add tags if it is not present
            if (!values["tags"]) {
                values["tags"] = this.defaultFilters["tags"];
            }

            return values;
        },

        storeSearch: function () {
            // do not store the filters if they are not valid
            if (!this.isValid()) {
                return;
            }
            var values = this.getSearchValues();
            // ZEN-34076 Convert stateChange to UTC as well
            var timeParams = ["firstTime", "lastTime", "stateChange"];
            var store = this.grid.getStore();

            timeParams.forEach(function (paramKey) {
                var timeParam = values[paramKey];
                if (timeParam && timeParam.dateFrom) {
                    values[paramKey] = moment(timeParam.dateFrom).format("x") + " TO " + moment(timeParam.dateTo).format("x");
                } else {
                    delete values[paramKey];
                }
            });
            if (!store.proxy.extraParams) {
                store.proxy.extraParams = {};
            }

            // this will make sure that all subsequent buffer loads have the parameters
            store.proxy.extraParams.params = values;

            // reset their scrolling when the filters change
            this.grid.scrollToTop();

            // only load the store if a context has been applied
            if (Ext.isDefined(this.grid.getContext()) || store.autoLoad) {
                // ZEN-29746 (ZEN-28768):
                // If the store has pageMap property then we have to clean it,
                // otherwise not filtered data will appear on the page
                if (store.pageMap) {
                    store.pageMap.clear();
                }

                this.grid.getStore().load({
                    callback: function () {
                        this.grid.fireEvent('filterschanged', this.grid, values);
                    },
                    scope: this
                });
            }

            // save the state
            this.grid.saveState();
        },

        resetFilterRow: function () {
            this.eachColumn(function (col) {
                if (!col.filterField) {
                    return;
                }
                col.filterField.setVisible(!col.isHidden());
            });

            if (!this.dockedFilter) {
                this.applyTemplate();
            }
        },

        resizeFilterField: function (headerCt, column, newColumnWidth) {
            var editor;
            if (!column.filterField) {
                //This is because of the reconfigure
                this.resetFilterRow();
                editor = this.grid.headerCt.items.findBy(
                    function (item) {
                        return item.dataIndex === column.dataIndex;
                    }).filterField;
            } else {
                editor = column.filterField;
            }

            if (editor) {
                editor.setWidth(newColumnWidth - 2);
            }
            this.view.el.dom.scrollLeft -= 1;
        },

        scrollFilterField: function (e, target) {
            var width = this.grid.headerCt.el.dom.firstChild.style.width;
            this.dockedFilter.el.dom.firstChild.style.width = width;
            this.dockedFilter.el.dom.scrollLeft = target.scrollLeft;
        },

        // Returns HTML ID of element containing filter div
        getFilterDivId: function (columnId) {
            return this.grid.id + '-filter-' + columnId;
        },

        // Iterates over each column that has filter
        eachFilterColumn: function (func) {
            this.eachColumn(function (col, i) {
                if (col.filterField) {
                    func.call(this, col, i);
                }
            });
        },
        setFilter: function (colId, value) {
            this.eachFilterColumn(function (col) {
                if (col.filterKey === colId) {
                    col.filterField.setValue(value);
                }
            });
        },
        // Iterates over each column in column config array
        eachColumn: function (func) {
            Ext.each(this.grid.columns, func, this);
        }
    });

    /**
     * @class Zenoss.ContextGridPanel
     * @extends Ext.grid.GridPanel
     * Base class for all of our grids that have a context.
     * @constructor
     */
    Ext.define('Zenoss.ContextGridPanel', {
        extend: 'Ext.grid.Panel',
        alias: ['widget.contextgridpanel'],
        selectedNodes: [],
        constructor: function (config) {
            var viewConfig = config.viewConfig || {};

            Zenoss.util.validateConfig(config,
                'store',
                'columns');
            viewConfig = config.viewConfig || {};

            Ext.applyIf(viewConfig, {
                autoScroll: false,
                stripeRows: true,
                loadMask: false,
                preserveScrollOnRefresh: true
            });

            Ext.applyIf(config, {
                scroll: 'both',
                viewConfig: viewConfig
            });
            this.callParent([config]);
            var after_request = function () {
                if (!this._disableSavedSelection) {
                    this.applySavedSelection();
                }
                // In case the new request returns less results that the previous
                // to avoid displaying a page that does not exist
                if (!this.getStore().buffered) {
                    var store = this.getStore();
                    var last_page = Math.floor(store.getTotalCount() / store.pageSize) + 1;
                    if (store.currentPage > last_page) {
                        store.loadPage(last_page);
                    }
                }
            };

            var before_request = function (store, operation) {
                if (!operation) {
                    return true;
                }
                this.start = operation.start;
                this.limit = operation.limit;
                if (!Ext.isDefined(operation.params)) {
                    operation.params = {};
                }
                // once a uid is set always send that uid
                if (this.uid) {
                    operation.params.uid = this.uid;
                }
                this.applyOptions(operation);
                return true;
            };

            if (this.getStore().buffered) {
                this.getStore().on('beforeprefetch', before_request, this);
                this.getStore().on("afterguaranteedrange", after_request, this);
            }
            else {
                this.getStore().on('beforeload', before_request, this);
                this.getStore().on("load", after_request, this);
            }

            this.addEvents(
                /**
                 * @event beforeactivate
                 * Fires when the context of the grid panel changes
                 * @param {Ext.Component} this
                 * @param {String} contextId
                 */
                'contextchange'
            );
        },
        saveSelection: function () {
            this.selectedNodes = this.getSelectionModel().getSelection();
        },
        disableSavedSelection: function (bool) {
            this._disableSavedSelection = bool;
        },
        applySavedSelection: function () {
            var curStore = this.getStore(),
                selModel = this.getSelectionModel(),
                i, node, rec,
                items = [];
            for (i = 0; i < this.selectedNodes.length; i++) {
                node = this.selectedNodes[i];
                // idProperty is usually UID or EVID in the case of events, but it has to uniquely identify the record
                rec = curStore.findRecord(node.idProperty, node.get(node.idProperty));
                if (rec) {
                    items.push(rec);
                }
            }

            if (items.length > 0) {
                this.suspendEvents();
                this.getSelectionModel().select(items, false, true);
                this.resumeEvents();
                selModel.fireEvent('selectionchange', selModel, selModel.getSelection());
                this.selectedNodes = [];
            }
        },
        clearSavedSelections: function () {
            this.selectedNodes = [];
        },
        applyOptions: function (options) {
            // Do nothing in the base implementation
        },
        /**
         * This will add a parameter to be sent
         * back to the server on every request for this store.
         **/
        setStoreParameter: function (name, value) {
            var store = this.getStore();
            if (!store.proxy.extraParams) {
                store.proxy.extraParams = {};
            }
            store.proxy.extraParams[name] = value;
        },
        setContext: function (uid) {
            this.uid = uid;
            this.setStoreParameter('uid', uid);
            this.fireEvent('contextchange', this, uid);
            this.getStore().load();
        },
        getContext: function () {
            return this.uid;
        },
        refresh: function () {
            // only refresh if we have a context set
            if (!this.getContext()) {
                return;
            }
            this.saveSelection();
            this.getStore().load();
        }
    });


    /**
     * @class Zenoss.BaseGridPanel
     * @extends Zenoss.ContextGridPanel
     * Base class for all of our Live Grids.
     * @constructor
     */
    Ext.define('Zenoss.BaseGridPanel', {
        extend: 'Zenoss.ContextGridPanel',
        alias: ['widget.basegridpanel'],
        constructor: function (config) {
            Ext.applyIf(config, {
                verticalScrollerType: 'paginggridscroller',
                invalidateScrollerOnRefresh: false,
                scroll: 'both',
                verticalScroller: {
                    scrollToLoadBuffer: 100
                },
                bbar: {
                    cls: 'commonlivegridinfopanel',
                    items: [{ xtype: 'pagingtoolbar', cls: 'commonlivegridinfopanel' },
                        '->',
                    { xtype: 'livegridinfopanel', grid: this }
                    ]
                }
            });
            this.callParent([config]);
        },
        initComponent: function () {
            this.callParent(arguments);
            this.headerCt.on('columnhide', this.onColumnChange, this);
            this.headerCt.on('columnshow', this.onColumnChange, this);

            this.refresh_in_progress = 0;
            this.isSuccessResponse = true;

            if (this.getStore().buffered) {
                this.getStore().on('beforeprefetch', this.before_request, this);
                this.getStore().on("afterguaranteedrange", this.after_request, this);
            } else {
                this.getStore().on('beforeload', this.before_request, this);
                this.getStore().on("load", this.after_request, this);
            }

            var paging_tb = this.down('pagingtoolbar');
            if (paging_tb) {
                // If we have an infinite grid or NonPagination store we hide the paging toolbar
                if (this.getStore().buffered || this.getStore().alias[0] === "store.directcombo") {
                    paging_tb.hide();
                }
                else {
                    paging_tb.on('beforechange', this.scrollToTop, this);
                    paging_tb.bindStore(this.getStore());
                    paging_tb.down('#refresh').hide();
                }
            }
        },
        before_request: function () {
            if (this.getStore().buffered) {
                this.refresh_in_progress = 1;
            }
            else {
                this.refresh_in_progress += 1;
            }
        },
        after_request: function () {
            if (this.refresh_in_progress > 0) {
                this.refresh_in_progress -= 1;
            }
            if (this._previousScrollPosition && this.getView().getEl()) {
                this.getView().getEl().dom.scrollTop = this._previousScrollPosition;
                delete this._previousScrollPosition;
            }
        },
        /**
         * Listeners for when you hide/show a column, the data isn't fetched yet so
         * we need to refresh the grid to get it. Otherwise there will be a blank column
         * until the page is manually refreshed.
         **/
        onColumnChange: function () {
            if (!this.onColumnChangeTask) {
                this.onColumnChangeTask = new Ext.util.DelayedTask(function () {
                    this.refresh();
                }, this);
            }

            // give them one second to hide/show other columns
            this.onColumnChangeTask.delay(1000);
        },
        setContext: function (uid) {
            this.scrollToTop();
            if (this.getStore().pageMap) {
                this.getStore().pageMap.clear();
            }
            this.callParent([uid]);
        },
        refresh: function (callback, scope) {
            // only refresh if a context is set
            if (!this.getContext()) {
                return;
            }
            this.saveSelection();
            var store = this.getStore();

            if (!store.buffered || store.totalCount < store.pageSize || !this.isSuccessResponse) {
                this.isSuccessResponse = true;
                this._previousScrollPosition = this.getViewScrollPosition();
                store.load({
                    callback: callback,
                    scope: scope || this
                });
            } else {
                // need to refresh the current rows, without changing the scroll position
                var start = Math.max(store.lastRequestStart, 0),
                    end = Math.min(start + store.pageSize - 1, store.totalCount),
                    page = store.pageMap.getPageFromRecordIndex(end);
                // make sure we do not have any records in cache
                store.pageMap.removeAtKey(page);

                // If a refresh kicks off before the initial store load store.totalCount is NaN
                if (isNaN(store.totalCount)) {
                    end = start + store.pageSize - 1;
                }

                if (store.getCount() >= store.getTotalCount() && this.verticalScroller) {
                    start = this.verticalScroller.getFirstVisibleRowIndex();
                }

                // this will fetch from the server and update the view since we removed it from cache
                if (Ext.isFunction(callback)) {
                    store.guaranteeRange(start, end, callback, scope);
                } else {
                    store.guaranteeRange(start, end);
                }
            }
        },
        scrollToTop: function () {
            var view = this.getView();
            if (view.getEl()) {
                view.getEl().dom.scrollTop = 0;
            }
        },
        getViewScrollPosition: function () {
            var view = this.getView();
            if (view.getEl()) {
                return view.getEl().dom.scrollTop;
            }
            return 0;
        }
    });


    /**
     * @class Zenoss.FilterGridPanel
     * @extends Zenoss.BaseGridPanel
     * Sub class of the base grid that allows adds filters to the columns.
     * @constructor
     */
    Ext.define('Zenoss.FilterGridPanel', {
        extend: 'Zenoss.BaseGridPanel',
        alias: ['widget.filtergridpanel'],
        constructor: function (config) {
            config = config || {};
            Ext.applyIf(config, {
                displayFilters: true,
                // only make it stateful if we have an id set
                stateful: Ext.isDefined(config.id),
                stateId: config.id
            });

            this.callParent(arguments);
        },
        initComponent: function () {
            /**
             * @event filterschanged
             * Fires after the filters are changed but after the store is reloaded
             * @param {Zenoss.FilterGridPanel} grid The grid panel.
             * @param {Object} filters Key/value pair of the new filters.
             */
            this.addEvents('filterschanged');
            this.callParent();
            // create the filter row
            var filters = Ext.create('Ext.ux.grid.FilterRow', {
                grid: this,
                appendGlob: this.appendGlob,
                defaultFilters: this.defaultFilters || {}
            });


            this.filterRow = filters;
        },
        getState: function () {
            var state = this.callParent();
            state.filters = this.filterRow.getState();
            return state;
        },
        applyState: function (state) {
            this.callParent([state]);
            if (this.displayFilters) {
                // defer rendering the filter rows until after the column state has been applied so
                // the filters have the correct column widths
                if (this.displayFilters) {
                    this.filterRow.init(this);
                }
                this.filterRow.applyState(state.filters);
            }
        },
        getFilters: function () {
            return this.filterRow.getSearchValues();
        },
        setFilter: function (colId, value) {
            this.filterRow.setFilter(colId, value);
        },
        afterRender: function () {
            this.callParent();
            this.applyState(this.getState());
        },
        refresh: function (callback) {
            if (!Zenoss.settings.enableLiveSearch) {
                var values = this.getFilters(),
                    store = this.getStore();
                if (!store.proxy.extraParams) {
                    store.proxy.extraParams = {};
                }
                store.proxy.extraParams.params = values;
                if (this.filterRow.isValid()) {
                    this.saveState();
                }
            }
            this.callParent([callback]);
        }
    });

    /**
     * @class Zenoss.LiveGridInfoPanel
     * @extends Ext.toolbar.TextItem
     * Toolbar addition that displays, e.g., "Showing 1-10 of 100 Rows"
     * @constructor
     * @grid {Object} the GridPanel whose information should be displayed
     */
    Ext.define('Zenoss.LiveGridInfoPanel', {
        extend: 'Ext.toolbar.TextItem',
        alias: ['widget.livegridinfopanel'],
        cls: 'livegridinfopanel',
        constructor: function (config) {
            this.emptyMsg = _t('NO RESULTS');
            this.firstRender = true;
            config = config || {};
            Ext.applyIf(config, {
                text: this.emptyMsg
            });
            this.callParent([config]);
        },
        initComponent: function () {
            if (this.grid) {
                if (!Ext.isObject(this.grid)) {
                    this.grid = Ext.getCmp(this.grid);
                }
                this.view = this.grid.getView();
                // We need to refresh this when one of two events happen:
                //  1.  The data in the data store changes
                //  2.  The user scrolls.
                this.grid.getStore().on('datachanged', this.onDataChanged, this);
                /*  added this guaranteedrange hack to make up for the ext bug where-by
                    updating store doesn't fire the datachanged except on load.
                */
                var store = this.grid.getStore();
                if (store.buffered) {
                    store.on('guaranteedrange', this.onDataChanged, this);
                }
                else {
                    store.on('load', this.onDataChanged, this);
                }
                this.view.on('bodyscroll', this.onScroll, this);
                this.view.on('resize', this.onResize, this);
            }
            this.lastScrollLeft = 0;
            this.rowHeight = null;
            this.visibleRows = null;
            this.displayMsg = _t('DISPLAYING {0} - {1} of {2} ROWS');
            this.callParent(arguments);
        },
        onResize: function () {
            this.visibleRows = null;
            this.onScroll();
            Zenoss.util.refreshScrollPosition(this);
        },
        getNumberOfVisibleRows: function () {
            if (this.visibleRows) {
                return this.visibleRows;
            }

            var gridHeight;

            gridHeight = this.view.el.getHeight();

            // this assumes that all rows are uniform height
            // and can not change
            var node = this.view.getNode(0),
                el = Ext.fly(node);
            // make sure the first row is rendered
            if (el) {
                this.rowHeight = el.getHeight();
            }

            if (this.rowHeight && gridHeight) {
                this.visibleRows = Math.floor(gridHeight / this.rowHeight);
                return this.visibleRows;
            }
            return 0;
        },
        getEndCount: function (start) {
            var numrows = this.getNumberOfVisibleRows();
            if (numrows) {
                return start + numrows + 1;
            }
            // we either aren't fully rendered yet or
            // there aren't any rows
            return 0;
        },
        getStartCount: function () {
            var scrollTop = this.view.el.dom.scrollTop;
            if (this.rowHeight && scrollTop) {
                return Math.ceil(scrollTop / this.rowHeight);
            }
            // ask the scroller, if the store is paginated
            if (this.grid.verticalScroller && this.grid.verticalScroller.getFirstVisibleRowIndex && this.grid.getStore().buffered) {
                var start = this.grid.verticalScroller.getFirstVisibleRowIndex();
                if (start) {
                    return start;
                }
            }
            return 0;
        },
        onDataChanged: function () {
            this.totalCount = this.grid.getStore().getTotalCount();
            if (!this.totalCount) {
                this.setText(this.emptyMsg);
            } else {
                this.updateRowText();
            }
        },
        onScroll: function (e, t) {
            // introduce a small delay so that we are
            // are not constantly updating the text when they are scrolling like crazy
            if (!this.onScrollTask || this.firstRender) {
                this.onScrollTask = new Ext.util.DelayedTask(this._doOnScroll, this);
            }
            this.onScrollTask.delay(250);
        },
        setText: function (text) {
            if (text !== this.text) {
                this.callParent(arguments);
            }
        },
        _doOnScroll: function () {
            // ext will fire the scroll event sometimes before the data is even set
            if (!this.totalCount) {
                return this.setText(this.emptyMsg);
            }
            if (this.firstRender) {
                this.firstRender = false;
            }
            this.updateRowText();
        },
        updateRowText: function () {
            var pagingScroller = this.grid.verticalScroller;
            if (pagingScroller && this.view && this.view.rendered) {
                var start = Math.max(this.getStartCount(), 0),
                    end = Math.min(this.getEndCount(start), this.totalCount),
                    currentScrollLeft = this.view.el.dom.scrollLeft;

                var store = this.grid.getStore();
                if (!store.buffered) {
                    var current_page = store.currentPage;
                    if (current_page > 0) {
                        var page_size = store.pageSize;
                        var offset = (current_page - 1) * page_size;
                        start = offset + start;
                        end = offset + end;
                        var real_page_end = current_page * page_size;
                        if (real_page_end > store.totalCount) {
                            real_page_end = store.totalCount;
                        }
                    }
                }
                var msg = Ext.String.format(this.displayMsg, start + 1, end, store.totalCount);
                if (this.scrollLeft !== currentScrollLeft) {
                    this.scrollLeft = currentScrollLeft;
                } else {
                    // only redraw the text if we're scrolling vertically; the DOM scrollLeft increment/decrement is a HACK
                    // to work around a (suspected) ExtJS bug that causes the headers to become misaligned
                    this.view.el.dom.scrollLeft += 1;
                    this.setText(msg);
                    this.view.el.dom.scrollLeft -= 1;
                }
            } else {
                // Drat, we didn't have the paging scroller, so assume we are showing all
                var showingAllMsg = _t('Found {0} records');
                msg = Ext.String.format(showingAllMsg, this.totalCount);
                this.setText(msg);
            }
        }
    });

}());
