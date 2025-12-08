import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import DOMAIN
from .utils.logger import LOGGER
from .data_client import StateGridDataClient


class StateGridOnnxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """国家电网（ONNX）集成的配置向导。"""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """第一个也是唯一一个配置步骤：输入账号和密码。"""
        # 只允许添加一次
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if self.hass.data.get(DOMAIN):
            return self.async_abort(reason="single_instance_allowed")

        errors: dict[str, str] = {}
        account: str = ""
        password: str = ""

        if user_input is not None:
            account = user_input.get("account", "").strip()
            password = user_input.get("password", "")

            if not account or not password:
                errors["base"] = "invalid_auth"
            else:
                dc = StateGridDataClient(hass=self.hass, config=None)
                try:
                    LOGGER.debug("开始使用 ONNX 滑块登录国家电网，账号=%s", account)
                    # encode=False 传入明文密码，由 data_client 内部做 MD5
                    result = await dc.password_login(account, password, encode=False, retry=3)
                except Exception as exc:  # noqa: BLE001
                    LOGGER.error("国家电网登录异常: %s", exc)
                    errors["base"] = "cannot_connect"
                else:
                    if result.get("errcode") == 0:
                        # 登录成功，保存一次数据到 storage（包含 token / userInfo / 户号数据等）
                        try:
                            await dc.save_data()
                        except Exception:  # noqa: BLE001
                            # 即使保存失败，集成本身也可以继续
                            LOGGER.exception("保存 state_grid.config 失败，但登录成功。")

                        # 把 data_client 暂存在 hass.data（方便 options 或后续调试用）
                        self.hass.data[DOMAIN] = dc

                        title = f"国家电网(ONNX) - {account}"
                        # 不在 entry.data 里保存账号/密码，仅用于展示标题
                        return self.async_create_entry(title=title, data={})
                    else:
                        # data_client 返回的错误信息通常在 errmsg / message 里
                        errmsg = (
                            result.get("errmsg")
                            or result.get("message")
                            or "登录失败，请检查账号密码"
                        )
                        LOGGER.warning("国家电网登录失败: %s", errmsg)
                        errors["base"] = "invalid_auth"

        # 首次进入 / 登录失败时展示表单
        data_schema = vol.Schema(
            {
                vol.Required("account", default=account): selector(
                    {"text": {"type": "text"}}
                ),
                vol.Required("password", default=password): selector(
                    {"text": {"type": "password"}}
                ),
            }
        )

        # step_id 必须是 "user"
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        """返回选项流程（这里只给一个空壳，后续你要加调试参数也可以扩展）。"""
        return OptionsFlowHandler(entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """集成选项：目前什么都不做，仅占位。"""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """入口步骤，直接完成，不提供额外选项。"""
        return self.async_create_entry(title="", data={})
