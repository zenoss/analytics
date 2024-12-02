Products.ZenUI3.navigation package
=========================

This package allows for two-tiered viewlet-based navigation menus. Primary menu
items may be parents of secondary menu items; when the primary menu item is
selected, the secondary menu will contain its child items.

Test setup: 

    >>> from Zope2.App import zcml
    >>> import Products.ZenUI3.navigation
    >>> zcml.load_config('testing.zcml', package=Products.ZenUI3.navigation)

And some dumb security:

    >>> from AccessControl import SecurityManager
    >>> from Products.Five.viewlet.tests import UnitTestSecurityPolicy
    >>> from AccessControl.SecurityManagement import newSecurityManager
    >>> from AccessControl.SecurityManagement import noSecurityManager
    >>> noSecurityManager()
    >>> oldPolicy = SecurityManager.setSecurityPolicy(UnitTestSecurityPolicy())

Goals:

We (and third parties) should be able to add items to the primary and secondary
navigation of the app. Secondary items should only appear when their primary
item is selected. Primary and secondary items should know that they are
selected based on the URL of the request. Items should be able to be ordered.
    
First, let's register a primary manager:

    >>> zcml.load_string("""
    ... <configure xmlns="http://namespaces.zope.org/browser">
    ...
    ...   <viewletManager  
    ...    name="primary_nav"
    ...    provides=".interfaces.IPrimaryNavigationMenu"
    ...    class=".manager.PrimaryNavigationManager"
    ...    permission="zope2.Public" />
    ...
    ... </configure>
    ... """)

Now let's look up the manager. To do that, we create some dummy objects:

    >>> import zope.interface
    >>> from ExtensionClass import Base
    >>> class Content(Base):
    ...     zope.interface.implements(zope.interface.Interface)
    >>> content = Content()

    >>> from zope.publisher.browser import TestRequest
    >>> request = TestRequest()

    >>> from zope.publisher.browser import BrowserView
    >>> view = BrowserView(content, request)

And do the lookup:

    >>> import zope.component
    >>> from Products.ZenUI3.navigation import interfaces
    >>> manager = zope.component.getMultiAdapter(
    ...     (content, request, view),
    ...     interfaces.IPrimaryNavigationMenu, name="primary_nav")
    >>> manager
    <zope.viewlet.manager.<ViewletManager providing IPrimaryNavigationMenu...>

No viewlets are registered yet:

    >>> manager.update()
    >>> manager.viewlets
    []

Now, let's add a primary navigation item:

    >>> zcml.load_string("""
    ... <configure xmlns="http://namespaces.zope.org/browser">
    ...  <viewlet
    ...     name="Events"
    ...     url="/events"
    ...     manager=".interfaces.IPrimaryNavigationMenu"
    ...     class=".menuitem.PrimaryNavigationMenuItem"
    ...     permission="zope2.Public"
    ...     />
    ... </configure>
    ... """)

When we look in the adapter registry, we'll find it:

    >>> from zope.viewlet import interfaces
    >>> viewlet = zope.component.getMultiAdapter(
    ...     (content, request, view, manager), interfaces.IViewlet,
    ...     name="Events")
    >>> viewlet
    <zope.viewlet.metaconfigure.PrimaryNavigationMenuItem object...>
    >>> viewlet.title
    u'Events'
    >>> viewlet.url
    u'/events'
    >>> viewlet.manager == manager
    True

Coming in from the other side, we can see that the manager now has an item:

    >>> manager.update()
    >>> manager.viewlets
    [<zope.viewlet.metaconfigure.PrimaryNavigationMenuItem...>]

We can also see that this menu item is not selected, because the request URL
doesn't match:

    >>> viewlet = manager.viewlets[0]
    >>> request.getURL()
    'http://127.0.0.1'
    >>> viewlet.url
    u'/events'
    >>> viewlet.selected
    False

If, however, make a request that does match our item's URL:

    >>> request = TestRequest(environ={'SCRIPT_NAME':'/events'})
    >>> request.getURL()
    'http://127.0.0.1/events'

And look up the manager using that request:

    >>> from Products.ZenUI3.navigation import interfaces
    >>> manager = zope.component.getMultiAdapter(
    ...     (content, request, view),
    ...     interfaces.IPrimaryNavigationMenu, name="primary_nav")
    >>> manager.update()

Our viewlet indicates that it is active, and provides a CSS class to match:

    >>> viewlet = manager.viewlets[0]
    >>> viewlet.url
    u'/events'
    >>> viewlet.selected
    True
    >>> viewlet.css
    'active'

