"""
Sheet Data Cache Service
Provides high-performance caching for Google Sheets data with intelligent cache management.
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import hashlib
import threading
from pathlib import Path


class SheetCacheService:
    """Service for caching Google Sheets data locally for improved performance."""
    
    def __init__(self, cache_file: str = "sheets_cache.json", spreadsheet_id: str = None):
        """Initialize the cache service.
        
        Args:
            cache_file: Path to the cache file.
            spreadsheet_id: The Google Sheets spreadsheet ID.
        """
        self.cache_file = Path(cache_file)
        self.spreadsheet_id = spreadsheet_id
        self.cache_data = {}
        self._lock = threading.Lock()  # Thread safety for cache operations
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from file into memory."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                print(f"📂 Loaded cache from {self.cache_file}")
            else:
                self.cache_data = self._create_empty_cache()
                print(f"🆕 Created new cache structure")
        except Exception as e:
            print(f"❌ Error loading cache: {e}")
            self.cache_data = self._create_empty_cache()
    
    def _create_empty_cache(self) -> Dict[str, Any]:
        """Create an empty cache structure."""
        return {
            "version": "1.0",
            "last_updated_at": datetime.now().isoformat(),
            "spreadsheet_id": self.spreadsheet_id,
            "data": {}
        }
    
    def _save_cache(self) -> None:
        """Save cache to file."""
        try:
            with self._lock:
                self.cache_data["last_updated_at"] = datetime.now().isoformat()
                
                # Create backup before writing
                if self.cache_file.exists():
                    backup_file = self.cache_file.with_suffix('.json.backup')
                    self.cache_file.rename(backup_file)
                
                # Write new cache
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
                
                print(f"💾 Cache saved to {self.cache_file}")
                
        except Exception as e:
            print(f"❌ Error saving cache: {e}")
            # Restore backup if write failed
            backup_file = self.cache_file.with_suffix('.json.backup')
            if backup_file.exists():
                backup_file.rename(self.cache_file)
    
    def get_sheet_data(self, sheet_name: str) -> Optional[Dict[str, Any]]:
        """Get cached data for a sheet.
        
        Args:
            sheet_name: Name of the sheet (e.g., 'january-2025').
            
        Returns:
            Cached sheet data or None if not cached.
        """
        with self._lock:
            sheet_key = sheet_name.lower().replace(' ', '-')
            return self.cache_data.get("data", {}).get(sheet_key)
    
    def cache_sheet_data(self, sheet_name: str, headers: List[str], 
                        rows: List[List[str]], save_immediately: bool = True) -> None:
        """Cache data for a sheet.
        
        Args:
            sheet_name: Name of the sheet.
            headers: Column headers.
            rows: Data rows.
            save_immediately: Whether to save to file immediately.
        """
        with self._lock:
            sheet_key = sheet_name.lower().replace(' ', '-')
            
            # Ensure data structure exists
            if "data" not in self.cache_data:
                self.cache_data["data"] = {}
            
            # Cache the sheet data
            self.cache_data["data"][sheet_key] = {
                "last_modified": datetime.now().isoformat(),
                "row_count": len(rows),
                "headers": headers.copy(),
                "rows": [row.copy() for row in rows],  # Deep copy to avoid mutations
                "data_hash": self._calculate_data_hash(headers, rows)
            }
            
            print(f"📝 Cached data for '{sheet_name}' ({len(rows)} rows)")
        
        if save_immediately:
            self._save_cache()
    
    def update_row_in_cache(self, sheet_name: str, row_index: int, 
                           row_data: List[str], save_immediately: bool = True) -> bool:
        """Update a single row in the cache.
        
        Args:
            sheet_name: Name of the sheet.
            row_index: Index of the row to update (0-based).
            row_data: New row data.
            save_immediately: Whether to save to file immediately.
            
        Returns:
            True if update successful, False otherwise.
        """
        try:
            with self._lock:
                sheet_key = sheet_name.lower().replace(' ', '-')
                sheet_data = self.cache_data.get("data", {}).get(sheet_key)
                
                if not sheet_data or row_index >= len(sheet_data.get("rows", [])):
                    print(f"⚠️ Cannot update row {row_index} in '{sheet_name}' - not found in cache")
                    return False
                
                # Update the row
                sheet_data["rows"][row_index] = row_data.copy()
                sheet_data["last_modified"] = datetime.now().isoformat()
                sheet_data["data_hash"] = self._calculate_data_hash(
                    sheet_data["headers"], sheet_data["rows"]
                )
                
                print(f"✏️ Updated row {row_index} in '{sheet_name}' cache")
            
            if save_immediately:
                self._save_cache()
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating row in cache: {e}")
            return False
    
    def add_row_to_cache(self, sheet_name: str, row_data: List[str], 
                        save_immediately: bool = True) -> bool:
        """Add a new row to the cache.
        
        Args:
            sheet_name: Name of the sheet.
            row_data: New row data.
            save_immediately: Whether to save to file immediately.
            
        Returns:
            True if add successful, False otherwise.
        """
        try:
            with self._lock:
                sheet_key = sheet_name.lower().replace(' ', '-')
                sheet_data = self.cache_data.get("data", {}).get(sheet_key)
                
                if not sheet_data:
                    print(f"⚠️ Cannot add row to '{sheet_name}' - sheet not found in cache")
                    return False
                
                # Add the row
                sheet_data["rows"].append(row_data.copy())
                sheet_data["row_count"] = len(sheet_data["rows"])
                sheet_data["last_modified"] = datetime.now().isoformat()
                sheet_data["data_hash"] = self._calculate_data_hash(
                    sheet_data["headers"], sheet_data["rows"]
                )
                
                print(f"➕ Added row to '{sheet_name}' cache (now {sheet_data['row_count']} rows)")
            
            if save_immediately:
                self._save_cache()
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding row to cache: {e}")
            return False
    
    def delete_rows_from_cache(self, sheet_name: str, row_indices: List[int], 
                              save_immediately: bool = True) -> bool:
        """Delete rows from the cache.
        
        Args:
            sheet_name: Name of the sheet.
            row_indices: List of row indices to delete (0-based).
            save_immediately: Whether to save to file immediately.
            
        Returns:
            True if delete successful, False otherwise.
        """
        try:
            with self._lock:
                sheet_key = sheet_name.lower().replace(' ', '-')
                sheet_data = self.cache_data.get("data", {}).get(sheet_key)
                
                if not sheet_data:
                    print(f"⚠️ Cannot delete rows from '{sheet_name}' - sheet not found in cache")
                    return False
                
                # Sort indices in descending order to delete from bottom up
                sorted_indices = sorted(row_indices, reverse=True)
                
                rows = sheet_data["rows"]
                for index in sorted_indices:
                    if 0 <= index < len(rows):
                        del rows[index]
                    else:
                        print(f"⚠️ Row index {index} out of range for '{sheet_name}'")
                
                # Update metadata
                sheet_data["row_count"] = len(rows)
                sheet_data["last_modified"] = datetime.now().isoformat()
                sheet_data["data_hash"] = self._calculate_data_hash(
                    sheet_data["headers"], rows
                )
                
                print(f"🗑️ Deleted {len(row_indices)} rows from '{sheet_name}' cache (now {sheet_data['row_count']} rows)")
            
            if save_immediately:
                self._save_cache()
            
            return True
            
        except Exception as e:
            print(f"❌ Error deleting rows from cache: {e}")
            return False
    
    def get_cached_sheet_names(self) -> List[str]:
        """Get list of all cached sheet names.
        
        Returns:
            List of sheet names in cache.
        """
        with self._lock:
            return list(self.cache_data.get("data", {}).keys())
    
    def is_sheet_cached(self, sheet_name: str) -> bool:
        """Check if a sheet is cached.
        
        Args:
            sheet_name: Name of the sheet.
            
        Returns:
            True if sheet is cached, False otherwise.
        """
        sheet_key = sheet_name.lower().replace(' ', '-')
        return sheet_key in self.cache_data.get("data", {})
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics.
        """
        with self._lock:
            data = self.cache_data.get("data", {})
            total_rows = sum(sheet.get("row_count", 0) for sheet in data.values())
            
            return {
                "cache_file": str(self.cache_file),
                "cache_exists": self.cache_file.exists(),
                "file_size_kb": round(self.cache_file.stat().st_size / 1024, 2) if self.cache_file.exists() else 0,
                "last_updated": self.cache_data.get("last_updated_at"),
                "spreadsheet_id": self.cache_data.get("spreadsheet_id"),
                "sheet_count": len(data),
                "total_rows": total_rows,
                "sheets": {
                    name: {
                        "row_count": sheet.get("row_count", 0),
                        "last_modified": sheet.get("last_modified")
                    }
                    for name, sheet in data.items()
                }
            }
    
    def clear_cache(self, save_immediately: bool = True) -> None:
        """Clear all cached data.
        
        Args:
            save_immediately: Whether to save to file immediately.
        """
        with self._lock:
            self.cache_data = self._create_empty_cache()
            print("🧹 Cache cleared")
        
        if save_immediately:
            self._save_cache()
    
    def _calculate_data_hash(self, headers: List[str], rows: List[List[str]]) -> str:
        """Calculate a hash of the sheet data for change detection.
        
        Args:
            headers: Column headers.
            rows: Data rows.
            
        Returns:
            MD5 hash of the data.
        """
        data_string = json.dumps([headers] + rows, sort_keys=True)
        return hashlib.md5(data_string.encode()).hexdigest()
    
    def validate_cache_integrity(self) -> Dict[str, Any]:
        """Validate cache integrity and return report.
        
        Returns:
            Dictionary with validation results.
        """
        issues = []
        warnings = []
        
        try:
            with self._lock:
                # Check cache structure
                required_keys = ["version", "last_updated_at", "data"]
                for key in required_keys:
                    if key not in self.cache_data:
                        issues.append(f"Missing required key: {key}")
                
                # Check each sheet
                for sheet_name, sheet_data in self.cache_data.get("data", {}).items():
                    if not isinstance(sheet_data, dict):
                        issues.append(f"Sheet '{sheet_name}': Invalid data type")
                        continue
                    
                    # Check sheet structure
                    sheet_keys = ["last_modified", "row_count", "headers", "rows"]
                    for key in sheet_keys:
                        if key not in sheet_data:
                            issues.append(f"Sheet '{sheet_name}': Missing key '{key}'")
                    
                    # Check data consistency
                    if "rows" in sheet_data and "row_count" in sheet_data:
                        actual_count = len(sheet_data["rows"])
                        declared_count = sheet_data["row_count"]
                        if actual_count != declared_count:
                            issues.append(f"Sheet '{sheet_name}': Row count mismatch (actual: {actual_count}, declared: {declared_count})")
        
        except Exception as e:
            issues.append(f"Validation error: {e}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
