SHELL := /bin/bash

.PHONY: setup lint typecheck test eval security review qa ci

setup:
	bash scripts/qa/bootstrap.sh setup

lint:
	bash scripts/qa/bootstrap.sh lint

typecheck:
	bash scripts/qa/bootstrap.sh typecheck

test:
	bash scripts/qa/bootstrap.sh tests

eval:
	bash scripts/qa/bootstrap.sh eval

security:
	bash scripts/qa/bootstrap.sh security

review:
	bash scripts/qa/bootstrap.sh review

qa:
	bash scripts/qa/bootstrap.sh all

ci: qa
