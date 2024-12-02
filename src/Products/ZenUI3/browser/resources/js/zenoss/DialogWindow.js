/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function(){

Ext.ns('Zenoss', 'Zenoss.dialog');

/**
 * @class Zenoss.dialog.BaseWindow
 * @extends Ext.window.Window
 * A modal window with some defaults. Will auto focus on the first
 * textfield and make the enter key hit submit
 *
 **/
Ext.define("Zenoss.dialog.BaseWindow", {
    extend: "Ext.window.Window",
    alias: ['widget.basewindow'],
    constructor: function(config) {
        config = config || {};
        Ext.applyIf(config, {
            //layout: (Ext.isIE) ? 'form': 'fit',
            plain: true,
            buttonAlign: 'left',
            modal: true,
            constrain: true
        });
        Zenoss.dialog.BaseWindow.superclass.constructor.apply(this, arguments);
    },
    initEvents: function() {
        Zenoss.dialog.BaseWindow.superclass.initEvents.apply(this, arguments);
        this.on('show', this.focusFirstTextField, this);
        this.on('show', this.registerEnterKey, this);
    },
    focusFirstTextField: function() {
        // go through our items and find a text field

        var fields = this.query("textfield");
        if (fields.length) {
            fields[0].focus(false, 300);
        }
    },
    registerEnterKey: function() {
        var km = this.getKeyMap();
        km.on(13, function(){
            var button, el;

            // make sure we are not focused on text areas
            if (document.activeElement) {
                el = document.activeElement;
                if (el.type === "textarea" || el.type === 'button') {
                    return;
                }
            }

            // the button is on the window
            var buttons = this.query("button");
            if (buttons && buttons.length) {
                button = buttons[0];
            }else{
                // the button is on a form
                var forms = this.query('form');
                if (forms) {
                    if (forms.length && forms[0]){
                        var form = forms[0];
                        if (form.query("button").length) {
                            button = form.query("button")[0];
                        }
                    }
                }
            }

            if (button && !button.disabled){
                button.handler(button);
            }
        }, this);

    },
    /**
     * Make sure any dialog appears above loadmasks.
     **/
    show: function() {
        var oldSeed = Ext.WindowManager.zseed;
        Ext.WindowManager.zseed = 20000;
        this.callParent(arguments);
        Ext.WindowManager.zseec = oldSeed;
    }

});



/**
 * @class Zenoss.dialog.BaseDialog
 * @extends Zenoss.dialog.BaseWindow
 * A modal dialog with Zenoss styling. Subclasses should specify a layout.
 * @constructor
 */
Ext.define("Zenoss.dialog.BaseDialog", {
    extend: "Zenoss.dialog.BaseWindow",
    constructor: function(config) {
        Ext.applyIf(config, {
            width: 310,
            closeAction: 'hide',
            buttonAlign: 'left',
            padding: 10,
            autoHeight: true
        });
        this.callParent([config]);
    }
});

function destroyWindow(button) {
    var win = button.up('window');
    if (win){
        return win.destroy();
    }
    if (button.ownerCt !== undefined){
        var container = button.ownerCt.ownerCt;
        if (container.ownerCt !== undefined){
            container.ownerCt.destroy();
        }else{
            container.destroy();
        }
    }
}

/**
 * @class Zenoss.dialog.HideDialogButton
 * @extends Ext.Button
 * A button that destroys its window.
 * @constructor
 */
Ext.define("Zenoss.dialog.DialogButton", {
    ui: 'dialog-dark',
    extend: "Ext.button.Button",
    alias: ['widget.DialogButton'],
    constructor: function(config) {
        var h = config.handler;
        config.handler = h ? Ext.Function.createSequence(h, destroyWindow) : destroyWindow;
        Zenoss.dialog.DialogButton.superclass.constructor.call(this, config);
    },
    setHandler: function(handler, scope) {
        var h = handler ? Ext.Function.createSequence(handler, destroyWindow) : destroyWindow;
        Zenoss.dialog.DialogButton.superclass.setHandler.call(this, h, scope);
    }
});



function hideWindow(button){
    button.ownerCt.ownerCt.hide();
}

/**
 * @class Zenoss.dialog.HideDialogButton
 * @extends Ext.Button
 * A button that hides it's window.
 * @constructor
 */
Ext.define("Zenoss.dialog.HideDialogButton", {
    ui: 'dialog-dark',
    extend: "Ext.button.Button",
    alias: ['widget.HideDialogButton'],
    constructor: function(config) {
        var h = config.handler;
        config.handler = h ? Ext.Function.createSequence(h, hideWindow) : hideWindow;
        Zenoss.dialog.HideDialogButton.superclass.constructor.call(this, config);
    },
    setHandler: function(handler, scope) {
        var h = handler ? Ext.Function.createSequence(handler, hideWindow) : hideWindow;
        Zenoss.dialog.HideDialogButton.superclass.setHandler.call(this, h, scope);
    }

});



Zenoss.dialog.CANCEL = {
    xtype: 'DialogButton',
    text: _t('Cancel')
};

/**
 * @class Zenoss.MessageDialog
 * @extends Zenoss.dialog.BaseDialog
 * A modal dialog window with Zenoss styling and a fit layout.  This window
 * meant to be instantiated once per page, and hidden each time the user
 * closes it.  Includes an OK and Cancel button.
 * @constructor
 */
Ext.define("Zenoss.MessageDialog", {
    extend: "Zenoss.dialog.BaseDialog",
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'fit',
            items: [ {
                xtype: 'label',
                text: config.message,
                ref: 'messagelabel'
                } ],
            buttons: [
                {
                    xtype: 'HideDialogButton',
                    text: _t('OK'),
                    handler: config.okHandler
                }, {
                    xtype: 'HideDialogButton',
                    text: _t('Cancel'),
                    handler: config.cancelHandler
                }
            ]
        });
        Zenoss.MessageDialog.superclass.constructor.call(this, config);
    },
    setText: function(text) {
        this.messagelabel.setText(text);
    }
});

