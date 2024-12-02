/*
 * Needs moving somewhere else...but not sure where yet.
 *
 * Note that there are umpteen implementations of this in libraries like prototype, so we
 * don't need another one here. But since we are only relying on YUI at the moment, we'll
 * need something.
 */

function myList()
{
    this._list = [];
}

function findKey(arr, key)
{
    var oRet = null;

    if (typeof(key) == "number")
        oRet = arr[key].item;
    else
    {
        for (var i = 0; i < arr.length; i++)
        {
            if (arr[i].name == key)
            {
                oRet = arr[i].item;
                break;
            }
        }
    }//if ( key is an index ) ... else ...
    return oRet;
}//findKey

myList.prototype.add = function(key, obj)
{
    var found = false;

    for (var i = 0; i < this._list.length; i++)
    {
        if (this._list[i].name == key)
        {
            found = true;
            break;
        }
    }
    if (!found)
    {
        this._list.push(
            {
                name: key,
                item: obj
            }
        );
        i = this._list.length - 1;
    }
    return this._list[i].item;
};//add

myList.prototype.get = function(key)
{
    var oRet = null;

    if (typeof(key) == "number")
        oRet = this._list[key].item;
    else
    {
        for (var i = 0; i < this._list.length; i++)
        {
            if (this._list[i].name == key)
            {
                oRet = this._list[i].item;
                break;
            }
        }
    }//if ( key is an index ) ... else ...
    return oRet;
};//get

/*
 * Work out the base URL for this document.
 *
 * [TODO] Use our URL library.
 */

function getBaseUrl()
{
    var sRet = "";

	var URL = new String(document.URL);

	if (URL.substr(0, 5) == "file:")
	{
		URL = URL.substr(5);
		while (URL.charAt(0) == "/")
		{
			URL = URL.substr(1);
		}

		URL = URL.replace(new RegExp("/", "g"), "\\");

		sRet = URL.substr(0, URL.lastIndexOf("\\") + 1);
	}
	else
		sRet = URL.substr(0, URL.lastIndexOf("/") + 1);
    return sRet;
}//getBaseUrl


/*
 * This first part is essentially 'Growl core'. It should be moved into its own module at
 * some point.
 */

function GrowlRawNotification()
{
    this.displayName = null;
    this.text = null;
    this.style = null;
    this.name = null;
    this.title = null;
    this.description = null;
    this.enabled = false;
    this.iconData = null;
    this.priority = 0;
    this.reserved = 0;
    this.isSticky = false;
    this.clickContext = null;
    this.clickCallback = null;
}//GrowlRawNotification

function GrowlNotification()
{
    this.name = null;
    this.title = null;
    this.description = null;
    this.enabled = true;
    this.iconData = null;
    this.priority = 0;
    this.reserved = 0;
    this.isSticky = false;
    this.clickContext = null;
    this.clickCallback = null;
}//GrowlNotification

