from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "state_grid_testpkg"

package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = package

login_spec = importlib.util.spec_from_file_location(
    f"{PACKAGE}.login_error", ROOT / "login_error.py"
)
assert login_spec is not None and login_spec.loader is not None
login_module = importlib.util.module_from_spec(login_spec)
sys.modules[f"{PACKAGE}.login_error"] = login_module
login_spec.loader.exec_module(login_module)

base_module = types.ModuleType(f"{PACKAGE}.data_client")
base_module.get_request_key_api = "/request-key"
base_module.get_verify_code_api = "/verify-code"
base_module.verify_password_api = "/verify-password"
base_module.LOGGER = types.SimpleNamespace(warning=lambda *args, **kwargs: None)
base_module.StateGridDataClient = type("StateGridDataClient", (), {})
sys.modules[f"{PACKAGE}.data_client"] = base_module

patched_spec = importlib.util.spec_from_file_location(
    f"{PACKAGE}.patched_data_client", ROOT / "patched_data_client.py"
)
assert patched_spec is not None and patched_spec.loader is not None
patched_module = importlib.util.module_from_spec(patched_spec)
sys.modules[f"{PACKAGE}.patched_data_client"] = patched_module
patched_spec.loader.exec_module(patched_module)


class EarlyLoginFailureTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, response):
        client = patched_module.StateGridDataClient()
        setattr(
            client,
            "_StateGridDataClient__fetch",
            AsyncMock(return_value=response),
        )
        client.handle_request_result_message = lambda *args, **kwargs: "fallback"
        return client

    async def test_request_key_failure_preserves_top_level_srvrt_code(self):
        client = self.make_client({
            "code": 1,
            "srvrt": {"resultCode": "RATE_LIMIT", "resultMessage": "操作频繁"},
        })
        result = await getattr(
            client, "_StateGridDataClient__get_request_key"
        )()
        self.assertEqual(result["original_code"], "RATE_LIMIT")
        self.assertEqual(
            login_module.format_login_error(result), "code=RATE_LIMIT，操作频繁"
        )

    async def test_verify_code_failure_preserves_upstream_errcode(self):
        client = self.make_client({"errcode": 429, "errmsg": "验证码请求过于频繁"})
        result = await getattr(
            client, "_StateGridDataClient__get_pass_verify_code"
        )("account", "password")
        self.assertEqual(result["original_code"], 429)
        self.assertEqual(
            login_module.format_login_error(result),
            "code=429，验证码请求过于频繁",
        )


if __name__ == "__main__":
    unittest.main()