/**
 * @class Zenoss.dialog.SimpleMessageDialog
 * @extends Zenoss.dialog.BaseDialog
 * A modal dialog window with Zenoss styling and a fit layout. No buttons are
 * included
 * @constructor
 */
Ext.define("Zenoss.dialog.SimpleMessageDialog", {
    extend: "Zenoss.dialog.BaseDialog",
    /**
     * message to be displayed on dialog
     * @param {Object} config
     */
    message: null,
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'anchor',
            items: [{
                html: config.message
            },{
                // add a spacer between the text and the buttons so it is not squished together
                height: 10
            }],
            closeAction: 'destroy'
        });
        Zenoss.MessageDialog.superclass.constructor.call(this, config);
    }
});

/**
 * @class Zenoss.FormDialog
 * @extends Zenoss.dialog.BaseWindow
 * A modal dialog window with Zenoss styling and a form layout.  This window
 * meant to be instantiated multiple times per page, and destroyed each time
 * the user closes it.
 * @constructor
 */
Ext.define("Zenoss.FormDialog", {
    extend: "Zenoss.dialog.BaseWindow",
    constructor: function(config) {
        var me = this;

        config = Ext.clone(config) || {};

        config.formListeners = config.formListeners || {};
        Ext.applyIf(config.formListeners, {
            validitychange: function(form, isValid) {
                me.query('DialogButton')[0].setDisabled(!isValid);
            }
        });
        var form = new Ext.form.FormPanel({
            id: config.formId,
            minWidth: 300,
            ref: 'editForm',
            fieldDefaults: {
                labelAlign: 'top'
            },
            autoScroll: true,
            defaults: {
                xtype: 'textfield'
            },
            items: config.items,
            html: config.html,
            listeners: config.formListeners,
            paramsAsHash: true,
            api: config.formApi || {}
        });

        // Remove config properties that don't pertain to the window
        Ext.destroyMembers(config, 'items', 'formApi', 'formId', 'html');

        Ext.applyIf(config, {
            // ie renders window correctly on when layout is set to form
            // this may change in future ext/ie version
            //layout: (Ext.isIE) ? 'form': 'fit',
            plain: true,
            buttonAlign: 'left',
            autoScroll: true,
            width: 375,
            modal: true,
            padding: 10
        });

        Zenoss.FormDialog.superclass.constructor.call(this, config);

        this.add(form);
        this.form = form;
    },

    getForm: function() {
        return this.form;
    }
});


Ext.define("Zenoss.dialog.CloseDialog",{
    extend: "Zenoss.dialog.BaseWindow",
    constructor: function(config) {
        Ext.applyIf(config, {
            width: 310,
            plain: true,
            layout: 'auto',
            buttonAlign: 'left',
            padding: 10,
            modal: true
        });
        Zenoss.dialog.CloseDialog.superclass.constructor.call(this, config);
    }
});


/**
 * @class Zenoss.HideFormDialog
 * @extends Zenoss.dialog.BaseDialog
 * A modal dialog window with Zenoss styling and a form layout.  This window
 * meant to be instantiated once per page, and hidden each time the user
 * closes it.
 * @constructor
 */
Ext.define("Zenoss.HideFormDialog", {
    extend: "Zenoss.dialog.BaseDialog",
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'anchor',
            fieldDefaults: {
                labelAlign: 'top'
            }
        });
        Zenoss.HideFormDialog.superclass.constructor.call(this, config);
    }
});

