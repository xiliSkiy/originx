# -*- coding: utf-8 -*-
"""
基准图像服务

管理基准图像的存储和检索
"""

import os
import json
import uuid
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
import cv2
import numpy as np

from storage import StorageManager


class BaselineService:
    """基准图像服务"""
    
    def __init__(self, storage_manager: Optional[StorageManager] = None):
        """
        初始化基准图像服务
        
        Args:
            storage_manager: 存储管理器
        """
        self.storage = storage_manager or StorageManager()
        self.baseline_dir = self.storage.get_storage_path("baselines")
        self.metadata_file = os.path.join(self.baseline_dir, "metadata.json")
        
        # 确保目录存在
        os.makedirs(self.baseline_dir, exist_ok=True)
        
        # 加载元数据
        self._metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """加载元数据"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_metadata(self) -> None:
        """保存元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass
    
    def save_baseline(
        self,
        image: np.ndarray,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        保存基准图像
        
        Args:
            image: 图像（BGR格式）
            name: 名称
            description: 描述
            tags: 标签列表
            
        Returns:
            str: 基准图像ID
        """
        baseline_id = str(uuid.uuid4())
        
        # 保存图像
        image_path = os.path.join(self.baseline_dir, f"{baseline_id}.jpg")
        cv2.imwrite(image_path, image)
        
        # 保存元数据
        self._metadata[baseline_id] = {
            "baseline_id": baseline_id,
            "name": name,
            "description": description or "",
            "tags": tags or [],
            "image_path": image_path,
            "created_at": datetime.now().isoformat(),
            "image_size": list(image.shape[:2][::-1]),
        }
        
        self._save_metadata()
        
        return baseline_id
    
    def get_baseline(self, baseline_id: str) -> Optional[Dict[str, Any]]:
        """
        获取基准图像信息
        
        Args:
            baseline_id: 基准图像ID
            
        Returns:
            基准图像信息字典，如果不存在返回None
        """
        if baseline_id not in self._metadata:
            return None
        
        metadata = self._metadata[baseline_id].copy()
        
        # 检查文件是否存在
        if not os.path.exists(metadata["image_path"]):
            return None
        
        return metadata
    
    def get_baseline_image(self, baseline_id: str) -> Optional[np.ndarray]:
        """
        获取基准图像
        
        Args:
            baseline_id: 基准图像ID
            
        Returns:
            图像数组，如果不存在返回None
        """
        metadata = self.get_baseline(baseline_id)
        if not metadata:
            return None
        
        image_path = metadata["image_path"]
        if not os.path.exists(image_path):
            return None
        
        image = cv2.imread(image_path)
        return image
    
    def list_baselines(self) -> List[Dict[str, Any]]:
        """
        列出所有基准图像
        
        Returns:
            基准图像列表
        """
        # 过滤掉文件不存在的
        valid_baselines = []
        for baseline_id, metadata in self._metadata.items():
            if os.path.exists(metadata["image_path"]):
                valid_baselines.append(metadata.copy())
        
        return valid_baselines
    
    def delete_baseline(self, baseline_id: str) -> bool:
        """
        删除基准图像
        
        Args:
            baseline_id: 基准图像ID
            
        Returns:
            bool: 是否成功删除
        """
        if baseline_id not in self._metadata:
            return False
        
        metadata = self._metadata[baseline_id]
        image_path = metadata["image_path"]
        
        # 删除文件
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass
        
        # 删除元数据
        del self._metadata[baseline_id]
        self._save_metadata()
        
        return True
    
    def update_baseline(
        self,
        baseline_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        更新基准图像信息
        
        Args:
            baseline_id: 基准图像ID
            name: 新名称
            description: 新描述
            tags: 新标签
            
        Returns:
            bool: 是否成功更新
        """
        if baseline_id not in self._metadata:
            return False
        
        if name is not None:
            self._metadata[baseline_id]["name"] = name
        if description is not None:
            self._metadata[baseline_id]["description"] = description
        if tags is not None:
            self._metadata[baseline_id]["tags"] = tags
        
        self._save_metadata()
        return True
