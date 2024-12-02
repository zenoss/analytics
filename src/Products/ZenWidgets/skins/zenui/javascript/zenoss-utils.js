// Define a helpful "class" function (thanks, Prototype)

YAHOO.namespace("YAHOO.zenoss.utils");

var Class={
    create:function(){
        return function(){
            bindMethods(this);
            this.__init__.apply(this,arguments);
        };
    }
};

YAHOO.zenoss.Class = Class;

function bindMethodsTo(src, scope) {
    for (var property in src) {
        if (typeof src[property]=='function') {
            src[property] = method(scope, src[property]);
        }
    }
}

// Subclassing! (thanks, me)

var Subclass={
    create: function(klass){
        return function() {
            this.superclass = {};
            for (var property in klass.prototype) {
                if (!(property in this))
                    this[property] = klass.prototype[property];
                    this.superclass[property] = klass.prototype[property];
            }
            bindMethods(this);
            bindMethodsTo(this.superclass, this);
            this.__init__.apply(this, arguments);
        };
    }
};
YAHOO.zenoss.Subclass = Subclass;


function purge(d) {
    var a = d.attributes, i, l, n;
    if (a) {
        l = a.length;
        for (i = 0; i < l; i += 1) {
            n = a[i].name;
            if (typeof d[n] === 'function') {
                d[n] = null;
            }
        }
    }
    a = d.childNodes;
    if (a) {
        l = a.length;
        for (i = 0; i < l; i += 1) {
            purge(d.childNodes[i]);
        }
    }
}
YAHOO.zenoss.purge = purge;

var setInnerHTML = function (el, html) {

   el = YAHOO.util.Dom.get(el);
   if (!el || typeof html !== 'string') {
       return null;
   }
   // Break circular references.
   (function (o) {
       var a = o.attributes, i, l, n, c;
       if (a) {
           l = a.length;
           for (i = 0; i <l; i += 1) {
               try{
                   n = a[i].name;
                   if (typeof o[n] === 'function') {
                       o[n] = null;
                   }
               }catch(e){
                    // this is here because sometimes, IE chokes on the .name and an IF doesn't work
                    // we swollow it for IE and everything runs fine. 
               }
           }
       }
       a = o.childNodes;
       if (a) {
           l = a.length;
           for (i = 0; i <l; i += 1) {
               c = o.childNodes[i];
               // Purge child nodes.
               arguments.callee(c);
               // Removes all listeners attached to the element via YUI's addListener.
               YAHOO.util.Event.purgeElement(c);
           }
       }
   })(el);
  
   // Remove scripts from HTML string, and set innerHTML property
   el.innerHTML = html.replace(/<script[^>]*>((.|[\r\n])*?)<\\?\/script>/ig, "");
   // Return a reference to the first child
   return el.firstChild;
};
YAHOO.zenoss.setInnerHTML = setInnerHTML;

function unescapeHTML(str) {
    if (!YAHOO.zenoss._dummydiv) YAHOO.zenoss._dummydiv=DIV(null, null);
    _dummydiv = YAHOO.zenoss._dummydiv;
    _dummydiv.innerHTML = str;
    return _dummydiv.textContent;
}
YAHOO.zenoss.unescapeHTML = unescapeHTML;

function getSelectValues(element) {
    var element = $MK(element);
    var values = [];
    forEach(element.options, function(opt){
        if(opt.selected) values.push(opt.value);
    });
    return values;
}
YAHOO.zenoss.getSelectValues = getSelectValues;

/************************************
 *   Less universally useful stuff
 *   (formerly separate scripts)
 ***********************************/

function toggleElement(elementid) {
    var element = $MK(elementid);
    if (element.visible == 0) {
        element.style.display = "none";
        element.visible = 1;
    } else {
        element.style.display = "";
        element.visible = 0;
    }
}


/* Panel Effects */

function toggleVisible(elem) {
    toggleElementClass("invisible", elem);
}

function makeVisible(elem) {
    removeElementClass(elem, "invisible");
}

function makeInvisible(elem) {
    addElementClass(elem, "invisible");
}

function isVisible(elem) {
    return !hasElementClass(elem, "invisible");
}

function getCookie(name) {
    var s = document.cookie.indexOf(name + "=");
    if ((!s) && name!=document.cookie.substring(0,name.length)) {
        return null;
    }
    if (s < 0) {
        return null;
    }
    var e = document.cookie.indexOf(';', s+name.length+1);
    if (e<0) e = document.cookie.length;
    if (e==s) {
        return '';
    }
    return unescape(document.cookie.substring(s+name.length+1, e));
}

