extdirect.zope

A Zope 2/3 implementation of extdirect

Using extdirect in Zope is extremely simple, due to a custom ZCML
directive that registers both a BrowserView for the server-side API and a
viewlet to deliver the provider definition to the client.

1. Define your class
   
   e.g., in myapi.py:

   from extdirect.zope import DirectRouter

   class MyApi(DirectRouter):

       def a_method(self):
           return 'A Value'


2. Register the class as a direct router

   <configure xmlns="http://namespaces.zope.org/browser">

     <include package="extdirect.zope" file="meta.zcml"/>

       <directRouter
          name="myapi"
          namespace="MyApp.remote"
          class=".myapi.MyApi"
          />

   </configure>


3. Provide the extdirect viewletManager in your template. 
   If you already have Ext loaded through other means, use the extdirect
   provider; otherwise, you can use the stripped-down Ext.Direct libraries
   provided with this package:

    <tal:block tal:content="structure provider:extdirect+direct.js"/>


4. Call methods at will!

    <script>

      function a_method_callback(result){
          ... do something with result ...
      }

      MyApp.remote.a_method({}, a_method_callback);

    </script>

