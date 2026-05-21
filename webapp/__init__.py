def __getattr__(name: str):
    """
    延迟导出 webapp 包的公开属性。

    主要用于在脚本方式启动或部分场景下避免循环导入开销，仅在访问属性时再导入目标对象。

    Args:
        name (str): 属性名。

    Returns:
        Any: 对应的属性对象（例如 create_app）。

    Raises:
        AttributeError: 当属性不存在时抛出。
    """
    if name == "create_app":
        from .app import create_app

        return create_app
    raise AttributeError(name)
