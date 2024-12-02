/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    var router = Zenoss.remote.UsersRouter;
    /**
     * @class Zenoss.quickstart.Wizard.controller.AddUserController
     * This is the controller for the first page of the wizard
     * @extends Ext.app.Controller
     */
    Ext.define('Zenoss.quickstart.Wizard.controller.AddUserController', {
        models: [],
        views: [
            "AddUserView"
        ],
        refs: [{
            ref: 'userForm',
            selector: 'wizardadduserview'
        }],
        extend: 'Ext.app.Controller',
        init: function() {
            this.control({
                'wizardadduserview': {
                    validitychange: this.onFormValidityChange,
                    show: this.onFormShow,
                    afterrender: function(form, opts){
                        form.keyNav = Ext.create("Ext.util.KeyNav", form.el, {
                            enter: function(){
                                // only move to next step if form is valid
                                if(form.isValid()){
                                    window.globalApp.fireEvent('nextstep');
                                }
                            },
                            scope: this
                        });
                    }
                }
            });
            var app = this.getApplication();
            app.on('finish', this.onFinish, this);
        },
        onFormValidityChange: function(form, isValid) {
            this.getApplication().formValidityChange(isValid);
        },
        onFormShow: function(form) {
            // See if the form is blank without triggering validation so the
            // user isn't presented with a blank form full of red fields.
            var values = form.getForm().getFieldValues();
            if (Ext.isEmpty(values.username)) {
                this.getApplication().formValidityChange(false);
            }
            // focus on the first input
            Ext.getCmp('admin-password1').focus();
        },
        /**
         * When we finish the wizard we need to do the following
         * 1. mark the wizard as finished
         * 2. save the admin password
         * 3. create the admin user
         * 4. log in as that user.
         *
         * To account for errrors we have to "chain" the methods.
         **/
        onFinish: function() {
            this.markWizardAsFinished();
        },
        markWizardAsFinished: function() {
            router.markWizardAsFinished({}, function(response){
                if (response.success) {
                    this.createAdminUser();
                }
            }, this);
        },
        createAdminUser: function() {
            var values = this.getUserForm().getForm().getFieldValues(),
                params = {
                    id: values.username,
                    password: values.password1,
                    email: values.emailAddress,
                    roles: ['ZenManager', 'Manager']
                };
            if (params.id) {
                router.addUser(params, function(response) {
                    if (response.success) {
                        this.saveAdminPassword();
                        this.loginAsUser();
                    }
                }, this);
            } else {
                // will redirect to step 0
                window.location = '';
            }
        },
        saveAdminPassword: function() {
            var values = this.getUserForm().getForm().getFieldValues(),
                newPassword = values['admin-password1'];
            router.setAdminPassword({
                newPassword: newPassword
            });
        },
        loginAsUser: function() {
            // this effectively ends the wizard
            var values = this.getUserForm().getForm().getFieldValues();

            // these are defined in a hidden form on quickstart.pt
            Ext.get('login_username').dom.value = values.username;
            Ext.get('login_password').dom.value = values.password1;
            // redirect to the dashboard when they are finished
            Ext.get('came_from').dom.value = '/zport/dmd/Dashboard';
            Ext.get('loginform').dom.submit();

        }
    });
})();
