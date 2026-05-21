"""
其他功能
    - 读取路径下文件内容  read_sql_language
    - 获取当前时间戳，单位为毫秒  timestamp
    - 随机生成一个 User-Agent 字符串  random_user_agent
"""

import time
import random


def read_sql_language(sql_path: str) -> str:
    """
    读取路径下文件内容
    Args:
        sql_path(str): 文件路径
    Returns:
        str: 文本格式命令
    """
    with open(sql_path, 'r', encoding='utf-8') as open_file:
        sql_language = open_file.read()
    return sql_language


def timestamp():
    """
    获取当前时间戳，单位为毫秒
    """
    return time.time_ns() // 1000000


def random_user_agent():
    """
    随机生成一个 User-Agent 字符串
    """
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.198 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Chrome/10.0.648.133 Safari/534.16',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11'
    ]
    return random.choice(user_agents)


if __name__ == "__main__":
    from config.address import root_dir

    print(timestamp())
    for i in range(5):
        print(random_user_agent())
    
    sql_path = root_dir + r'/src/get_update_info/select_table.sql'
    print(read_sql_language(sql_path))