if (!document.Growl)
{
    document.Growl = {
        _applicationsList: new myList(),

        _displayList: [],
        _displayDefault: null,

        _notifyContainer: null,

        _notifyCount: 0,

        _userSettings: null,

        addUserSettings: function(settings)
        {
            this._userSettings = settings;
            return;
        },//addUserSettings()

        rawNotification: function(app, displayStyle, notification)
        {
            if (displayStyle.impl.init())
            {
                var delegate = app.delegate;
                var panel = (notification.useExternal && displayStyle.implExternal)
                  ? displayStyle.implExternal.createPanel()
                  : displayStyle.impl.createPanel();

                panel.setMessage(notification);
                panel.show();
    
                if (!notification.isSticky)
                {
                    setTimeout(
                        function ()
                        {
                            if (panel)
                            {
                                panel.destroy();
                                panel = null;
                            }//if ( the panel is still around )
                            if (notification.clickContext && delegate.growlNotificationTimedOut)
                                delegate.growlNotificationTimedOut("id");
                        },
                        (notification.duration) ? notification.duration * 1000 : 4000
                    );
                }
                panel.registerForClick(
                    function()
                    {
                        if (panel)
                        {
                            panel.destroy();
                            panel = null;
                        }

                        /*
                         * The 'per notification' callback overrides the delegate's.
                         */

                        if (notification.clickCallback)
                            notification.clickCallback.call(notification.clickContext);
                        else
                        {
                            if (delegate.growlNotificationWasClicked)
                                delegate.growlNotificationWasClicked("id");
                        }
                    }//onclick handler
                );
            }//if ( the style handler was initialised successfully )
            return panel;
        },//rawNotification()

        setGrowlDelegate: function(delegate)
        {

            /*
             * Create a new notification list for each application.
             */

            var appname;

            if (!delegate.applicationNameForGrowl)
                throw "Growl delegate must implement applicationNameForGrowl()";
            else
                appname = delegate.applicationNameForGrowl();

            /*
             * It doesn't hurt to try to add it even if it's already there.
             */

            var app = this._applicationsList.add(
                appname,
                {
                    delegate: null,
                    displayName: "default",
                    _notificationsList: new myList()
                }
            );

            if (app.delegate)
                app.delegate.release();
            app.delegate = delegate;

            var nl = app._notificationsList;

            /*
             * Each notification that is being registered gets its own entry
             * in the list.
             */

            var dictionary;

            if (!delegate.registrationDictionaryForGrowl)
                throw "Growl delegate must implement registrationDictionaryForGrowl()";
            else
                dictionary = delegate.registrationDictionaryForGrowl();

            var fullList = dictionary[0];
            
            for (var i = 0; i < fullList.length; i++)
                nl.add(fullList[i], { displayName: "default", enabled: false } );

            /*
            * Now we can set the default 'enable' state of the notifications.
            */

            var enabledList = dictionary[1];

            for (i = 0; i < enabledList.length; i++)
            {
                var n = nl.get(enabledList[i]);

                //if (String(n.enabled) == "undefined")
                    n.enabled = true;
            }
            return;
        },//setGrowlDelegate()

        notify: function(notificationName, title, description, applicationName, image, sticky, priority)
        {
            /*
             * First create a notification object that will hold the format of our message.
             */

            var panel;
            var notification = new GrowlRawNotification();

            notification.title = title;
            notification.description = description;

            /*
             * Next get the various settings. These come from:
             *
             * - a user's global default settings;
             * - a user's per application settings;
             * - a user's per notification settings;
             * - a user's per display settings;
             * - parameters set by the author in the call to this function.
             */

            /*
             * Get the application from the list of registered applications, and
             * get the notification that we're about to use.
             */

            var app = this._applicationsList.get(applicationName);

            if (app)
            {
                var n = app._notificationsList.get(notificationName);

                notification.enabled = n.enabled;

                /*
                 * See if the user has any settings for this application, and if so
                 * get the settings for the notification.
                 */

                var userNotification = null;

                if (this._userSettings)
                {
                    var userApp = findKey(this._userSettings._applicationsList, applicationName);
    
                    if (userApp)
                        userNotification = findKey(userApp._notificationsList, notificationName);
                }
    
                /*
                 * First work out the theme to use. If the user has set one, for the
                 * notification or for the application then it takes priority.
                 */
    
                var displayName = "default";
    
                if (userNotification && userNotification.displayName)
                    displayName = userNotification.displayName;
    
                if (displayName == "default")
                {
                    if (userApp && userApp._default && userApp._default.displayName)
                        displayName = userApp._default.displayName;
                }

                if (displayName == "default")
                    displayName = this._displayDefault;

                /*
                 * Now that we have a display theme we copy all of its properties into
                 * our notification object.
                 */
    
                var d = this._displayList[displayName];
    
                for (var k in d)
                    notification[k] = d[k];
    
    
                /*
                 * Get some defaults for the application. If there is no image then use the
                 * application image.
                 */
    
                notification.iconData = app.delegate.applicationIconDataForGrowl();
    
    
                /*
                 * Now we override the display settings with any parameters passed.
                 */
    
                if (image)
                    notification.iconData = image;
                if (sticky)
                    notification.isSticky = sticky;
                if (priority)
                    notification.priority = priority;
    
                /*
                 * Finally, we apply any changes to the settings that the user has put on.
                 */
    
                if (userNotification)
                {
                    for (k in userNotification)
                        notification[k] = userNotification[k];
                }
                notification.displayName = displayName;
    
                /*
                 * Only show the notification if it is enabled.
                 */
    
                if (notification.enabled)
                    panel = this.rawNotification(app, d, notification);
            }//if ( the application is registered )
            return panel;
        },//notify()

        /*
         * This method will add themes stored in a Google spreadsheet.
         */

        addThemes: function(json)
        {
          for (var i = 0; i < json.feed.entry.length; i++)
          {
            var x = json.feed.entry[i].content.$t;
            var o;
            eval( "o = {" + json.feed.entry[i].content.$t + "}" );
            var name = o.n;
            var t = o.t;
            var b = o.b;
            var op = o.o;
            var d = o.d;
            var f = o.f;

            document.Growl._displayList[name] = {
                text: t,
                style: "background-color: " + b + "; opacity: " + op + ";",
                duration: d,
                floatingicon: false,
                impl: document.displayYui
            };
          }//for ( each theme )
          return;
        }//addThemes()
    };

    /*
     * These are the default styles.
     */

    document.Growl._displayList["plain"] = {
        text: "black",
        style: "background-color: #D0D0D0; border: thin solid black",
        radius: 0,
        opacity: 95,
        duration: 4,
        floatingicon: false
    };

    document.Growl._displayList["smoke"] = {
        text: "white",
        style: "background-color: black;",
        radius: 10,
        opacity: 70,
        duration: 15,
        floatingicon: false
    };

    /*
     * The user will be able to control this.
     */

    document.Growl._displayDefault = "smoke";
}//if ( there is no Growl object )


