/*****************************************************************************
 * 
 * Copyright (C) Zenoss, Inc. 2007, all rights reserved.
 * 
 * This content is made available according to terms specified in
 * License.zenoss under the directory where your Zenoss product is installed.
 * 
 ****************************************************************************/


//var url="data.json";

// IE detection in 20 bytes!
var isie//@cc_on=1;

function updateTimestamp(){
    $("dashTime").innerHTML = "<b>Refreshing...</b>";
    callLater(1,updateTimestampNow);
}

function updateTimestampNow(){
    var d = new Date();
    var h = "Last Updated: ";
    h += getServerTimestamp()
    $("dashTime").innerHTML = h;
}


statusUpdate = function(id, data) {
    /* draw clear then draw the rows of the tbody */
    //log("drawTableBody "+id);
    var tbody = null;
    if (isie) {
        tbody = $(id);
        clearTableBody(tbody);
    } else {
        tbody = TBODY({'id':id});
    }
    for (var r=0; r<data.length;r++) {
        var tr = tbody.insertRow(tbody.rows.length);
        var odd = (r%2)?"odd":"even";
        setElementClass(tr, "tablevalues " + odd);
        var row = data[r];
        for (var j=0; j<row.length; j++) {
            var td = tr.insertCell(tr.cells.length);
            if (row[j].cssclass) { 
                setElementClass(td, row[j].cssclass);
                td.innerHTML = row[j].data;
            } else if (typeof(row[j]) == "string") {
                td.innerHTML = row[j]
            }
        }
    }
    if (!isie) swapDOM(id, tbody);
}

clearTableBody = function(tbody) {
    /* remove all rows from table */
    while (tbody.rows.length > 0) {
        tbody.deleteRow(0);
    }
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


updateDashboard = function(data) {
    //log("got data");
    for (var id in data) {
        statusUpdate(id, data[id]);
    }
    updateTimestamp();
}

updateError = function(err) {
    logError(err);
    $("dashTime").innerHTML = "<b class='errortitle'>Lost Connection to Zenoss</b>";
}

refreshData = function() {
    log("Loading dashboard data...");
    var defr = cancelWithTimeout(
        loadJSONDoc(dashurl, dashparams), timeout); // timeout set on Dashboard
    defr.addCallback(updateDashboard);
    defr.addErrback(updateError);
    callLater(refresh, refreshData, dashurl); // refresh set on Dashboard
}

addLoadEvent(refreshData)
