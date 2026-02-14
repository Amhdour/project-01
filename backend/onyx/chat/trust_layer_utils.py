from __future__ import annotations

import importlib
from functools import lru_cache

from onyx.configs.app_configs import TRUST_LAYER_HOOKS_ENABLED
from onyx.configs.app_configs import TRUST_LAYER_IMPL
from onyx.utils.logger import setup_logger
from trust_layer.interface import TrustLayer

logger = setup_logger()


@lru_cache(maxsize=1)
def get_configured_trust_layer() -> TrustLayer | None:
    if not TRUST_LAYER_HOOKS_ENABLED:
        return None
    if not TRUST_LAYER_IMPL:
        logger.warning(
            "TRUST_LAYER_HOOKS_ENABLED is true but TRUST_LAYER_IMPL is not configured; trust hooks disabled"
        )
        return None

    try:
        if ":" in TRUST_LAYER_IMPL:
            module_name, attr_name = TRUST_LAYER_IMPL.split(":", 1)
        else:
            module_name, attr_name = TRUST_LAYER_IMPL.rsplit(".", 1)

        module = importlib.import_module(module_name)
        impl = getattr(module, attr_name)
        instance = impl() if isinstance(impl, type) else impl
        if not isinstance(instance, TrustLayer):
            logger.error(
                f"Configured trust layer '{TRUST_LAYER_IMPL}' is not a TrustLayer implementation"
            )
            return None
        return instance
    except Exception:
        logger.exception("Failed to initialize configured trust layer; hooks will be disabled")
        return None
