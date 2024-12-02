/*****************************************************************************
 *
 * Copyright (C) Zenoss, Inc. 2010, all rights reserved.
 *
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 *
 ****************************************************************************/


(function() {

Ext.ns('Zenoss.form');

Ext.define("Zenoss.form.IDField", {
    alias: ['widget.idfield'],
    extend: "Ext.form.TextField",
    anchor:'80%',
    /*
    * Context on which to check for id validity. Defaults to
    * Zenoss.env.PARENT_CONTEXT.
    */
    context: null,
    /*
    * Limit characters to those accepted by ObjectManager
    */
    maskRe: /[a-zA-Z0-9-_~,.$\(\)# @]/,
    _serverIsValid: false,
    /*
    * Validator function that makes a request to the parent context and calls
    * the checkValidId method.
    */
    validator: function(value) {
        var context = this.context || Zenoss.env.PARENT_CONTEXT;

        // Don't bother with empty values
        if (Ext.isEmpty(value)) {
            return true;
        }
        // if the value has not changed do not send an ajax request
        if(typeof this._previousValue !== 'undefined'){
            if (value === this._previousValue) {
                return this.reportResponse(this._previousResponseText);
            }
        }
        this._previousValue = value;

        if (this.vtransaction) {
            Ext.Ajax.abort(this.vtransaction);
        }
        function callback(response) {
            this._previousResponseText = response.responseText;
            return this.reportResponse(response.responseText);
        }
        this.vtransaction = Ext.Ajax.request({
            url: context + '/checkValidId?id='+value,
            method: 'GET',
            success: callback,

            failure: function(response) {
                this.markInvalid(_t('That name is invalid or is already in use.'));
                this.fireEvent('validitychange', this, false);
            },
            scope: this
        });
        return true;
    },
    validate: function() {
        var result = this.callParent(arguments);
        return result && this._serverIsValid;
    },
    /**
    * Interprets a response from the server to determine if this field is valid.
    **/
    reportResponse: function(responseText) {
        if (responseText === "True") {
            this.fireEvent('validitychange', this, true);
            this._serverIsValid = true;
            return true;
        }
        // the server responds with a string of why it is invalid
        this._serverIsValid = false;
        this.markInvalid(
            _t('That name is invalid: ') + ' ' + responseText
        );

        // let any event listeners know that we are invalid
        this.fireEvent('validitychange', this, false);

        return false;
    }
});

})();
