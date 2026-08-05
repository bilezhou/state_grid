from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "login_error.py"
SPEC = importlib.util.spec_from_file_location("state_grid_login_error", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
LOGIN_ERROR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LOGIN_ERROR)


class LoginErrorTests(unittest.TestCase):
    def test_password_error_keeps_upstream_result_code(self):
        response = {
            "code": 1,
            "data": {
                "srvrt": {
                    "resultCode": "PASSWORD_INVALID",
                    "resultMessage": "账号或密码错误",
                }
            },
        }
        wrapped = LOGIN_ERROR.build_login_error_result(response)
        rendered = LOGIN_ERROR.format_login_error(wrapped)
        self.assertEqual(wrapped["original_code"], "PASSWORD_INVALID")
        self.assertEqual(rendered, "code=PASSWORD_INVALID，账号或密码错误")
        self.assertNotIn("errcode=1", rendered)

    def test_risk_control_error_is_not_collapsed_to_password_error(self):
        password_error = LOGIN_ERROR.build_login_error_result({
            "code": 1,
            "data": {"srvrt": {"resultCode": "PASSWORD_INVALID", "resultMessage": "账号或密码错误"}},
        })
        risk_control_error = LOGIN_ERROR.build_login_error_result({
            "code": 1,
            "data": {"srvrt": {"resultCode": "RISK_CONTROL", "resultMessage": "操作频繁，请稍后再试"}},
        })
        password_text = LOGIN_ERROR.format_login_error(password_error)
        risk_control_text = LOGIN_ERROR.format_login_error(risk_control_error)
        self.assertNotEqual(password_text, risk_control_text)
        self.assertIn("code=PASSWORD_INVALID", password_text)
        self.assertIn("code=RISK_CONTROL", risk_control_text)
        self.assertNotIn("errcode=1", risk_control_text)

    def test_top_level_upstream_errcode_is_preserved(self):
        wrapped = LOGIN_ERROR.build_login_error_result({"errcode": 429, "errmsg": "操作频繁"})
        rendered = LOGIN_ERROR.format_login_error(wrapped)
        self.assertEqual(wrapped["original_code"], 429)
        self.assertEqual(rendered, "code=429，操作频繁")
        self.assertNotIn("errcode=1", rendered)

    def test_nested_upstream_errcode_is_preserved(self):
        wrapped = LOGIN_ERROR.build_login_error_result({
            "code": 1,
            "data": {"srvrt": {"errcode": "CAPTCHA_REQUIRED", "errmsg": "需要验证码"}},
        })
        rendered = LOGIN_ERROR.format_login_error(wrapped)
        self.assertEqual(wrapped["original_code"], "CAPTCHA_REQUIRED")
        self.assertEqual(rendered, "code=CAPTCHA_REQUIRED，需要验证码")

    def test_top_level_srvrt_result_code_is_preserved(self):
        wrapped = LOGIN_ERROR.build_login_error_result({
            "code": 1,
            "srvrt": {"resultCode": "RISK_CONTROL", "resultMessage": "操作频繁"},
        })
        rendered = LOGIN_ERROR.format_login_error(wrapped)
        self.assertEqual(wrapped["original_code"], "RISK_CONTROL")
        self.assertEqual(rendered, "code=RISK_CONTROL，操作频繁")

    def test_wrapper_errcode_one_is_hidden_without_an_original_code(self):
        rendered = LOGIN_ERROR.format_login_error({"errcode": 1, "errmsg": "上游暂时不可用"})
        self.assertEqual(rendered, "上游暂时不可用")


if __name__ == "__main__":
    unittest.main()
