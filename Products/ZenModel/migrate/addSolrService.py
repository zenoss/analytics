##############################################################################
#
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import json
import logging
import os
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.1.11")
from servicemigration import HealthCheck
from Products.ZenUtils.path import zenPath

class AddSolrService(Migrate.Step):
    """
    Add Solr service and associated healthchecks.
    """
    version = Migrate.Version(200, 0, 0)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        changed = False

        # If the service lacks Solr, add it now.
        solr = filter(lambda s: s.name == "Solr", ctx.services)
        log.info("Found %i services named 'Solr'." % len(solr))
        if not solr:
            imageid = os.environ['SERVICED_SERVICE_IMAGE']
            log.info("No Solr found; creating new service.")
            new_solr = default_solr_service(imageid)
            infrastructure = ctx.findServices('^[^/]+/Infrastructure$')[0]
            ctx.deployService(json.dumps(new_solr), infrastructure)
            changed = True

        # Remove the zencatalogservice-uri global conf option from the top service
        zenoss = ctx.getTopService()
        global_conf = zenoss.context
        if global_conf and "global.conf.zencatalogservice-uri" in global_conf:
            del global_conf["global.conf.zencatalogservice-uri"]
            changed = True

        # Now healthchecks
        solr_answering_healthcheck = HealthCheck(
            name="solr_answering",
            interval=10.0,
            script="curl -A 'Solr answering healthcheck' -s http://localhost:8983/solr/zenoss_model/admin/ping?wt=json | grep -q '\"status\":\"OK\"'"
        )

        for svc in ctx.services:
            # Remove zencatalogservice, if it still exists
            if svc.name == "zencatalogservice":
                svcid = svc._Service__data['ID']
                # ZEN-28127: during unittests, ctx is an instance of
                # FakeServiceContext which is set to None.
                if ctx._client is not None:
                    ctx._client.deleteService(svcid)
                ctx.services.remove(svc)
                changed = True
                continue
            # Remove zencatalogservice response prereq and add solr one
            for pr in svc.prereqs[:]:
                if pr.name == "zencatalogservice response":
                    svc.prereqs.remove(pr)
                    svc.prereqs.append(sm.Prereq(name='Solr answering', script="""curl -A 'Solr answering prereq' -s http://localhost:8983/solr/zenoss_model/admin/ping?wt=json | grep -q '\"status\":\"OK\"'"""))
                    changed = True
            # If we've got a solr_answering health check, we can stop.
            # Otherwise, remove catalogservice health checks and add Solr ones
            if filter(lambda c: c.name == 'solr_answering', svc.healthChecks):
                continue
            for hc in svc.healthChecks:
                if hc.name == "catalogservice_answering":
                    svc.healthChecks.remove(hc)
                    changed = True

            # Get rid of erroneous "solr" endpoints that some older migrations added and the "zodb_zencatalogservice" endpoint import that zenimpactstate may have
            eps_to_remove = filter(lambda ep: ep.purpose == 'import' and (ep.application == 'solr' or ep.application == 'zodb_zencatalogservice'), svc.endpoints)

            for ep in eps_to_remove:
                changed = True
                svc.endpoints.remove(ep)

            for ep in svc.endpoints:
                if ep.purpose == 'import' and ep.application == 'zodb_.*':
                    svc.healthChecks.append(solr_answering_healthcheck)
                    changed = True
                    break

        filterName = 'solr'
        filename = 'Products/ZenModel/migrate/data/%s-6.0.0.conf' % filterName
        with open(zenPath(filename)) as filterFile:
            try:
                filterDef = filterFile.read()
            except Exception as e:
                log.error("Error reading {0} logfilter file: {1}".format(filename, e))
                return
            log.info("Updating log filter named {0}".format(filterName))
            changed = True
            ctx.addLogFilter(filterName, filterDef)

        if changed:
            ctx.commit()