/**
 * @class Zenoss.SmartFormDialog
 * @extends Zenoss.FormDialog
 * A modal dialog window with Zenoss styling and a form layout.  This window
 * meant to be instantiated once and then thrown away after use.
 *
 * It smartly cleans up it's own form items when "hidden" and provides a better
 * handler mechanism for the callback, returning an object with properties of
 * all form values.
 * @constructor
 */
Ext.define("Zenoss.SmartFormDialog", {
    extend: "Zenoss.FormDialog",
    alias: 'widget.smartformdialog',
    message: '',
    submitHandler: null,
    constructor: function(config) {
        var me = this;
        this.listeners = config.listeners;
        Ext.applyIf(this.listeners, {
            validitychange: function(form, isValid) {
                var btn = me.query("button[ref='buttonSubmit']")[0];
                btn.setDisabled(!isValid);
            }
        });
        Ext.applyIf(config, {
            buttons: [{
                xtype: 'DialogButton',
                text: _t('Submit'),
                disabled: true,
                type: 'submit',
                ref: 'buttonSubmit'
             }, {
                xtype: 'DialogButton',
                ref: 'buttonCancel',
                text: _t('Cancel')
            }],
            modal: true,
            closeAction: 'destroy'
        });

        Zenoss.SmartFormDialog.superclass.constructor.call(this, config);

        if ( config.message || this.message ) {
            this.insert(0, {
                xtype: 'label',
                ref: 'label',
                text: config.message || this.message
            });
        }
    },
    setSubmitHandler: function(callbackFunction) {
        var btn = this.query("button[ref='buttonSubmit']")[0];

        if (callbackFunction === null) {
            btn.setHandler(null);
        }
        else {
            btn.setHandler(Ext.bind(function() {
                var form = this.getForm();
                var values = form.getValues();
                return callbackFunction(values);
            }, this));
        }
    },
    initComponent: function() {
        this.callParent();
        if (this.submitHandler) {
            this.setSubmitHandler(this.submitHandler);
            delete this.submitHandler;
        }
        this.on('show', function() {
            this.getForm().getForm().checkValidity();
        }, this);
    }
});


/**
 * @class Zenoss.dialog.Form
 * @extends Zenoss.dialog.BaseDialog
 * A modal dialog window with Zenoss styling and a form layout.  This window
 * meant to be instantiated once and then thrown away after use.
 *
 * Users provide a configuration 
 *
 * @constructor
 */
Ext.define("Zenoss.dialog.Form", {
    extend: "Zenoss.dialog.BaseDialog",
    alias: "widget.formdialog",
    message: '',
    submitHandler: null,
    constructor: function(config) {
        var dialog = this,
            dialogConfig = Ext.clone(config),
            formConfig = Ext.clone((dialogConfig.form || {}));
        Ext.destroyMembers(dialogConfig, 'form');

        formConfig.defaults = formConfig.defaults || {};
        Ext.applyIf(formConfig.defaults, {
            xtype: 'textfield'
        });
        formConfig.fieldDefaults = formConfig.fieldDefaults || {};
        Ext.applyIf(formConfig.fieldDefaults, {
            labelAlign: 'top'
        });
        formConfig.listeners = formConfig.listeners || {};
        Ext.applyIf(formConfig.listeners, {
            validitychange: function(form, isValid) {
                var btn = dialog.query("button[ref='buttonSubmit']")[0];
                btn.setDisabled(!isValid);
            }
        });
        Ext.applyIf(formConfig, {
            xtype: "form",
            paramsAsHash: true,
            ref: 'editForm'
        });

        Ext.applyIf(dialogConfig, {
            layout: 'fit',
            items: [formConfig],
            dockedItems: [{
                xtype: 'toolbar',
                dock: 'bottom',
                ui: 'footer',
                margin: '15 0 0 0',
                layout: {
                    pack: 'start'
                },
                items: [{
                    xtype: 'DialogButton',
                    ref: 'buttonSubmit',
                    text: _t('Submit'),
                    type: 'submit',
                    formBind: true,
                    disabled: true,
                    handler: function() {
                        var dialog = this.up("formdialog"),
                            form = dialog.down("form");
                        if (dialog.submitHandler) {
                            dialog.submitHandler(form);
                        }
                    }
                 }, {
                    xtype: 'DialogButton',
                    ref: 'buttonCancel',
                    text: _t('Cancel')
                 }]
            }],
            modal: true,
            closeAction: 'destroy',
            plain: true,
            padding: 10
        });
        this.callParent([dialogConfig]);
    }
});