function setCookie( name, value, expires, path, domain, secure ) {
    var today = new Date();
    today.setTime( today.getTime() );
    if ( expires ) {
        expires = expires * 1000 * 60 * 60 * 24;
    }
    var expires_date = new Date( today.getTime() + (expires) );
    document.cookie = name + "=" +escape( value ) +
        ( ( expires ) ? ";expires=" + expires_date.toGMTString() : "" ) +
        ( ( path ) ? ";path=" + path : "" ) +
        ( ( domain ) ? ";domain=" + domain : "" ) +
        ( ( secure ) ? ";secure" : "" );
}

function deleteCookie(name,path,domain) {
     if (getCookie(name)) {
         document.cookie =
         name + '=' +
         ( (path) ? ';path=' + path : '') +
         ( (domain) ? ';domain=' + domain : '') +
         ';expires=Thu, 01-Jan-1970 00:00:01 GMT';
     }
}

function hideLeftPane() {
    var leftPane = $MK('leftPane');
    var rightPane = $MK('rightPane');
    //showElement('leftPaneToggle');
    makeInvisible(leftPane);
    makeInvisible($MK('paneToggle'));
    setStyle('paneToggle', {
        'background-image':'url(img/paneToggle_bg_collapsed.gif)',
        'border-right':'1px solid black'
    });
    if ($MK('breadCrumbPane')) {
    setStyle('breadCrumbPane', { 'padding-left':'35px'});}
    setStyle('rightPane', {'margin-left':'12px'});
    setStyle('leftPaneToggle', {
    'background':'transparent url(img/leftpanetoggle_bg.gif) top left repeat-x',
    'height':'30px',
    'width':'30px'
    });
    disconnectAll('leftPaneToggle');
    connect('leftPaneToggle', 'onclick', function(){
        clearTimeout(t);
        doShowing();
    });
    doHover();
}

function showLeftPane() {
    var leftPane = $MK('leftPane');
    var rightPane = $MK('rightPane');
    makeVisible(leftPane);
    makeVisible($MK('paneToggle'));
    //hideElement('leftPaneToggle');
    setStyle('paneToggle', {
        'background-image':'url(img/paneToggle_bg.gif)',
        'border-right':'1px solid black'
    });
    if ($MK('breadCrumbPane')) {
    setStyle('breadCrumbPane', { 'padding-left':'120px'});}
    setStyle(rightPane, {'margin-left':'120px'});
    setStyle('leftPaneToggle', {
    'background':'#5a6f8f url(img/leftpanetoggle_bg_expanded.gif) ' +
        'top left repeat-x',
    'height':'30px',
    'width':'115px'
    });
    disconnectAll('leftPaneToggle');
    connect('leftPaneToggle','onclick',toggleLeftPane);
    cancelHover();
}

function toggleLeftPane() {
    var leftPane = $MK('leftPane');
    if (!isVisible(leftPane)) { showLeftPane(); }
    else { hideLeftPane(); }
}

function doHiding() {
    hideElement($MK('leftPane'));
    hideElement($MK('paneToggle'));
}

function doShowing() {
    showElement($MK('leftPane'));
    showElement($MK('paneToggle'));
}

var t;
function doHover() {
    var leftPane = $MK('leftPane');
    var paneToggle = $MK('paneToggle');
    var leftPaneToggle = $MK('leftPaneToggle');
    var lpPopup = leftPane;
    setStyle(paneToggle, {
        'z-index':'10000'
    });
    setStyle(lpPopup, {
        'position':'absolute',
//        'background-color':'white',
//        'padding':'2px',
//        'padding-top':'2px',
        'z-index':'10000'
    });
    connect(leftPane, 'onmouseover', function(){
        clearTimeout(t);
        doShowing();
    });
    connect($MK('paneToggle'), 'onmouseover', function(){
        clearTimeout(t);
        doShowing();
    });
    connect(paneToggle,'onmouseout',function(){
        t=setTimeout('doHiding()',500);
    });
    connect(leftPane, 'onmouseout', function(){
        t=setTimeout('doHiding()',500);
    });
    connect('leftPaneToggle', 'onmouseout', function(){
        t=setTimeout('doHiding()',500);
    });
    connect(paneToggle, 'onclick', function(){
        clearTimeout(t);
        toggleLeftPane();
    });
    connect('leftPaneToggle','onmouseover', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_depressed.gif") top left repeat-x'
            });
    });
    connect('leftPaneToggle','onmouseout', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg.gif") top left repeat-x'
            });
    });
    connect('leftPaneToggle', 'onclick', function(){
        clearTimeout(t);
        doShowing();
    });
    setCookie('Zenoss_Collapsed_Menu', 'true',30,'/','','');
}

