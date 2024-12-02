/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){

    /**
     * Add a vtype for "form fields must match"
     **/
    Ext.apply(Ext.form.VTypes, {
        password: function(val, field) {
            // If the password field has initialPassField (2nd box), do a comparison.
            if (field.initialPassField) {
                var pwd = Ext.getCmp(field.initialPassField);
                if (val !== pwd.getValue()){
                    Ext.form.VTypes["passwordText"] = _t("The passwords you've typed don't match.");
                    return false;
                }
            }
            // Validate the validity of the password field (either of them)
            var pattern = new RegExp("(?=.*\\d)(?=.*[a-z])(?=.*[A-Z]).{8,}");
            if (!val.match(pattern)){
                Ext.form.VTypes["passwordText"] = _t("Password does not meet password rules");
                return false;
            }
            return true;
        }

    });
    /**
     * @class Zenoss.quickstart.Wizard.view.AddUserView
     * @extends Ext.panel.Panel
     * @constructor
     *
     */
    Ext.define('Zenoss.quickstart.Wizard.view.AddUserView', {
        extend: 'Ext.form.Panel',
        alias: 'widget.wizardadduserview',
        stepTitle: _t('Setup Users'),
        constructor: function(config) {
            config = config || {};
            Ext.applyIf(config, {
                labelWidth: 100,
                frame: false,
                border: false,
                layout: {
                    type: 'hbox'
                },
                defaults: {
                    layout: 'anchor',
                    frame: false,
                    width: "50%",
                    border: false,
                    style: {
                        padding: "25px"
                    }
                },
                items: [{
                    xtype: 'fieldset',
                    border: false,
                    layout: 'anchor',
                    defaultType: 'textfield',
                    defaults: {
                        anchor: '95%',
                        labelAlign: 'top',
                        padding: "0 0 7px 0"
                    },
                    title: _t("Set admin password"),
                    items: [{
                        xtype: 'panel',
                        frame: false,
                        border: false,
                        cls: 'helptext',
                        html: _t("\
                            The admin account has extended privileges,\
                            similar to Linux's <span class='noem'>root</span>\
                            or Windows' <span class='noem'>Administrator</span>.\
                            Its use should be limited to administrative tasks.\
                            <br><br>\
                            <strong>Password Must:</strong><br>\
                            <ul class='list'>\
                                <li>Contain 8 or more characters</li>\
                                <li>Contain at least one number</li>\
                                <li>Contain at least one upper and lower case character</li>\
                            </ul>\
                        ")
                    },{
                        fieldLabel: _t('Admin password'),
                        inputType: 'password',
                        vtype: 'password',
                        name: 'admin-password1',
                        id: 'admin-password1',
                        allowBlank: false
                    },{
                        fieldLabel: _t('Confirm password'),
                        inputType: 'password',
                        vtype: 'password',
                        name: 'admin-password2',
                        initialPassField: 'admin-password1',
                        allowBlank: false,
                        msgTarget: 'under'
                    }]
                },{
                    xtype: 'fieldset',
                    border: false,
                    layout: 'anchor',
                    defaults: {
                        anchor: '95%',
                        labelAlign: 'top',
                        padding: "0 0 7px 0"
                    },
                    id: 'userfieldset',
                    defaultType: 'textfield',
                    title: _t("Create your account"),
                    items: [{
                        xtype: 'panel',
                        frame: false,
                        border: false,
                        cls: 'helptext',
                        html: _t("Enter information for your personal user "+
                            "account. You'll use this to perform "+
                            "most tasks.")
                    },{
                        context: '/zport/dmd/ZenUsers',
                        xtype: 'idfield',
                        id: 'username',
                        fieldLabel: _t('Username'),
                        name: 'username',
                        allowBlank: false
                    },{
                        fieldLabel: _t('Password'),
                        inputType: 'password',
                        vtype: 'password',
                        name: 'password1',
                        id: 'password1',
                        allowBlank: false
                    },{
                        fieldLabel: _t('Retype password'),
                        inputType: 'password',
                        vtype: 'password',
                        name: 'password2',
                        initialPassField: 'password1',
                        allowBlank: false,
                        msgTarget: 'under'
                    },{
                        fieldLabel: _t('Your email'),
                        vtype: 'email',
                        name: 'emailAddress',
                        allowBlank: true
                    }]
                }]
            });
            this.callParent([config]);
        }
    });




})();
