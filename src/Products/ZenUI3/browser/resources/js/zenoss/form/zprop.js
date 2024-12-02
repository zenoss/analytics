/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


/*
A widget that handles the fact that zProperties can be acquired from parents
in the dmd object hierarchy. The strategy is to use a field set. The title of
the field set is a friendly name for the zProperty (not the z* name). Inside
the field set are two lines. The user selects a line as being the active
setting by clicking on the radio button at the beginning of the row. The top
line has a label that reads 'Set Local Value:', and an appropriate widget for
the type of the zProp (checkbox, textfield, numberfield, or combobox). The 2nd
line states 'Inherit Value' and then indicates the acquired value and the path
of the ancestor from which the value is acquired.

Example usage:

var zMonitor = Ext.create({
    xtype: 'zprop',
    name: 'zMonitor',
    title: _t('Is Monitoring Enabled?'),
    localField: {
        xtype: 'select',
        model: 'local',
        store: [[true, 'Yes'], [false, 'No']],
        value: true
    }
});

zMonitor.setValues({
    isAcquired: false,
    localValue: false,
    acquiredValue: 'No',
    ancestor: '/Processes/Apache'
});

*/

(function() {

Ext.ns('Zenoss.form');


/* A radio button that allows for the boxLabel to be updated.
 */
Ext.define("Zenoss.form.Radio", {
    extend: "Ext.form.Radio",
    alias: ['widget.zradio'],

    setBoxLabel: function(boxLabel) {
        if (this.rendered) {
            this.boxLabel = boxLabel;
            this.boxLabelEl.update(boxLabel);
        } else {
            this.boxLabel = boxLabel;
        }
    }

});

/* A hidden field used internally by the ZProperty fieldset. This hidden field
   overrides getValue to return an object with isAcquired and localValue.
   Introduces the zpropFieldSet config prop which is a reference to the
   ZProperty field set.
 */
Ext.define("Zenoss.form.ZPropHidden", {
    extend: "Ext.form.Hidden",
    alias: ['widget.zprophidden'],

    getValue: function() {
        return {
            isAcquired: this.zpropFieldSet.acquiredRadio.getValue(),
            localValue: this.zpropFieldSet.localField.getValue(),

            // acquiredValue and ancestor aren't needed by the server, but it
            // is needed by reset which is called when the form is submitted
            acquiredValue: this.zpropFieldSet.acquiredValue,
            ancestor: this.zpropFieldSet.ancestor
        };
    },
    getRawValue: function() {
        return this.getValue();
    },
    setValue: function(values) {
        this.zpropFieldSet.setValues(values);
    },

    isDirty: function() {
        return this.zpropFieldSet.acquiredRadio.isDirty() || this.zpropFieldSet.localField.isDirty();
    }

});




/*
A field set that represents a zProperty.

The config parameter passed into the constructor must have a ref. The refOwner
must be the FormPanel.

Additional config keys:
    localField - config for the Ext.form.Field used to input a local setting
    name - string that that is submited to the server as the name

New public method:
    setValues - upon context change in the client code, set all the values
                of this composite widget
 */
Ext.define("Zenoss.form.ZProperty", {
    extend: "Ext.form.FieldSet",
    alias: ['widget.zprop'],

    constructor: function(config) {
        Ext.applyIf(config, {
            hideLabels: true,
            hideBorders: true,
            border:false,
            defaults:{border:false},
            items: [
                this.getLocalRadioConfig(config.localField),
                this.getAcquiredRadioConfig(),
                this.getHiddenFieldConfig(config.name)
            ]
        });
        Zenoss.form.ZProperty.superclass.constructor.call(this, config);
    },
    setValues: function(values) {
        // values has isAcquired, localValue, acquiredValue, and ancestor
        // localValue is the appropriate type
        // acquiredValue is always a string

        // setting the values this away marks the form clean and disables the
        // submit and cancel buttons

        if (!values) {
            return;
        }
        var basicForm = this.refOwner.getForm();
        basicForm.setValues([
            {id: this.localRadio.getName(), value: !values.isAcquired},
            {id: this.localField.getName(), value: values.localValue},
            {id: this.acquiredRadio.getName(), value: values.isAcquired}
        ]);

        // update the boxLabel with the acquiredValue and ancestor
        var boxLabel;
        if ( values.acquiredValue !== null && values.ancestor !== null ) {
            boxLabel = Ext.String.format('Inherit Value "{0}" from {1}', values.acquiredValue, values.ancestor);
            this.acquiredRadio.enable();
        } else {
            boxLabel = Ext.String.format('Inherit Value');
            this.acquiredRadio.disable();
        }
        this.acquiredRadio.setBoxLabel(boxLabel);
        this.acquiredValue = values.acquiredValue;
        this.ancestor = values.ancestor;
    },

    // private
    getHiddenFieldConfig: function(name) {
        return {
            xtype: 'zprophidden',
            name: name,
            zpropFieldSet: this
        };
    },

    // private
    getAcquiredRadioConfig: function() {
        return {
            xtype: 'zradio',
            ref: 'acquiredRadio',
            boxLabel: 'Inherit Value',
            scope: this,
            anchor: '75%',
            handler: function(acquiredRadio, checked) {
                this.localRadio.setValue(!checked);
            }
        };
    },

    //private
    getLocalRadioConfig: function(localField) {
        return {
            xtype: 'panel',
            layout: 'column',
            hideBorders: true,
            border:false,
            defaults: {
                xtype: 'panel',
                layout: 'anchor',
                border:false,
                hideLabels: true
            },
            items: [{
                width: 130,
                items: [{
                    xtype: 'radio',
                    ref: '../../localRadio',
                    boxLabel: _t('Set Local Value:'),
                    checked: true,
                    scope: this,
                    handler: function(localRadio, checked) {
                        this.acquiredRadio.setValue(!checked);
                    }
                }]
            }, {
                columnWidth: 0.94,
                items: [
                    // Set submitValue to false in case localField has a name
                    Ext.apply(localField, {
                        ref: '../../localField',
                        submitValue: false,
                        anchor: '75%',
                        listeners: {
                            scope: this,
                            focus: function() {
                                this.localRadio.setValue(true);
                            }
                        }
                    })
                ]
            }]
        };
    }

});

// A simple ComboBox that behaves like an HTML select tag
Ext.define("Zenoss.form.Select", {
    extend: "Ext.form.ComboBox",
    alias: ['widget.select'],

    constructor: function(config){
        Ext.applyIf(config, {
            allowBlank: false,
            triggerAction: 'all',
            typeAhead: false,
            forceSelection: true
        });
        Zenoss.form.Select.superclass.constructor.call(this, config);
    }

});

})();
