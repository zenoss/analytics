var UserMsgsPortlet = Subclass.create(YAHOO.zenoss.portlet.Portlet);
UserMsgsPortlet.prototype = {
    __class__: "YAHOO.zenoss.portlet.UserMsgsPortlet",
    __init__: function(args) {
        args = args || {};
        id = 'id' in args? args.id : getUID('heartbeats');
        datasource = 'datasource' in args? args.datasource :
            new YAHOO.zenoss.portlet.TableDatasource(
            {'url':'/zport/dmd/userMessageTable'});
        bodyHeight = 'bodyHeight' in args? args.bodyHeight :
            200;
        title = 'title' in args? args.title:"Messages";
        refreshTime = 'refreshTime' in args? args.refreshTime : 60;
        this.superclass.__init__(
            {id:id, 
             title:title,
             datasource:datasource,
             bodyHeight: bodyHeight,
             refreshTime: refreshTime
            }
        );
    },
    fillTable: function(contents) {
        columnDefs = contents.columnDefs;
        dataSource = contents.dataSource;

        newLiveData = [];
        i=0;
        forEach(dataSource.liveData, bind(function(x){
            tmplt = "<table class='fatrow'><tr>" +
              "<td style='width:36px;'><img src='"+ x.imgpath +"'/></td>" +
              "<td><span class='msg-title'>"+x.title+"</span><br/>" +
              "    <span class='msg-body'>"+ x.body +"</span></td>" +
              "<td class='msg-ago'><span class='msg-ago'>" + x.ago  +
              "</span></td><td><div class='msg-markread'></div>"+
              "<input id='msg-row-"+i+"' type='hidden' value='"+
            x.deletelink+"'/></td></tr></table>";
            newLiveData.push({Message:tmplt});
            i++;
        }));
        dataSource.liveData = newLiveData;
        if (this.dataTable) {
            oRequest = {'results':dataSource.liveData}
            this.dataTable.onDataReturnInitializeTable(null, oRequest);
        } else {
            var myDataTable = new YAHOO.widget.DataTable(
                this.body.id, columnDefs, dataSource, {});
            this.dataTable = myDataTable;
        }
        forEach(this.dataTable.getRecordSet().getRecords(), bind(function(x){
            var row = this.dataTable.getTrEl(x);
            var link = getElementsByTagAndClassName('div','msg-markread',
                row)[0];
            connect(link, "onclick", method(this, 
                function(){this.markAsRead(x);}));
        }, this));
    },
    markAsRead: function(record) {
        var data = record.getData()['Message'];
        var name = data.match(/msg\-row\-\d+/)[0];
        var sUrl = $MK(name).value;
        var d = doXHR(sUrl);
        var DT = this.dataTable;
        d.addCallback(function(){DT.deleteRow(record)});
    }
}
YAHOO.zenoss.portlet.UserMsgsPortlet = UserMsgsPortlet;
