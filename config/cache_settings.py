"""
Cache Settings Configuration
Settings and configuration options for the caching system.
"""

from datetime import timedelta


class CacheSettings:
    """Configuration settings for the caching system."""
    
    # Core Settings
    AUTO_SAVE = True                    # Save cache after each operation
    STARTUP_REFRESH = True              # Refresh cache on startup
    CACHE_FILE = "expense_sheets_cache.json"  # Default cache filename
    
    # Performance Settings
    BATCH_SAVE_INTERVAL = 1.0          # Seconds to wait before batch saving multiple operations
    MAX_CACHE_SIZE_MB = 50              # Maximum cache file size in MB
    
    # Future Features (not yet implemented)
    BACKGROUND_SYNC = False             # Background synchronization with server
    MAX_CACHE_AGE = timedelta(hours=24) # Maximum age before cache refresh
    AUTO_BACKUP = True                  # Create backup copies of cache
    COMPRESSION_ENABLED = False         # Compress cache files (for large datasets)
    
    # Debug Settings
    VERBOSE_LOGGING = False             # Enable detailed cache operation logging
    CACHE_VALIDATION = True             # Validate cache integrity on startup


class CacheConfig:
    """Dynamic cache configuration that can be modified at runtime."""
    
    def __init__(self):
        """Initialize with default settings."""
        self.auto_save = CacheSettings.AUTO_SAVE
        self.startup_refresh = CacheSettings.STARTUP_REFRESH
        self.cache_file = CacheSettings.CACHE_FILE
        self.verbose_logging = CacheSettings.VERBOSE_LOGGING
        self.cache_validation = CacheSettings.CACHE_VALIDATION
        
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            'auto_save': self.auto_save,
            'startup_refresh': self.startup_refresh,
            'cache_file': self.cache_file,
            'verbose_logging': self.verbose_logging,
            'cache_validation': self.cache_validation
        }
    
    def from_dict(self, config_dict: dict) -> None:
        """Load config from dictionary."""
        self.auto_save = config_dict.get('auto_save', self.auto_save)
        self.startup_refresh = config_dict.get('startup_refresh', self.startup_refresh) 
        self.cache_file = config_dict.get('cache_file', self.cache_file)
        self.verbose_logging = config_dict.get('verbose_logging', self.verbose_logging)
        self.cache_validation = config_dict.get('cache_validation', self.cache_validation)


# Global config instance
cache_config = CacheConfig()
