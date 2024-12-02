/* jshint boss:true */
(function() {

    var directStoreWorkaroundListeners = {
        beforedestroy: function() {
            // This is to work around a bug in Sencha 4.x:
            // http://www.sencha.com/forum/archive/index.php/t-136583.html?s=0737c51cf4da51fa8cb875c351c5b2b4
            this.bindStore(null);
        },
        afterrender: function(comp, eOpts) {
            // TODO: why does this get called twice?
            this.getStore().load();
        }
    };


    var ZF = Ext.ns('Zenoss.form.rule'),
         unparen=/^\((.*)\)$/,
         nested=/\)( and | or )\(/,
         conjunctions_inverse = {};

    ZF.CONJUNCTIONS = {
        any: {
            text: _t('any'),
            tpl: ' or '
        },
        all: {
            text: _t('all'),
            tpl: ' and '
        }
    };

    var buttons = function(scope) {
        return [{
            xtype: 'button',
            ref: 'buttonAdd',
            iconCls: 'add',
            handler: function() {
                var realowner = scope.ownerCt,
                idx = realowner.items.indexOf(scope);
                var clause = realowner.insert(idx + 1, {
                    xtype: 'ruleclause',
                    nestedRule: scope,
                    builder: scope.getBuilder()
                });
                realowner.doComponentLayout();
                clause.subject.focus();
            },
            scope: scope
        },{
            xtype: 'button',
            ref: 'buttonDelete',
            iconCls: 'delete',
            handler: function() {
                scope.ownerCt.remove(scope, true /* autoDestroy */);
                scope.getBuilder().fireEvent('rulechange', scope);
            },
            scope: scope
        },{
            xtype: 'button',
            ref: 'buttonSubclause',
            iconCls: 'classify',
            handler: function() {
                var realowner = scope.ownerCt,
                idx = realowner.items.indexOf(scope);
                realowner.insert(idx + 1, {
                    xtype: 'nestedrule',
                    ruleBuilder: scope.getBuilder()
                });
                realowner.doComponentLayout();
            },
            scope: scope
        }];
    };

    ZF.CONJUNCTION_STORE = [];
    for (var conjunction in ZF.CONJUNCTIONS) {
        if (ZF.CONJUNCTIONS.hasOwnProperty(conjunction)) {
            var conj = ZF.CONJUNCTIONS[conjunction];
            ZF.CONJUNCTION_STORE.push([conjunction, conj.text]);
            conjunctions_inverse[Ext.String.trim(conj.tpl)] = conjunction;
        }
    }


    /*
     *  The order of the comparisons in the following object matters. The
     *  templates are used to create regular expressions where the {#} substitutions
     *  get replaced with '(.*)'. When loading a clause, the following object
     *  is iterated over and the first matching regular expression gets used to
     *  parse the clause.
     */
    ZF.COMPARISONS = {
        doesnotcontain: {
            text: _t('does not contain'),
            tpl: '{1} not in {0}'
        },
        doesnotstartwith: {
            text: _t('does not start with'),
            tpl: 'not {0}.startswith({1})'
        },
        doesnotendwith: {
            text: _t('does not end with'),
            tpl: 'not {0}.endswith({1})'
        },
        contains: {
            text: _t('contains'),
            tpl: '{1} in {0}'
        },
        startswith: {
            text: _t('starts with'),
            tpl: '{0}.startswith({1})'
        },
        endswith: {
            text: _t('ends with'),
            tpl: '{0}.endswith({1})'
        },
        equals: {
            text: _t('equals'),
            tpl: '{0} == {1}'
        },
        doesnotequal: {
            text: _t('does not equal'),
            tpl: '{0} != {1}'
        },
        lessthan: {
            text: _t('is less than'),
            tpl: '{0} < {1}',
            field: {xtype: 'numberfield'}
        },
        greaterthan: {
            text: _t('is greater than'),
            tpl: '{0} > {1}',
            field: {xtype: 'numberfield'}
        },
        lessthanorequalto: {
            text: _t('is less than or equal to'),
            tpl: '{0} <= {1}',
            field: {xtype: 'numberfield'}
        },
        greaterthanorequalto: {
            text: _t('is greater than or equal to'),
            tpl: '{0} >= {1}',
            field: {xtype: 'numberfield'}
        }
    };
    ZF.COMPARISON_STORE = [];
    var comparison_patterns = {};
    for (var comparison in ZF.COMPARISONS) {
        if (ZF.COMPARISONS.hasOwnProperty(comparison)) {
            var cmp = ZF.COMPARISONS[comparison];
            ZF.COMPARISON_STORE.push([comparison, cmp.text]);
            comparison_patterns[comparison] = new RegExp(
                cmp.tpl.replace('(', '\\(')
                       .replace(')', '\\)')
                       .xsplit(/\{\d+\}/)
                       .join('(.*)'));
        }
    }

    Ext.define("Zenoss.form.rule.RuleClause", {
        alias:['widget.ruleclause'],
        extend:"Ext.Toolbar",
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                cls: 'rule-clause',
                items: [{
                    ref: 'subject',
                    xtype: 'combo',
                    autoSelect: true,
                    allowBlank: false,
                    editable: false,
                    forceSelection: true,
                    triggerAction: 'all',
                    store: [[null,null]],
                    listConfig: {
                        resizable: true,
                        maxWidth:200,
                        maxHeight: 250
                    },
                    getSubject: Ext.bind(function() {
                        return this.getBuilder().subject_map[this.subject.getValue()];
                    }, this),
                    listeners: {
                        change: function() {
                            // when opening a second window this
                            // change fires before the component is rendered
                            if (!this.subject) {
                                return;
                            }
                            // Get the associated subject
                            var subject = this.subject.getSubject(),
                                comparisons = [];
                            this.comparison.reset();
                            // Update comparisons
                            if (subject.comparisons) {
                                Ext.each(subject.comparisons, function(cmp) {
                                    var c = ZF.COMPARISONS[cmp];
                                    if (!c) {
                                        return;
                                    }
                                    comparisons.push([cmp, c.text]);
                                });
                            } else {
                                comparisons = ZF.COMPARISON_STORE;
                            }

                            this.comparison.store.loadData(comparisons);
                            this.comparison.setValue(comparisons[0][0]);
                            this.getBuilder().fireEvent(
                                'rulechange',
                                this
                            );
                        },
                        scope: this
                    }
                },{
                    ref: 'comparison',
                    xtype: 'combo',
                    autoSelect: true,
                    editable: false,
                    allowBlank: false,
                    store: ZF.COMPARISON_STORE,
                    value: ZF.COMPARISON_STORE[0][0],
                    forceSelection: true,
                    triggerAction: 'all',
                    listConfig: {
                        maxWidth:200
                    },
                    listeners: {
                        change: function() {
                            var cmp = ZF.COMPARISONS[this.comparison.getValue()],
                                field = this.subject.getSubject().field || (cmp && cmp.field) || {xtype:'textfield'},
                                idx = Ext.Array.indexOf(this.items.items, this.predicate),
                                oldvalue = this.predicate.getValue(),
                                oldxtype = this.predicate.xtype;
                            this.remove(this.predicate);
                            this.insert(idx, Ext.apply({
                                ref: 'predicate',
                                allowBlank: false,
                                width: 150,
                                listeners: {
                                    change: function() {
                                        this.getBuilder().fireEvent(
                                            'rulechange',
                                            this
                                        );
                                    },
                                    scope: this
                                }
                            }, field));
                            if (typeof oldvalue !== 'undefined' && this.predicate.xtype === oldxtype) {
                                this.predicate.setValue(oldvalue);
                            }
                            this.doComponentLayout();
                            this.getBuilder().fireEvent(
                                'rulechange',
                                this
                            );
                            this.predicate.focus();
                        },
                        scope: this
                    }
                },{
                    ref: 'predicate',
                    xtype: 'textfield',
                    width: 150,
                    listeners: {
                        change: function() {
                            this.getBuilder().fireEvent(
                                'rulechange',
                                this
                            );
                        },
                        scope: this
                    }
                },'->']
            });
            Ext.each(buttons(this), function(btn) {
                config.items.push(btn);
            });
            this.callParent([config]);
            var subjects = this.getBuilder().subject_store;
            this.subject.store.loadData(subjects);
            this.subject.setValue(subjects[0][0]);
            this.on('added', function(){
                this.getBuilder().fireEvent('rulechange', this);
            }, this);
        },
        getValue: function() {
            var comparison = this.comparison.getValue(),
                sub = this.subject.getValue(),
                pred = this.predicate.getValue();
            if (!comparison || !sub || Ext.isEmpty(pred)) { return; }
            var cmp = ZF.COMPARISONS[comparison];
            var clause = Ext.String.format(cmp.tpl, this.getBuilder().prefix + sub, Ext.encode(pred));

            var clause_code = Ext.String.format("({0})", clause);
            if (sub.startsWith(Zenoss.env.ZP_DETAILS_TRIGGER_PREFIX)) {
                // for custom details we add a check to ensure the detail is present
                var replace_text = Zenoss.env.ZP_DETAILS_TRIGGER_PREFIX + '.';
                var detail = sub.replace(replace_text, '');
                var exists_code = Ext.String.format("hasattr({0}, \"{1}\")", Zenoss.env.ZP_DETAILS_TRIGGER_PREFIX, detail);
                clause_code = Ext.String.format("({0} and {1})", exists_code, clause);
            }
            return clause_code;
        },
        setValue: function(expression) {
            var matchOperator = false;

            // If the clause is for a custom zenpack detail, we need to remove
            // the hasattr condition
            if (expression.startsWith("hasattr")) {
                expression = expression.replace(/hasattr.* and /, '');
            }
            for (var cmp in comparison_patterns) {
                if (comparison_patterns.hasOwnProperty(cmp)) {
                    var pat = comparison_patterns[cmp];
                    if (pat.test(expression)) {
                        var vals = pat.exec(expression).slice(1),
                            spots = pat.exec(ZF.COMPARISONS[cmp].tpl).slice(1),
                            sorted = Ext.zip.apply(this, Ext.zip(spots, vals).sort())[1],
                            subject = sorted[0],
                            value = sorted[1],
                            cleansub = subject.replace(
                                new RegExp("^"+this.getBuilder().prefix), '');

                        try {
                            this.subject.setValue(cleansub);
                        } catch(e) {
                            Zenoss.message.warning("Invalid rule '"+ expression +"'. could not find subject '"+ cleansub +"'");
                            return;
                        }

                        this.comparison.setValue(cmp);
                        this.predicate.setValue(Ext.decode(value));
                        matchOperator = true;

                        break;
                    }
                }
            }
            // loop's over but we didn't find a comparison operator
            // that matched :(
            if(!matchOperator){
                Zenoss.message.warning("Invalid rule '"+ expression +"'. Could not match comparison operator");
            }

        },
        getBuilder: function() {
            if (!this.builder) {
                this.builder = this.nestedRule.ruleBuilder || this.findParentByType('rulebuilder', true);
            }
            return this.builder;
        }
    });



    ZF.changeListener = function(me, cmp) {
        var items = this.items.items;

        // If we're somewhere in the middle of initialization don't do anything
        if (items.length===0) {
            return;
        }

        var item = items[0],
            delbtn = item instanceof ZF.NestedRule ?
                     item.items.items[0].buttonDelete :
                     item.buttonDelete;

        // Disable the delete button if only one at this level
        if (items.length===1) {
            delbtn.disable();
        } else if (items.length > 1){
            delbtn.enable();
        }

        // Disable the nested button if it would mean more than 4 deep
        var i = 0, btn;

        while (item = item.findParentByType('nestedrule')) {
            i++;
            if (i>=4) {
                if (btn = cmp.buttonSubclause) {
                    btn.disable();
                }
                break;
            }
        }

    };

    Ext.define("Zenoss.form.rule.NestedRule", {
        alias:['widget.nestedrule'],
        extend:"Ext.Container",
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                showButtons: true,
                cls: 'nested-rule',
                items: [{
                    xtype: 'toolbar',
                    cls: 'rule-clause nested-rule-header',

                    items: [{
                        ref: '../conjunction',
                        xtype: 'combo',
                        width: 60,
                        store: ZF.CONJUNCTION_STORE,
                        editable: false,
                        allowBlank: false,
                        forceSelection: true,
                        triggerAction: 'all',
                        value: 'all',
                        listConfig: {
                            maxWidth:60
                        },
                        listeners: {
                            change: function() {
                                this.getBuilder().fireEvent(
                                    'rulechange',
                                    this
                                );
                            },
                            scope: this
                        }
                    },{
                        xtype: 'label',
                        html: _t('of the following rules:'),
                        style: 'margin-left: 7px; font-size: 12px; color: #444'
                    }]
                },{
                    ref: 'clauses',
                    xtype: 'container',
                    cls: 'rule-clause-container',
                    items: {
                        xtype: 'ruleclause',
                        nestedRule: this
                    },
                    listeners: {
                        add: ZF.changeListener,
                        remove: ZF.changeListener
                    }
                }]
            });
            if (config.showButtons) {
                var items = config.items[0].items;
                items.push('->');
                Ext.each(buttons(this), function(btn) {
                    items.push(btn);
                });
            }
            this.callParent([config]);
        },
        getBuilder: function() {
            if (!this.builder) {
                this.builder = this.findParentByType('rulebuilder', true);
            }
            return this.builder;
        },
        getValue: function() {
            var values = [],
                joiner = ZF.CONJUNCTIONS[this.conjunction.getValue()].tpl,
                result;
            Ext.each(this.clauses.items.items, function(clause) {
                var value = clause.getValue();
                if (value) {
                    values.push(value);
                }
            }, this);
            result = values.join(joiner);
            if (values.length > 1) {
                result = Ext.String.format('({0})', result);
            }
            return result;
        },
        setValue: function(expression) {
            var c, q, i=0, p=0, tokens=[], token=[],
                funcflag=false;
            c = expression.charAt(i);
            var savetoken = function() {
                var v = Ext.String.trim(token.join(''));
                if (v) {
                    tokens.push(v);
                }
                token = [];
            };
            while (c) {
                //token.push(c);
                // Don't deal with contents of string literals
                if (c==='"'||c==='\'') {
                    q = c;
                    token.push(c);
                    for (;;) {
                        i++;
                        c = expression.charAt(i);
                        token.push(c);
                        if (c===q) {
                            // Closing quote
                            break;
                        }
                        if (c === '\\') {
                            // Skip escaped chars
                            i++;
                            token.push(expression.charAt(i));
                        }
                    }
                } else if (c==="("||c===")"){
                    if (p===0) {
                        savetoken();
                    }
                    token.push(c);
                    if (c==='(') {
                        var prev = expression.charAt(i-1);
                        if (i>0 && prev!==' ' && prev!=='(') {
                            funcflag = true;
                        } else {
                            p++;
                        }
                    } else if (c===')') {
                        if (funcflag) {
                            funcflag = false;
                        } else {
                            p--;
                        }
                    }
                    if (p===0) {
                        savetoken();
                    }
                } else {
                    token.push(c);
                }
                i++;
                c = expression.charAt(i);
            }
            savetoken();

            if (tokens) {
                this.clauses.removeAll();
                var conjunction, rule;

                Ext.each(tokens, function(t) {
                    if (t) {
                        if (conjunction = conjunctions_inverse[t]){
                             this.conjunction.setValue(conjunction);
                             return;
                        } else if (nested.test(t)) {
                            // Nested rule
                            rule = this.clauses.add({xtype:'nestedrule', ruleBuilder: this.ruleBuilder});
                        } else {
                            // Clause
                            rule = this.clauses.add({xtype: 'ruleclause', nestedRule: this});
                        }
                        var clause = t;
                        try {
                            clause = unparen.exec(t)[1];
                        } catch(ignored) {}
                        rule.setValue(clause);
                    }
                }, this);
            }
        }
    });



    Ext.define("Zenoss.form.rule.RuleBuilder", {
        alias:['widget.rulebuilder'],
        extend:"Ext.form.FieldContainer",
        constructor: function(config) {
            config = Ext.applyIf(config||{}, {
                cls: 'rule-builder',
                prefix: '',
                items: [{
                    ref: 'rootrule',
                    xtype: 'nestedrule',
                    showButtons: false,
                    ruleBuilder: this
                }]
            });
            this.subject_store = [];
            this.subject_map = {};
            Ext.each(config.subjects, function(subject) {
                if (!Ext.isObject(subject)) {
                    subject = {value: subject};
                }
                this.subject_store.push([subject.value, subject.text || subject.value]);
                this.subject_map[subject.value] = subject;
            }, this);
            this.callParent([config]);
            this.addEvents('rulechange');
        },
        getValue: function() {
            var result = this.rootrule.getValue();
            if (result && nested.test(result)) {
                // There will be one extra paren set wrapping the clause as a
                // whole that is hard to prevent earlier than this; don't save
                // it, as it will be treated as an unnecessary nested rule
                result = unparen.exec(result)[1];
            }
            return result;
        },
        setValue: function(expression) {
            if (!expression) {
                this.reset();
            } else {
                this.rootrule.setValue(expression);
            }
            this.doComponentLayout();
        },
        reset: function() {
            this.rootrule.clauses.removeAll();
            this.rootrule.clauses.add({
                xtype: 'ruleclause',
                nestedRule: this.rootrule,
                builder: this
            });
        }
    });

    Ext.define("Zenoss.form.rule.DeviceCombo",{
            extend: "Zenoss.form.SmartCombo",
            alias: ["widget.rule.devicecombo"],
            constructor: function(config){
                config = Ext.applyIf(config || {}, {
                    queryMode: 'remote',
                    directFn: Zenoss.remote.DeviceRouter.getDeviceUuidsByName,
                    root: 'data',
                    model: 'Zenoss.model.BasicUUID',
                    remoteFilter: true,
                    minChars: 3,
                    typeAhead: true,
                    valueField: 'uuid',
                    displayField: 'name',
                    forceSelection: true,
                    triggerAction: 'all',
                    editable: true,
                    autoLoad: false
                });
                this.callParent([config]);
            },

            setValue: function() {
                var uuid = arguments[0];
                // uuid can be undefined, an empty string, a string containing the uuid,
                // or a BasicUUID object.  Force a reload if it is a uuid-containing string
                // and the corresponding device is not already in the combobox dropdown.
                if (uuid && Ext.isString(uuid)) {
                    this.getStore().setBaseParam("uuid", uuid);
                    if (this.getStore().getById(uuid) === null) {
                        this.getStore().load();
                    }
                }
                return this.callParent(arguments);
            }
        }
    );


    ZF.STRINGCOMPARISONS = [
        'contains',
        'doesnotcontain',
        'startswith',
        'doesnotstartwith',
        'endswith',
        'doesnotendwith',
        'equals',
        'doesnotequal'
    ];

    ZF.NUMBERCOMPARISONS = [
        'equals',
        'doesnotequal',
        'lessthan',
        'greaterthan',
        'lessthanorequalto',
        'greaterthanorequalto'
    ];

    ZF.IDENTITYCOMPARISONS = [
        'equals',
        'doesnotequal'
    ];

    ZF.LISTCOMPARISONS = [
        'contains',
        'doesnotcontain'
    ];


    Ext.apply(ZF, {
        EVENTSEVERITY: {
            text: _t('Severity'),
            value: 'severity',
            comparisons: ZF.NUMBERCOMPARISONS,
            field: {
                xtype: 'combo',
                queryMode: 'local',
                valueField: 'value',
                displayField: 'name',
                typeAhead: false,
                forceSelection: true,
                triggerAction: 'all',
                listConfig: {
                    maxWidth:200
                },
                store: new Ext.data.ArrayStore({
                    model: 'Zenoss.model.NameValue',
                    data: [[
                        _t('Critical'), 5
                    ],[
                        _t('Error'), 4
                    ],[
                        _t('Warning'), 3
                    ],[
                        _t('Info'), 2
                    ],[
                        _t('Debug'), 1
                    ],[
                        _t('Clear'), 0
                    ]]
                })
            }
        },
        PRODUCTIONSTATE: {
            text: _t('Production state'),
            value: 'productionState',
            field: {
                xtype: 'ProductionStateCombo',
                listConfig: {
                    maxWidth:200
                }
            },
            comparisons: ZF.NUMBERCOMPARISONS
        },
        DEVICEPRIORITY: {
            text: _t('Device priority'),
            value: 'priority',
            field: {
                xtype: 'PriorityCombo',
                listConfig: {
                    maxWidth:200
                }
            },
            comparisons: ZF.NUMBERCOMPARISONS
        },
        DEVICE: {
            text: _t('Device'),
            value: 'device_uuid',
            comparisons: ZF.IDENTITYCOMPARISONS,
            field: {
                xtype: 'rule.devicecombo',
                listConfig: {
                    maxWidth:200
                }
            }
        },
        DEVICECLASS: {
            text: _t('Device Class'),
            value: 'dev.device_class',
            comparisons: ZF.STRINGCOMPARISONS,
            field: {
                xtype: 'smartcombo',
                defaultListConfig: {
                    maxWidth:200
                },
                fields: ['name'],
                directFn: Zenoss.remote.DeviceRouter.getDeviceClasses,
                root: 'deviceClasses',
                listeners: directStoreWorkaroundListeners,
                typeAhead: true,
                editable: true,
                valueField: 'name',
                displayField: 'name',
                forceSelection: true
            }
        },
        SYSTEMS: {
            text: _t('Systems'),
            value: 'dev.systems',
            comparisons: ZF.LISTCOMPARISONS,
            field: {
                xtype: 'smartcombo',
                defaultListConfig: {
                    maxWidth:200
                },
                directFn: Zenoss.remote.DeviceRouter.getSystems,
                root: 'systems',
                fields: ['name'],
                listeners: directStoreWorkaroundListeners,
                typeAhead: true,
                editable: true,
                valueField: 'name',
                displayField: 'name',
                forceSelection: false
            }
        },
        DEVICEGROUPS: {
            text: _t('Device Groups'),
            value: 'dev.groups',
            comparisons: ZF.LISTCOMPARISONS,
            field: {
                xtype: 'smartcombo',
                defaultListConfig: {
                    maxWidth:200
                },
                directFn: Zenoss.remote.DeviceRouter.getGroups,
                root: 'groups',
                fields: ['name'],
                listeners: directStoreWorkaroundListeners,
                typeAhead: true,
                editable: true,
                valueField: 'name',
                displayField: 'name',
                forceSelection: false
            }
        }
    });
})();
