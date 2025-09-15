"""
Account Holder Service
Business logic for account holder management.
"""

from dataclasses import dataclass
from typing import List, Optional, Callable, Dict, Any

from models.account_holder_model import AccountHolder, create_default_account_holder
from repositories.account_holder_repository import AccountHolderRepository


@dataclass
class AccountHolderChangeEvent:
    """Event data for account holder changes."""
    account_holder: AccountHolder
    change_type: str  # "created", "updated", "deleted"
    timestamp: str


class AccountHolderService:
    """Service for managing account holders with business logic."""
    
    def __init__(self, account_holder_repo: AccountHolderRepository):
        """Initialize service.
        
        Args:
            account_holder_repo: Repository for account holder data.
        """
        self.account_holder_repo = account_holder_repo
        self._change_subscribers: List[Callable[[AccountHolderChangeEvent], None]] = []
    
    def subscribe_to_changes(self, callback: Callable[[AccountHolderChangeEvent], None]):
        """Subscribe to account holder change events.
        
        Args:
            callback: Function to call when account holders change.
        """
        if callback not in self._change_subscribers:
            self._change_subscribers.append(callback)
    
    def unsubscribe_from_changes(self, callback: Callable[[AccountHolderChangeEvent], None]):
        """Unsubscribe from account holder change events.
        
        Args:
            callback: Function to remove from subscribers.
        """
        if callback in self._change_subscribers:
            self._change_subscribers.remove(callback)
    
    def _publish_change_event(self, account_holder: AccountHolder, change_type: str):
        """Publish account holder change event to subscribers.
        
        Args:
            account_holder: The account holder that changed.
            change_type: Type of change ("created", "updated", "deleted").
        """
        from datetime import datetime
        
        event = AccountHolderChangeEvent(
            account_holder=account_holder,
            change_type=change_type,
            timestamp=datetime.now().isoformat()
        )
        
        for callback in self._change_subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in account holder change subscriber: {e}")
    
    def get_all_account_holders(self) -> List[AccountHolder]:
        """Get all account holders.
        
        Returns:
            List of AccountHolder objects.
        """
        return self.account_holder_repo.get_all_account_holders()
    
    def get_account_holder_by_id(self, account_holder_id: str) -> Optional[AccountHolder]:
        """Get account holder by ID.
        
        Args:
            account_holder_id: Account holder ID.
            
        Returns:
            AccountHolder object or None if not found.
        """
        account_holders = self.get_all_account_holders()
        for holder in account_holders:
            if holder.id == account_holder_id:
                return holder
        return None
    
    def get_account_holder_by_name(self, name: str) -> Optional[AccountHolder]:
        """Get account holder by name.
        
        Args:
            name: Account holder name.
            
        Returns:
            AccountHolder object or None if not found.
        """
        account_holders = self.get_all_account_holders()
        for holder in account_holders:
            if holder.name.lower() == name.lower():
                return holder
        return None
    
    def create_account_holder(self, account_holder: AccountHolder) -> bool:
        """Create a new account holder.
        
        Args:
            account_holder: AccountHolder object to create.
            
        Returns:
            True if successful, False otherwise.
        """
        # Check for duplicate names
        existing = self.get_account_holder_by_name(account_holder.name)
        if existing:
            print(f"❌ Account holder with name '{account_holder.name}' already exists")
            return False
        
        # Create the account holder
        success = self.account_holder_repo.create_account_holder(account_holder)
        
        if success:
            self._publish_change_event(account_holder, "created")
        
        return success
    
    def update_account_holder(self, account_holder: AccountHolder) -> bool:
        """Update an existing account holder.
        
        Args:
            account_holder: AccountHolder object with updated data.
            
        Returns:
            True if successful, False otherwise.
        """
        # Check if account holder exists
        existing = self.get_account_holder_by_id(account_holder.id)
        if not existing:
            print(f"❌ Account holder not found: {account_holder.id}")
            return False
        
        # Check for duplicate names (excluding current account holder)
        name_check = self.get_account_holder_by_name(account_holder.name)
        if name_check and name_check.id != account_holder.id:
            print(f"❌ Account holder with name '{account_holder.name}' already exists")
            return False
        
        # Update the account holder
        success = self.account_holder_repo.update_account_holder(account_holder)
        
        if success:
            self._publish_change_event(account_holder, "updated")
        
        return success
    
    def delete_account_holder(self, account_holder_id: str) -> bool:
        """Delete an account holder.
        
        Args:
            account_holder_id: ID of the account holder to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        # Get the account holder first (for event)
        account_holder = self.get_account_holder_by_id(account_holder_id)
        if not account_holder:
            print(f"❌ Account holder not found: {account_holder_id}")
            return False
        
        # Delete the account holder
        success = self.account_holder_repo.delete_account_holder(account_holder_id)
        
        if success:
            self._publish_change_event(account_holder, "deleted")
        
        return success
    
    def get_account_holder_summary(self) -> Dict[str, Any]:
        """Get summary statistics for account holders.
        
        Returns:
            Dictionary with summary data.
        """
        account_holders = self.get_all_account_holders()
        
        return {
            'total_count': len(account_holders),
            'names': [holder.name for holder in account_holders]
        }
    
    def initialize_default_account_holder(self) -> bool:
        """Initialize a default account holder if none exist.
        
        Returns:
            True if successful or account holders already exist.
        """
        account_holders = self.get_all_account_holders()
        
        if account_holders:
            print(f"Account holders already exist ({len(account_holders)} found). Skipping default initialization.")
            return True
        
        # Create default account holder
        default_holder = create_default_account_holder("Default User")
        
        success = self.create_account_holder(default_holder)
        
        if success:
            print(f"✅ Created default account holder: {default_holder.name}")
        else:
            print(f"❌ Failed to create default account holder")
        
        return success
    
    def get_account_holder_names(self) -> List[str]:
        """Get list of account holder names for dropdowns.
        
        Returns:
            List of account holder names.
        """
        account_holders = self.get_all_account_holders()
        return [holder.name for holder in account_holders]
