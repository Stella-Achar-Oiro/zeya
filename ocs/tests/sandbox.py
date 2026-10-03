"""
Run OCS Python-node source the way Open Chat Studio does.

If ``OCS_SOURCE`` points at an OCS checkout, the real
``apps.utils.python_execution.RestrictedPythonExecutionMixin`` is used. Otherwise a
pinned copy of the parts that matter here is used (OCS commit 7df40d8a4):
``exec(code, globals, locals)`` semantics, the single-``main`` validation, and the
allowed-module import guard.

``NodeHarness`` provides the subset of CodeNode helper functions our nodes call
(``apps/pipelines/nodes/nodes.py`` ``CodeNode._get_custom_functions``) and records
their side effects so tests can assert on them.
"""

import datetime
import inspect
import json
import os
import sys
import time
import types
from typing import Any

from RestrictedPython import (
    compile_restricted,
    limited_builtins,
    safe_builtins,
    utility_builtins,
)
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.Guards import guarded_iter_unpack_sequence

OCS_SOURCE = os.environ.get("OCS_SOURCE")

READ_ONLY_TEMP_STATE_KEYS = {"user_input", "outputs", "attachments"}


class CodeValidationError(Exception):
    """Raised when node source would be rejected by the OCS CodeNode validator."""


class _PinnedExecutor:
    """Copy of RestrictedPythonExecutionMixin behaviour at OCS 7df40d8a4."""

    allowed_modules = {"json", "re", "datetime", "time", "random"}

    def __init__(self, code: str):
        self.code = code
        self._validate()

    def _validate(self) -> None:
        try:
            byte_code = compile_restricted(self.code, filename="<inline code>", mode="exec")
        except SyntaxError as exc:
            raise CodeValidationError(exc.msg) from exc
        custom_locals: dict[str, Any] = {}
        exec(byte_code, {}, custom_locals)
        if "main" not in custom_locals:
            raise CodeValidationError("You must define a 'main' function")
        for name, item in custom_locals.items():
            if name != "main" and inspect.isfunction(item):
                raise CodeValidationError("You can only define a single function, 'main' at the top level.")
        params = list(inspect.signature(custom_locals["main"]).parameters.values())
        if (
            len(params) != 2
            or params[0].name != "input"
            or params[1].kind != inspect.Parameter.VAR_KEYWORD
            or params[1].name != "kwargs"
        ):
            raise CodeValidationError("The main function should have the signature main(input, **kwargs) only.")

    def _builtins(self) -> dict[str, Any]:
        builtins = safe_builtins.copy()
        builtins.update(
            {"min": min, "max": max, "sum": sum, "abs": abs, "all": all, "any": any, "datetime": datetime, "dict": dict}
        )
        builtins.update(utility_builtins)
        builtins.update(limited_builtins)
        allowed = self.allowed_modules

        def guarded_import(name, *args, **kwargs):
            if name not in allowed:
                raise ImportError(f"Importing '{name}' is not allowed")
            return __import__(name, *args, **kwargs)

        builtins["__import__"] = guarded_import
        return builtins

    def compile_and_execute_code(self, additional_globals=None, *args, **kwargs):
        all_globals = {
            "__builtins__": self._builtins(),
            "json": json,
            "datetime": datetime,
            "time": time,
            "_getitem_": default_guarded_getitem,
            "_getiter_": default_guarded_getiter,
            "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
            "_write_": lambda x: x,
        } | (additional_globals or {})
        custom_locals: dict[str, Any] = {}
        exec(compile_restricted(self.code, filename="<inline_code>", mode="exec"), all_globals, custom_locals)
        return custom_locals["main"](*args, **kwargs)


def _real_executor_class():
    if OCS_SOURCE not in sys.path:
        sys.path.insert(0, OCS_SOURCE)
    from apps.utils.python_execution import RestrictedPythonExecutionMixin  # noqa: PLC0415
    from pydantic import ValidationError  # noqa: PLC0415

    class _RealExecutor(RestrictedPythonExecutionMixin):
        @classmethod
        def _get_function_args(cls):
            return ["input", "**kwargs"]

        @classmethod
        def _get_default_code(cls):
            return ""

    def build(code: str):
        try:
            return _RealExecutor(code=code)
        except ValidationError as exc:
            raise CodeValidationError(str(exc)) from exc

    return build


def make_executor(code: str):
    """Validate ``code`` like OCS does and return an object with ``compile_and_execute_code``."""
    if OCS_SOURCE:
        return _real_executor_class()(code)
    return _PinnedExecutor(code)


class NodeHarness:
    """Executes one node's source with CodeNode-equivalent helpers and records effects."""

    def __init__(
        self,
        code: str,
        temp_state: dict | None = None,
        participant_data: dict | None = None,
        now: datetime.datetime | None = None,
    ):
        self.executor = make_executor(code)
        self.now = now
        self.temp_state: dict[str, Any] = dict(temp_state or {})
        self.participant_data: dict[str, Any] = dict(participant_data or {})
        self.message_tags: list[str] = []
        self.session_tags: list[str] = []

    def _globals(self) -> dict[str, Any]:
        def get_temp_state_key(key_name):
            return self.temp_state.get(key_name)

        def set_temp_state_key(key_name, value):
            if key_name in READ_ONLY_TEMP_STATE_KEYS:
                raise ValueError(f"Cannot set the '{key_name}' key of the temporary state")
            self.temp_state[key_name] = value

        def get_participant_data():
            return dict(self.participant_data)

        def set_participant_data_key(key_name, value):
            self.participant_data[key_name] = value

        helpers = {
            "get_temp_state_key": get_temp_state_key,
            "set_temp_state_key": set_temp_state_key,
            "get_participant_data": get_participant_data,
            "set_participant_data_key": set_participant_data_key,
            "add_message_tag": self.message_tags.append,
            "add_session_tag": self.session_tags.append,
        }
        if self.now is not None:
            # OCS exposes the datetime module as a global; replacing it freezes the clock.
            helpers["datetime"] = frozen_datetime_module(self.now)
        return helpers

    def run(self, input: str) -> str:  # noqa: A002 - mirrors the OCS argument name
        self.temp_state.setdefault("user_input", input)
        return str(self.executor.compile_and_execute_code(self._globals(), input=input, node_inputs=[input]))


def frozen_datetime_module(now: datetime.datetime):
    """A stand-in for the ``datetime`` module whose ``datetime.now()`` returns ``now``."""

    class FrozenDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            frozen = cls.fromtimestamp(now.timestamp(), tz=datetime.UTC)
            return frozen.astimezone(tz) if tz else frozen.replace(tzinfo=None)

    return types.SimpleNamespace(
        datetime=FrozenDatetime,
        date=datetime.date,
        timedelta=datetime.timedelta,
        timezone=datetime.timezone,
    )
