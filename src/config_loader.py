"""
配置加载器
统一管理所有配置项，从 config.env 文件加载
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """
    单例配置类
    从 .env 文件加载配置，供全局使用
    """
    _instance: Optional['Config'] = None
    _loaded: bool = False

    # 配置项
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    MODEL_PROVIDER: str = "openai"  # 可选: "openai" 或 "deepseek"
    LOG_LEVEL: str = "INFO"
    SIMULATION_MODE: bool = False
    SKILL_LIBRARY_PATH: str = "data/skills/skill_library.json"
    REALSENSE_DEVICE_SN: str = ""

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def load(cls, env_path: Optional[str] = None) -> 'Config':
        """
        从 .env 文件加载配置

        Args:
            env_path: 可选，.env 文件路径。默认为项目根目录下的 config.env
        """
        if cls._loaded:
            return cls._instance

        if env_path is None:
            # 默认查找项目根目录的 config.env
            _src_dir = Path(__file__).parent.parent
            env_path = _src_dir / "config.env"
        else:
            env_path = Path(env_path)

        # 优先从指定路径加载
        if env_path.exists():
            load_dotenv(env_path, override=False)
        else:
            # 尝试从项目根目录加载
            _src_dir = Path(__file__).parent.parent
            default_env = _src_dir / "config.env"
            if default_env.exists():
                load_dotenv(default_env, override=False)

        instance = cls._instance
        instance.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        instance.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
        instance.MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")
        instance.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        instance.SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() in ("true", "1", "yes")
        instance.SKILL_LIBRARY_PATH = os.getenv("SKILL_LIBRARY_PATH", "data/skills/skill_library.json")
        instance.REALSENSE_DEVICE_SN = os.getenv("REALSENSE_DEVICE_SN", "")

        cls._loaded = True
        return instance

    @classmethod
    def get_instance(cls) -> 'Config':
        """获取单例实例，如果未加载则先加载"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        if not cls._loaded:
            cls.load()
        return cls._instance

    @classmethod
    def is_api_key_set(cls) -> bool:
        """检查 OpenAI API Key 是否已配置"""
        key = cls.get_instance().OPENAI_API_KEY
        return bool(key and key != "your_openai_key_here")

    @classmethod
    def get_skill_library_path(cls) -> Path:
        """获取技能库文件的绝对路径"""
        instance = cls.get_instance()
        path = Path(instance.SKILL_LIBRARY_PATH)

        # 如果是相对路径，转换为相对于项目根目录
        if not path.is_absolute():
            _src_dir = Path(__file__).parent.parent
            path = _src_dir / instance.SKILL_LIBRARY_PATH

        return path

    @classmethod
    def reset(cls):
        """重置配置（用于测试）"""
        cls._instance = None
        cls._loaded = False
