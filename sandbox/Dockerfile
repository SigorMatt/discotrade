# The sandbox image (DESIGN 12.4, 3; decision 2026-10-14-m13 102 (e)). Built only by
# `discotrade sandbox build`, which assembles its context from the files named in
# discotrade.sandbox.container.IMAGE_INPUTS and tags it with the first 12 hex digits
# of a sha256 over them. It holds a pinned Python, the pinned numpy and pandas (with
# the two packages pandas needs), the runner and the indicator library, and nothing
# else: no pyarrow, no httpx, no other module of discotrade.
#
# The base: python 3.14.6 (the minor version uv runs the project with), pinned by the
# digest of its image index on Docker Hub.
FROM python:3.14.6-slim@sha256:7bec7ddcddeff7975d6ba9b4be7dd6f6b2f55e7491539145e2978f7f97ce9144

# numpy and pandas at the versions uv.lock holds for Python 3.14, by the wheel hashes
# uv.lock records; then pip itself is removed.
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --no-deps --only-binary=:all: --require-hashes \
        -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt \
    && python -m pip uninstall --yes pip \
    && rm -rf /root/.cache

# The runner imports `discotrade.indicators`: the package is the indicator library and
# the runner under two package files of their own (package_init.py), so that nothing
# else of discotrade, and no importlib.metadata lookup, is in the image (REVIEW-12 6).
ARG SITE=/usr/local/lib/python3.14/site-packages/discotrade
COPY package_init.py ${SITE}/__init__.py
COPY package_init.py ${SITE}/sandbox/__init__.py
COPY indicators.py ${SITE}/indicators.py
COPY runner.py ${SITE}/sandbox/runner.py
RUN python -m compileall -q ${SITE} \
    && groupadd --gid 10001 sandbox \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent \
        --shell /usr/sbin/nologin sandbox

USER 10001:10001
WORKDIR /tmp
