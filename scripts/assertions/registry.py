from __future__ import annotations

from typing import List, Type

from .base import BaseAssertionPlugin


PLUGINS: List[Type[BaseAssertionPlugin]] = []


def register(plugin_cls: Type[BaseAssertionPlugin]):
    # plugin_name 기반으로 중복 확인 (같은 이름의 플러그인이 이미 등록되어 있으면 추가하지 않음)
    existing_names = {p.plugin_name for p in PLUGINS}
    if hasattr(plugin_cls, 'plugin_name') and plugin_cls.plugin_name not in existing_names:
        PLUGINS.append(plugin_cls)
    elif not hasattr(plugin_cls, 'plugin_name'):
        # plugin_name이 없으면 그냥 추가 (이상 상황)
        if plugin_cls not in PLUGINS:
            PLUGINS.append(plugin_cls)
    return plugin_cls


def get_registered_plugins() -> List[Type[BaseAssertionPlugin]]:
    return list(PLUGINS)


