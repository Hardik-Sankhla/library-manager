"""Configuration management for Library Manager."""
import yaml
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
import os

CONFIG_DIR = Path.home() / ".config" / "library-manager"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

DEFAULT_CONFIG = {
    "library_root": "/mnt/Storage/library",
    "symlink_path": "/library",
    "telegram": {
        "api_id": None,
        "api_hash": None,
        "channel_id": None,
        "session_name": "library_bot",
        "use_bot_token": False,
        "bot_token": None,
    },
    "organization": {
        "by_category": True,
        "by_author": True,
        "create_series_folders": True,
        "max_depth": 3,
    },
    "naming": {
        "pattern": "{author} - {title} ({year}){ext}",
        "series_pattern": "{author} - {series} {series_num:02d} - {title} ({year}){ext}",
        "remove_patterns": [
            r"\(Z-Library\)",
            r"_OceanofPDF\.com_",
            r"\[.*?\]",
            r"\(.*?Copy.*?\)",
            r"\s*-\s*Copy\s*\d*",
            r"\s*\d{10,}\s*",
            r"^\d+[_\-\s]+",
            r"\(PDFDrive\)",
            r"\(z-lib\.org\)",
            r"\[.*?libribook\.com.*?\]",
            r"\[.*?O'Reilly.*?\]",
        ],
    },
    "categories": {
        "AI/ML/LLM": ["ai", "machine learning", "deep learning", "llm", "language model", "neural network", "transformer", "generative ai", "agentic", "rag", "mlops", "pytorch", "tensorflow"],
        "Programming": ["programming", "software", "clean code", "refactoring", "design pattern", "architecture", "algorithm", "data structure", "compiler", "interpreter", "debugging", "testing", "tdd"],
        "Data Science": ["data science", "data analysis", "pandas", "numpy", "visualization", "statistics", "statistical learning", "data engineering", "etl", "pipeline"],
        "Math/Stats": ["mathematics", "calculus", "linear algebra", "probability", "statistics", "mathematical", "proof", "theorem"],
        "Web Development": ["web", "frontend", "backend", "react", "vue", "angular", "node", "django", "flask", "fastapi", "api", "rest", "graphql", "javascript", "typescript", "css", "html"],
        "Systems": ["operating system", "linux", "kernel", "distributed", "concurrency", "parallel", "network", "protocol", "tcp", "http", "grpc", "microservice", "kubernetes", "docker", "container"],
        "Security": ["security", "cryptography", "encryption", "hacking", "penetration", "vulnerability", "auth", "oauth", "jwt", "ssl", "tls"],
        "Cloud": ["cloud", "aws", "azure", "gcp", "serverless", "lambda", "terraform", "infrastructure", "devops", "ci/cd"],
        "Science": ["physics", "chemistry", "biology", "neuroscience", "cognitive", "quantum", "relativity"],
        "Psychology": ["psychology", "behavioral", "cognitive", "therapy", "cbt", "mindfulness", "mental health", "personality"],
        "Philosophy": ["philosophy", "ethics", "logic", "epistemology", "metaphysics", "stoicism", "existentialism"],
        "Fiction": ["novel", "fiction", "fantasy", "sci-fi", "science fiction", "mystery", "thriller", "romance", "shadow slave"],
        "Business": ["business", "entrepreneur", "startup", "management", "leadership", "strategy", "marketing", "finance", "economics", "lean startup"],
        "Self-Help": ["self-help", "habit", "productivity", "motivation", "mindset", "atomic habits", "deep work", "essentialism", "influence", "persuasion"],
        "Biography": ["biography", "autobiography", "memoir", "life of", "story of"],
        "Reference": ["reference", "handbook", "guide", "manual", "encyclopedia", "dictionary", "companion"],
    },
    "sync": {
        "auto_sync": False,
        "sync_interval_hours": 24,
        "max_file_size_mb": 1900,  # Telegram limit is 2GB
        "parallel_uploads": 3,
        "verify_checksums": True,
    },
    "database": {
        "path": None,  # Auto-set to {library_root}/.library-manager/catalog.db
    },
}

@dataclass
class TelegramConfig:
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    channel_id: Optional[int] = None
    session_name: str = "library_bot"
    use_bot_token: bool = False
    bot_token: Optional[str] = None

@dataclass
class OrganizationConfig:
    by_category: bool = True
    by_author: bool = True
    create_series_folders: bool = True
    max_depth: int = 3

@dataclass
class NamingConfig:
    pattern: str = "{author} - {title} ({year}){ext}"
    series_pattern: str = "{author} - {series} {series_num:02d} - {title} ({year}){ext}"
    remove_patterns: list = field(default_factory=list)

@dataclass
class SyncConfig:
    auto_sync: bool = False
    sync_interval_hours: int = 24
    max_file_size_mb: int = 1900
    parallel_uploads: int = 3
    verify_checksums: bool = True

@dataclass
class Config:
    library_root: str = "/mnt/Storage/library"
    symlink_path: str = "/library"
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    organization: OrganizationConfig = field(default_factory=OrganizationConfig)
    naming: NamingConfig = field(default_factory=NamingConfig)
    categories: dict = field(default_factory=dict)
    sync: SyncConfig = field(default_factory=SyncConfig)
    database: dict = field(default_factory=dict)

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file."""
        if not CONFIG_FILE.exists():
            return cls.get_default()
        
        with open(CONFIG_FILE) as f:
            data = yaml.safe_load(f) or {}
        
        # Merge with defaults
        merged = cls._deep_merge(DEFAULT_CONFIG.copy(), data)
        return cls.from_dict(merged)
    
    @classmethod
    def get_default(cls) -> "Config":
        return cls.from_dict(DEFAULT_CONFIG)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        telegram = TelegramConfig(**data.get("telegram", {}))
        organization = OrganizationConfig(**data.get("organization", {}))
        naming = NamingConfig(**data.get("naming", {}))
        sync = SyncConfig(**data.get("sync", {}))
        
        return cls(
            library_root=data.get("library_root", DEFAULT_CONFIG["library_root"]),
            symlink_path=data.get("symlink_path", DEFAULT_CONFIG["symlink_path"]),
            telegram=telegram,
            organization=organization,
            naming=naming,
            categories=data.get("categories", DEFAULT_CONFIG["categories"]),
            sync=sync,
            database=data.get("database", {}),
        )
    
    @classmethod
    def _deep_merge(cls, base: dict, override: dict) -> dict:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = cls._deep_merge(base[key], value)
            else:
                base[key] = value
        return base
    
    def save(self):
        """Save configuration to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        data = {
            "library_root": self.library_root,
            "symlink_path": self.symlink_path,
            "telegram": asdict(self.telegram),
            "organization": asdict(self.organization),
            "naming": asdict(self.naming),
            "categories": self.categories,
            "sync": asdict(self.sync),
            "database": self.database,
        }
        
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def get_database_path(self) -> Path:
        if self.database.get("path"):
            return Path(self.database["path"])
        return Path(self.library_root) / ".library-manager" / "catalog.db"
    
    def get_library_root(self) -> Path:
        return Path(self.library_root)
    
    def get_books_dir(self) -> Path:
        return self.get_library_root() / "books"
    
    def get_inbox_dir(self) -> Path:
        return self.get_library_root() / "_inbox"
    
    def get_duplicates_dir(self) -> Path:
        return self.get_library_root() / "_duplicates"
    
    def get_metadata_dir(self) -> Path:
        return self.get_library_root() / "_metadata"


# Global config instance
_config: Optional[Config] = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.load()
    return _config

def set_config(config: Config):
    global _config
    _config = config