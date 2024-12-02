/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2009, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

Ext.define("Zenoss.DisplayField", {
    extend: "Ext.form.DisplayField",
    alias: ['widget.displayfield'],
    constructor: function(config) {
        Ext.applyIf(config, {
            fieldClass: 'display-field'
        });
        Zenoss.DisplayField.superclass.constructor.call(this, config);
    },
    setRawValue: function(v) {
        if (v && Ext.isIE && typeof v === 'string') {
            v = v.replace(/\n/g, '<br/>');
        }
        Zenoss.DisplayField.superclass.setRawValue.call(this, v);
    }
});

Ext.define("Zenoss.EditorWithButtons", {
    extend: "Ext.Editor",
    alias: ['widget.btneditor'],
    onRender: function() {
        Zenoss.EditorWithButtons.superclass.onRender.apply(this, arguments);
        this.editorpanel = new Ext.Panel({
            frame: true,
            bodyStyle: Ext.isIE ? 'padding-bottom:5px' : '',
            buttonAlign: 'left',
            buttons: [{
                text:_t('Save'),
                handler: Ext.bind(this.completeEdit, this)
            }, {
                text:_t('Cancel'),
                handler: Ext.bind(this.cancelEdit, this)
            }],
            items: this.field
        });
        if (Ext.isIE) {
            // IE can't set the layer width properly; always gets set to 11189
            this.el.setWidth(450);
        }
        this.editorpanel.render(this.el).show();
    },
    onBlur: function(){
        // do nothing
    }
});

Ext.define("Zenoss.EditableField", {
    extend: "Zenoss.DisplayField",
    alias: ['widget.editable'],
    constructor: function(config) {
        config = Ext.applyIf(config||{}, {
            cls: 'editable-field',
            overCls: 'editable-field-over',
            editEvent: 'click'
        });
        config.editor = Ext.applyIf(config.editor||{}, {
            xtype: 'btneditor',
            updateEl: !Ext.isIE,
            ignoreNoChange: true,
            autoSize: 'width',
            field: {
                xtype: 'textfield',
                selectOnFocus: true
            }
        });
        Zenoss.EditableField.superclass.constructor.call(this, config);
        this.initEditor();
        this.on('render', function(){
            this.getEl().on(this.editEvent, this.startEdit, this);
        }, this);
    },
    initEditor: function() {
        if (!(this.editor instanceof Ext.Editor)) {
            this.editor = Ext.create(this.editor);
        }
        var ed = this.editor;
        ed.on('beforecomplete', this.onBeforeComplete, this);
        if (Ext.isIE) {
            ed.field.origSetValue = ed.field.setValue;
            ed.field.setValue = Ext.bind(function(v){
                v = v.replace(/<BR\>/g, '\n');
                return this.origSetValue(v);
            }, ed.field);
        }
    },
    getForm: function() {
        var ownerCt = this.ownerCt;
        while (ownerCt && !(ownerCt instanceof Ext.FormPanel)) {
            ownerCt = ownerCt.ownerCt;
        }
        return ownerCt;
    },
    onBeforeComplete: function(t, val, startVal) {
        var opts = Ext.apply({}, this.getForm().baseParams||{});
        opts[this.name] = val;
        this.getForm().api.submit(opts, function(result) {
            if (result.success) {
                this.setValue(result[this.name] || val);
            } else {
                this.setValue(startVal);
            }
        }, this);
    },
    startEdit: function(e, t) {
        if (!this.disabled) {
            this.editor.startEdit(t);
        }
    }
});


Ext.define("Zenoss.EditableTextarea", {
    extend: "Zenoss.EditableField",
    alias: ['widget.editabletextarea'],
    constructor: function(config) {
        config.editor = config.editor || {};
        config.editor.field = Ext.applyIf(config.editor.field||{}, {
            xtype: 'textarea',
            grow: true
        });
        Zenoss.EditableTextarea.superclass.constructor.call(this, config);
    }
});

})();
