
==============================
Internationalization (i18n)
==============================

To add a new locale
====================

Create the locale Domain
---------------------------
This example will use the Japanese locale (`ja`)

#. Determine the locale name (eg `en`, `fr`, `ja`).  The list of locale names can
   be determeined from here http://www.iana.org/assignments/language-subtag-registry
#. Create the directory structure for the new locale domain
::

   $ cd $ZENHOME/Products/ZenUI3/locales
   $ mkdir ja/LC_MESSAGES

Translate the Text
----------------------
The translation "domain" used by Zenoss is ``zenoss``, so the
filename used to store the translations must match that name (ie ``zenoss.po``, ``zenoss.mo``)
#. Copy an existing translation file containing the source strings.
::

   $ cp fr/LC_MESSAGES/zenoss.po ja/LC_MESSAGES/zenoss.po

#. Update the translations as appropriate.
#. Create the binary form of the translations, which are for faster machine lookup.
::

   $ msgfmt -o zenoss.mo zenoss.po
 
Restart the Webserver
----------------------
For Core users:

::

 $ zopectl restart

For Enterprise users:

::

 $ zenwebserver restart


To test in a browser
=======================
Web browsers support languages by keeping a list
of languages that the user desires, and going through
that list until the web server finds a language that
it can support.

Firefox
-----------
#. Go to 'File' -> 'Preferences'
#. Click on the 'Content' tab.
#. Under the 'Languages' area, click on the 'Choose...' button.
#. Add a language, or move the desired language up to the top.
#. Click the 'OK' button
#. Close the Preferences dialog.
#. Navigate to the desired page.

Chrome
--------
#. Go to 'Chrome' -> 'Preferences'
#. On the new page, click on the 'Show advanced settings...' link at the bottom of the page.
#. Under the 'Languages' area, click on the 'Language settings...' button.
#. Add a language, or move the desired language up to the top.
#. Click the 'OK' button
#. Close the Preferences page.
#. Navigate to the desired page.



To Add a Device with a Non-ASCII Name
==============================================
Current Zenoss only supports adding devices with all ASCII names.
To add a device with a non-ASCII name, use the following procedure:

#. Go to Infrastructure page.
#. Click on the 'Add Device' button and select 'Add Single Device' to bring up a dialog.
#. In the 'Name of IP' field, use an ASCII name.
#. In the 'Title' field, use any Unicode name that is appropriate.
#. Add in any other information and then click on the 'Add' button.

