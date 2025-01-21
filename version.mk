BRANCH_NAME = $(shell git symbolic-ref --short HEAD)
UPSTREAM = $(shell git config --get branch.$(BRANCH_NAME).merge)
ifeq ($(UPSTREAM),)
BRANCH ?= $(BRANCH_NAME)
else
BRANCH ?= $(shell git rev-parse --symbolic-full-name --abbrev-ref @{upstream})
endif
VERSION_BRANCH = $(shell echo "$(BRANCH_NAME)" | tr A-Z-/ a-z.)

DESCRIBE = $(shell git describe --tags --long --always $(BRANCH))
DESC_LIST = $(subst -, ,$(DESCRIBE))
ifeq ($(words $(DESC_LIST)),3)
COUNT = $(word 2,$(DESC_LIST))
SHA = $(word 3,$(DESC_LIST))
else
COUNT = $(shell git rev-list --count $(BRANCH))
SHA = $(word 1,$(DESC_LIST))
endif

REV_SUFFIX = $(or\
	$(if $(findstring master,$(BRANCH)),""),\
	$(if $(findstring develop,$(BRANCH)),.dev$(COUNT)),\
	$(if $(findstring release/,$(BRANCH)),rc$(COUNT)),\
	$(if $(findstring hotfix/,$(BRANCH)),rc$(COUNT)),\
	$(if $(findstring feature/,$(BRANCH)),.dev$(COUNT)+$(VERSION_BRANCH)),\
	$(if $(findstring bugfix/,$(BRANCH)),.dev$(COUNT)+$(VERSION_BRANCH)),\
	.dev0+badbranch\
)
BASE_VERSION = $(shell cat VERSION)
VERSION = $(BASE_VERSION)$(REV_SUFFIX)

SDIST = prodbin-$(VERSION).tar.gz
WHEEL = prodbin-$(VERSION)-py2-none-any.whl
