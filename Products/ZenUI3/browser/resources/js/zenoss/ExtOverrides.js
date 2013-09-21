(function(){


/**
 * Natural Sort algorithm for Javascript - Version 0.7 - Released under MIT license
 * Author: Jim Palmer (based on chunking idea from Dave Koelle)
 *
 * Imported from https://github.com/overset/javascript-natural-sort.  Thanks!
 */

Ext.override(Ext.util.Sorter, {
    defaultSorterFn: function (o1, o2) {
        var a = this.getRoot(o1)[this.property],
            b = this.getRoot(o2)[this.property],
            re = /(^-?[0-9]+(\.?[0-9]*)[df]?e?[0-9]?$|^0x[0-9a-f]+$|[0-9]+)/gi,
            sre = /(^[ ]*|[ ]*$)/g,
            dre = /(^([\w ]+,?[\w ]+)?[\w ]+,?[\w ]+\d+:\d+(:\d+)?[\w ]?|^\d{1,4}[\/\-]\d{1,4}[\/\-]\d{1,4}|^\w+, \w+ \d+, \d{4})/,
            hre = /^0x[0-9a-f]+$/i,
            ore = /^0/,
            //force case insensitivity - Joseph and Seth
            //i = function(s) { return naturalSort.insensitive && (''+s).toLowerCase() || ''+s },
            i = function(s) { return (''+s).toLowerCase() || ''+s },

            // convert all to strings strip whitespace
            x = i(a).replace(sre, '') || '',
            y = i(b).replace(sre, '') || '',
            // chunk/tokenize
            xN = x.replace(re, '\0$1\0').replace(/\0$/,'').replace(/^\0/,'').split('\0'),
            yN = y.replace(re, '\0$1\0').replace(/\0$/,'').replace(/^\0/,'').split('\0'),
            // numeric, hex or date detection
            xD = parseInt(x.match(hre)) || (xN.length != 1 && x.match(dre) && Date.parse(x)),
            yD = parseInt(y.match(hre)) || xD && y.match(dre) && Date.parse(y) || null,
            oFxNcL,
            oFyNcL;
        // first try and sort Hex codes or Dates
        if (yD)
            if ( xD < yD )
                return -1;
            else if ( xD > yD )
                return 1;
        // natural sorting through split numeric strings and default strings
        for(var cLoc=0, numS=Math.max(xN.length, yN.length); cLoc < numS; cLoc++) {
            // find floats not starting with '0', string or 0 if not defined (Clint Priest)
            oFxNcL = !(xN[cLoc] || '').match(ore) && parseFloat(xN[cLoc]) || xN[cLoc] || 0;
            oFyNcL = !(yN[cLoc] || '').match(ore) && parseFloat(yN[cLoc]) || yN[cLoc] || 0;
            // handle numeric vs string comparison - number < string - (Kyle Adams)
            if (isNaN(oFxNcL) !== isNaN(oFyNcL)) { return (isNaN(oFxNcL)) ? 1 : -1; }
            // rely on string comparison if different types - i.e. '02' < 2 != '02' < '2'
            else if (typeof oFxNcL !== typeof oFyNcL) {
                oFxNcL += '';
                oFyNcL += '';
            }
            if (oFxNcL < oFyNcL) return -1;
            if (oFxNcL > oFyNcL) return 1;
        }
        return 0;
    }
});
    /**
     * This file contains overrides we are appyling to the Ext framework. These are default values we are setting
     * and convenience methods on the main Ext classes.
     **/

    /**
     * This makes the default value for checkboxes getSubmitValue (called by getFieldValues on the form)
     * return true/false if it is checked or unchecked. The normal default is "on" or nothing which means the
     * key isn't even sent to the server.
     **/
    Ext.override(Ext.form.field.Checkbox, {
        inputValue: true,
        uncheckedValue: false
    });

    /**
    * Splitter needs to be resized thinner based on the older UI. The default is 5
    **/
   Ext.override(Ext.resizer.Splitter, {
       width: 2
   });

    /**
     * In every one of our panels we want border and frame to be false so override it on the base class.
     **/
    Ext.override(Ext.panel.Panel, {
        frame: false,
        border: false
    });

    /**
     * Refs were removed when going from Ext3 to 4, we rely heavily on this feature and it is much more
     * concise way of accessing children so we are patching it back in.
     **/
    Ext.override(Ext.AbstractComponent, {
        initRef: function() {
            if(this.ref && !this.refOwner){
                var levels = this.ref.split('/'),
                last = levels.length,
                i = 0,
                t = this;
                while(t && i < last){
                    t = t.ownerCt;
                    ++i;
                }
                if(t){
                    t[this.refName = levels[--i]] = this;
                    this.refOwner = t;
                }
            }
        },
        recursiveInitRef: function() {
            this.initRef();
            if (Ext.isDefined(this.items)) {
                Ext.each(this.items.items, function(item){
                    item.recursiveInitRef();
                }, this);
            }
            if (Ext.isFunction(this.child)) {
                var tbar = this.child('*[dock="top"]');
                if (tbar) {
                    tbar.recursiveInitRef();
                }
                var bbar = this.child('*[dock="bottom"]');
                if (bbar) {
                    bbar.recursiveInitRef();
                }
            }
        },
        removeRef: function() {
            if (this.refOwner && this.refName) {
                delete this.refOwner[this.refName];
                delete this.refOwner;
            }
        },
        onAdded: function(container, pos) {
            this.ownerCt = container;
            this.recursiveInitRef();
            this.fireEvent('added', this, container, pos);
        },
        onRemoved: function() {
            this.removeRef();
            var me = this;
            me.fireEvent('removed', me, me.ownerCt);
            delete me.ownerCt;
        },
        removeCls : function(cls) {
          try{
            var me = this,
            el = me.rendered ? me.el : me.protoEl;
            el.removeCls.apply(el, arguments);
            return me;
            }catch(e){};
        }
    });


    /**
     * Back compat for Ext3 Component grid definitions.
     * NOTE: This only works if you follow the convention of having the xtype be the same
     * as the last part of the namespace defitions. (e.g. "Zenoss.component.foo" having an xtype "foo")
     * @param xtype
     * @param cls
     */
    Ext.reg = function(xtype, cls){
        if (Ext.isString(cls)) {
            Ext.ClassManager.setAlias(cls, 'widget.'+xtype);
        } else {
            // try to register the component
            var clsName ="Zenoss.component." + xtype;
            if (Ext.ClassManager.get(clsName)) {
                Ext.ClassManager.setAlias(clsName, 'widget.'+xtype);
            }else {
                throw Ext.String.format("Unable to to register the xtype {0}: change the Ext.reg definition from the object to a string", xtype);
            }
        }
    };

    /**
     * The Ext.grid.Panel component row selection has a flaw in it:

     Steps to recreate:
     1. Create a standard Ext.grid.Panel with multiple records in it and turn "multiSelect: true"
     Note that you can just go to the documentation page
     http://docs.sencha.com/ext-js/4-0/#!/api/Ext.grid.Panel and insert the multiSelect:
     true line right into there and flip to live preview.

     2. Select the top row, then press and hold shift and click on the second row, then the third row,
     then the fourth. You would expect to see all 4 rows selected but instead you just get the last two.

     3. For reference, release the shift and select the bottom row (4th row). Now press and hold shift
     and select the 3rd row, then the 2nd row, then the 1st row. You now see all four rows selected.

     To Fix this I have to override the Ext.selection.Model to handle the top down versus bottom up selection.
     *
     */
    Ext.override(Ext.selection.Model, {
        /**
         * Selects a range of rows if the selection model {@link #isLocked is not locked}.
         * All rows in between startRow and endRow are also selected.
         * @param {Ext.data.Model/Number} startRow The record or index of the first row in the range
         * @param {Ext.data.Model/Number} endRow The record or index of the last row in the range
         * @param {Boolean} keepExisting (optional) True to retain existing selections
         */
        selectRange : function(startRow, endRow, keepExisting, dir){
            var me = this,
                store = me.store,
                selectedCount = 0,
                i,
                tmp,
                dontDeselect,
                records = [];

            if (me.isLocked()){
                return;
            }

            if (!keepExisting) {
                me.deselectAll(true);
            }

            if (!Ext.isNumber(startRow)) {
                startRow = store.indexOf(startRow);
            }
            if (!Ext.isNumber(endRow)) {
                endRow = store.indexOf(endRow);
            }

            // WG: create a flag to see if we are swapping
            var swapped = false;
            // ---

            // swap values
            if (startRow > endRow){
                // WG:  set value to true for my flag
                swapped = true;
                // ----
                tmp = endRow;
                endRow = startRow;
                startRow = tmp;
            }

            for (i = startRow; i <= endRow; i++) {
                if (me.isSelected(store.getAt(i))) {
                    selectedCount++;
                }
            }

            if (!dir) {
                dontDeselect = -1;
            } else {
                dontDeselect = (dir == 'up') ? startRow : endRow;
            }

            for (i = startRow; i <= endRow; i++){
                if (selectedCount == (endRow - startRow + 1)) {
                    if (i != dontDeselect) {
                        me.doDeselect(i, true);
                    }
                } else {
                    records.push(store.getAt(i));
                }
            }

            //WG:  START  CHANGE
            // This is my fix, we need to flip the order
            // for it to correctly track what was selected first.
            if(!swapped){
                records.reverse();
            }
            //WG:  END CHANGE



            me.doMultiSelect(records, true);
        }
    });

    /**
     * This is a workaround to make sure the node isn't null as it has happened
     * to be on occasion. These only affect the UI class switches.
     * See Trac Ticket #29912
     **/
    Ext.override(Ext.view.AbstractView, {
        // invoked by the selection model to maintain visual UI cues
        onItemDeselect: function(record) {
            var node = this.getNode(record);
            if(node) Ext.fly(node).removeCls(this.selectedItemCls);
        },
        // invoked by the selection model to maintain visual UI cues
        onItemSelect: function(record) {
            var node = this.getNode(record);
            if(node) Ext.fly(node).addCls(this.selectedItemCls);
        }
    });


   /**
    * workaround for scrollbars missing in IE. IE ignores the parent size between parent and child
    * so we end up with the part that should have scrollbars the same size as the child, thus
    * no scrollbars. This normalizes the sizes between elements in IE only.
    **/
    if(Ext.isIE){
        Ext.override(Ext.form.ComboBox, {
            onExpand: function() {
                var me = this, picker = this.getPicker();
                var child = Ext.DomQuery.selectNode('#'+picker.id+' .x-boundlist-list-ct');
                Ext.defer(function(){ // defer a bit so the grandpaw will have a height
                    try{
                        var grandpaw = Ext.DomQuery.selectNode('#'+picker.id);
                        child.style.cssText = 'width: 100%; height: 100%; overflow: auto;';
                    }catch(e){
                        // couldn't traverse, so just swallow it.
                    }
                }, 100, me);
                this.callOverridden();
            }
        }
                    );
    }

    Ext.override(Ext.form.ComboBox, {
        getSelectedIndex: function() {
            var combo = this,
                v = combo.getValue(),
            record = combo.findRecord(combo.valueField || combo.displayField, v),
            index = combo.store.indexOf(record);
            return index;
    }});

    /**
     * The Event console filters are not rendering correctly in our application. This override is a temporary workaround
     * until we can figure out exactly why it is not rendering. Instead of aborting on an failed layout, just keep
     * running (flush) and ignore the failed layout.
     **/
    Ext.override(Ext.layout.Context, {
        runComplete: function () {
            var me = this;

            me.state = 2;

            if (me.remainingLayouts) {
                me.handleFailure();
                // return false;
            }

            me.flush();

            // Call finishedLayout on all layouts, but do not clear the queue.
            me.flushLayouts('finishQueue', 'finishedLayout', true);

            // Call notifyOwner on all layouts and then clear the queue.
            me.flushLayouts('finishQueue', 'notifyOwner');

            me.flush(); // in case any setProp calls were made

            me.flushAnimations();

            return true;
        }

    });

    /**
     * The multiselect doesn't test to see if it has a valid return value.
     *
     **/
    Ext.override(Ext.ux.form.MultiSelect, {
        getSubmitValue: function() {
            var me = this,
                delimiter = me.delimiter,
                val = me.getValue();
            if (Ext.isString(val)) {
                return Ext.isString(delimiter) ? val.join(delimiter) : val;
            }
            return "";
        }
    });

    /**
     *  Fixes a bug in Ext where when the store is canceling
     *  requests and there are not any outstanding requests.
     **/
    Ext.override(Ext.data.Store, {
        onPageMapClear: function() {
            var me = this,
            reqs = me.pageRequests,
            req,
            page;

            // If any requests return, we no longer respond to them.
            if (me.pageMap.events.pageadded) {
                me.pageMap.events.pageadded.clearListeners();
            }

            // If the page cache gets cleared it's because a full reload is in porogress
            this.totalCount = 0;

            // Cancel all outstanding requests
            for (page in reqs) {
                if (reqs.hasOwnProperty(page)) {
                    req = reqs[page];
                    delete reqs[page];
                    if (req) {
                        delete req.callback;
                    }
                }
            }
        }

    });

    /**
     *  Fixes a bug in Ext: they forgot to make the flashParams actually work
     *  Added wmode: 'transparent' here so that IE would allow us to overlay a div
     **/
    Ext.override(Ext.flash.Component, {
        afterRender: function() {
            var me = this,
                flashParams = Ext.apply({wmode: 'transparent'}, me.flashParams),
                flashVars = Ext.apply({}, me.flashVars);

            me.callParent();

            new swfobject.embedSWF(
                me.url,
                me.getSwfId(),
                me.swfWidth,
                me.swfHeight,
                me.flashVersion,
                me.expressInstall ? me.statics.EXPRESS_INSTALL_URL : undefined,
                flashVars,
                flashParams,
                me.flashAttributes,
                Ext.bind(me.swfCallback, me)
            );
        }

    });



    /*
        Fixes a known issue in Ext where sometimes the target is null and so getTarget cannot connect the
        event to the target at that moment. One suggestion on the forums is to update ExtJs. We're not
        going to do that yet, so here's a work-around. Not going to bother with browser sniffing since this
         == null should only happen happen in IE anyway.
    */
    Ext.EventObjectImpl.prototype.getTarget = function (selector, maxDepth, returnEl) {
        if (this.target == null) return null;
        if (selector) {
            return Ext.fly(this.target).findParent(selector, maxDepth, returnEl);
        }
        return returnEl ? Ext.get(this.target) : this.target;
    };

    Ext.override(Ext.grid.column.Column, {
        defaultRenderer: Ext.htmlEncode
    });

    Ext.define('Ext.data.TreeStoreOverride',{
        override: 'Ext.data.TreeStore',

        /**
         * @private
         * @param {Object[]} filters The filters array
         */
        applyFilters: function(filters){
            var me = this,
                decoded = me.decodeFilters(filters),
            i = 0,
            length = decoded.length,
            node,
            visibleNodes = [],
            resultNodes = [],
            root = me.getRootNode(),
            flattened = me.tree.flatten(),
            items,
            item,
            fn;


            /**
             * @property {Ext.util.MixedCollection} snapshot
             * A pristine (unfiltered) collection of the records in this store. This is used to reinstate
             * records when a filter is removed or changed
             */
            me.snapshot = me.snapshot || me.getRootNode().copy(null, true);

            for (i = 0; i < length; i++) {
                me.filters.replace(decoded[i]);
            }


            //collect all the nodes that match the filter
            items = me.filters.items;
            length = items.length;
            for (i = 0; i < length; i++){
                item = items[i];
                fn = item.filterFn || function(item){ return item.get(item.property) == item.value; };
                visibleNodes = Ext.Array.merge(visibleNodes, Ext.Array.filter(flattened, fn));
            }

            //collect the parents of the visible nodes so the tree has the corresponding branches
            length = visibleNodes.length;
            for (i = 0; i < length; i++){
                node = visibleNodes[i];
                node.bubble(function(n){
                    if (n.parentNode){
                        resultNodes.push(n.parentNode);
                    } else {
                        return false;
                    }
                });
            }
            visibleNodes = Ext.Array.merge(visibleNodes, resultNodes);

            //identify all the other nodes that should be removed (either they are not visible or are not a parent of a visible node)
            resultNodes = [];
            root.cascadeBy(function(n){
                if (!Ext.Array.contains(visibleNodes,n)){
                    resultNodes.push(n);
                }
            });
            //we can't remove them during the cascade - pulling rug out ...
            length = resultNodes.length;
            for (i = 0; i < length; i++){
                resultNodes[i].remove();
            }

            //necessary for async-loaded trees
            root.getOwnerTree().getView().refresh();
            root.getOwnerTree().expandAll();
            if (Ext.isFunction(root.getOwnerTree().postFilter)) {
                root.getOwnerTree().postFilter();
            }
        },
        //@inheritdoc
        filter: function(filters, value) {
            var nodes, nodeLength, i, filterFn;

                if (Ext.isString(filters)) {
                    filters = {
                        property: filters,
                        value: value
                    };
                }

            //find branch nodes that have not been loaded yet - this approach is in contrast to expanding all nodes recursively, which is unnecessary if some nodes are already loaded.
            filterFn = function(item){ return !item.isLeaf() && !(item.isLoading() || item.isLoaded()); };
            nodes = Ext.Array.filter(this.tree.flatten(), filterFn);
            nodeLength = nodes.length;

            if (nodeLength === 0){
                this.applyFilters(filters);
            } else {
                for (i = 0; i < nodeLength; i++){
                    this.load({
                        node: nodes[i],
                        callback: function(){
                            nodeLength--;
                            if (nodeLength === 0){
                                //start again & re-test for newly loaded nodes in case more branches exist
                                this.filter(filters,value);
                            }
                        },
                        scope: this
                    });
                }
            }
        },
        clearFilter: function(suppressEvent) {

            this.filters.clear();

            if (this.isFiltered()){
                this.setRootNode(this.snapshot);
                delete this.snapshot;
            }
        },
        isFiltered: function() {
            var snapshot = this.snapshot;
            return !! snapshot && snapshot !== this.getRootNode();
        }
    });


<<<<<<< HEAD
=======


>>>>>>> 8f94551... ZEN-8376: Fixing a set of security vulnerabilities
}());
