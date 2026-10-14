"""The in-process backend (DESIGN 12.4; decision 95 (f) of 2026-10-14-m12).

Calls a Python function object directly, for unit tests: the same slices, the
same result check and the same error stages as the runner
(:func:`discotrade.sandbox.runner.execute`), with the function in place of a
freshly loaded text. It accepts no source text: a job carrying one is refused
(:class:`~discotrade.sandbox.base.SandboxRefused`, rule ``source``). It
enforces no limit and records call times.
"""

from __future__ import annotations

from discotrade.sandbox import runner
from discotrade.sandbox.base import (
    SandboxJob,
    SandboxRefused,
    SandboxResult,
    job_arrays,
    job_doc,
    result_from_doc,
)


class InProcessSandbox:
    """The unit-test backend: runs ``job.function``, never a source text."""

    def run(self, job: SandboxJob) -> SandboxResult:
        if job.source is not None:
            raise SandboxRefused("source", "the in-process backend runs a function object "
                                 "only and accepts no source text (DESIGN 12.4)")
        if job.function is None:
            raise SandboxRefused("function", "the job carries no function object")
        function = job.function
        doc = runner.execute(job_doc(job), [job_arrays(i) for i in job.instruments],
                             lambda: function)
        return result_from_doc(job, doc)
