#!/usr/bin/env python3
"""Removed unsafe legacy branch-writing uploader.

Public-layer acquisition now uses Actions artifacts with contents:read. This
session never writes public-layers or any branch other than its Arena branch.
Use `gh run download RUN_ID -n official-audit-inputs -D data/raw/official_audit`.
"""
raise SystemExit("Disabled: use the read-only Official audit inputs workflow and gh run download.")