/**
 * @class Zenoss.dialog.ErrorDialog
 * @extends Zenoss.dialog.BaseDialog
 * A modal dialog window with Zenoss styling and a fit layout.
 * @constructor
 */
Ext.define("Zenoss.dialog.ErrorDialog", {
    extend: "Zenoss.dialog.BaseDialog",
    title:_t('Error'),
    message: null,
    constructor: function(config) {
        Ext.applyIf(config, {
            layout: 'fit',
            cls:'errorbox',
            items: [{
                html: config.message,
                buttons: [{
                    xtype: 'DialogButton',
                    text: _t('OK')
                }]
            }],
            closeAction: 'destroy'
        });
         this.callParent([config]);
    },
    initComponent: function(){
        this.callParent(arguments);
        this.show();
    }
});


/**
 * @class Zenoss.HideFitDialog
 * @extends Zenoss.dialog.BaseWindow
 * A modal dialog window with Zenoss styling and a fit layout.
 * @constructor
 */
Ext.define("Zenoss.HideFitDialog", {
    extend: "Zenoss.dialog.BaseWindow",
    constructor: function(config) {
        Ext.applyIf(config, {
            width: 600,
            height: 300,
            closeAction: 'hide',
            plain: true,
            buttonAlign: 'left',
            padding: 10,
            modal: true
        });
        Zenoss.HideFitDialog.superclass.constructor.call(this, config);
    }
});

/**
 * Works in conjunction with Zenoss.dialog.DialogFormPanel. Loads a formPanel
 * with ID diynamic-dialog-panel and submits the form on the panel when the
 * submit button on this dialog is pressed.
 */
Ext.define("Zenoss.dialog.DynamicDialog", {
    extend: "Zenoss.dialog.BaseDialog",
    initEvents: function(){
        Zenoss.dialog.DynamicDialog.superclass.initEvents.call(this);
        this.body.getLoader().on('failure', function(el, response) {
            el.update("Failed to load dialog");
        });
    },
    constructor: function(config) {
        config = Ext.applyIf(config || {}, {
            layout: 'fit',
            modal: true,
            stateful: false,
            closeAction: 'close',
            minHeight: '150',
            buttons: [{
                xtype: 'DialogButton',
                text: _t('Submit'),
                handler: Ext.bind(this.submitHandler, this)
            },{
                xtype: 'DialogButton',
                text: _t('Cancel')
            }]
        });
        Ext.apply(config, {
            id: 'dynamic-dialog'
        });
        Zenoss.dialog.DynamicDialog.superclass.constructor.call(this, config);
    },
    submitHandler: function(b, event){
        var formPanel = Ext.getCmp('dynamic-dialog-panel');
        var form = formPanel.getForm();
        var params = {};
        if (Ext.isDefined(formPanel.submitName) && formPanel.submitName !== null){
            params[formPanel.submitName] = 'OK';
        }
        form.submit({
            params: params,
            success: Ext.bind(function(form, action){
                Zenoss.message.success(_t('{0} finished successfully'), this.title);
            }, this),
            failure: function(form, action){
                Zenoss.message.error(_t('{0} had errors'), this.title);
            }
        });
    }
});

/**
 * Used to create dialogs that will be added dynamically
 */
Ext.define("Zenoss.dialog.DialogFormPanel", {
    extend: "Ext.form.FormPanel",
    alias: ['widget.DialogFormPanel'],
    /**
     * whether or not the result of submitting the form associated with this
     * panel will return a json result. Default true
     */
    jsonResult: true,
    /**
     * extra parameter to send when submitted
     */
    submitName: null,
    /**
     * name of an existing from to be submitted; if not defined a new form
     * will be created.  Primarily used for backwards compatibility so existing
     * dialog forms don't have to be entirely rewritten.
     */
    existingFormId: null,
    constructor: function(config) {
        config = config || {};
        Ext.apply(config, {
            id: 'dynamic-dialog-panel'
        });
        Zenoss.dialog.DialogFormPanel.superclass.constructor.call(this, config);
    },
    /**
     * private; override from base class so that a basic form can be created
     * to point at an existing from if configured and also set a different
     * response reader if expected result from submit is not JSON
     */
    createForm: function(){
        var config = Ext.applyIf({listeners: {}}, this.initialConfig);
        if (!this.jsonResult) {
            config.errorReader = {
                read: function(xhr) {
                    var success = true;
                    //TODO scan result for exceptions/errors
                    if (xhr.status !== 200) {
                        success = false;
                    }
                    return {
                        records: [],
                        success: success
                    };
                }
            };
        }
        var formId = null;
        if (this.existingFormId !== null){
            formId = this.existingFormId;
        }
        return new Ext.form.BasicForm(formId, config);
    }
});



})();
