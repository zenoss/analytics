/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


/* package level */
(function() {
    Ext.namespace('Zenoss.form');
    /**
     * Config Options:
     * - record (required) - the record we are editing, it is attached to each item
     * - items - received from the Schema declaration
     * - directFn - The server call when we press Save
     * - saveHandler - the router callback from after we save
     **/
    Ext.define("Zenoss.form.DataSourceEditDialog", {
        extend: "Zenoss.dialog.BaseWindow",
        alias: ['widget.datasourceeditdialog'],
        constructor: function(config) {
            config = config || {};

            // verify we received the record we are editing
            var record = config.record,
                items = config.items,
                i,
                autoHeight = true,
                that = this; // used in the save handler closure
            this.itemCount = 0;
            // make sure the record was passed in
            if (!record) {
                throw "EditDialog did not recieve a record to edit (config.record is undefined)";
            }

            if (!config.singleColumn) {
                items = this.sortItems(items, record);
            }else{
                // the items come in the form of a single fieldset
                // and we can not have a fieldset because it looks ugly in a dialog
                items = items.items[0].items;
                for(i=0; i<items.length; i+=1) {
                    items[i].record = record;
                    this.itemCount += 1;
                    // datapointitemselectors are tall
                    if (items[i]['xtype'] === 'datapointitemselector') {
                        this.itemCount += 4;
                    }
                }
            }

            // Since ext has no maxheight property, we need to only use autoheight if we don't
            // have a lot of items. Otherwise the dialog expands off the screen.
            if (this.itemCount > 10) {
                autoHeight = false;
            }

            Ext.apply(config, {
                layout: 'anchor',
                plain: true,
                buttonAlign: 'left',
                autoScroll: true,
                constrain: true,
                modal: true,
                padding: 10,
                height: 500,
                autoHeight: autoHeight,
                items: [{
                    xtype:'form',
                    minWidth: 300,
                    ref: 'editForm',
                    fieldDefaults: {
                        labelAlign: 'top'
                    },
                    autoScroll:true,

                    defaults: {
                        xtype: 'textfield',
                        anchor: '85%'
                    },
                    listeners: {
                        /**
                         * Sets the windows submit button to be disabled when the form is not valid
                         **/
                        validitychange: function(formPanel, valid){
                            var dialogWindow = that;
                            // check security first
                            if (Zenoss.Security.hasPermission('Manage DMD')) {
                                dialogWindow.submitButton.setDisabled(!valid);
                            }
                        }
                    },
                    items: items

                }],
                buttons: [{
                    xtype: 'DialogButton',
                    ref: '../submitButton',
                    disabled: Zenoss.Security.doesNotHavePermission('Manage DMD'),
                    text: _t('Save'),
                    handler: function () {
                        var form = that.editForm.form,
                            dirtyOnly = true,
                            values = form.getFieldValues(dirtyOnly);

                        values.uid = record.uid;
                        config.directFn(values, config.saveHandler);
                    }
                },
                    Zenoss.dialog.CANCEL
                ]

            });
            Zenoss.form.DataSourceEditDialog.superclass.constructor.apply(this, arguments);
        },

        /**
         * This function returns a two column layout with the fields auto divided between the
         * column according to the order they are defined.
         * If you specify a group in your datasource schema, they will appear in that "panel" on this dialog
         **/
        sortItems: function(fieldsets, record) {
            var panel = [], i, j, currentPanel,
            item, fieldset, tmp, header, textareas;

            // items comes back from the server in the form
            // fieldsets.items[0] = fieldset
            fieldsets = fieldsets.items;

            // The datasources have a convention to where the first items are
            // ungrouped.
            // This section makes sure the non-titled one is first.
            // (It swaps the titled first fieldset with the untitled fieldset)
            if (fieldsets[0].title) {
                tmp = fieldsets[0];
                for (i=0; i < fieldsets.length; i += 1) {
                    if (!fieldsets[i].title) {
                        fieldsets[0] = fieldsets[i];
                        fieldsets[i] = tmp;
                        break;
                    }
                }
            }

            // this creates a new panel for each group of items that come back from the server
            for (i =0; i < fieldsets.length; i += 1) {
                fieldset = fieldsets[i];

                // format the title a little funny
                if (fieldset.title) {
                    header = {
                        xtype: 'panel',
                        layout: 'anchor',
                        html: '<br /><br /><h1>' + fieldset.title + '</h1>'
                    };
                }else {
                    header = null;
                }

                textareas = [];

                currentPanel = {
                    xtype:'panel',
                    layout: 'column',
                    items: [{
                        layout:'anchor',
                        border:false,
                        columnWidth: 0.5,
                        items: []
                    },{
                        layout:'anchor',
                        border:false,
                        columnWidth: 0.5,
                        items: []
                    }]
                };

                // alternate which column this item belongs too
                for(j = 0; j < fieldset.items.length; j += 1) {
                    item = fieldset.items[j];
                    this.itemCount += 1;
                    item.record = record;

                    // we want to keep text areas to put them in a single column panel
                    if (item.xtype.search(/textarea/) >= 0) {
                        textareas.push(item);
                    }else{
                        currentPanel.items[j%2].items.push(item);
                    }
                }

                // if we have a header set display it
                if (header) {
                    panel.push(header);
                }

                // add the non-textarea fields
                panel.push(currentPanel);

                // put text areas in a single column layout
                if (textareas.length) {
                    for (j=0; j<textareas.length; j += 1) {
                        panel.push({
                            xtype: 'panel',
                            layout: 'anchor',
                            items: textareas[j]
                        });
                    }
                }

            }// fieldsets

            return panel;
        }
    });


}());
