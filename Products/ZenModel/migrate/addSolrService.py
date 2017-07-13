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
sm.require("1.0.0")
from servicemigration import HealthCheck

class AddSolrService(Migrate.Step):
    """
    Add Solr service and associated healthchecks.
    """
    version = Migrate.Version(116, 0, 0)

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
                ctx._client.deleteService(svcid)
                ctx.services.remove(svc)
                changed = True
                continue
            # If we've got a solr_answering health check, we can stop.
            # Otherwise, remove catalogservice health checks and add Solr ones
            if filter(lambda c: c.name == 'solr_answering', svc.healthChecks):
                continue
            for hc in svc.healthChecks:
                if hc.name == "catalogservice_answering":
                    svc.healthChecks.remove(hc)
                    changed = True
            for ep in svc.endpoints:
                if ep.purpose == 'import' and ep.application == 'zodb_.*':
                    svc.healthChecks.append(solr_answering_healthcheck)
                    changed = True
                    break

        if changed:
            ctx.commit()


def default_solr_service(imageid):
    return {
        "CPUCommitment": 2,
        "Command": "setuser zenoss /opt/solr/zenoss/bin/start-solr -cloud -Dbootstrap_confdir=/opt/solr/server/solr/configsets/zenoss_model/conf -Dcollection.configName=zenoss_model",
        "ConfigFiles": {
            "/opt/solr/server/solr/configsets/zenoss_model/conf/solrconfig.xml": {
                "Filename": "/opt/solr/server/solr/configsets/zenoss_model/conf/solrconfig.xml",
                "Owner": "root:root",
                "Permissions": "0664",
                "Content": "\u003c?xml version=\"1.0\" encoding=\"UTF-8\" ?\u003e\n\u003c!--\n Licensed to the Apache Software Foundation (ASF) under one or more\n contributor license agreements.  See the NOTICE file distributed with\n this work for additional information regarding copyright ownership.\n The ASF licenses this file to You under the Apache License, Version 2.0\n (the \"License\"); you may not use this file except in compliance with\n the License.  You may obtain a copy of the License at\n\n     http://www.apache.org/licenses/LICENSE-2.0\n\n Unless required by applicable law or agreed to in writing, software\n distributed under the License is distributed on an \"AS IS\" BASIS,\n WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n See the License for the specific language governing permissions and\n limitations under the License.\n--\u003e\n\n\u003c!-- \n     For more details about configurations options that may appear in\n     this file, see http://wiki.apache.org/solr/SolrConfigXml. \n--\u003e\n\u003cconfig\u003e\n  \u003c!-- In all configuration below, a prefix of \"solr.\" for class names\n       is an alias that causes solr to search appropriate packages,\n       including org.apache.solr.(search|update|request|core|analysis)\n\n       You may also specify a fully qualified Java classname if you\n       have your own custom plugins.\n    --\u003e\n\n  \u003c!-- Controls what version of Lucene various components of Solr\n       adhere to.  Generally, you want to use the latest version to\n       get all bug fixes and improvements. It is highly recommended\n       that you fully re-index after changing this setting as it can\n       affect both how text is indexed and queried.\n  --\u003e\n  \u003cluceneMatchVersion\u003e6.5.0\u003c/luceneMatchVersion\u003e\n\n  \u003c!-- Data Directory\n\n       Used to specify an alternate directory to hold all index data\n       other than the default ./data under the Solr home.  If\n       replication is in use, this should match the replication\n       configuration.\n    --\u003e\n  \u003cdataDir\u003e${solr.data.dir:}\u003c/dataDir\u003e\n\n\n  \u003c!-- The DirectoryFactory to use for indexes.\n       \n       solr.StandardDirectoryFactory is filesystem\n       based and tries to pick the best implementation for the current\n       JVM and platform.  solr.NRTCachingDirectoryFactory, the default,\n       wraps solr.StandardDirectoryFactory and caches small files in memory\n       for better NRT performance.\n\n       One can force a particular implementation via solr.MMapDirectoryFactory,\n       solr.NIOFSDirectoryFactory, or solr.SimpleFSDirectoryFactory.\n\n       solr.RAMDirectoryFactory is memory based, not\n       persistent, and doesn't work with replication.\n    --\u003e\n  \u003cdirectoryFactory name=\"DirectoryFactory\" \n                    class=\"${solr.directoryFactory:solr.NRTCachingDirectoryFactory}\"\u003e\n  \u003c/directoryFactory\u003e \n\n  \u003c!-- The CodecFactory for defining the format of the inverted index.\n       The default implementation is SchemaCodecFactory, which is the official Lucene\n       index format, but hooks into the schema to provide per-field customization of\n       the postings lists and per-document values in the fieldType element\n       (postingsFormat/docValuesFormat). Note that most of the alternative implementations\n       are experimental, so if you choose to customize the index format, it's a good\n       idea to convert back to the official format e.g. via IndexWriter.addIndexes(IndexReader)\n       before upgrading to a newer version to avoid unnecessary reindexing.\n  --\u003e\n  \u003ccodecFactory class=\"solr.SchemaCodecFactory\"/\u003e\n\n  \u003cschemaFactory class=\"ClassicIndexSchemaFactory\"/\u003e\n\n  \u003c!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n       Index Config - These settings control low-level behavior of indexing\n       Most example settings here show the default value, but are commented\n       out, to more easily see where customizations have been made.\n       \n       Note: This replaces \u003cindexDefaults\u003e and \u003cmainIndex\u003e from older versions\n       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ --\u003e\n  \u003cindexConfig\u003e\n\n    \u003c!-- LockFactory \n\n         This option specifies which Lucene LockFactory implementation\n         to use.\n      \n         single = SingleInstanceLockFactory - suggested for a\n                  read-only index or when there is no possibility of\n                  another process trying to modify the index.\n         native = NativeFSLockFactory - uses OS native file locking.\n                  Do not use when multiple solr webapps in the same\n                  JVM are attempting to share a single index.\n         simple = SimpleFSLockFactory  - uses a plain file for locking\n\n         Defaults: 'native' is default for Solr3.6 and later, otherwise\n                   'simple' is the default\n\n         More details on the nuances of each LockFactory...\n         http://wiki.apache.org/lucene-java/AvailableLockFactories\n    --\u003e\n    \u003clockType\u003e${solr.lock.type:native}\u003c/lockType\u003e\n\n    \u003c!-- Lucene Infostream\n       \n         To aid in advanced debugging, Lucene provides an \"InfoStream\"\n         of detailed information when indexing.\n\n         Setting the value to true will instruct the underlying Lucene\n         IndexWriter to write its info stream to solr's log. By default,\n         this is enabled here, and controlled through log4j.properties.\n      --\u003e\n     \u003cinfoStream\u003etrue\u003c/infoStream\u003e\n  \u003c/indexConfig\u003e\n\n\n  \u003c!-- JMX\n       \n       This example enables JMX if and only if an existing MBeanServer\n       is found, use this if you want to configure JMX through JVM\n       parameters. Remove this to disable exposing Solr configuration\n       and statistics to JMX.\n\n       For more details see http://wiki.apache.org/solr/SolrJmx\n    --\u003e\n  \u003cjmx /\u003e\n  \u003c!-- If you want to connect to a particular server, specify the\n       agentId \n    --\u003e\n  \u003c!-- \u003cjmx agentId=\"myAgent\" /\u003e --\u003e\n  \u003c!-- If you want to start a new MBeanServer, specify the serviceUrl --\u003e\n  \u003c!-- \u003cjmx serviceUrl=\"service:jmx:rmi:///jndi/rmi://localhost:9999/solr\"/\u003e\n    --\u003e\n\n  \u003c!-- The default high-performance update handler --\u003e\n  \u003cupdateHandler class=\"solr.DirectUpdateHandler2\"\u003e\n\n    \u003c!-- Enables a transaction log, used for real-time get, durability, and\n         and solr cloud replica recovery.  The log can grow as big as\n         uncommitted changes to the index, so use of a hard autoCommit\n         is recommended (see below).\n         \"dir\" - the target directory for transaction logs, defaults to the\n                solr data directory.  --\u003e \n    \u003cupdateLog\u003e\n      \u003cstr name=\"dir\"\u003e${solr.ulog.dir:}\u003c/str\u003e\n    \u003c/updateLog\u003e\n \n    \u003c!-- AutoCommit\n\n         Perform a hard commit automatically under certain conditions.\n         Instead of enabling autoCommit, consider using \"commitWithin\"\n         when adding documents. \n\n         http://wiki.apache.org/solr/UpdateXmlMessages\n\n         maxDocs - Maximum number of documents to add since the last\n                   commit before automatically triggering a new commit.\n\n         maxTime - Maximum amount of time in ms that is allowed to pass\n                   since a document was added before automatically\n                   triggering a new commit. \n         openSearcher - if false, the commit causes recent index changes\n           to be flushed to stable storage, but does not cause a new\n           searcher to be opened to make those changes visible.\n\n         If the updateLog is enabled, then it's highly recommended to\n         have some sort of hard autoCommit to limit the log size.\n      --\u003e\n     \u003cautoCommit\u003e \n       \u003cmaxTime\u003e${solr.autoCommit.maxTime:15000}\u003c/maxTime\u003e \n       \u003copenSearcher\u003efalse\u003c/openSearcher\u003e \n     \u003c/autoCommit\u003e\n\n    \u003c!-- softAutoCommit is like autoCommit except it causes a\n         'soft' commit which only ensures that changes are visible\n         but does not ensure that data is synced to disk.  This is\n         faster and more near-realtime friendly than a hard commit.\n      --\u003e\n     \u003cautoSoftCommit\u003e \n       \u003cmaxTime\u003e${solr.autoSoftCommit.maxTime:-1}\u003c/maxTime\u003e \n     \u003c/autoSoftCommit\u003e\n\n  \u003c/updateHandler\u003e\n  \n  \u003c!-- ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n       Query section - these settings control query time things like caches\n       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ --\u003e\n  \u003cquery\u003e\n    \u003c!-- Max Boolean Clauses\n\n         Maximum number of clauses in each BooleanQuery,  an exception\n         is thrown if exceeded.\n\n         ** WARNING **\n         \n         This option actually modifies a global Lucene property that\n         will affect all SolrCores.  If multiple solrconfig.xml files\n         disagree on this property, the value at any given moment will\n         be based on the last SolrCore to be initialized.\n         \n      --\u003e\n    \u003cmaxBooleanClauses\u003e20000\u003c/maxBooleanClauses\u003e\n\n\n    \u003c!-- Solr Internal Query Caches\n\n         There are two implementations of cache available for Solr,\n         LRUCache, based on a synchronized LinkedHashMap, and\n         FastLRUCache, based on a ConcurrentHashMap.  \n\n         FastLRUCache has faster gets and slower puts in single\n         threaded operation and thus is generally faster than LRUCache\n         when the hit ratio of the cache is high (\u003e 75%), and may be\n         faster under other scenarios on multi-cpu systems.\n    --\u003e\n\n    \u003c!-- Filter Cache\n\n         Cache used by SolrIndexSearcher for filters (DocSets),\n         unordered sets of *all* documents that match a query.  When a\n         new searcher is opened, its caches may be prepopulated or\n         \"autowarmed\" using data from caches in the old searcher.\n         autowarmCount is the number of items to prepopulate.  For\n         LRUCache, the autowarmed items will be the most recently\n         accessed items.\n\n         Parameters:\n           class - the SolrCache implementation LRUCache or\n               (LRUCache or FastLRUCache)\n           size - the maximum number of entries in the cache\n           initialSize - the initial capacity (number of entries) of\n               the cache.  (see java.util.HashMap)\n           autowarmCount - the number of entries to prepopulate from\n               and old cache.  \n      --\u003e\n    \u003cfilterCache class=\"solr.FastLRUCache\"\n                 size=\"512\"\n                 initialSize=\"512\"\n                 autowarmCount=\"0\"/\u003e\n\n    \u003c!-- Query Result Cache\n         \n         Caches results of searches - ordered lists of document ids\n         (DocList) based on a query, a sort, and the range of documents requested.  \n      --\u003e\n    \u003cqueryResultCache class=\"solr.LRUCache\"\n                     size=\"512\"\n                     initialSize=\"512\"\n                     autowarmCount=\"0\"/\u003e\n   \n    \u003c!-- Document Cache\n\n         Caches Lucene Document objects (the stored fields for each\n         document).  Since Lucene internal document ids are transient,\n         this cache will not be autowarmed.  \n      --\u003e\n    \u003cdocumentCache class=\"solr.LRUCache\"\n                   size=\"512\"\n                   initialSize=\"512\"\n                   autowarmCount=\"0\"/\u003e\n    \n    \u003c!-- custom cache currently used by block join --\u003e \n    \u003ccache name=\"perSegFilter\"\n      class=\"solr.search.LRUCache\"\n      size=\"10\"\n      initialSize=\"0\"\n      autowarmCount=\"10\"\n      regenerator=\"solr.NoOpRegenerator\" /\u003e\n\n    \u003c!-- Lazy Field Loading\n\n         If true, stored fields that are not requested will be loaded\n         lazily.  This can result in a significant speed improvement\n         if the usual case is to not load all stored fields,\n         especially if the skipped fields are large compressed text\n         fields.\n    --\u003e\n    \u003cenableLazyFieldLoading\u003etrue\u003c/enableLazyFieldLoading\u003e\n\n   \u003c!-- Result Window Size\n\n        An optimization for use with the queryResultCache.  When a search\n        is requested, a superset of the requested number of document ids\n        are collected.  For example, if a search for a particular query\n        requests matching documents 10 through 19, and queryWindowSize is 50,\n        then documents 0 through 49 will be collected and cached.  Any further\n        requests in that range can be satisfied via the cache.  \n     --\u003e\n   \u003cqueryResultWindowSize\u003e20\u003c/queryResultWindowSize\u003e\n\n   \u003c!-- Maximum number of documents to cache for any entry in the\n        queryResultCache. \n     --\u003e\n   \u003cqueryResultMaxDocsCached\u003e200\u003c/queryResultMaxDocsCached\u003e\n\n    \u003c!-- Use Cold Searcher\n\n         If a search request comes in and there is no current\n         registered searcher, then immediately register the still\n         warming searcher and use it.  If \"false\" then all requests\n         will block until the first searcher is done warming.\n      --\u003e\n    \u003cuseColdSearcher\u003efalse\u003c/useColdSearcher\u003e\n\n    \u003c!-- Max Warming Searchers\n         \n         Maximum number of searchers that may be warming in the\n         background concurrently.  An error is returned if this limit\n         is exceeded.\n\n         Recommend values of 1-2 for read-only slaves, higher for\n         masters w/o cache warming.\n      --\u003e\n    \u003cmaxWarmingSearchers\u003e2\u003c/maxWarmingSearchers\u003e\n\n  \u003c/query\u003e\n\n\n  \u003c!-- Request Dispatcher\n\n       This section contains instructions for how the SolrDispatchFilter\n       should behave when processing requests for this SolrCore.\n\n       handleSelect is a legacy option that affects the behavior of requests\n       such as /select?qt=XXX\n\n       handleSelect=\"true\" will cause the SolrDispatchFilter to process\n       the request and dispatch the query to a handler specified by the \n       \"qt\" param, assuming \"/select\" isn't already registered.\n\n       handleSelect=\"false\" will cause the SolrDispatchFilter to\n       ignore \"/select\" requests, resulting in a 404 unless a handler\n       is explicitly registered with the name \"/select\"\n\n       handleSelect=\"true\" is not recommended for new users, but is the default\n       for backwards compatibility\n    --\u003e\n  \u003crequestDispatcher handleSelect=\"false\" \u003e\n    \u003c!-- Request Parsing\n\n         These settings indicate how Solr Requests may be parsed, and\n         what restrictions may be placed on the ContentStreams from\n         those requests\n\n         enableRemoteStreaming - enables use of the stream.file\n         and stream.url parameters for specifying remote streams.\n\n         multipartUploadLimitInKB - specifies the max size (in KiB) of\n         Multipart File Uploads that Solr will allow in a Request.\n         \n         formdataUploadLimitInKB - specifies the max size (in KiB) of\n         form data (application/x-www-form-urlencoded) sent via\n         POST. You can use POST to pass request parameters not\n         fitting into the URL.\n         \n         addHttpRequestToContext - if set to true, it will instruct\n         the requestParsers to include the original HttpServletRequest\n         object in the context map of the SolrQueryRequest under the \n         key \"httpRequest\". It will not be used by any of the existing\n         Solr components, but may be useful when developing custom \n         plugins.\n         \n         *** WARNING ***\n         The settings below authorize Solr to fetch remote files, You\n         should make sure your system has some authentication before\n         using enableRemoteStreaming=\"true\"\n\n      --\u003e \n    \u003crequestParsers enableRemoteStreaming=\"true\" \n                    multipartUploadLimitInKB=\"2048000\"\n                    formdataUploadLimitInKB=\"2048\"\n                    addHttpRequestToContext=\"false\"/\u003e\n\n    \u003c!-- HTTP Caching\n\n         Set HTTP caching related parameters (for proxy caches and clients).\n\n         The options below instruct Solr not to output any HTTP Caching\n         related headers\n      --\u003e\n    \u003chttpCaching never304=\"true\" /\u003e\n\n  \u003c/requestDispatcher\u003e\n\n  \u003c!-- Request Handlers \n\n       http://wiki.apache.org/solr/SolrRequestHandler\n\n       Incoming queries will be dispatched to a specific handler by name\n       based on the path specified in the request.\n\n       Legacy behavior: If the request path uses \"/select\" but no Request\n       Handler has that name, and if handleSelect=\"true\" has been specified in\n       the requestDispatcher, then the Request Handler is dispatched based on\n       the qt parameter.  Handlers without a leading '/' are accessed this way\n       like so: http://host/app/[core/]select?qt=name  If no qt is\n       given, then the requestHandler that declares default=\"true\" will be\n       used or the one named \"standard\".\n\n       If a Request Handler is declared with startup=\"lazy\", then it will\n       not be initialized until the first request that uses it.\n\n    --\u003e\n  \u003c!-- SearchHandler\n\n       http://wiki.apache.org/solr/SearchHandler\n\n       For processing Search Queries, the primary Request Handler\n       provided with Solr is \"SearchHandler\" It delegates to a sequent\n       of SearchComponents (see below) and supports distributed\n       queries across multiple shards\n    --\u003e\n  \u003crequestHandler name=\"/select\" class=\"solr.SearchHandler\"\u003e\n    \u003c!-- default values for query parameters can be specified, these\n         will be overridden by parameters in the request\n      --\u003e\n     \u003clst name=\"defaults\"\u003e\n       \u003cstr name=\"echoParams\"\u003eexplicit\u003c/str\u003e\n       \u003cint name=\"rows\"\u003e10\u003c/int\u003e\n     \u003c/lst\u003e\n\n    \u003c/requestHandler\u003e\n\n  \u003c!-- A request handler that returns indented JSON by default --\u003e\n  \u003crequestHandler name=\"/query\" class=\"solr.SearchHandler\"\u003e\n     \u003clst name=\"defaults\"\u003e\n       \u003cstr name=\"echoParams\"\u003eexplicit\u003c/str\u003e\n       \u003cstr name=\"wt\"\u003ejson\u003c/str\u003e\n       \u003cstr name=\"indent\"\u003etrue\u003c/str\u003e\n       \u003cstr name=\"df\"\u003etext\u003c/str\u003e\n     \u003c/lst\u003e\n  \u003c/requestHandler\u003e\n\n  \u003c!--\n    The export request handler is used to export full sorted result sets.\n    Do not change these defaults.\n  --\u003e\n  \u003crequestHandler name=\"/export\" class=\"solr.SearchHandler\"\u003e\n    \u003clst name=\"invariants\"\u003e\n      \u003cstr name=\"rq\"\u003e{!xport}\u003c/str\u003e\n      \u003cstr name=\"wt\"\u003exsort\u003c/str\u003e\n      \u003cstr name=\"distrib\"\u003efalse\u003c/str\u003e\n    \u003c/lst\u003e\n\n    \u003carr name=\"components\"\u003e\n      \u003cstr\u003equery\u003c/str\u003e\n    \u003c/arr\u003e\n  \u003c/requestHandler\u003e\n\n\n  \u003cinitParams path=\"/update/**,/query,/select,/tvrh,/elevate,/spell\"\u003e\n    \u003clst name=\"defaults\"\u003e\n      \u003cstr name=\"df\"\u003etext\u003c/str\u003e\n    \u003c/lst\u003e\n  \u003c/initParams\u003e\n\n  \u003c!-- Field Analysis Request Handler\n\n       RequestHandler that provides much the same functionality as\n       analysis.jsp. Provides the ability to specify multiple field\n       types and field names in the same request and outputs\n       index-time and query-time analysis for each of them.\n\n       Request parameters are:\n       analysis.fieldname - field name whose analyzers are to be used\n\n       analysis.fieldtype - field type whose analyzers are to be used\n       analysis.fieldvalue - text for index-time analysis\n       q (or analysis.q) - text for query time analysis\n       analysis.showmatch (true|false) - When set to true and when\n           query analysis is performed, the produced tokens of the\n           field value analysis will be marked as \"matched\" for every\n           token that is produces by the query analysis\n   --\u003e\n  \u003crequestHandler name=\"/analysis/field\" \n                  startup=\"lazy\"\n                  class=\"solr.FieldAnalysisRequestHandler\" /\u003e\n\n\n  \u003c!-- Document Analysis Handler\n\n       http://wiki.apache.org/solr/AnalysisRequestHandler\n\n       An analysis handler that provides a breakdown of the analysis\n       process of provided documents. This handler expects a (single)\n       content stream with the following format:\n\n       \u003cdocs\u003e\n         \u003cdoc\u003e\n           \u003cfield name=\"id\"\u003e1\u003c/field\u003e\n           \u003cfield name=\"name\"\u003eThe Name\u003c/field\u003e\n           \u003cfield name=\"text\"\u003eThe Text Value\u003c/field\u003e\n         \u003c/doc\u003e\n         \u003cdoc\u003e...\u003c/doc\u003e\n         \u003cdoc\u003e...\u003c/doc\u003e\n         ...\n       \u003c/docs\u003e\n\n    Note: Each document must contain a field which serves as the\n    unique key. This key is used in the returned response to associate\n    an analysis breakdown to the analyzed document.\n\n    Like the FieldAnalysisRequestHandler, this handler also supports\n    query analysis by sending either an \"analysis.query\" or \"q\"\n    request parameter that holds the query text to be analyzed. It\n    also supports the \"analysis.showmatch\" parameter which when set to\n    true, all field tokens that match the query tokens will be marked\n    as a \"match\". \n  --\u003e\n  \u003crequestHandler name=\"/analysis/document\" \n                  class=\"solr.DocumentAnalysisRequestHandler\" \n                  startup=\"lazy\" /\u003e\n\n  \u003c!-- Echo the request contents back to the client --\u003e\n  \u003crequestHandler name=\"/debug/dump\" class=\"solr.DumpRequestHandler\" \u003e\n    \u003clst name=\"defaults\"\u003e\n     \u003cstr name=\"echoParams\"\u003eexplicit\u003c/str\u003e \n     \u003cstr name=\"echoHandler\"\u003etrue\u003c/str\u003e\n    \u003c/lst\u003e\n  \u003c/requestHandler\u003e\n  \n\n\n  \u003c!-- Search Components\n\n       Search components are registered to SolrCore and used by \n       instances of SearchHandler (which can access them by name)\n       \n       By default, the following components are available:\n       \n       \u003csearchComponent name=\"query\"     class=\"solr.QueryComponent\" /\u003e\n       \u003csearchComponent name=\"facet\"     class=\"solr.FacetComponent\" /\u003e\n       \u003csearchComponent name=\"mlt\"       class=\"solr.MoreLikeThisComponent\" /\u003e\n       \u003csearchComponent name=\"highlight\" class=\"solr.HighlightComponent\" /\u003e\n       \u003csearchComponent name=\"stats\"     class=\"solr.StatsComponent\" /\u003e\n       \u003csearchComponent name=\"debug\"     class=\"solr.DebugComponent\" /\u003e\n       \n     --\u003e\n\n  \u003c!-- Terms Component\n\n       http://wiki.apache.org/solr/TermsComponent\n\n       A component to return terms and document frequency of those\n       terms\n    --\u003e\n  \u003csearchComponent name=\"terms\" class=\"solr.TermsComponent\"/\u003e\n\n  \u003c!-- A request handler for demonstrating the terms component --\u003e\n  \u003crequestHandler name=\"/terms\" class=\"solr.SearchHandler\" startup=\"lazy\"\u003e\n     \u003clst name=\"defaults\"\u003e\n      \u003cbool name=\"terms\"\u003etrue\u003c/bool\u003e\n      \u003cbool name=\"distrib\"\u003efalse\u003c/bool\u003e\n    \u003c/lst\u003e     \n    \u003carr name=\"components\"\u003e\n      \u003cstr\u003eterms\u003c/str\u003e\n    \u003c/arr\u003e\n  \u003c/requestHandler\u003e\n\n  \u003c!-- Request handler for health checks; does a simplistic query --\u003e\n  \u003crequestHandler name=\"/ping\" class=\"solr.PingRequestHandler\"\u003e\n      \u003clst name=\"invariants\"\u003e\n          \u003cstr name=\"q\"\u003esolrpingquery\u003c/str\u003e\n      \u003c/lst\u003e\n      \u003clst name=\"defaults\"\u003e\n          \u003cstr name=\"echoParams\"\u003eall\u003c/str\u003e\n          \u003cstr name=\"df\"\u003eid\u003c/str\u003e\n      \u003c/lst\u003e\n  \u003c/requestHandler\u003e\n\n  \u003c!-- Legacy config for the admin interface --\u003e\n  \u003cadmin\u003e\n    \u003cdefaultQuery\u003e*:*\u003c/defaultQuery\u003e\n  \u003c/admin\u003e\n\n\u003c/config\u003e\n"
            },
            "/opt/solr/server/solr/solr.xml": {
                "FileName": "/opt/solr/server/solr/solr.xml",
                "Owner": "root:root",
                "Permissions": "0664",
                "Content": "\u003c?xml version=\"1.0\" encoding=\"UTF-8\" ?\u003e\n\u003c!--\n Licensed to the Apache Software Foundation (ASF) under one or more\n contributor license agreements.  See the NOTICE file distributed with\n this work for additional information regarding copyright ownership.\n The ASF licenses this file to You under the Apache License, Version 2.0\n (the \"License\"); you may not use this file except in compliance with\n the License.  You may obtain a copy of the License at\n\n     http://www.apache.org/licenses/LICENSE-2.0\n\n Unless required by applicable law or agreed to in writing, software\n distributed under the License is distributed on an \"AS IS\" BASIS,\n WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n See the License for the specific language governing permissions and\n limitations under the License.\n--\u003e\n\n\u003c!--\n   This is an example of a simple \"solr.xml\" file for configuring one or \n   more Solr Cores, as well as allowing Cores to be added, removed, and \n   reloaded via HTTP requests.\n\n   More information about options available in this configuration file, \n   and Solr Core administration can be found online:\n   http://wiki.apache.org/solr/CoreAdmin\n--\u003e\n\n\u003csolr\u003e\n\n  \u003csolrcloud\u003e\n\n    \u003cstr name=\"host\"\u003e${host:}\u003c/str\u003e\n    \u003cint name=\"hostPort\"\u003e${jetty.port:8983}\u003c/int\u003e\n    \u003cstr name=\"hostContext\"\u003e${hostContext:solr}\u003c/str\u003e\n\n    \u003cbool name=\"genericCoreNodeNames\"\u003e${genericCoreNodeNames:true}\u003c/bool\u003e\n\n    \u003cint name=\"zkClientTimeout\"\u003e${zkClientTimeout:30000}\u003c/int\u003e\n    \u003cint name=\"distribUpdateSoTimeout\"\u003e${distribUpdateSoTimeout:600000}\u003c/int\u003e\n    \u003cint name=\"distribUpdateConnTimeout\"\u003e${distribUpdateConnTimeout:60000}\u003c/int\u003e\n\n  \u003c/solrcloud\u003e\n\n  \u003cshardHandlerFactory name=\"shardHandlerFactory\" class=\"HttpShardHandlerFactory\"\u003e\n    \u003cint name=\"socketTimeout\"\u003e${socketTimeout:600000}\u003c/int\u003e\n    \u003cint name=\"connTimeout\"\u003e${connTimeout:60000}\u003c/int\u003e\n  \u003c/shardHandlerFactory\u003e\n\n\u003c/solr\u003e\n"
            },
            "/opt/solr/zenoss/etc/solr.in.sh": {
                "Filename": "/opt/solr/zenoss/etc/solr.in.sh",
                "Owner": "root:root",
                "Permissions": "0664",
                "Content": "# This file is injected by ControlCenter with container-specific parameters\n# ZK_HOST={{with $zks := (child (child (parent .) \"HBase\") \"ZooKeeper\").Instances }}{{range (each $zks)}}127.0.0.1:{{plus 2181 .}}{{if ne (plus 1 .) $zks}},{{end}}{{end}}{{end}}/solr\n\n"
            }
        },
        "Description": "Solr Cloud",
        "EmergencyShutdownLevel": 1,
        "Endpoints": [
            {
                "Application": "solr",
                "Name": "solr",
                "PortNumber": 8983,
                "Protocol": "tcp",
                "Purpose": "export",
                "Vhosts": [
                    "solr"
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
        ]
    }

AddSolrService()
