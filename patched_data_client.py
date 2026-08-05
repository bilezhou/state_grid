from __future__ import annotations

from . import data_client as _base
from .login_error import build_login_error_result, format_login_error


class StateGridDataClient(_base.StateGridDataClient):
    """State Grid client with lossless upstream login-error propagation."""

    async def __get_request_key(self):
        self.keyCode = None
        response = await self.__fetch(_base.get_request_key_api, {})
        fallback_message = self.handle_request_result_message(
            "get_request_key_api", response
        )

        data = response.get("data") if isinstance(response, dict) else None
        data = data if isinstance(data, dict) else {}
        if str(response.get("code")) == "1" and data.get("keyCode") and data.get("publicKey"):
            self.keyCode = data["keyCode"]
            self.publicKey = data["publicKey"]
            return {"errcode": 0}

        return build_login_error_result(response, fallback_message)

    async def __get_pass_verify_code(self, account, password):
        payload = {
            "account": account,
            "password": password,
            "canvasHeight": 200,
            "canvasWidth": 310,
        }
        response = await self.__fetch(_base.get_verify_code_api, payload)
        fallback_message = self.handle_request_result_message(
            "get_verify_code_api", response, False
        )

        data = response.get("data") if isinstance(response, dict) else None
        data = data if isinstance(data, dict) else {}
        required_fields = ("ticket", "canvasSrc", "blockSrc", "blockY")
        if str(response.get("code")) == "1" and all(
            field in data for field in required_fields
        ):
            self.ticket = data["ticket"]
            return {
                "errcode": 0,
                "canvasSrc": data["canvasSrc"],
                "blockSrc": data["blockSrc"],
                "blockY": data["blockY"],
            }

        return build_login_error_result(response, fallback_message)

    async def __verify_password(self, account, password, code, loginKey):
        payload = {
            "loginKey": loginKey,
            "code": code,
            "params": {
                "uscInfo": {
                    "devciceIp": "",
                    "tenant": "state_grid",
                    "member": "0902",
                    "devciceId": "",
                },
                "quInfo": {
                    "optSys": "ios",
                    "pushId": "00000",
                    "addressProvince": "110100",
                    "password": password,
                    "addressRegion": "110101",
                    "account": account,
                    "addressCity": "330100",
                },
            },
            "Channels": "web",
        }
        response = await self.__fetch(_base.verify_password_api, payload)
        fallback_message = self.handle_request_result_message(
            "verify_password_api", response
        )

        if response.get("code") == 1:
            data = response.get("data")
            data = data if isinstance(data, dict) else {}
            service_result = data.get("srvrt")
            if not isinstance(service_result, dict):
                service_result = response.get("srvrt")
            service_result = service_result if isinstance(service_result, dict) else {}
            if service_result.get("resultCode") == "0000":
                business_result = data["bizrt"]
                self.token = business_result["token"]
                self.userInfo = business_result["userInfo"][0]
                return {"errcode": 0}

        return build_login_error_result(response, fallback_message)

    async def __try_password_login(self):
        result = await self.password_login(
            self.account, self.password, encode=True, retry=0
        )
        if result.get("errcode") == 0:
            self.need_login = False
            self.shown_notification = False
            self.last_login_error = None
            await self.save_data()
            return

        self.last_login_error = format_login_error(result)
        _base.LOGGER.warning("国家电网登录失败: %s", self.last_login_error)
