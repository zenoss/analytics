/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2016, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/

(function () {

    /**
     * @class Zenoss.quickstart.Wizard.controller.AddSmtpController
     * This is the controller for the last page of the wizard
     * @extends Ext.app.Controller
     */
    Ext.define('Zenoss.quickstart.Wizard.controller.AddSmtpController', {
        models: [],
        views: [
            "AddSmtpView"
        ],
        refs: [{
            ref: 'userForm',
            selector: 'wizardaddsmtpview'
        }],
        extend: 'Ext.app.Controller',
        onFormValidityChange: function (form, isValid) {
            this.getApplication().formValidityChange(isValid);
        },
        init: function () {
            var app = this.getApplication();
            app.on('finish', this.onFinish, this);
            this.control({
                wizardaddsmtpview: {
                    validitychange: this.onFormValidityChange
                }
            });
        },

        onFinish: function () {
            var form = this.getUserForm().getForm();
            if (form.isValid()) {
                var values = form.getValues();
                var params = {
                    smtpHost: values.smtpHost,
                    smtpPort: values.smtpPort,
                    smtpUser: values.smtpUser,
                    smtpPass: values.smtpPass,
                    emailFrom: values.emailFrom,
                    smtpUseTLS: values.smtpUseTLS
                };
                Zenoss.remote.SettingsRouter.setDmdSettings(params);
            }
        }
    });
})();