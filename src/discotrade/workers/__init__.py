"""Workers (DESIGN 13): what the harness computes and builds for a worker's
prompt. Nothing here reaches the network or a secret (I-11, I-13), and nothing
here is called from ``run-day`` or ``replay`` in step S3.1 (decision 109 (a) of
2026-10-15-m14)."""