function cancelHover() {
    var leftPane = $MK('leftPane');
    var paneToggle = $MK('paneToggle');
    if (leftPane && paneToggle) {
        setStyle(paneToggle, {'z-index':'1'});
        setStyle(leftPane, {'z-index':'1'});
    disconnectAll(paneToggle);
    disconnectAll(leftPane);
    disconnectAll('leftPaneToggle');
    connect('leftPaneToggle', 'onclick', toggleLeftPane);
    connect('leftPaneToggle','onmouseover', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded_depressed.gif") '+
            'top left repeat-x'
            });
    });
    connect('leftPaneToggle','onmouseout', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded.gif") top left repeat-x'
            });
    });
    deleteCookie('Zenoss_Collapsed_Menu','/','');
    updateNodeAttributes(leftPane, {
        'style':'display:block'
    });}
}

function checkForCollapsed() {
    var x = getCookie('Zenoss_Collapsed_Menu');
    if ($MK('leftPaneToggle')){
    if (!x){
    disconnectAll('leftPaneToggle');
    connect('leftPaneToggle','onclick',toggleLeftPane);
    connect('leftPaneToggle','onmouseover', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded_depressed.gif") top left repeat-x'
            });
    });
    connect('leftPaneToggle','onmouseout', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded.gif") top left repeat-x'
            });
    });
    } else {
        hideLeftPane();
    }
    }
}

function getChildCheckboxes(element) {
    return filter(
        function(x){return x.type=='checkbox';},
        element.getElementsByTagName('input')
    );
}

var tablesOnPage=0;
function insertSelBar(table, index) {
    var getselall = function() {
        return function() {selectAllCheckboxes(table);};
    };
    var getselnone = function() {
        return function() {selectNoneCheckboxes(table);};
    };
    var all = LI({id:'selectall_' + index}, 'All');
    var nun = LI({id:'selectnone_' + index}, 'None');
    var selbar = DIV({'class':'zentable_selectionbar'},
        [ 'Select:  ', UL(null, [all, nun ]) ]);
    insertSiblingNodesBefore(table, selbar);
    connect(all, 'onclick', getselall());
    connect(nun, 'onclick', getselnone());
}

function selectAllCheckboxes(table) {
    var cbs = getChildCheckboxes(table);
    map(function(x){x.checked=true;},cbs);
}

function selectNoneCheckboxes(table) {
    var cbs = getChildCheckboxes(table);
    map(function(x){x.checked=null;},cbs);
}

function addSelectionBar() {
    var tables = getElementsByTagAndClassName('table', 'innerzentable');
    for (i=0;i<tables.length;i++) {
        if (!getNodeAttribute(tables[i], 'noselectionbar')) {
            var inputs = tables[i].getElementsByTagName('input');
            var cbs = filter(function(x){return x.type=='checkbox';}, inputs);
            if (cbs.length>1) insertSelBar(tables[i], i);
        }
    }
}

function applyBrowserSpecificStyles() {
    if (navigator.userAgent.match('Mac')) {
        var searchform=$MK("searchform-label");
        if (searchform)
            setStyle(searchform, {
                'left':'-5em'
            });
    }
}

var removeAutoComplete = function(el) {
    setNodeAttribute(el, 'autocomplete', 'off');
};

var removeElementAutoCompletes = function() {
    var inputs = $$('input');
    map(removeAutoComplete, inputs);
};



postJSONDoc = function (url, postVars) {
        var req = getXMLHttpRequest();
        req.open("POST", url, true);
        req.setRequestHeader("Content-type",
                             "application/x-www-form-urlencoded");
        var data = queryString(postVars);
        var d = sendXMLHttpRequest(req, data);
        return d.addCallback(evalJSONRequest);

};

var cancelWithTimeout = function (deferred, timeout) {
    var canceller = callLater(timeout, function () {
        // cancel the deferred after timeout seconds
        deferred.cancel();
        //log("cancel load data")
    });
    return deferred.addCallback(function (res) {
        // if the deferred fires successfully, cancel the timeout
        canceller.cancel();
        return res;
    });
};

function handle(delta) {
    if (delta < 0)
        /* something. */;
    else
        /* something. */;
}

