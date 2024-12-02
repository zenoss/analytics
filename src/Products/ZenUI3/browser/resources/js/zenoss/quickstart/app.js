/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2014, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/
(function(){
    Ext.ns('Zenoss.quickstart.Wizard');

    Zenoss.quickstart.Wizard.wizardSteps = [{
        xtype: 'wizardoutlineview'
    }, {
        xtype: 'wizardadduserview'
    }, {
        xtype: 'wizardautodiscoveryview'
    }, {
        xtype: 'wizardadddeviceview'
    }, {
        xtype: 'wizardaddsmtpview'
    }];
    Zenoss.quickstart.Wizard.controllers = ["OutlineController", "AddUserController", "AutoDiscoveryController", "AddDeviceController", "AddSmtpController"];
    Zenoss.quickstart.Wizard.events = Ext.create('Ext.util.Observable', {});
    Zenoss.quickstart.Wizard.events.addEvents('beforeapplaunch');


    /**
     * Allow zenpacks to add/remove steps
     **/
    Zenoss.quickstart.Wizard.addStep = function(config, position) {
        var steps = Zenoss.quickstart.Wizard.wizardSteps;
        steps = steps.splice(position, 0, config);
    };

    Zenoss.quickstart.Wizard.overrideStep = function(config, position) {
        Zenoss.quickstart.Wizard.wizardSteps[position] = config;
    };

    Zenoss.quickstart.Wizard.removeStep = function(position) {
        delete Zenoss.quickstart.Wizard.wizardSteps[position];
    };


    Zenoss.quickstart.Wizard.addController = function(name, id,  app) {
        var controller = Ext.create(name, {
            application: app,
            id: id
        });
        controller.doInit(app);
        app.controllers.add(controller);
    };

    Ext.application({
        name: 'Zenoss.quickstart.Wizard',
        appFolder: "/++resource++zenui/js/zenoss/quickstart",
        controllers: Zenoss.quickstart.Wizard.controllers,
        currentStep: 0,
        launch: function() {
            Zenoss.quickstart.Wizard.events.fireEvent('beforeapplaunch', this);
            var panel = Ext.create('Ext.Panel', {
                layout: 'anchor',
                anchor: "100% 100%",
                renderTo: 'center_panel',
                style: {
                    padding: "40px"
                },
                items: [{
                    region: 'north',
                    layout: 'vbox',
                    items: [,{
                        id: 'wizard_step_id',
                        html: "<h1> Wizard Steps and outline here </h1>",
                        height: 28
                    },{
                        html: '<hr />',
                        width: "100%",
                    }]
                }, {
                    id: 'wizard_card_panel',
                    region: 'center',
                    layout: 'card',
                    items: Zenoss.quickstart.Wizard.wizardSteps,
                    dockedItems:[{
                        dock: 'bottom',
                        itemId: 'toolbar',
                        baseCls: 'no-grey',
                        cls: 'no-grey',
                        xtype: 'toolbar',
                        items: [{
                            xtype: 'button',
                            hidden: true,
                            itemId: 'doneButton',
                            cls: "btn",
                            disabledCls: "disabled",
                            text: _t('Done'),
                            handler: function() {
                                window.globalApp.doneAddingDevices();
                            }
                        }, {
                            xtype: 'button',
                            hidden: true,
                            itemId: 'previousButton',
                            cls: "btn minor",
                            disabledCls: "disabled",
                            text: _t('« Previous'),
                            handler: function() {
                                window.globalApp.fireEvent('previousstep');
                            }
                        }, {
                            xtype: 'tbfill'
                        }, {
                            xtype: 'button',
                            hidden: true,
                            itemId: 'nextButton',
                            cls: "btn",
                            disabledCls: "disabled",
                            text: _t('Next »'),
                            handler: function() {
                                window.globalApp.fireEvent('nextstep');
                            }
                        }, {
                            xtype: 'button',
                            itemId: 'getStartedButton',
                            cls: "btn big",
                            disabledCls: "disabled",
                            text: _t('Get Started »'),
                            handler: function() {
                                window.globalApp.fireEvent('nextstep');
                            }
                        }, {
                            xtype: 'button',
                            hidden: true,
                            itemId: 'finishButton',
                            cls: "btn",
                            disabledCls: "disabled",
                            text: _t('✔ Finish'),
                            handler: function() {
                                window.globalApp.fireEvent('finish');
                                Zenoss.remote.JobsRouter.quickstartWizardFinished({});
                            }
                        }]
                    }]
                }]
            });

            // resize panel on window resize
            Ext.EventManager.onWindowResize(function(){
                panel.doComponentLayout();
            });
            // set shortcuts for wizard controls
            this.mainPanel = panel;
            this.cardPanel = Ext.getCmp('wizard_card_panel');
            this.titlePanel = Ext.getCmp('wizard_step_id');
            this.previous = this.cardPanel.query('button[itemId="previousButton"]')[0];
            this.next = this.cardPanel.query('button[itemId="nextButton"]')[0];
            this.done = this.cardPanel.query('button[itemId="doneButton"]')[0];
            this.getStarted = this.cardPanel.query('button[itemId="getStartedButton"]')[0];
            this.finish = this.cardPanel.query('button[itemId="finishButton"]')[0];
            this.toolbar = this.cardPanel.getDockedItems()[0];

            // save any GET parameters
            this.params = Ext.Object.fromQueryString(window.location.search);

            // setup the wizard button events
            this.setupEvents();
            this.setTitle();
            this.deepLink();
            window.globalApp = this;
        },
        setupEvents: function() {
            this.addEvents(
                /**
                 * @event finish
                 * Fires when the wizard is finished
                 */
                'finish',
                /**
                 * @event next button pressed
                 * Fires when the next button on the wizard is pressed
                 * @param {integer} The step that you are moving towards
                 */
                'nextstep',
                /**
                 * @event previous button pressed
                 * Fires when the previous button on the wizard is pressed
                 * @param {integer} The page you are about to go to
                 */
                'previousstep');
            this.on('nextstep', this.pressNext, this);
            this.on('previousstep', this.pressPrevious, this);
        },
        /**
         * Sets the H1 title based on the current wizard step
         *
         **/
        setTitle: function() {
            var cardTitle = this.cardPanel.layout.getActiveItem().stepTitle;
            if (this.currentStep > 0 && !this.params.came_from) {
                cardTitle = Ext.String.format("{0} {1}: {2}",
                                          _t("Step"),
                                          this.currentStep,
                                          cardTitle);
            }
            this.titlePanel.update(Ext.String.format("<h1>{0}</h1>", cardTitle));

            // update the window title to reflect the page the user is on
            if (this.params.came_from) {
                var title = document.title.split(":")[0];
                document.title = title + ": " + cardTitle;
            }
        },
        /**
         * This is called when the application is loaded.
         * If we have a history in the URL then go straight to that step, otherwise
         * set the history for the first page.
         **/
        deepLink: function() {
            // called when
            var token = Ext.History.getToken(),
                cardPanel = this.cardPanel,
                i=0,
                me = this;
            if (Ext.isNumeric(token)) {
                token = parseInt(token);
            }

            // if it is not set or 0
            if (token) {
                this.currentStep = token;
                if (Ext.isNumeric(token)) {
                    cardPanel.layout.setActiveItem(this.currentStep);
                } else {
                    // look it up by step id
                    cardPanel.items.each(function(item) {
                        if (item.stepId === token) {
                            cardPanel.layout.setActiveItem(item);
                            me.currentStep = i;
                            return false;
                        }
                        i++;
                    });
                }

                this.updateWizard();
            } else {
                this.updateHistory();
            }
        },
        /**
         * Updates the History token with the current step. It is always assumed to
         * be the number of which step we are on.
         **/
        updateHistory: function() {
            var step = this.currentStep;
            Ext.History.add(step);
        },
        /**
         * This updates both the history and the toolbar buttons
         * based on which step of the wizard we are on.
         * It is expected to be called after the card panel is set
         * and application variable "currentStep" is set;
         **/
        updateWizard: function() {
            var stepCount = this.cardPanel.items.getCount() - 1,
                params = this.params;
            this.setTitle();
            this.updateHistory();

            // we can redirected here to add devices after the user has finished the wizard
            // TODO - more sensible state handling for buttons
            if (params && params.came_from) {
                this.done.show();
                this.next.hide();
                this.previous.hide();
                this.getStarted.hide();
                this.finish.hide();
            }else if (this.currentStep === 0) {
                // they are on the first step
                this.done.hide();
                this.next.hide();
                this.previous.hide();
                this.getStarted.show();
                this.finish.hide();
            }else if (this.currentStep === stepCount) {
                // they are on the last step
                this.done.hide();
                this.next.hide();
                this.previous.show();
                this.getStarted.hide();
                this.finish.show();
            } else {
                // they have more steps to go
                this.done.hide();
                this.next.show();
                this.previous.show();
                this.getStarted.hide();
                this.finish.hide();
            }
        },
        formValidityChange: function(isValid) {
            this.next.setDisabled(!isValid);
            this.finish.setDisabled(!isValid);
        },
        /**
         * Application handler for the previouspressed event
         **/
        pressPrevious:function () {
            var form = this.cardPanel;

            this.currentStep--;

            // set the active page
            form.layout.setActiveItem(this.currentStep);
            this.updateWizard();
        },
        /**
         * Application handler for the nextstep event
         **/
        pressNext:function () {
            var form = this.cardPanel;
            this.currentStep++;

            // set the active page
            form.layout.setActiveItem(this.currentStep);
            this.updateWizard();
        },
        doneAddingDevices: function() {
            var params = this.params;
            window.location = params.came_from;
        }
    });
})();