if (!document.Yowl)
{
    document.Yowl = {
        _dictionary: [],

        notify: function(notificationName, title, description, applicationName, image, sticky, priority)
        {
            var panel = document.Growl.notify(
                notificationName,
                title,
                description,
                applicationName,
                image,
                sticky,
                priority
            );
            return panel;
        },//notify()

        register: function(applicationName, allNotifications, defaultNotifications, iconOfApplication)
        {
            this._dictionary[0] = applicationName;
            this._dictionary[1] = allNotifications;
            this._dictionary[2] = defaultNotifications;
            this._dictionary[3] = iconOfApplication;
            this.setGrowlDelegate(this);
            return;
        },//register()

        setGrowlDelegate: function(delegate)
        {
            document.Growl.setGrowlDelegate(delegate);
            return;
        },//setGrowlDelegate()

        getGrowlDelegate: function()
        {
            return this;
        },//getGrowlDelegate()

        /*
         * The following are for the delegate interface.
         */

        registrationDictionaryForGrowl: function()
        {
            return [ this._dictionary[1], this._dictionary[2] ];
        },

        applicationNameForGrowl: function()
        {
            return this._dictionary[0];
        },

        applicationIconDataForGrowl: function()
        {
            return this._dictionary[3];
        },

        release: function()
        {
            return;
        },//release()

        growlIsReady: function()
        {
            return;
        },

        growlNotificationWasClicked: function(id)
        {
            return;
        },

        growlNotificationTimedOut: function(id)
        {
            return;
        }
    };
}//if ( there is no document.Yowl )

var IFrameObj; // our IFrame object
function callToServer() {
  if (!document.createElement) {return true};
  var IFrameDoc;
  var URL = 'server.html';
  if (!IFrameObj && document.createElement) {
    // create the IFrame and assign a reference to the
    // object to our global variable IFrameObj.
    // this will only happen the first time 
    // callToServer() is called
   try {
      var tempIFrame=document.createElement('iframe');
      tempIFrame.setAttribute('id','RSIFrame');
      tempIFrame.style.border='0px';
      tempIFrame.style.width='0px';
      tempIFrame.style.height='0px';
      IFrameObj = document.body.appendChild(tempIFrame);
      
      if (document.frames) {
        // this is for IE5 Mac, because it will only
        // allow access to the document object
        // of the IFrame if we access it through
        // the document.frames array
        IFrameObj = document.frames['RSIFrame'];
      }
    } catch(exception) {
      // This is for IE5 PC, which does not allow dynamic creation
      // and manipulation of an iframe object. Instead, we'll fake
      // it up by creating our own objects.
      iframeHTML='\<iframe id="RSIFrame" style="';
      iframeHTML+='border:0px;';
      iframeHTML+='width:0px;';
      iframeHTML+='height:0px;';
      iframeHTML+='"><\/iframe>';
      document.body.innerHTML+=iframeHTML;
      IFrameObj = new Object();
      IFrameObj.document = new Object();
      IFrameObj.document.location = new Object();
      IFrameObj.document.location.iframe = document.getElementById('RSIFrame');
      IFrameObj.document.location.replace = function(location) {
        this.iframe.src = location;
      }
    }
  }
  
  if (navigator.userAgent.indexOf('Gecko') !=-1 && !IFrameObj.contentDocument) {
    // we have to give NS6 a fraction of a second
    // to recognize the new IFrame
    setTimeout('callToServer()',10);
    return false;
  }
  
  if (IFrameObj.contentDocument) {
    // For NS6
    IFrameDoc = IFrameObj.contentDocument; 
  } else if (IFrameObj.contentWindow) {
    // For IE5.5 and IE6
    IFrameDoc = IFrameObj.contentWindow.document;
  } else if (IFrameObj.document) {
    // For IE5
    IFrameDoc = IFrameObj.document;
  } else {
    return true;
  }
  
  IFrameDoc.location.replace(URL);
  return false;
}
