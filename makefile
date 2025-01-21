include version.mk
include javascript.mk
include migration.mk

.DEFAULT_GOAL := build

.PHONY: build
build:
	@docker build -t zenoss/prodbin-build .
	@docker run --rm -v $(shell pwd):/work -w /work zenoss/prodbin-build make -f wheel.mk

.PHONY: clean
clean: clean-javascript clean-migration
	@make -f wheel.mk clean-wheel
