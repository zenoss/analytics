(function() {
     Ext.namespace('Zenoss.form.Alias');

     /**
      * When you press the "Add" button this will add a new
      * alias row to the panel.
      **/
     function addAliasRow() {
         var cmp = that,
             button = Ext.getCmp('add_alias_button');

         cmp.remove(button);
         cmp.add(getRowTemplate());
         cmp.add(addAliasButton);
         cmp.doLayout();
     }

     /**
      * Variable Definitions
      **/
     var addAliasButton = {
         id: 'add_alias_button',
         xtype: 'button',
         ui: 'dialog-dark',
         text: 'Add',
         handler: addAliasRow
     },
     that;

     /**
      * Returns the panel definition for the id/formula row
      **/
     function getRowTemplate(id, formula) {
         return {
             xtype: 'container',
             bodyCls: 'alias',
             layout: 'hbox',
             items: [{
                 aliasType: 'id',
                 xtype: 'textfield',
                 width:'150',
                 value: id,
                 regex: /^[^\s]+$/,
                 maxLength: 30
             },{
                 aliasType: 'formula',
                 xtype: 'textfield',
                 width:'150',
                 style: {'margin-left':'10px;'},
                 value: formula
             },{
                 xtype: 'button',
                 ui: 'dialog-dark',
                 text: 'Delete',
                 width: '10',
                 style: {'margin-left':'10px;'},
                 handler: function() {
                     var container = this.findParentByType('container'),
                         cmp = that;
                     cmp.remove(container);
                     cmp.doLayout();
                 }
             }]
        };
     }

     /**
      * Alias Panel. NOTE: This control is designed to have
      * only one instance per page.
      **/
     Ext.define("Zenoss.form.Alias", {
         alias:['widget.alias'],
         extend:"Ext.Panel",
         constructor: function(config) {
             var aliases = config.record.aliases,
             items = [],
             i,
             alias;
             // use "that" as a closure so we have a reference to it
             that = this;
             items.push({
                xtype: 'panel',
                layout: 'anchor',
                html: _t('Alias:<br>ID / FORMULA')
             });
             config = config || {};
             // add a row for each alias defined
             for (i=0; i < aliases.length; i++) {
                 alias = aliases[i];
                 items.push(getRowTemplate(alias.name, alias.formula));
             }
             // always show an extra blank row
             items.push(getRowTemplate());

             // add the button
             items.push(addAliasButton);
             Ext.applyIf(config, {
                 items:items
             });

             Zenoss.form.Alias.superclass.constructor.apply(this, arguments);
         },

         /**
          * This returns a list of all of the  aliases in object form.
          * Since this is a Panel it must explicitly be called.
          * Ex:
          *    Ext.getCmp('aliasId').getValue();
          **/
         getValue: function(){
             var cmp = that,
                 textfields = cmp.query('textfield'),
                 results = [],
                 i, field;

             // initialize the return structure. We want an array of object literals
             // (will be dicts in python)
             for (i = 0; i < textfields.length / 2; i++ ) {
                 results[i] = {};
             }

             // turn each entry into an object literal with the properties
             // id and formula
             for (i = 0; i < textfields.length; i++ ) {
                 field = textfields[i];

                 // aliasType was defined on the dynamically created rows above
                 results[Math.floor(i/2)][field.aliasType] = field.getValue();
             }

             return results;
         }
     });

}());