function wheel(event){
    var delta = 0;
    if (!event) event = window.event;
    if (event.wheelDelta) {
        delta = event.wheelDelta/120;
        if (window.opera) delta = -delta;
    } else if (event.detail) {
        delta = -event.detail/3;
    }
    if (delta)
        handle(delta);
       if (event.preventDefault)
           event.preventDefault();
       event.returnValue = false;
}

function captureSubmit(e){
    switch (e.key().string) {
        case 'KEY_ENTER':
            var submit = $MK('dialog_submit');
            submit.click();
            return;
        default:
    }
}


function checkValidId(e){
    var errmsg = $MK('errmsg');
    var input = $MK('new_id');
    var label = $MK('new_id_label');
    var new_id = escape(input.value);
    var submit = $MK('dialog_submit');
    var path = $MK('checkValidIdPath').value;

    errmsg.innerHTML = "";
    Morph(input, {"style": {"color": "black"}});
    Morph(label, {"style": {"color": "white"}});

    d = callLater(0, doXHR, path+'/checkValidId', {queryString:{'id':new_id}});
    d.addCallback(function (r) {
        if (r.responseText == 'True') {
            submit.disabled = false;
            if (e && e.key().string == 'KEY_ENTER') submit.click();
        } else {
            submit.disabled = true;
            Morph(input, {"style": {"color": "red"}});
            Morph(label, {"style": {"color": "red"}});
            errmsg.innerHTML = r.responseText;
            shake(input);
            shake(label);
            shake(errmsg);
        }
    });
}

function connectTextareas() {

    function resizeAll(area) {
        if (!hasElementClass(area, 'dontexpand'))
            resizeArea(area);
    }
    function resizeArea(area) {
        var td = getFirstParentByTagAndClassName(area, 'td', null);
        aDims = getElementDimensions(td);
        var w = aDims.w - 20;
        setElementDimensions(area, {w:w});
    }
    connect(currentWindow(), 'onresize', function(e) {
        map(resizeAll, $$('textarea'));
    });
    map(resizeAll, $$('textarea'));

}
addLoadEvent(connectTextareas);


/* MENUS */
var calcSubmenuPos = function(rel, sub) {
    // rel is the parent that triggered the submenu show
    var pPos  = getElementPosition(rel);
    var pDims = getElementDimensions(rel);
    var sDims = getElementDimensions(sub);
    var vDims = getViewportDimensions();
    var vPos = getViewportPosition();
    var finalDims = {x:0, y:0};
    // Check to see if the menu will appear outside the viewport
    // If so, make it fly out on the left
    totalX = pPos.x + pDims.w + sDims.w;
    finalDims.x = totalX>=vDims.w+vPos.x?-sDims.w+2:sDims.w-10;
    // Check to see if the menu bottom is outside the viewport
    // If so, move it up so that it fits
    totalY = pPos.y + sDims.h;
    finalDims.y = totalY>=vDims.h+vPos.y?0-(totalY-vDims.h)+vPos.y:0;
    return finalDims;
};


var calcMenuPos = function(rel, menu) {
    var isIE;
    var pPos = getElementPosition(rel);
    var pDims = getElementDimensions(rel);
    var vDims = getViewportDimensions();
    var mDims = getElementDimensions(menu);
    var vPos = getViewportPosition();
    finalDims = $MK(menu).className=='devmovemenuitems'?{x:0, y:0}:{x:0, y:24};
    totalX = pPos.x + mDims.w;
    finalDims.x = totalX>=vDims.w+vPos.x?pDims.w-mDims.w:3+finalDims.x;
    finalDims.x = $MK(menu).className=='devmovemenuitems'?4-pDims.w:finalDims.x;
    finalDims.x -= 1;
    totalY = pPos.y + pDims.h + mDims.h;
    var topmenu = getElementsByTagAndClassName('div', 'menu_top', menu)[0];
    if (totalY>=vDims.h+vPos.y) {
        finalDims.y = 0-(totalY-vDims.h)+vPos.y;
        setStyle(topmenu, {'background-image':'url(img/menu_top_rounded.gif)'});
    } else {
        setStyle(topmenu, {'background-image':'url(img/menu_top.gif)'});
    }
    if (isIE && $MK(menu).className!='devmovemenuitems') finalDims.y += 10;
    return finalDims;
};

var showSubMenu = function(rel, sub) {
    var relPos = calcSubmenuPos(rel, sub);
    setElementPosition(sub, relPos);
    setStyle(sub, {'visibility':'visible','z-index':'10001'});
    hideOtherSubmenus(rel, sub);
};