def default_solr_service(imageid):
    return {
        "ID": "abcd",
        "CPUCommitment": 2,
        "Command": "/bin/supervisord -n -c /opt/solr/zenoss/etc/supervisor.conf",
        "ConfigFiles": {
            "/opt/solr/server/solr/configsets/zenoss_model/conf/solrconfig.xml": {
                "Filename": "/opt/solr/server/solr/configsets/zenoss_model/conf/solrconfig.xml",
                "Owner": "root:root",
                "Permissions": "0664",
                "Content": "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n<!--\n Licensed to the Apache Software Foundation (ASF) under one or more\n contributor license agreements.  See the NOTICE file distributed with\n this work for additional information regarding copyright ownership.\n The ASF licenses this file to You under the Apache License, Version 2.0\n (the \"License\"); you may not use this file except in compliance with\n the License.  You may obtain a copy of the License at\n\n     http://www.apache.org/licenses/LICENSE-2.0\n\n Unless required by applicable law or agreed to in writing, software\n distributed under the License is distributed on an \"AS IS\" BASIS,\n WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n See the License for the specific language governing permissions and\n limitations under the License.\n-->\n\n<!-- \n     For more details about configurations options that may appear in\n     this file, see http://wiki.apache.org/solr/SolrConfigXml. \n-->\n<config>\n  <!-- In all configuration below, a prefix of \"solr.\" for class names\n       is an alias that causes solr to search appropriate packages,\n       including org.apache.solr.(search|update|request|core|analysis)\n\n       You may also specify a fully qualified Java classname if you\n       have your own custom plugins.\n    -->\n\n  <!-- Controls what version of Lucene various components of Solr\n       adhere to.  Generally, you want to use the latest version to\n       get all bug fixes and improvements. It is highly recommended\n       that you fully re-index after changing this setting as it can\n       affect both how text is indexed and queried.\n  -->\n  <luceneMatchVersion>6.5.0</luceneMatchVersion>\n\n  <!-- Data Directory\n\n       Used to specify an alternate directory to hold all index data\n       other than the default ./data under the Solr home.  If\n       replication is in use, this should match the replication\n       configuration.\n    -->\n  <dataDir>${solr.data.dir:}</dataDir>\n\n\n  <!-- The DirectoryFactory to use for indexes.\n       \n       solr.StandardDirectoryFactory is filesystem\n       based and tries to pick the best implementation for the current\n       JVM and platform.  solr.NRTCachingDirectoryFactory, the default,\n       wraps solr.StandardDirectoryFactory and caches small files in memory\n       for better NRT performance.\n\n       One can force a particular implementation via solr.MMapDirectoryFactory,\n       solr.NIOFSDirectoryFactory, or solr.SimpleFSDirectoryFactory.\n\n       solr.RAMDirectoryFactory is memory based, not\n       persistent, and doesn't work with replication.\n    -->\n  <directoryFactory name=\"DirectoryFactory\" \n                    class=\"${solr.directoryFactory:solr.NRTCachingDirectoryFactory}\">\n  </directoryFactory> \n\n  <!-- The CodecFactory for defining the format of the inverted index.\n       The default implementation is SchemaCodecFactory, which is the official Lucene\n       index format, but hooks into the schema to provide per-field customization of\n       the postings lists and per-document values in the fieldType element\n       (postingsFormat/docValuesFormat). Note that most of the alternative implementations\n       are experimental, so if you choose to customize the index format, it's a good\n       idea to convert back to the official format e.g. via IndexWriter.addIndexes(IndexReader)\n       before upgrading to a newer version to avoid unnecessary reindexing.\n  -->\n  <codecFactory class=\"solr.SchemaCodecFactory\"/>\n\n  <schemaFactory class=\"ClassicIndexSchemaFactory\"/>\n\n  <!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n       Index Config - These settings control low-level behavior of indexing\n       Most example settings here show the default value, but are commented\n       out, to more easily see where customizations have been made.\n       \n       Note: This replaces <indexDefaults> and <mainIndex> from older versions\n       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->\n  <indexConfig>\n\n    <!-- LockFactory \n\n         This option specifies which Lucene LockFactory implementation\n         to use.\n      \n         single = SingleInstanceLockFactory - suggested for a\n                  read-only index or when there is no possibility of\n                  another process trying to modify the index.\n         native = NativeFSLockFactory - uses OS native file locking.\n                  Do not use when multiple solr webapps in the same\n                  JVM are attempting to share a single index.\n         simple = SimpleFSLockFactory  - uses a plain file for locking\n\n         Defaults: 'native' is default for Solr3.6 and later, otherwise\n                   'simple' is the default\n\n         More details on the nuances of each LockFactory...\n         http://wiki.apache.org/lucene-java/AvailableLockFactories\n    -->\n    <lockType>${solr.lock.type:native}</lockType>\n\n    <!-- Lucene Infostream\n       \n         To aid in advanced debugging, Lucene provides an \"InfoStream\"\n         of detailed information when indexing.\n\n         Setting the value to true will instruct the underlying Lucene\n         IndexWriter to write its info stream to solr's log. By default,\n         this is enabled here, and controlled through log4j.properties.\n      -->\n     <infoStream>true</infoStream>\n  </indexConfig>\n\n\n  <!-- JMX\n       \n       This example enables JMX if and only if an existing MBeanServer\n       is found, use this if you want to configure JMX through JVM\n       parameters. Remove this to disable exposing Solr configuration\n       and statistics to JMX.\n\n       For more details see http://wiki.apache.org/solr/SolrJmx\n    -->\n  <jmx />\n  <!-- If you want to connect to a particular server, specify the\n       agentId \n    -->\n  <!-- <jmx agentId=\"myAgent\" /> -->\n  <!-- If you want to start a new MBeanServer, specify the serviceUrl -->\n  <!-- <jmx serviceUrl=\"service:jmx:rmi:///jndi/rmi://localhost:9999/solr\"/>\n    -->\n\n  <!-- The default high-performance update handler -->\n  <updateHandler class=\"solr.DirectUpdateHandler2\">\n\n    <!-- Enables a transaction log, used for real-time get, durability, and\n         and solr cloud replica recovery.  The log can grow as big as\n         uncommitted changes to the index, so use of a hard autoCommit\n         is recommended (see below).\n         \"dir\" - the target directory for transaction logs, defaults to the\n                solr data directory.  --> \n    <updateLog>\n      <str name=\"dir\">${solr.ulog.dir:}</str>\n    </updateLog>\n \n    <!-- AutoCommit\n\n         Perform a hard commit automatically under certain conditions.\n         Instead of enabling autoCommit, consider using \"commitWithin\"\n         when adding documents. \n\n         http://wiki.apache.org/solr/UpdateXmlMessages\n\n         maxDocs - Maximum number of documents to add since the last\n                   commit before automatically triggering a new commit.\n\n         maxTime - Maximum amount of time in ms that is allowed to pass\n                   since a document was added before automatically\n                   triggering a new commit. \n         openSearcher - if false, the commit causes recent index changes\n           to be flushed to stable storage, but does not cause a new\n           searcher to be opened to make those changes visible.\n\n         If the updateLog is enabled, then it's highly recommended to\n         have some sort of hard autoCommit to limit the log size.\n      -->\n     <autoCommit> \n       <maxTime>${solr.autoCommit.maxTime:15000}</maxTime> \n       <openSearcher>false</openSearcher> \n     </autoCommit>\n\n    <!-- softAutoCommit is like autoCommit except it causes a\n         'soft' commit which only ensures that changes are visible\n         but does not ensure that data is synced to disk.  This is\n         faster and more near-realtime friendly than a hard commit.\n      -->\n     <autoSoftCommit> \n       <maxTime>${solr.autoSoftCommit.maxTime:-1}</maxTime> \n     </autoSoftCommit>\n\n  </updateHandler>\n  \n  <!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n       Query section - these settings control query time things like caches\n       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ -->\n  <query>\n    <!-- Max Boolean Clauses\n\n         Maximum number of clauses in each BooleanQuery,  an exception\n         is thrown if exceeded.\n\n         ** WARNING **\n         \n         This option actually modifies a global Lucene property that\n         will affect all SolrCores.  If multiple solrconfig.xml files\n         disagree on this property, the value at any given moment will\n         be based on the last SolrCore to be initialized.\n         \n      -->\n    <maxBooleanClauses>20000</maxBooleanClauses>\n\n\n    <!-- Solr Internal Query Caches\n\n         There are two implementations of cache available for Solr,\n         LRUCache, based on a synchronized LinkedHashMap, and\n         FastLRUCache, based on a ConcurrentHashMap.  \n\n         FastLRUCache has faster gets and slower puts in single\n         threaded operation and thus is generally faster than LRUCache\n         when the hit ratio of the cache is high (> 75%), and may be\n         faster under other scenarios on multi-cpu systems.\n    -->\n\n    <!-- Filter Cache\n\n         Cache used by SolrIndexSearcher for filters (DocSets),\n         unordered sets of *all* documents that match a query.  When a\n         new searcher is opened, its caches may be prepopulated or\n         \"autowarmed\" using data from caches in the old searcher.\n         autowarmCount is the number of items to prepopulate.  For\n         LRUCache, the autowarmed items will be the most recently\n         accessed items.\n\n         Parameters:\n           class - the SolrCache implementation LRUCache or\n               (LRUCache or FastLRUCache)\n           size - the maximum number of entries in the cache\n           initialSize - the initial capacity (number of entries) of\n               the cache.  (see java.util.HashMap)\n           autowarmCount - the number of entries to prepopulate from\n               and old cache.  \n      -->\n    <filterCache class=\"solr.FastLRUCache\"\n                 size=\"512\"\n                 initialSize=\"512\"\n                 autowarmCount=\"0\"/>\n\n    <!-- Query Result Cache\n         \n         Caches results of searches - ordered lists of document ids\n         (DocList) based on a query, a sort, and the range of documents requested.  \n      -->\n    <queryResultCache class=\"solr.LRUCache\"\n                     size=\"512\"\n                     initialSize=\"512\"\n                     autowarmCount=\"0\"/>\n   \n    <!-- Document Cache\n\n         Caches Lucene Document objects (the stored fields for each\n         document).  Since Lucene internal document ids are transient,\n         this cache will not be autowarmed.  \n      -->\n    <documentCache class=\"solr.LRUCache\"\n                   size=\"512\"\n                   initialSize=\"512\"\n                   autowarmCount=\"0\"/>\n    \n    <!-- custom cache currently used by block join --> \n    <cache name=\"perSegFilter\"\n      class=\"solr.search.LRUCache\"\n      size=\"10\"\n      initialSize=\"0\"\n      autowarmCount=\"10\"\n      regenerator=\"solr.NoOpRegenerator\" />\n\n    <!-- Lazy Field Loading\n\n         If true, stored fields that are not requested will be loaded\n         lazily.  This can result in a significant speed improvement\n         if the usual case is to not load all stored fields,\n         especially if the skipped fields are large compressed text\n         fields.\n    -->\n    <enableLazyFieldLoading>true</enableLazyFieldLoading>\n\n   <!-- Result Window Size\n\n        An optimization for use with the queryResultCache.  When a search\n        is requested, a superset of the requested number of document ids\n        are collected.  For example, if a search for a particular query\n        requests matching documents 10 through 19, and queryWindowSize is 50,\n        then documents 0 through 49 will be collected and cached.  Any further\n        requests in that range can be satisfied via the cache.  \n     -->\n   <queryResultWindowSize>20</queryResultWindowSize>\n\n   <!-- Maximum number of documents to cache for any entry in the\n        queryResultCache. \n     -->\n   <queryResultMaxDocsCached>200</queryResultMaxDocsCached>\n\n    <!-- Use Cold Searcher\n\n         If a search request comes in and there is no current\n         registered searcher, then immediately register the still\n         warming searcher and use it.  If \"false\" then all requests\n         will block until the first searcher is done warming.\n      -->\n    <useColdSearcher>false</useColdSearcher>\n\n    <!-- Max Warming Searchers\n         \n         Maximum number of searchers that may be warming in the\n         background concurrently.  An error is returned if this limit\n         is exceeded.\n\n         Recommend values of 1-2 for read-only slaves, higher for\n         masters w/o cache warming.\n      -->\n    <maxWarmingSearchers>2</maxWarmingSearchers>\n\n  </query>\n\n\n  <!-- Request Dispatcher\n\n       This section contains instructions for how the SolrDispatchFilter\n       should behave when processing requests for this SolrCore.\n\n       handleSelect is a legacy option that affects the behavior of requests\n       such as /select?qt=XXX\n\n       handleSelect=\"true\" will cause the SolrDispatchFilter to process\n       the request and dispatch the query to a handler specified by the \n       \"qt\" param, assuming \"/select\" isn't already registered.\n\n       handleSelect=\"false\" will cause the SolrDispatchFilter to\n       ignore \"/select\" requests, resulting in a 404 unless a handler\n       is explicitly registered with the name \"/select\"\n\n       handleSelect=\"true\" is not recommended for new users, but is the default\n       for backwards compatibility\n    -->\n  <requestDispatcher handleSelect=\"false\" >\n    <!-- Request Parsing\n\n         These settings indicate how Solr Requests may be parsed, and\n         what restrictions may be placed on the ContentStreams from\n         those requests\n\n         enableRemoteStreaming - enables use of the stream.file\n         and stream.url parameters for specifying remote streams.\n\n         multipartUploadLimitInKB - specifies the max size (in KiB) of\n         Multipart File Uploads that Solr will allow in a Request.\n         \n         formdataUploadLimitInKB - specifies the max size (in KiB) of\n         form data (application/x-www-form-urlencoded) sent via\n         POST. You can use POST to pass request parameters not\n         fitting into the URL.\n         \n         addHttpRequestToContext - if set to true, it will instruct\n         the requestParsers to include the original HttpServletRequest\n         object in the context map of the SolrQueryRequest under the \n         key \"httpRequest\". It will not be used by any of the existing\n         Solr components, but may be useful when developing custom \n         plugins.\n         \n         *** WARNING ***\n         The settings below authorize Solr to fetch remote files, You\n         should make sure your system has some authentication before\n         using enableRemoteStreaming=\"true\"\n\n      --> \n    <requestParsers enableRemoteStreaming=\"true\" \n                    multipartUploadLimitInKB=\"2048000\"\n                    formdataUploadLimitInKB=\"2048\"\n                    addHttpRequestToContext=\"false\"/>\n\n    <!-- HTTP Caching\n\n         Set HTTP caching related parameters (for proxy caches and clients).\n\n         The options below instruct Solr not to output any HTTP Caching\n         related headers\n      -->\n    <httpCaching never304=\"true\" />\n\n  </requestDispatcher>\n\n  <!-- Request Handlers \n\n       http://wiki.apache.org/solr/SolrRequestHandler\n\n       Incoming queries will be dispatched to a specific handler by name\n       based on the path specified in the request.\n\n       Legacy behavior: If the request path uses \"/select\" but no Request\n       Handler has that name, and if handleSelect=\"true\" has been specified in\n       the requestDispatcher, then the Request Handler is dispatched based on\n       the qt parameter.  Handlers without a leading '/' are accessed this way\n       like so: http://host/app/[core/]select?qt=name  If no qt is\n       given, then the requestHandler that declares default=\"true\" will be\n       used or the one named \"standard\".\n\n       If a Request Handler is declared with startup=\"lazy\", then it will\n       not be initialized until the first request that uses it.\n\n    -->\n  <!-- SearchHandler\n\n       http://wiki.apache.org/solr/SearchHandler\n\n       For processing Search Queries, the primary Request Handler\n       provided with Solr is \"SearchHandler\" It delegates to a sequent\n       of SearchComponents (see below) and supports distributed\n       queries across multiple shards\n    -->\n  <requestHandler name=\"/select\" class=\"solr.SearchHandler\">\n    <!-- default values for query parameters can be specified, these\n         will be overridden by parameters in the request\n      -->\n     <lst name=\"defaults\">\n       <str name=\"echoParams\">explicit</str>\n       <int name=\"rows\">10</int>\n     </lst>\n\n    </requestHandler>\n\n  <!-- A request handler that returns indented JSON by default -->\n  <requestHandler name=\"/query\" class=\"solr.SearchHandler\">\n     <lst name=\"defaults\">\n       <str name=\"echoParams\">explicit</str>\n       <str name=\"wt\">json</str>\n       <str name=\"indent\">true</str>\n       <str name=\"df\">text</str>\n     </lst>\n  </requestHandler>\n\n  <!--\n    The export request handler is used to export full sorted result sets.\n    Do not change these defaults.\n  -->\n  <requestHandler name=\"/export\" class=\"solr.SearchHandler\">\n    <lst name=\"invariants\">\n      <str name=\"rq\">{!xport}</str>\n      <str name=\"wt\">xsort</str>\n      <str name=\"distrib\">false</str>\n    </lst>\n\n    <arr name=\"components\">\n      <str>query</str>\n    </arr>\n  </requestHandler>\n\n\n  <initParams path=\"/update/**,/query,/select,/tvrh,/elevate,/spell\">\n    <lst name=\"defaults\">\n      <str name=\"df\">text</str>\n    </lst>\n  </initParams>\n\n  <!-- Field Analysis Request Handler\n\n       RequestHandler that provides much the same functionality as\n       analysis.jsp. Provides the ability to specify multiple field\n       types and field names in the same request and outputs\n       index-time and query-time analysis for each of them.\n\n       Request parameters are:\n       analysis.fieldname - field name whose analyzers are to be used\n\n       analysis.fieldtype - field type whose analyzers are to be used\n       analysis.fieldvalue - text for index-time analysis\n       q (or analysis.q) - text for query time analysis\n       analysis.showmatch (true|false) - When set to true and when\n           query analysis is performed, the produced tokens of the\n           field value analysis will be marked as \"matched\" for every\n           token that is produces by the query analysis\n   -->\n  <requestHandler name=\"/analysis/field\" \n                  startup=\"lazy\"\n                  class=\"solr.FieldAnalysisRequestHandler\" />\n\n\n  <!-- Document Analysis Handler\n\n       http://wiki.apache.org/solr/AnalysisRequestHandler\n\n       An analysis handler that provides a breakdown of the analysis\n       process of provided documents. This handler expects a (single)\n       content stream with the following format:\n\n       <docs>\n         <doc>\n           <field name=\"id\">1</field>\n           <field name=\"name\">The Name</field>\n           <field name=\"text\">The Text Value</field>\n         </doc>\n         <doc>...</doc>\n         <doc>...</doc>\n         ...\n       </docs>\n\n    Note: Each document must contain a field which serves as the\n    unique key. This key is used in the returned response to associate\n    an analysis breakdown to the analyzed document.\n\n    Like the FieldAnalysisRequestHandler, this handler also supports\n    query analysis by sending either an \"analysis.query\" or \"q\"\n    request parameter that holds the query text to be analyzed. It\n    also supports the \"analysis.showmatch\" parameter which when set to\n    true, all field tokens that match the query tokens will be marked\n    as a \"match\". \n  -->\n  <requestHandler name=\"/analysis/document\" \n                  class=\"solr.DocumentAnalysisRequestHandler\" \n                  startup=\"lazy\" />\n\n  <!-- Echo the request contents back to the client -->\n  <requestHandler name=\"/debug/dump\" class=\"solr.DumpRequestHandler\" >\n    <lst name=\"defaults\">\n     <str name=\"echoParams\">explicit</str> \n     <str name=\"echoHandler\">true</str>\n    </lst>\n  </requestHandler>\n  \n\n\n  <!-- Search Components\n\n       Search components are registered to SolrCore and used by \n       instances of SearchHandler (which can access them by name)\n       \n       By default, the following components are available:\n       \n       <searchComponent name=\"query\"     class=\"solr.QueryComponent\" />\n       <searchComponent name=\"facet\"     class=\"solr.FacetComponent\" />\n       <searchComponent name=\"mlt\"       class=\"solr.MoreLikeThisComponent\" />\n       <searchComponent name=\"highlight\" class=\"solr.HighlightComponent\" />\n       <searchComponent name=\"stats\"     class=\"solr.StatsComponent\" />\n       <searchComponent name=\"debug\"     class=\"solr.DebugComponent\" />\n       \n     -->\n\n  <!-- Terms Component\n\n       http://wiki.apache.org/solr/TermsComponent\n\n       A component to return terms and document frequency of those\n       terms\n    -->\n  <searchComponent name=\"terms\" class=\"solr.TermsComponent\"/>\n\n  <!-- A request handler for demonstrating the terms component -->\n  <requestHandler name=\"/terms\" class=\"solr.SearchHandler\" startup=\"lazy\">\n     <lst name=\"defaults\">\n      <bool name=\"terms\">true</bool>\n      <bool name=\"distrib\">false</bool>\n    </lst>     \n    <arr name=\"components\">\n      <str>terms</str>\n    </arr>\n  </requestHandler>\n\n  <!-- Request handler for health checks; does a simplistic query -->\n  <requestHandler name=\"/ping\" class=\"solr.PingRequestHandler\">\n      <lst name=\"invariants\">\n          <str name=\"q\">solrpingquery</str>\n      </lst>\n      <lst name=\"defaults\">\n          <str name=\"echoParams\">all</str>\n          <str name=\"df\">id</str>\n      </lst>\n  </requestHandler>\n\n  <!-- Legacy config for the admin interface -->\n  <admin>\n    <defaultQuery>*:*</defaultQuery>\n  </admin>\n\n</config>\n"
            },
            "/opt/solr/server/solr/solr.xml": {
                "FileName": "/opt/solr/server/solr/solr.xml",
                "Owner": "root:root",
                "Permissions": "0664",
                "Content": "<?xml version=\"1.0\" encoding=\"UTF-8\" ?>\n<!--\n Licensed to the Apache Software Foundation (ASF) under one or more\n contributor license agreements.  See the NOTICE file distributed with\n this work for additional information regarding copyright ownership.\n The ASF licenses this file to You under the Apache License, Version 2.0\n (the \"License\"); you may not use this file except in compliance with\n the License.  You may obtain a copy of the License at\n\n     http://www.apache.org/licenses/LICENSE-2.0\n\n Unless required by applicable law or agreed to in writing, software\n distributed under the License is distributed on an \"AS IS\" BASIS,\n WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n See the License for the specific language governing permissions and\n limitations under the License.\n-->\n\n<!--\n   This is an example of a simple \"solr.xml\" file for configuring one or \n   more Solr Cores, as well as allowing Cores to be added, removed, and \n   reloaded via HTTP requests.\n\n   More information about options available in this configuration file, \n   and Solr Core administration can be found online:\n   http://wiki.apache.org/solr/CoreAdmin\n-->\n\n<solr>\n\n  <solrcloud>\n\n    <str name=\"host\">${host:}</str>\n    <int name=\"hostPort\">${jetty.port:8983}</int>\n    <str name=\"hostContext\">${hostContext:solr}</str>\n\n    <bool name=\"genericCoreNodeNames\">${genericCoreNodeNames:true}</bool>\n\n    <int name=\"zkClientTimeout\">${zkClientTimeout:30000}</int>\n    <int name=\"distribUpdateSoTimeout\">${distribUpdateSoTimeout:600000}</int>\n    <int name=\"distribUpdateConnTimeout\">${distribUpdateConnTimeout:60000}</int>\n\n  </solrcloud>\n\n  <shardHandlerFactory name=\"shardHandlerFactory\" class=\"HttpShardHandlerFactory\">\n    <int name=\"socketTimeout\">${socketTimeout:600000}</int>\n    <int name=\"connTimeout\">${connTimeout:60000}</int>\n  </shardHandlerFactory>\n\n</solr>\n"
            },
            "/opt/solr/zenoss/etc/solr.in.sh": {
                "Filename": "/opt/solr/zenoss/etc/solr.in.sh",
                "Owner": "root:root",
                "Permissions": "0664",
                "Content": "# This file is injected by ControlCenter with container-specific parameters\n# ZK_HOST={{with $zks := (child (child (parent .) \"HBase\") \"ZooKeeper\").Instances }}{{range (each $zks)}}127.0.0.1:{{plus 2181 .}}{{if ne (plus 1 .) $zks}},{{end}}{{end}}{{end}}/solr\nSOLR_JAVA_MEM=\"-Xmx{{.RAMCommitment}}\"\n\n"
            },
            "/opt/solr/zenoss/etc/supervisor.conf": {
                "Filename": "/opt/solr/zenoss/etc/supervisor.conf",
                "Owner": "root:root",
                "Permissions": "0664",
                "Content": "[supervisord]\nnodaemon=true\nlogfile = /opt/zenoss/log/solr_supervisord.log\n\n[unix_http_server]\nfile=/tmp/supervisor.sock\n\n[supervisorctl]\nserverurl=unix:///tmp/supervisor.sock ; use a unix:// URL  for a unix socket\n\n[rpcinterface:supervisor]\nsupervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface\n\n[program:solr]\ncommand=setuser zenoss /opt/solr/zenoss/bin/start-solr -cloud -Dbootstrap_confdir=/opt/solr/server/solr/configsets/zenoss_model/conf -Dcollection.configName=zenoss_model -Dsolr.jetty.request.header.size=1000000\nautorestart=true\nautostart=true\nstartsecs=5\npriority=1\n\n[program:solr_metrics]\ncommand=/usr/bin/python /opt/zenoss/bin/metrics/solrstats.py\nautorestart=true\nautostart=true\nstartsecs=5\n\n; logging\nredirect_stderr=true\nstdout_logfile_maxbytes=10MB\nstdout_logfile_backups=10\nstdout_logfile=/opt/zenoss/log/%(program_name)s.log\n"
            }
        },
        "Description": "Solr Cloud",
        "EmergencyShutdownLevel": 1,
        "Endpoints": [
            {
                "Application": "zodb_solr",
                "Name": "solr",
                "PortNumber": 8983,
                "Protocol": "tcp",
                "Purpose": "export",
                "VHostList": [
                    {
                        "Enabled": False,
                        "Name": "solr"
                    }
                ]
            }
        ],
        "HealthChecks": {
            "answering": {
                "Interval": 10.0,
                "Script": "curl -A 'Solr answering healthcheck' -s http://localhost:8983/solr/zenoss_model/admin/ping?wt=json | grep -q '\"status\":\"OK\"'"
            },
            "embedded_zk_answering": {
                "Interval": 10.0,
                "Script": "{ echo stats; sleep 1; } | nc 127.0.0.1 9983 | grep -q Zookeeper"
            },
            "zk_connected": {
                "Interval": 10.0,
                "Script": "curl -A 'Solr zk_connected healthcheck' -s http://localhost:8983/solr/zenoss_model/admin/ping?wt=json | grep -q '\"zkConnected\":true'"
            }
        },
        "ImageID": imageid,
        "Instances": {
            "Default": 1,
            "Max": 1,
            "Min": 1
        },
        "Launch": "auto",
        "LogConfigs": [
            {
                "filters": [
                    "solr"
                ],
                "path": "/var/solr/logs/solr.log",
                "type": "solr"
            }
        ],
        "Name": "Solr",
        "Prereqs": [],
        "RAMCommitment": "1G",
        "StartLevel": 1,
        "Tags": [
            "daemon"
        ],
        "Volumes": [
            {
                "ContainerPath": "/opt/solr/server/logs",
                "Owner": "zenoss:zenoss",
                "Permission": "0750",
                "ResourcePath": "solr-logs-{{.InstanceID}}"
            },
            {
                "ContainerPath": "/var/solr/data",
                "Owner": "zenoss:zenoss",
                "Permission": "0750",
                "ResourcePath": "solr-{{.InstanceID}}"
            }
        ],
        "Version": ""
    }

AddSolrService()
