var page = require('webpage').create(),
    system = require('system'),
    address, output, size, username, password, outputFile, forcedRenderTimeout, maxRenderWait = 7200000, pageLoaded = false,
    pageZoomFactor, pageFormat;

function doRender() {
    page.render(outputFile);
    phantom.exit(0);
}

//phantomjs rasterize.js URL USERNAME PASSWORD PDF
if (system.args.length < 5 || system.args.length > 7) {
    console.log('Usage: rasterize.js URL username password output_filename [paperwidth*paperheight|paperformat] [zoom]');
    console.log('  paper (pdf output) examples: "5in*7.5in", "10cm*20cm", "A4", "Letter"');
    phantom.exit(1);
} else {
    address = system.args[1];
    username = system.args[2];
    password = system.args[3];
    outputFile = system.args[4];
    pageFormat = system.args[5] || "A4";
    pageZoomFactor = system.args[6] || 1;

    page.settings.localToRemoteUrlAccessEnabled = true;
    page.settings.resourceTimeout = 1800000;

    page.onLoadFinished = function(status) {
        pageLoaded = true;
        forcedRenderTimeout = setTimeout(function () {
            doRender();
        }, 10000);
    };

    page.onResourceRequested = function(requestData, networkRequest) {
        // prevent resource requests after the page loads
        if (pageLoaded) {
            networkRequest.abort();
        }
    };

    // use the provided username and password if they were provided
    if (username != "nil" && password != "nil") {
        page.customHeaders={'Authorization': 'Basic '+btoa(username + ':' + password)};
    } else {
        console.log('Username and password were not provided');
    }

    page.zoomFactor = pageZoomFactor;
    page.paperSize = {
        format: pageFormat,
        orientation: "portrait",
        margin: "0.25in"
    };

    page.open(address, function (status) {
        if (status !== 'success') {
            console.log('Unable to load the address!');
            phantom.exit(1);
        } else {
            var el = document.createElement( 'html' );
            el.innerHTML = page.content;
            var report = el.querySelector('[id="graph_report"]');
            if (report) {
                page.viewportSize = { width: 1000, height: parseInt(report.style.height)+110 };
            }
            page.open(address, function (status) {
                forcedRenderTimeout = setTimeout(function () {
                    doRender();
                }, maxRenderWait);
            });
        }
    });
}
