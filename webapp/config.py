import os


class Settings:
    def __init__(self) -> None:
        """
        读取并组织 Web 应用配置。

        配置来源为环境变量（通常由项目根目录 .env 加载）。

        Returns:
            None: 无返回值。
        """
        self.secret_key = os.getenv("FLASK_SECRET_KEY", "")
        self.admin_username = os.getenv("ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("ADMIN_PASSWORD", "")

        self.default_page_size = 100
        self.allowed_page_sizes = (100, 200, 500)
