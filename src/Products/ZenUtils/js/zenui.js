
function toggleElement(elementid) {
    var element = $(elementid);
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
    var leftPane = $('leftPane');
    var rightPane = $('rightPane');
    //showElement('leftPaneToggle');
    makeInvisible(leftPane);
    makeInvisible($('paneToggle'));
    setStyle('paneToggle', {
        'background-image':'url(img/paneToggle_bg_collapsed.gif)',
        'border-right':'1px solid black'
    });
    if ($('breadCrumbPane')) {
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
    var leftPane = $('leftPane');
    var rightPane = $('rightPane');
    makeVisible(leftPane);
    makeVisible($('paneToggle'));
    //hideElement('leftPaneToggle');
    setStyle('paneToggle', {
        'background-image':'url(img/paneToggle_bg.gif)',
        'border-right':'1px solid black'
    });
    if ($('breadCrumbPane')) {
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
    var leftPane = $('leftPane');
    if (!isVisible(leftPane)) { showLeftPane() }
    else { hideLeftPane() }
}

function doHiding() {
    hideElement($('leftPane'));
    hideElement($('paneToggle'));
}

function doShowing() {
    showElement($('leftPane'));
    showElement($('paneToggle'));
}

var t;
function doHover() {
    var leftPane = $('leftPane');
    var paneToggle = $('paneToggle');
    var leftPaneToggle = $('leftPaneToggle');
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
    connect($('paneToggle'), 'onmouseover', function(){
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
            })
    });
    connect('leftPaneToggle','onmouseout', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg.gif") top left repeat-x'
            })
    });
    connect('leftPaneToggle', 'onclick', function(){
        clearTimeout(t);
        doShowing();
    });
    setCookie('Zenoss_Collapsed_Menu', 'true',30,'/','','');
}

function cancelHover() {
    var leftPane = $('leftPane');
    var paneToggle = $('paneToggle');
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
            })
    });
    connect('leftPaneToggle','onmouseout', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded.gif") top left repeat-x'
            })
    });
    deleteCookie('Zenoss_Collapsed_Menu','/','');
    updateNodeAttributes(leftPane, {
        'style':'display:block'
    });}
}

function checkForCollapsed() {
    var x = getCookie('Zenoss_Collapsed_Menu');
    if ($('leftPaneToggle')){
    if (!x){
    disconnectAll('leftPaneToggle');
    connect('leftPaneToggle','onclick',toggleLeftPane);
    connect('leftPaneToggle','onmouseover', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded_depressed.gif") top left repeat-x'
            })
    });
    connect('leftPaneToggle','onmouseout', function() {
        setStyle('leftPaneToggle', {
            'background':'transparent ' +
            'url("img/leftpanetoggle_bg_expanded.gif") top left repeat-x'
            })
    });
    } else {
        hideLeftPane();
    }
    }
}

function getChildCheckboxes(element) {
    return filter(
        function(x){return x.type=='checkbox'},
        element.getElementsByTagName('input')
    )
}

var tablesOnPage=0;
function insertSelBar(table) {
    var getselall = function() {
        return function() {selectAllCheckboxes(table)}
    }
    var getselnone = function() {
        return function() {selectNoneCheckboxes(table)}
    }
    var all = LI(null, 'All');
    var nun = LI(null, 'None');
    var selbar = DIV({'class':'zentable_selectionbar'}, 
        [ 'Select:  ', UL(null, [all, nun ]) ]);
    insertSiblingNodesBefore(table, selbar);
    connect(all, 'onclick', getselall());
    connect(nun, 'onclick', getselnone());
}

function selectAllCheckboxes(table) {
    var cbs = getChildCheckboxes(table);
    map(function(x){x.checked=true},cbs);
}

function selectNoneCheckboxes(table) {
    var cbs = getChildCheckboxes(table);
    map(function(x){x.checked=null},cbs);
}

function addSelectionBar() {
    var tables = getElementsByTagAndClassName('table', 'innerzentable');
    for (i=0;i<tables.length;i++) {
        if (!getNodeAttribute(tables[i], 'noselectionbar')) {
            var inputs = tables[i].getElementsByTagName('input');
            var cbs = filter(function(x){return x.type=='checkbox'}, inputs);
            if (cbs.length) insertSelBar(tables[i]);
        }
    }
}

function applyBrowserSpecificStyles() {
    if (navigator.userAgent.match('Mac')) {
        var searchform=$("searchform-label");
        setStyle(searchform, {
            'left':'-5em'
        });
    }
}

var removeAutoComplete = function(el) {
    setNodeAttribute(el, 'autocomplete', 'off');
}

var removeElementAutoCompletes = function() {
    var inputs = $$('input');
    map(removeAutoComplete, inputs);
}

addLoadEvent(removeElementAutoCompletes);
addLoadEvent(applyBrowserSpecificStyles);
addLoadEvent(addSelectionBar);
addLoadEvent(checkForCollapsed);