var hideSubMenu = function(sub) {
    setStyle(sub, {'visibility':'hidden','z-index':'1'});
};

var hideMenu = function(menu) {
    setStyle(menu, {'visibility':'hidden','z-index':'1'});
    try {
    setStyle(getFirstParentByTagAndClassName(menu, 'div',
        'tabletitlecontainer'), {'z-index':'1'});
    } catch(e){noop();}
    if (navigator.userAgent.match('Mac')) {
        try {setStyle(eventZenGrid.scrollbar, {'overflow':'auto'});}
        catch(e) {noop();};
    }
};

var showMenu = function(rel, menu) {
    dropOtherMenuButtons(rel);
    var relPos = calcMenuPos(rel, menu);
    setElementPosition(menu, relPos);
    setStyle(menu, {'visibility':'visible','z-index':'10000',
                    'zoom':1});
    if (navigator.userAgent.match('Mac')) {
        try {setStyle(eventZenGrid.scrollbar, {'overflow':'hidden'});}
        catch(e) {noop();};
    }
};

var showContextMenu = function() {
    var menu = $MK('contextmenuitems');

};

var dropOtherMenuButtons = function(button) {
    var lowerButton = function(btn) { setStyle(btn, {'z-index':'1'});};
    try {
        mymenu = getFirstParentByTagAndClassName($MK(button).parentNode, 'div',
        'tabletitlecontainer');
    } catch(e) {
        mymenu = null;
    }
    others = $$("div.tabletitlecontainer");
    map(lowerButton, others);
    if (mymenu) setStyle(mymenu, {'z-index':'10000'});
};

var hideOtherSubmenus = function(menu, submenu) {
    var smartHideSub = function(sub){if ($MK(submenu)!=sub) hideSubMenu(sub);};
    map(smartHideSub, $$('div.submenu'));
};

var smto = Array();

var registerSubmenu = function(menu, submenu) {
    try {
    connect(menu, 'onmouseover', function() {
        clearTimeout(smto[menu]);
        clearTimeout(smto[submenu]);
        showSubMenu(menu, submenu); });
    connect(submenu, 'onmouseover', function() {
        clearTimeout(smto[menu]);
        clearTimeout(smto[submenu]);
        showSubMenu(menu, submenu); });
    connect(menu, 'onmouseout', function() {
        smto[submenu] = setTimeout('hideSubMenu("'+submenu+'")', 500); });
    connect(submenu, 'onmouseout', function() {
        smto[submenu] = setTimeout('hideSubMenu("'+submenu+'")', 500); });
    connect(submenu, 'onclick', function() {
        hideSubMenu(submenu);
    });
    } catch(e) {noop();};
};

var registerMenu = function(button, menu) {
    connect(button, 'onclick', function() {
        clearTimeout(smto[menu]);
        showMenu(button, menu);
        addElementClass(button, 'menuselected');
        connect(button, 'onmouseover', function() {
            clearTimeout(smto[menu]);
            showMenu(button, menu);
            addElementClass(button, 'menuselected');
        });
    });
    connect(menu, 'onmouseover', function() {
        clearTimeout(smto[menu]);
        showMenu(button, menu);
        addElementClass(button, 'menuselected');
        connect(button, 'onmouseover', function() {
            clearTimeout(smto[menu]);
            showMenu(button, menu);
            addElementClass(button, 'menuselected');
        });
    });
    connect(menu, 'onclick', function() {
        hideMenu(menu);
        disconnectAll(button, 'onmouseover');
    });
    connect(button, 'onmouseout', function() {
        smto[menu] = setTimeout('hideMenu("'+menu+'");disconnectAll("'+
            button+'", "onmouseover");', 500); });
    connect(menu, 'onmouseout', function() {
        smto[menu] = setTimeout('hideMenu("'+menu+'");disconnectAll("'+
            button+'", "onmouseover");', 500); });
};


/* ZGDAgent */

function notifyParentOfNewUrl() {
    try {
        var parwin = currentWindow().parent;
        var url = location.href;
        if (parwin && parwin.zmlistener) {
            parwin.zmlistener.checkForDomainChange(url);
        }

    }
    catch(e){ noop(); }
}


/* Selection stuff */
var checkboxes;
var currentCheckbox;
var isCheckbox = function(elem) {
    return (elem.type=='checkbox'); };

