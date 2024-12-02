MIGRATE_VERSION = src/Products/ZenModel/ZMigrateVersion.py

# The SCHEMA_* values define the DB schema version used for upgrades.
# See the topic "Managing Migrate.Version" in src/Products/ZenModel/migrate/README.md
# for more information about setting these values.

pick_version_part = $(word $(1),$(subst ., ,$(2)))

SCHEMA_VERSION  = $(shell cat SCHEMA_VERSION)
SCHEMA_MAJOR    = $(call pick_version_part,1,$(SCHEMA_VERSION))
SCHEMA_MINOR    = $(call pick_version_part,2,$(SCHEMA_VERSION))
SCHEMA_REVISION = $(call pick_version_part,3,$(SCHEMA_VERSION))

.PHONY: clean-migration
clean-migration:
	rm -f $(MIGRATE_VERSION)

# Exists for backward compatibility
.PHONY: generate-zversion
generate-zversion: generate-zmigrateversion

.PHONY: generate-zmigrateversion
generate-zmigrateversion: $(MIGRATE_VERSION)

$(MIGRATE_VERSION): $(MIGRATE_VERSION).in SCHEMA_VERSION
	@echo "Generating ZMigrateVersion.py"
	@sed \
	    -e "s/%SCHEMA_MAJOR%/$(SCHEMA_MAJOR)/g" \
	    -e "s/%SCHEMA_MINOR%/$(SCHEMA_MINOR)/g" \
	    -e "s/%SCHEMA_REVISION%/$(SCHEMA_REVISION)/g" \
	    $< > $@

# The target replace-zmigrationversion should be used just prior to release to lock
# down the schema versions for a particular release
.PHONY: replace-zmigrateversion
replace-zmigrateversion:
	@echo Replacing SCHEMA_MAJOR with $(SCHEMA_MAJOR)
	@echo Replacing SCHEMA_MINOR with $(SCHEMA_MINOR)
	@echo Replacing SCHEMA_REVISION with $(SCHEMA_REVISION)
	@cd src/Products/ZenModel/migrate; \
	    for file in `grep -l ZMigrateVersion *.py`; do \
	        sed \
	            -i \
	            -e "/ZMigrateVersion/d" \
				-e "s/SCHEMA_MAJOR/$(SCHEMA_MAJOR)/g" \
				-e "s/SCHEMA_MINOR/$(SCHEMA_MINOR)/g" \
				-e "s/SCHEMA_REVISION/$(SCHEMA_REVISION)/g" \
	            $$file; \
	    done

SCHEMA_FOUND = $(shell grep Migrate.Version src/Products/ZenModel/migrate/*.py  | grep SCHEMA_ | cut -f1 -d':')

# The target verify-explicit-zmigrateversion should be invoked as a first step in all release
# builds to verify that all of the SCHEMA_* variables were replaced with an actual numeric value.
.PHONY: verify-explicit-zmigrateversion
verify-explicit-zmigrateversion:
ifeq ($(SCHEMA_FOUND),)
	@echo "Good - no SCHEMA_* variables found: $(SCHEMA_FOUND)"
else
	$(info Some SCHEMA_* variables found in src/Products/ZenModel/migrate/*.py:)
	$(info )
	$(foreach item,$(SCHEMA_FOUND),$(info $(item)))
	$(info )
	$(error At least one of the SCHEMA_* variables found)
endif
