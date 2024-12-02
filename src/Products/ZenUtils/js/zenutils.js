var Class = YAHOO.zenoss.Class;

postJSONDoc = function (url, postVars) {
        var req = getXMLHttpRequest();
        req.open("POST", url, true);
        req.setRequestHeader("Content-type", 
                             "application/x-www-form-urlencoded");
        var data = queryString(postVars);
        var d = sendXMLHttpRequest(req, data);
        return d.addCallback(evalJSONRequest);

}

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
            var submit = $('dialog_submit');
            submit.click();
            return;
        default:
    }
}


function checkValidId(e){
    var errmsg = $('errmsg');
    var input = $('new_id');
    var label = $('new_id_label');
    var new_id = escape(input.value);
    var submit = $('dialog_submit');
    var path = $('checkValidIdPath').value
    
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

    var vDims, vPos, aDims, aPos, rightedge_area, rightedge_vp;

    var refreshVars = function() {
        vDims = getViewportDimensions();
        vPos = getViewportPosition();
        rightedge_vp = vDims.w + vPos.x;
        var area = $$('textarea')[0];
        aDims = getElementDimensions(area);
        aPos = getElementPosition(area);
        rightedge_area = aDims.w + aPos.x;
    }

    function resizeAll() {
        refreshVars();
        map(resizeArea, $$('textarea'));
    }

    function resizeArea(area) {
        var w = aDims.w + rightedge_vp-rightedge_area-50;
        setElementDimensions(area, {w:w});
    }

    connect(currentWindow(), 'onresize', function(e) {
        map(resizeAll, $$('textarea'));
    });

    map(resizeAll, $$('textarea'));
}


ImagePreloader = Class.create();
ImagePreloader.prototype = {
    __init__: function() {
        bindMethods(this);
        this.buffer = new Image(25, 25);
        this.queue = new Array();
        this.lock = new DeferredLock();
    },
    add: function(img) {
        this.queue.push(img);
        this.start();
    },
    start: function() {
        var d = this.lock.acquire();
        d.addCallback(this.next);
    },
    next: function() {
        var img = this.queue.pop();
        if (img) this.buffer.src = img;
        this.lock.release();
    }
}