function getCheckboxes(elem) {
    var inputs = getElementsByTagAndClassName('input', null);
    return filter(isCheckbox, inputs);
}

function selectCheckboxRange(start, end) {
    a = end>start?start:end;
    b = start==a?end:start;
    newstate = -checkboxes[end].checked;
    var todo = checkboxes.slice(a, b+1);
    for (i=0;(box=todo[i]);i++) {
        if ((!box.checked && newstate) ||
            (box.checked && !newstate)) box.click();
        //box.checked = newstate;
    }
}

function getIndex(box) {
    return findIdentical(checkboxes, box);
}

function handleChange(e) {
    var t = e.src();
    var shift = e.modifier().shift;
    if (isCheckbox(t) && shift) {
        if (currentCheckbox){
            selectCheckboxRange(
            getIndex(currentCheckbox), getIndex(t));
            currentCheckbox = t;
        }
    }
    currentCheckbox = t;
}

var CbCxs = new Array();
function connectCheckboxListeners() {
    disconnectAllTo(handleChange);
    checkboxes = getCheckboxes();
    for (i=0; i<checkboxes.length; i++){
        var box = checkboxes[i];
        connect(box, 'onkeypress', handleChange);
        connect(box, 'onclick', handleChange);
    }
}


/* zenmodelfuncs */

function zenPageInit(){

    var as = $$('#leftPane a');
    for(var i=0; i< as.length; i++){
        if (location.href.indexOf('notabs') != -1 &&
            location.href==as[i].href) {
                as[i].className = 'selected';
        }
        else if( location.href.indexOf('notabs')==-1 &&
                 as[i].href.indexOf('notabs')==-1 &&
                 location.pathname.indexOf(as[i].pathname) != -1){
            as[i].className = 'selected';
            //lastLeft = as[i];
        }
        else {
            as[i].className = 'unselected';
        }
    }
}

function submitAction(myform, url) {
    myform.action=url;
    myform.submit();
}

function submitViaEnter(evt, submitName) {
    evt = (evt) ? evt : event;
    var target = (evt.target) ? evt.target : evt.srcElement;
    var form = target.form;
    var charCode = (evt.charCode) ? evt.charCode :
        ((evt.which) ? evt.which : evt.keyCode);
    if (charCode == 13 || charCode == 3) {
        if (submitName) { form.action += "/" + submitName; }
        form.submit();
        return false;
    }
    return true;
}

function blockSubmitViaEnter(evt) {
    evt = (evt) ? evt : event;
    var charCode = (evt.charCode) ? evt.charCode :
        ((evt.which) ? evt.which : evt.keyCode);
    if (charCode == 13 || charCode == 3) {
        return false;
    }
    return true;
}

isSelected = false;

function toggleSelect(form) {
    if (isSelected == false) {
        for (i = 0; i < form.length; i++) {
            if (form.elements[i].name == "negateFilter") { continue; }
            form.elements[i].checked = true ;
        }
        isSelected = true;
        form.SelectButton.value = "Deselect All";
        return isSelected;
    }
    else {
        for (i = 0; i < form.length; i++) {
            if (form.elements[i].name == "negateFilter") { continue; }
            form.elements[i].checked = false ;
        }
        isSelected = false;
        form.SelectButton.value = "Select All";
        return isSelected;
    }
}

/* DIALOGS */

function getFormElements(parentbox) {
    var firstElement;
    var textBoxes = [];
    var submitButtons = [];
    var formElements = [];
    var traverse = function(node) {
        if ((node.tagName=='SELECT'||node.tagName=='INPUT'||
            node.tagName=='TEXTAREA')&&node.type!='hidden') {
                formElements[formElements.length]=node;
                if (!firstElement)
                    firstElement = node;
        }
        if (node.tagName=='INPUT'&&(node.type=='text'||node.type=='password'))
            textBoxes[textBoxes.length]=node;
        if (node.tagName=='INPUT'&&(node.type=='submit'||node.type=='button')&&
            node.id!='dialog_cancel')
            submitButtons[submitButtons.length] = node;
        if (node.childNodes != null) {
            for (var i=0;i<node.childNodes.length;i++) {
                traverse(node.childNodes.item(i));
            }
        }
    };
    traverse(parentbox);
    return [firstElement, textBoxes, submitButtons, formElements];
}

