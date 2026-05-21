"""
用于配置数据库连接信息
"""

import os
from dotenv import load_dotenv


load_dotenv()


class DockerPostgreSQL:
    """docker-postgresql"""
    type = 'PostgreSQL'
    user = os.getenv('DockerPostgreSQLUser')
    password = os.getenv('DockerPostgreSQLPassword')
    host = os.getenv('DockerPostgreSQLHost')
    database = os.getenv('DockerPostgreSQLDatabase')


if __name__ == "__main__":
    print(DockerPostgreSQL.user)
    print(DockerPostgreSQL.password)
    print(DockerPostgreSQL.host)
    print(DockerPostgreSQL.database)