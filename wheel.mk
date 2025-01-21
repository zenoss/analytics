include version.mk
include javascript.mk
include migration.mk

.DEFAULT_GOAL := $(WHEEL)

package_version: VERSION
	@echo $(VERSION) > $@

.PHONY: clean
clean-wheel:
	rm -f $(WHEEL) $(SDIST) package_version

$(WHEEL): $(JSB_TARGETS) $(MIGRATE_VERSION) VERSION setup.py MANIFEST.in setup.cfg SCHEMA_VERSION package_version
	python2 -m build -xn