var Dialog = {};
Dialog.Box = Class.create();
Dialog.Box.prototype = {
    __init__: function(id) {
        bindMethods(this);
        this.makeDimBg();
        this.box = $MK(id);
        this.framework = DIV(
            {'class':'dialog_container'},
            [
            //top row
            DIV({'class':'dbox_tl'},
             [ DIV({'class':'dbox_tr'},
               [ DIV({'class':'dbox_tc'}, null)])]),
            //middle row
            DIV({'class':'dbox_ml'},
             [ DIV({'class':'dbox_mr'},
               [ DIV({'class':'dbox_mc',
                      'id':'dialog_content'}, null)])]),
            //bottom row
            DIV({'class':'dbox_bl'},
             [ DIV({'class':'dbox_br'},
               [ DIV({'class':'dbox_bc'}, null)])])
            ]);
        insertSiblingNodesBefore(this.box, this.framework);
        setStyle(this.framework, {'position':'absolute'});
        removeElement(this.box);
        appendChildNodes($MK('dialog_content'), this.box);
        this.loadEvents = {};
        this.unloadEvents = {};
        this.box.addLoadEvent = bind(this.addLoadEvent, this);
        this.box.addUnloadEvent = bind(this.addUnloadEvent, this);
        this.box.show = bind(this.show, this);
        this.box.hide = bind(this.hide, this);
        this.box.fill = bind(this.fill, this);
        this.box.submit_form = bind(this.submit_form, this);
        this.box.submit_form_and_check = bind(this.submit_form_and_check, this);
        this.parentElem = this.box.parentNode;
        this.defaultContent = this.box.innerHTML;
        setStyle(this.box, {
            'position':'absolute',
            'z-index':'5001',
            'display':'none'});
        setStyle('dialog_innercontent', {'visibility':'visible'});
        setStyle('dialog_content', {'visibility':'visible'});
        setStyle(this.box, {'visibility':'visible'});
    },
    addLoadEvent: function(id, func) {
        if (!(id in this.loadEvents)) this.loadEvents[id] = [];
        this.loadEvents[id].push(func);
    },
    addUnloadEvent: function(id, func) {
        if (!(id in this.unloadEvents)) this.unloadEvents[id] = [];
        this.unloadEvents[id].push(func);
    },
    makeDimBg: function() {
        if($MK('dialog_dim_bg')) {
            this.dimbg = $MK('dialog_dim_bg');
        } else {
            this.dimbg = DIV({'id':'dialog_dim_bg'},null);
            setStyle(this.dimbg, {
                'position':'absolute',
                'top':'0',
                'left':'0',
                'z-index':'5000',
                'width':'100%',
                'background-color':'white',
                'display':'none'
            });
            insertSiblingNodesBefore(document.body.firstChild, this.dimbg);
        }
    },
    moveBox: function(dir) {
        this.framework = removeElement(this.framework);
        if(dir=='back') {
            this.framework = this.dimbg.parentNode.appendChild(this.framework);
        } else {
            this.framework = this.dimbg.parentNode.insertBefore(
                this.framework, this.dimbg);
        }
    },
    lock: new DeferredLock(),
    show: function(form, url) {
        var d1 = this.lock.acquire();
        d1.addCallback(bind(function() {
            if (url) this.fetch(url);
        }, this));
        this.form = form;
        var dims = getViewportDimensions();
        var vPos = getViewportPosition();
        setStyle(this.framework, {'z-index':'1','display':'block'});
        var bdims = getElementDimensions(this.framework);
        setStyle(this.framework, {'z-index':'10002','display':'none'});
        map(function(menu) {setStyle(menu, {'z-index':'3000'});},
            concat($$('.menu'), $$('.littlemenu'), $$('#messageSlot')));
        setElementDimensions(this.dimbg, getViewportDimensions());
        setElementPosition(this.dimbg, getViewportPosition());
        setStyle(this.box, {'position':'relative'});
        setElementPosition(this.framework, {
            x:((dims.w+vPos.x)/2)-(bdims.w/2),
            y:((dims.h/2)+vPos.y)-(bdims.h/2)
        });
        this.moveBox('front');
        connect('dialog_close','onclick',function(){$MK('dialog').hide();});
        var d2 = this.lock.acquire();
        d2.addCallback(bind(function() {
            try {
                connect('new_id','onkeyup', captureSubmit);
            } catch(e) { noop(); }
            this.lock.release();
        }, this));
        appear(this.dimbg, {duration:0.1, from:0.0, to:0.7});
        showElement(this.box);
        showElement(this.framework);

        /*
         * HACK: Fixes ZEN-1883.  Have to stop the JobsRouter while the dialog
         * box is open to stop jumping between selections.  Issue discovered
         * only in Chrome for Windows and Ubuntu.
         */
        if (jobsWidget = Ext.getCmp('jobswidget'))
            jobsWidget.pause();
    },
    hide: function() {
        fade(this.dimbg, {duration:0.1});
        if (this.curid in this.unloadEvents)
            forEach(this.unloadEvents[this.curid], function(f){f();});
        YAHOO.zenoss.setInnerHTML(this.defaultContent);
        this.curid = null;
        hideElement(this.framework);
        this.moveBox('back');
        if (this.lock.locked) this.lock.release();

        /*
         * HACK: Fixes ZEN-1883.  Restarting the JobsRouter as it was
         * previously halted by the show() method.
         */
        if (jobsWidget = Ext.getCmp('jobswidget'))
            jobsWidget.poll();
    },
    fetch: function(url) {
        var urlsplit = url.split('/');
        var id = urlsplit[urlsplit.length-1];
        this.curid = id;
        var d = doSimpleXMLHttpRequest(url, {dontCache: new Date().getTime()});
        d.addCallback(method(this, function(req){this.fill(id, req);}));
    },
    fill: function(dialogid, request) {
        YAHOO.zenoss.setInnerHTML($MK('dialog_innercontent'), request.responseText);     
        if (dialogid in this.loadEvents){
            forEach(this.loadEvents[dialogid], function(f){f();});
        }    
        var elements = getFormElements($MK('dialog_innercontent'));
        var first = elements[0];
        var textboxes = elements[1];
        var submits = elements[2];
        var submt = submits[0];
        first.focus();
        var connectTextboxes = function(box) {
            connect(box, 'onkeyup', function(e){
                if (e.key().string=='KEY_ENTER') submt.click();
            });
        };
        if (submits.length==1) map(connectTextboxes, textboxes);
        first.focus();
        if (this.lock.locked) this.lock.release();
    },
    submit_form: function(action, formname) {
        var f = formname?document.forms[formname]:(this.form?this.form:$MK('proxy_form'));
        setStyle(this.box, {'z-index':'-1'});
        this.box = removeElement(this.box);
        if (action != '') f.action = action;
        f.appendChild(this.box);
        return true;
    },
    submit_form_and_check: function(action, formname, prep_id) {
        var errmsg = $MK('errmsg');
        var input = $MK('new_id');
        var label = $MK('new_id_label');
        var new_id = escape(input.value);
        var submit = $MK('dialog_submit');
        var path = $MK('checkValidIdPath').value;
        var myform = formname?document.forms[formname]:this.form;
        errmsg.innerHTML = "";
        Morph(input, {"style": {"color": "black"}});
        Morph(label, {"style": {"color": "white"}});
        var d = doSimpleXMLHttpRequest(path+'/checkValidId',
            {'id':new_id, 'prep_id':prep_id});

        d.addCallback(bind(function (r) {
            if (r.responseText == 'True') {
                var f = formname?document.forms[formname]:
                    (this.form?this.form:$MK('proxy_form'));
                setStyle(this.box, {'z-index':'-1'});
                this.box = removeElement(this.box);
                if (action != '') f.action = action;
                f.appendChild(this.box);
                submit.onclick = "";
                submit.click();
            } else {
                Morph(input, {"style": {"color": "red"}});
                Morph(label, {"style": {"color": "red"}});
                errmsg.innerHTML = r.responseText;
                shake(input);
                shake(label);
                shake(errmsg);
            }
        }, this));
    }
};

var RefreshManager = Class.create();
RefreshManager.prototype = {
    __init__: function(time, func) {
        bindMethods(this);
        this.time = time;
        this.func = func;
        this.firstTime = true;
        this.doRefresh();
    },
    doRefresh: function() {
        if (!this.firstTime) {
            this.func();
        } else {
            this.firstTime = false;
        }
        this.current = callLater(this.time, this.doRefresh);
    },
    cancelRefresh: function() {
        if(this.current) this.current.cancel();
        this.current = null;
    }
};


/**
 * Converts an array of message strings to an HTML list representation that
 * can be located within some other document container.
 *
 * @param {Object} messages an array of messages
 */
YAHOO.zenoss.utils.messagesToList = function(messages) {
    var html = "<ul>\n";
    for (msg in messages) {
        // TODO: make each message HTML-safe
        html += "<li>" + messages[msg] + "</li>\n";
    }
    html += "</ul>\n";
    return html;
};



YAHOO.register("zenossutils", YAHOO.zenoss.utils, {});

