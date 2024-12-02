function submitViaEnter(evt) {
    evt = (evt) ? evt : event;
    var target = (evt.target) ? evt.target : evt.srcElement;
    var form = target.form;
    var charCode = (evt.charCode) ? evt.charCode : 
        ((evt.which) ? evt.which : evt.keyCode);
    if (charCode == 13 || charCode == 3) {
        // if we are on a zentable and pressing enter we do not want to export
        // we want to filter
        if (document.getElementById('exportInput')) {
            document.getElementById('exportInput').name = "";
        }
        form.submit();
        return false;
    } else if (evt.type == "change") {
        form.submit();
        return false;
    }
    return true;
}

