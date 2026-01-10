# -*- coding: utf-8 -*-
"""
存储管理模块
"""

import os
from typing import Optional
from config import get_config


class StorageManager:
    """存储管理器"""
    
    def __init__(self, base_path: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            base_path: 基础存储路径，None则使用配置中的路径
        """
        config = get_config()
        if base_path:
            self.base_path = base_path
        else:
            # 使用配置中的存储路径，或默认路径
            self.base_path = getattr(config, 'storage_path', os.path.join(os.getcwd(), 'storage'))
        
        # 确保基础目录存在
        os.makedirs(self.base_path, exist_ok=True)
    
    def get_storage_path(self, subpath: str) -> str:
        """
        获取存储路径
        
        Args:
            subpath: 子路径
            
        Returns:
            完整存储路径
        """
        path = os.path.join(self.base_path, subpath)
        os.makedirs(path, exist_ok=True)
        return path
