buildProdSelect = function(prodid, req) {
    log("buildPopSelect prodid=", prodid);
    if (req.status==200) {
        log(req.resultText);
        log("req response=", req.responseText);
        var prodsel = document.getElementById(prodid);
        var prods = evalJSONRequest(req);
        prodsel.options.length = 0;
        for (var i = 0; i < prods.length; i++) {
            prodsel.options[i] = new Option(prods[i], prods[i], false, false);
        }
    } else {
        log("req status=", req.statusText);
    }
}

getProdSelectList = function(compsel, prodid, type){
    var url = '/zport/dmd/Manufacturers/getProductNames';
    var cname = compsel.options[compsel.selectedIndex].value
    log("getProdSelectList url=", url);
    d = doSimpleXMLHttpRequest(url, {mname:cname,type:type});
    d.addBoth(buildProdSelect, prodid);
}
