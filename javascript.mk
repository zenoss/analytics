#
# Makefile for Zenoss Javascript files
#
# Approximately 100+ individual zenoss javascript files are compressed into
# a single 'minified' file using a Sencha tool called JSBuilder. The
# minification process is orchestrated by a json-structured jsb2 build
# file:
#
#                                                   +--------------+
# Products/ZenUI3/browser/resources/builder.jsb2 -->|    sencha    |
# Products/ZenUI3/browser/resources/js/*/*.js ----->|   minifier   |-->zenoss-compiled.js
#                                                   |--------------|
#                                                   |JSBuilder2.jar|
#                                                   +--------------+
#
# The jsb2 file defines the output file (e.g. zenoss-compiled.js) and the
# output directory (e.g. resources/js/deploy), so we parse the jsb2 file to
# get those settings.
#---------------------------------------------------------------------------#

JS_BASEDIR = src/Products/ZenUI3/browser/resources
JSB_FILE   = $(JS_BASEDIR)/builder.jsb2

#
# JS_DEPLOYPATH - the output directory relative to the repo root;
# e.g. src/Products/ZenUI3/browser/resources/deploy
#
JS_DEPLOYPATH = $(JS_BASEDIR)/$(shell python2 -c "import json; print json.load(open('$(JSB_FILE)'))['deployDir']")

# BUILDJS - path to the `buildjs` command
BUILDJS = $(shell which buildjs)

ifeq ($(BUILDJS),)
$(error The buildjs command not found. Please install the jsbuilder package.)
endif

BUILDJS_COMMAND = buildjs -d $(JS_BASEDIR)

# Dependencies for compilation
JSB_SOURCES = $(shell python2 -c "import json, os.path; print ' '.join(os.path.join('$(JS_BASEDIR)', e['path'], e['text']) for e in json.load(open('$(JSB_FILE)'))['pkgs'][0]['fileIncludes'])")

JSB_TARGETS = $(JS_DEPLOYPATH)/zenoss-compiled.js $(JS_DEPLOYPATH)/zenoss-compiled-debug.js

.PHONY: build-javascript
build-javascript: $(JSB_TARGETS)

.PHONY: clean-javascript
clean-javascript:
	@-rm -vrf $(JS_DEPLOYPATH)

$(JSB_TARGETS): $(JSB_SOURCES)
	@echo "Minifying $(JS_BASEDIR)/js -> $@"
ifeq ($(DOCKER),)
	$(BUILDJS_COMMAND)
else
	$(DOCKER_USER) $(BUILDJS_COMMAND)
endif
