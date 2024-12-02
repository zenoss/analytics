## Service Definitions ##

In order to run under Control Center a ZenPack needs to register any services
which it provides (e.g., daemons, commands, etc.) with Control Center.

By default, files in this directory matching the pattern "*.json" will be
processed as service definition files.   The default behavior for discovering
service definitions can be controlled by overriding ZenPack.getServiceDefinition().

The service definition file consists of an object with two key-value pairs:
servicePath and serviceDefinition.  The service path indicates where in the service
hierarchy the service will be installed; the service definition describes the
service to be installed.

A "service path" is a string which applies file-system semantics to the service
hierarchy; i.e., a string of components separated by slashes.  Components are
matched against the tags of candidate services unless they begin with the "="
character, in which case they are matched against the name of the service.
Common usages are "/" to create a root level service and "/hub/collector" to
create a service in every collector.

Examples of the service definition structure may be seen by executing the command

```
$ serviced service list $SERVICE_ID
```

Note that there is a special value for the ImageId field in the service definition.
An empty string indicates that the service should use the same zenoss image used
by the Zope container.

The **ConfigFiles.\<path\>.Content** field in the service definition is
also treated specially.  If that field is not defined or is the empty string,
then the Content will be loaded from the file at the corresponding path in the
-CONFIGS- directory.  If the Content field is non-empty then the config file
will be created with that value.

For more information, see this [example ZenPack][example_zenpack].


[example_zenpack]: https://github.com/zenoss/ZenPacks.zenoss.ExampleService

