/*
 * triggersComponents.js
 */
(function(){

var router = Zenoss.remote.TriggersRouter;

    /**
     * @class Zenoss.triggers.TriggersModel
     * @extends Ext.data.Model
     * Field definitions for the triggers
     **/
    Ext.define('Zenoss.triggers.TriggersModel',  {
        extend: 'Ext.data.Model',
        idProperty: 'uuid',
        fields: [
            { name:'uuid'},
            { name:'enabled'},
            { name:'name'},
            { name:'rule'},
            { name:'users'},
            { name:'globalRead'},
            { name:'globalWrite'},
            { name:'globalManage'},
            { name:'userRead'},
            { name:'userWrite'},
            { name:'userManage'}
        ]
    });



Ext.define("Zenoss.trigger.TriggerSubscriptions", {
    alias:['widget.triggersSubscriptions'],
    extend:"Ext.grid.Panel",
    constructor: function(config) {
        var me = this;
        Ext.applyIf(config, {
            ref: 'grid_panel',
            border: false,
            viewConfig: {forceFit: true},
            title: _t('Triggers'),
            autoExpandColumn: 'value',
            loadMask: {msg:_t('Loading...')},
            autoHeight: true,
            deferRowRender: true,
            keys: [{
                key: [Ext.EventObject.ENTER],
                handler: function() {
                    me.addValueFromCombo();
                }
            }],
            tbar: {
                items: [{
                    xtype: 'combo',
                    ref: 'data_combo',
                    typeAhead: true,
                    triggerAction: 'all',
                    lazyRender:true,
                    width: 505,
                    queryMode: 'local',
                    store: Ext.create('Zenoss.NonPaginatedStore', {
                        root: 'data',
                        autoLoad: true,
                        idProperty: 'uuid',
                        fields:['uuid','name'],
                        directFn: router.getTriggerList,
                        autoDestroy: false,
                        listeners:  {
                            load: function() {
                                // The renderer for the trigger column depends
                                // on this store being loaded in order for it to
                                // render the name correctly.
                                me.getView().refresh();
                            }
                        }
                    }),

                    valueField: 'uuid',
                    displayField: 'name'
                },{
                        xtype: 'button',
                        text: 'Add',
                        ref: 'add_button',
                        handler: function() {
                            me.addValueFromCombo();
                        }
                    },{
                        xtype: 'button',
                        ref: 'delete_button',
                        iconCls: 'delete',
                        handler: function() {
                            var row = me.getSelectionModel().getSelected();
                            me.getStore().remove(row);
                            me.getView().refresh();
                        }
                    }
                ]
            },
            store: new Ext.data.JsonStore({
                model: 'Zenoss.triggers.TriggersModel',
                storeId: 'triggers_combo_store',
                autoLoad: false,
                autoDestroy: false,
                data: []
            }),

            columns: [{
                header: _t('Trigger'),
                dataIndex: 'uuid',
                flex: 1,
                renderer: function(value) {
                    var toolbar = me.getDockedItems('toolbar')[0];
                    var comboStore = toolbar.data_combo.store;
                    var idx = comboStore.find('uuid', value);
                    if (idx > -1) {
                        return comboStore.getAt(idx).data.name;
                    }
                    else {
                        // instead of displaying a uuid to the user, just display
                        // something that lets them know the value is hidden.
                        return _t('(Hidden)');
                    }
                }
            }],

            selModel: Ext.create('Zenoss.SingleRowSelectionModel', {})
        });
        this.callParent(arguments);
    },
    addValueFromCombo: function() {
        var combo = this.getDockedItems('toolbar')[0].data_combo,
            val = combo.getValue(),
            existingIndex = this.getStore().findExact('uuid', val);

        if (!Ext.isEmpty(val) && existingIndex === -1) {

            var record =  Ext.create('Zenoss.triggers.TriggersModel', {uuid:val});
            this.getStore().add(record);
            combo.setValue('');
        }
        else if (existingIndex !== -1) {
            Zenoss.message.error(_t('Duplicate items not permitted here.'));
        }
    },
    loadData: function(data) {
        this.getStore().loadData(data);
    }
});


})();
