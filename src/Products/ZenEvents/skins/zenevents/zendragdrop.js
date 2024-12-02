var Class = {
    create:function(){
        return function(){
            this.__init__.apply(this,arguments);
        }
    }
}

Function.prototype.bind = function(obj){
    var method=this;
    temp=function(){
        return method.apply(obj,arguments);
    }
        return temp;
}

var nodeHash = function(node) {
    var a = node.attributes;
    var r = {};
    for (i=0;i<a.length;i++) {
        if (isEmpty(a[i].nodeValue)) continue;
        r[a[i].localName] = a[i].nodeValue;
    }
    return r;
}

var getSelected = function(node) {
    var options = iter(node.getElementsByTagName('option'));
    var isSel = function(obj) { return obj.selected }
    var r = ifilter(isSel, options);
    return list(r);
}

ZenHiddenSelect = Class.create();
ZenHiddenSelect.prototype = {
    __init__: function(obj) {
        this.obj = obj;
    },
    values: function() {
        return this.obj.value.split('\n');
    },
    update: function(vals) {
        var opts = vals.getElementsByTagName('li');
        var getText = function(li) {
            var x = li.innerHTML.replace(/<span.*<\/span>/,'');
            return x;
        }
        var strs = map(getText, opts);
        this.obj.innerHTML = strs.join('\n');
    },
    toUL: function() {
        var options = this.values();
        var atts = nodeHash(this.obj);
        atts['class'] = 'sortable_list resultfields';
        var ul = UL(atts,
                    map(this.toLI, options));
        return ul;
    },
    toLI: function(val) {
        var atts = {'id':'li_' + val,'class':'sortable_item resultfields'};
        if (val.length) {
            var li = LI(atts, val);
            return li;
        } else {
            return;
        }
    }
}

ZenULSelect = Class.create();
ZenULSelect.prototype = {
    __init__: function(obj) {
        this.obj = obj;
        this.ul = obj.toUL();
        insertSiblingNodesAfter(this.obj.obj, this.ul);
        this.obj.obj.style.height="0";
        this.obj.obj.style.border="0";
        this.obj.obj.style.padding="0";
        this.obj.obj.style.visiblity = 'hidden';
    }
}

ZenDragDropList = Class.create();
ZenDragDropList.prototype = {
    // Pass a textarea of selected and a ul of possibles
    __init__: function(ta, ul) { 
        ta = $(ta);
        ul = $(ul);
        this.hiddenselect = new ZenHiddenSelect(ta);
        this.fields = ul;
        var toggleme = function(){
            toggle(this.fields.parentNode,'appear',{duration:0.2});
            var x = this.toggle.innerHTML=="Add Fields";
            this.toggle.innerHTML = x?"Hide Fields":"Add Fields";
        }
        this.toggle = DIV({'style':'float:left;width:8em;text-align:center;'+
                             'padding:1em;color:darkgrey;cursor:pointer;'
                             },
                             "Add Fields");
        _cfg = {'valign':'top'};
        cell1 = TD(_cfg, null);
        cell2 = TD(_cfg, null);
        cell3 = TD(_cfg, null);
        this.table = TABLE(null, [
            TR(null, [
                cell1,
                cell2,
                cell3
            ])
        ]);
        hideElement(this.fields.parentNode);
        connect(this.toggle, 'onclick', bind(toggleme, this));
        this.s = new ZenULSelect(this.hiddenselect); 
        appendChildNodes(ta.parentNode, this.table);
        appendChildNodes(cell3, this.fields.parentNode);
        appendChildNodes(cell2, this.toggle);
        appendChildNodes(cell1, [$('ultitle'), this.s.ul]);
        setElementDimensions(this.fields, getElementDimensions(this.s.ul));
        this.addXspan(this.s.ul);
        this.sortable1 = MochiKit.Sortable.Sortable.create(this.s.ul,
        {onUpdate:bind(this.newField, this),
         dropOnEmpty:true,
         containment:[this.s.ul, this.fields],
         constraint:false,
         scroll:true
         //ghosting:true
         });
        this.sortable2 = MochiKit.Sortable.Sortable.create(this.fields,
        {dropOnEmpty:true,
         containment:[this.s.ul, this.fields],
         constraint:false
         //ghosting:true
        });
    },
    addXspan: function(ul) {
        var childs = ul.getElementsByTagName('li');
        for (i=0;i<childs.length;i++) {
            var xspan = SPAN({'style':'position:absolute;right:0;color:grey;'+
                              'cursor:pointer;font-size:smaller;font-weight:normal;'
                              }, "X");
            appendChildNodes(childs[i], xspan);
            connect(xspan, 'onclick', bind(this.removeField, this, childs[i]));
        }
    },
    addSingleX: function(li) {
        var xspan= SPAN({'style':'position:absolute;right:0;color:grey;'+
                         'cursor:pointer;font-size:smaller;font-weight:normal;'
                        }, "X");
        appendChildNodes(li, xspan);
        connect(xspan, 'onclick', bind(this.removeField, this, li));
    },
    removeXspan: function(li) {
        var x = li.getElementsByTagName('span')[0];
        removeElement(x);
    },
    newField: function() {
        this.s.obj.update.bind(this.s.obj)(this.s.ul);
        var lis = this.s.ul.getElementsByTagName('li');
        for (i=0;i<lis.length;i++) {
            if (!lis[i].getElementsByTagName('span').length){
                this.addSingleX(lis[i]);
            }
        }
    },
    removeField: function(li) {
        li = removeElement(li);
        this.removeXspan(li);
        insertSiblingNodesBefore(this.fields.firstChild, li);
        this.s.obj.update.bind(this.s.obj)(this.s.ul);
    }   
}

