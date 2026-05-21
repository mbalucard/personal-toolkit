"""
用于配置项目根目录
"""

import os 


root_dir = os.path.dirname(os.path.dirname(__file__))

if __name__ == "__main__":
    print(type(root_dir))
    print(root_dir)