Let's add a few more items, just to hammer the point home. This time, let's
specify weights; if a weight is specified, that will be the index of the item:

    >>> zcml.load_string("""
    ... <configure xmlns="http://namespaces.zope.org/browser">
    ...  <viewlet
    ...     name="Dashboard"
    ...     weight="2"
    ...     url="/dashboard"
    ...     manager=".interfaces.IPrimaryNavigationMenu"
    ...     class=".menuitem.PrimaryNavigationMenuItem"
    ...     permission="zope2.Public"
    ...     />
    ...  <viewlet
    ...     name="IT Infrastructure"
    ...     weight="1"
    ...     url="/devices"
    ...     manager=".interfaces.IPrimaryNavigationMenu"
    ...     class=".menuitem.PrimaryNavigationMenuItem"
    ...     permission="zope2.Public"
    ...     />
    ... </configure>
    ... """)

    >>> manager.update()
    >>> for viewlet in manager.viewlets:
    ...     print viewlet.title, viewlet.selected
    Events True
    IT Infrastructure False
    Dashboard False


So, that's a single tier of navigation. Now let's add a second.

    >>> zcml.load_string("""
    ... <configure xmlns="http://namespaces.zope.org/browser">
    ...
    ...   <viewletManager  
    ...    name="secondary_nav"
    ...    provides=".interfaces.ISecondaryNavigationMenu"
    ...    class=".manager.SecondaryNavigationManager"
    ...    permission="zope2.Public" />
    ...
    ... </configure>
    ... """)

We add items to the secondary navigation the same way as to the primary, except
we of course use a different interface and class. Most importantly, however, we
specify the name of the parent menu item in the primary navigation with the
parentItem attribute. We'll add a few for control:

    >>> zcml.load_string("""
    ... <configure xmlns="http://namespaces.zope.org/browser">
    ...
    ...  <viewlet
    ...     name="Event Console"
    ...     parentItem="Events"
    ...     weight="1"
    ...     url="/evconsole"
    ...     manager=".interfaces.ISecondaryNavigationMenu"
    ...     class=".menuitem.SecondaryNavigationMenuItem"
    ...     permission="zope2.Public"
    ...     />
    ...
    ...  <viewlet
    ...     name="Notifications"
    ...     parentItem="Events"
    ...     weight="2"
    ...     url="/notifications"
    ...     manager=".interfaces.ISecondaryNavigationMenu"
    ...     class=".menuitem.SecondaryNavigationMenuItem"
    ...     permission="zope2.Public"
    ...     />
    ...
    ...  <viewlet
    ...     name="Devices"
    ...     parentItem="IT Infrastructure"
    ...     weight="0"
    ...     url="/device-view"
    ...     manager=".interfaces.ISecondaryNavigationMenu"
    ...     class=".menuitem.SecondaryNavigationMenuItem"
    ...     permission="zope2.Public"
    ...     />
    ...
    ... </configure>
    ... """)

The secondary manager determines which viewlets to return based on the primary
navigation item selected. So, still using our '/events' request, let's look up
both:

    >>> primary_mgr = zope.component.getMultiAdapter(
    ...     (content, request, view),
    ...     interfaces.IPrimaryNavigationMenu, name="primary_nav")
    >>> secondary_mgr = zope.component.getMultiAdapter(
    ...     (content, request, view),
    ...     interfaces.ISecondaryNavigationMenu, name="secondary_nav")

    >>> primary_mgr
    <zope.viewlet.manager.<ViewletManager providing IPrimaryNavigationMenu...>

    >>> secondary_mgr
    <zope.viewlet.manager.<ViewletManager providing ISecondaryNavigationMenu...>

We can see that the secondary manager has three items registered:

    >>> primary_mgr.update()
    >>> secondary_mgr.update()
    >>> primary_mgr.viewlets[0].title
    u'Events'
    >>> [v.title for v in secondary_mgr.viewlets]
    [u'Devices', u'Event Console', u'Notifications']

The secondary manager knows how to determine which primary item is active, and
from that can determine which of its own viewlets should be displayed:

    >>> secondary_mgr.getActivePrimaryName()
    u'Events'
    >>> sorted([v.title for v in secondary_mgr.getActiveViewlets()])
    [u'Event Console', u'Notifications']

Similarly, the primary manager is smart enough to understand that when one of
its children is selected, it should be selected too. Let's make a new request that points to a secondary menu item:

    >>> request = TestRequest(environ={'SCRIPT_NAME':'/evconsole'})
    >>> request.getURL()
    'http://127.0.0.1/evconsole'

Then re-look up our managers and see which items are selected:

    >>> primary_mgr = zope.component.getMultiAdapter(
    ...     (content, request, view),
    ...     interfaces.IPrimaryNavigationMenu, name="primary_nav")
    >>> secondary_mgr = zope.component.getMultiAdapter(
    ...     (content, request, view),
    ...     interfaces.ISecondaryNavigationMenu, name="secondary_nav")
    >>> primary_mgr.update()
    >>> secondary_mgr.update()

    >>> for v in primary_mgr.viewlets: 
    ...     print v.title, v.selected
    Events True
    IT Infrastructure False
    Dashboard False

    >>> for v in secondary_mgr.getActiveViewlets():
    ...     print v.title, v.selected
    Event Console True
    Notifications False


