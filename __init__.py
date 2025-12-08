from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform

from .const import DOMAIN
from .utils.store import async_load_from_store
from .data_client import StateGridDataClient


PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """当用户在 UI 里点击“添加集成”并完成配置时调用。"""
    # 读取原来保存在 .storage/state_grid.config 里的数据（如果有）
    config = await async_load_from_store(hass, "state_grid.config") or None

    # 创建带 ONNX 登录能力的 StateGridDataClient
    hass.data[DOMAIN] = StateGridDataClient(hass=hass, config=config)

    # 注册 sensor 平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载集成时调用（不删除存储文件）。"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """注意：这里故意什么都不做，不删除 state_grid.config。"""
    # 不调用 async_remove_store(hass, "state_grid.config")
    # 这样 /config/.storage/state_grid.config 会被保留
    return None
