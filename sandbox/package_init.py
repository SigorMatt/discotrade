"""discotrade inside the sandbox image (DESIGN 12.4; decision 2026-10-14-m13 102 (e)).

The image holds only the runner and the indicator library of discotrade; this file is
the package file of ``discotrade`` and of ``discotrade.sandbox`` there, so that the
runner's ``from discotrade import indicators`` resolves without the installed
distribution's metadata (REVIEW-12 note 6).
"""
