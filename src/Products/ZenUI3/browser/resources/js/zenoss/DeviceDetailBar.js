(function(){

Ext.define("Zenoss.DeviceDetailItem", {
    alias:['widget.devdetailitem'],
    extend:"Ext.Container",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            hideParent: true,
            cls: 'devdetailitem',
            items: [{
                cls: 'devdetail-textitem ' + (config.textCls||''),
                ref: 'textitem',
                xtype: 'tbtext',
                text: config.text || ''
            },{
                cls: 'devdetail-labelitem ' + (config.labelCls||''),
                ref: 'labelitem',
                xtype: 'tbtext',
                text: config.label || ''
            }]
        });
        Zenoss.DeviceDetailItem.superclass.constructor.call(this, config);
    },
    setText: function(t) {
        this.textitem.setText(t);
    },
    setLabel: function(t) {
        this.labelitem.setText(t);
    }
});



Ext.define("Zenoss.DeviceNameItem", {
    alias:['widget.devnameitem'],
    extend:"Ext.Container",
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            defaults: {
                xtype: 'tbtext'
            },
            items: [{
                cls: 'devdetail-devname',
                ref: 'devname'
            },{
                ref: 'devclass',
                cls: 'devdetail-devclass'
            },{
                ref: 'ipAddress',
                cls: 'devdetail-ipaddress'
            }]
        });
        Zenoss.DeviceNameItem.superclass.constructor.call(this, config);
    }
});



Ext.define("Zenoss.DeviceDetailBar", {
    alias:['widget.devdetailbar'],
    extend:"Zenoss.LargeToolbar",
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            cls: 'largetoolbar devdetailbar',
            height: 55,
            directFn: Zenoss.remote.DeviceRouter.getInfo,
            defaultType: 'devdetailitem',
            items: [{
                ref: 'iconitem',
                cls: 'devdetail-icon'
            },{
                cls: 'evdetail-sep'
            },{
                xtype: 'devnameitem',
                height: 45,
                ref: 'deviditem'
            },'-',{
                xtype: "eventrainbow",
                width:202,
                ref: 'eventsitem',
                id: 'detailrainbow',
                label: _t('Events'),
                listeners: {
                    render: function(me) {
                        me.getEl().on('click', function(){
                            Ext.History.add('#deviceDetailNav:device_events');
                        });
                    }
                },
                count: 4
            },'-',{
                ref: 'statusitem',
                width:98,
                label: _t('Device Status'),
                id: 'statusitem'
            },'-',{
                ref: 'prodstateitem',
                width:120,
                label: _t('Production State'),
                id: 'prodstateitem'
            },'-',{
                ref: 'priorityitem',
                width:100,
                label: _t('Priority'),
                id: 'priorityitem'
            }, {
                ref: 'renamingitemseparator',
                cls: 'x-toolbar-separator x-box-item x-toolbar-item x-toolbar-separator-horizontal'
            }, {
                ref: 'renamingitem',
                width:100,
                label: _t('Monitoring'),
                id: 'renamingitem'
            }]
        });
        this.contextKeys = [
            'ipAddressString',
            'deviceClass',
            'name',
            'icon',
            'status',
            'productionState',
            'priority',
            'renameInProgress'
        ];
        Zenoss.DeviceDetailBar.superclass.constructor.call(this, config);
    },
    contextCallbacks: [],
    addDeviceDetailBarItem: function(item, fn, added_keys) {
      this.add('-');
      this.add(item);
      this.on('contextchange', fn, this);
      for (var i = 0; i < added_keys.length; i++) {
        this.contextKeys.push(added_keys[i]);
      }
    },
    refresh: function() {
        this.setContext(this.contextUid);
    },
    setContext: function(uid) {
        this.contextUid = uid;
        this.directFn({uid:uid, keys:this.contextKeys}, function(result){
            this.suspendLayouts();
            this.layout.targetEl.setWidth(this.getWidth());
            var ZR = Zenoss.render,
                data = result.data;
            Zenoss.env.icon = this.iconitem;
            this.iconitem.getEl().setStyle({
                'background-image' : 'url(' + data.icon + ')'
            });
            this.deviditem.devname.setText(Ext.htmlEncode(data.name));
            var ipAddress = data.ipAddressString;
            this.deviditem.ipAddress.setText(ipAddress);
            this.deviditem.devclass.setText(ZR.DeviceClass(data.deviceClass.uid));
            this.eventsitem.setContext(uid);
            this.statusitem.setText(
                ZR.pingStatusLarge(data.status));
            /* reformat the production state name so that it doesn't mess up the UI when too long */
            var pstatetxt = Zenoss.env.PRODUCTION_STATES_MAP[data.productionState];
            var pstate =  "<span title='"+pstatetxt+"'>";
                pstate += pstatetxt.length > 14 ? pstatetxt.substring(0, 12)+"..." : pstatetxt;
                pstate += "</span>";
            this.prodstateitem.setText(pstate);
            this.priorityitem.setText(Zenoss.env.PRIORITIES_MAP[data.priority]);

            if(data.renameInProgress){
                this.renamingitem.setText("Paused");
                this.renamingitemseparator.show();
                if(!Zenoss.Security.doesNotHavePermission('Admin Device')){
                    var resetRenameCmp = Ext.getCmp("resetRenameCmp");
                    if(resetRenameCmp) {
                        resetRenameCmp.show();
                    } else {
                        // sometimes the component gets loaded afterwards
                        Ext.defer(function() {
                            resetRenameCmp = Ext.getCmp("resetRenameCmp");
                            if(resetRenameCmp) {
                                resetRenameCmp.show();
                            }
                        }, 1000);
                    }
                }
            } else {
                this.renamingitem.hide();
                this.renamingitemseparator.hide();
                if(!Zenoss.Security.doesNotHavePermission('Admin Device')){
                    var resetRenameCmp = Ext.getCmp("resetRenameCmp");
                    if(resetRenameCmp) {
                        resetRenameCmp.hide();
                    } else {
                        // sometimes the component gets loaded afterwards
                        Ext.defer(function() {
                            resetRenameCmp = Ext.getCmp("resetRenameCmp");
                            if(resetRenameCmp) {
                                resetRenameCmp.hide();
                            }
                        }, 1000);
                    }
                }
            }

            // reset the positions based on text width and what not:
            this.iconitem.setPosition(0, 0);
            Ext.getCmp(Ext.query('.evdetail-sep')[0].id).setPosition(this.iconitem.getWidth()+this.iconitem.x, 0);
            var devitem_y = Ext.isEmpty(ipAddress) ? 7 : -2;
            this.deviditem.setPosition(this.iconitem.getWidth() +this.iconitem.x + 30, devitem_y);
            Ext.getCmp('detailrainbow').setPosition(this.deviditem.devname.getWidth() +this.deviditem.x + 30, 3);
            this.statusitem.setPosition(Ext.getCmp('detailrainbow').getWidth() +Ext.getCmp('detailrainbow').x + 30, -2);
            Ext.getCmp(Ext.query('.x-toolbar-separator')[0].id).setPosition(this.statusitem.getWidth()+this.statusitem.x+10, 14);
            this.prodstateitem.setPosition(this.statusitem.getWidth() +this.statusitem.x + 30, -2);
            Ext.getCmp(Ext.query('.x-toolbar-separator')[1].id).setPosition(this.prodstateitem.getWidth()+this.prodstateitem.x+10, 14);
            this.priorityitem.setPosition(this.prodstateitem.getWidth() +this.prodstateitem.x + 30, -2);

            this.fireEvent('contextchange', this, data);
            this.resumeLayouts();
        }, this);
    }
});



})();
