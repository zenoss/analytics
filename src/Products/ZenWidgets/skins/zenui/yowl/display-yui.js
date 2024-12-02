if (!document.displayYui)
{
    function panel(id)
    {
        this._panel = new YAHOO.widget.Module(
                "smoke-notification-" + id,
                {
                    visible: false
                }
            );

        this.setMessage = function(notification)
            {
        			  var style = "-moz-border-radius: " + notification.radius + "px; "
        			    + "filter: alpha(opacity=" + notification.opacity + "); opacity: " + (notification.opacity / 100) + "; "
        			    + notification.style;

                this._panel.setBody(
                    "<div class='notification " + notification.displayName + " " + notification.priority + "' style='color: " + notification.text + "'>"
                        + "<div class='background' style='" + style + "'></div>"
                        + "<div class='icon'>"
                            + ((notification.iconData) ? "<img src='" + notification.iconData + "' />" : "")
                        + "</div>"
                        + "<div class='title'>" + notification.title + "</div>"
                        + "<div class='text'>" + notification.description + "</div>"
                    + "</div>"
                );
                this._panel.render(document.displayYui._containerId);
                return;
            };//setMessage()

        this.registerForClick = function(f)
            {
                this._panel.element.onclick = f;
                return;
            };//registerForClick

        this.show = function()
            {
                this._panel.show();
                return;
            };//show()

        this.destroy = function()
            {
                /*
                 * We kick off a fade out animation, and when it's complete
                 * we do the actual destroy.
                 */

                var anim = new YAHOO.util.Anim(
                    this._panel.id,
                    { opacity: { to: 0 } },
                    1,
                    YAHOO.util.Easing.easeOut
                );
                var pThis = this;
                anim.onComplete.subscribe(
                    function ()
                    {
                        if (pThis._panel)
                        {
                            pThis._panel.destroy();
                            pThis._panel = null;
                        }
                    }
                );
                anim.animate();
                return;
            };//destory()
    };//panel()

    document.displayYui = {
        _containerId: "yui_notification_container",
        _initialised: false,
        _notificationContainer: null,
        _notifyCount: 0,

        init: function()
            {
                if (!this._notificationContainer)
                {
                    var el = document.createElement("div");

                    el.setAttribute("id", this._containerId);
                    document.body.appendChild(el);

                    this._notificationContainer = el;

                    if (false)
                    this._notificationContainer = new YAHOO.widget.Overlay(
                        this._containerId,
                        {
                            //xy: [600, 0 ],
                            context: [document.body, "tl", "tl"],
                            visible: false,
                            width: "300px",
                            constraintoviewport: true
                        }
                    );
    
                    /*
                     * Instantiate the container for the messages.
                     */
    
                    if (this._notificationContainer)
                    {
                        ////this._notificationContainer.setBody("hello");
                        //this._notificationContainer.render(document.body);
                        //this._notificationContainer.show();
                        this._initialised = true;
                    }
                }//if ( there is no notification container )
                return this._initialised;
            },//init

        createPanel: function()
            {
                return new panel(this._notifyCount++);
            }//createPanel
    }//YUI object

    document.Growl._displayList["plain"].impl = document.displayYui;
    document.Growl._displayList["smoke"].impl = document.displayYui;
}//if ( the YUI module is not initialised )
