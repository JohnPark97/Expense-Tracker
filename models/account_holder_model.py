"""
Account Holder Management Models
Simple data structures for account holder management.
"""

from dataclasses import dataclass
from typing import Dict, Any
import uuid


@dataclass
class AccountHolder:
    """Simple account holder entity representing a person who owns/manages accounts."""
    
    id: str
    name: str  # "John Doe", "Jane Smith"
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.id:
            self.id = f"holder_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountHolder':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            name=data['name']
        )

    @property
    def display_name(self) -> str:
        """Account holder-friendly display name."""
        return self.name


# Helper functions for account holder management
def create_default_account_holder(name: str) -> AccountHolder:
    """Create a default account holder."""
    return AccountHolder(
        id=f"holder_{name.lower().replace(' ', '_')}",
        name=name
    )
