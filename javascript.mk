# Makefile for Zenoss Javascript files

JS_BASEDIR = src/Products/ZenUI3/browser/resources
JSB_FILE = $(JS_BASEDIR)/builder.jsb2

#
# JS_DEPLOYPATH - the output directory relative to the repo root;
# e.g. src/Products/ZenUI3/browser/resources/deploy
#
JS_DEPLOYPATH = $(JS_BASEDIR)/$(shell python2 -c "import json; print json.load(open('$(JSB_FILE)'))['deployDir']")

BUILDJS_COMMAND_ARGS = -d $(JS_BASEDIR)

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
	@buildjs $(BUILDJS_COMMAND_ARGS)
