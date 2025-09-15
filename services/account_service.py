"""
Account Service
Business logic for account management, balance tracking, and transaction processing.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from collections import defaultdict
import threading

from models.account_model import Account, Transaction, AccountSnapshot, AccountGroup
from models.account_model import AccountType, TransactionType, create_default_accounts
from repositories.account_repository import AccountRepository, TransactionRepository


class BalanceChangeEvent:
    """Event triggered when account balance changes."""
    
    def __init__(self, account: Account, old_balance: float, new_balance: float,
                 transaction: Optional[Transaction] = None):
        self.account = account
        self.old_balance = old_balance
        self.new_balance = new_balance
        self.transaction = transaction
        self.timestamp = datetime.now()
        self.balance_change = new_balance - old_balance


class AccountService:
    """Service for managing accounts and processing transactions."""
    
    def __init__(self, account_repo: AccountRepository, transaction_repo: TransactionRepository):
        """Initialize account service.
        
        Args:
            account_repo: Account repository for data persistence.
            transaction_repo: Transaction repository for data persistence.
        """
        self.account_repo = account_repo
        self.transaction_repo = transaction_repo
        
        # Event subscribers (Observer pattern)
        self._balance_change_subscribers: List[Callable[[BalanceChangeEvent], None]] = []
        self._lock = threading.Lock()
        
        # Cache for frequently accessed accounts
        self._accounts_cache: Dict[str, Account] = {}
        self._cache_last_refresh: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5 minutes
    
    # ======================== Account Management ========================
    
    def get_all_accounts(self, include_inactive: bool = False, refresh_cache: bool = False) -> List[Account]:
        """Get all accounts with optional caching.
        
        Args:
            include_inactive: Whether to include inactive accounts.
            refresh_cache: Force refresh of accounts cache.
            
        Returns:
            List of Account objects.
        """
        # Check cache freshness
        if (refresh_cache or not self._cache_last_refresh or 
            (datetime.now() - self._cache_last_refresh).total_seconds() > self._cache_ttl_seconds):
            self._refresh_accounts_cache()
        
        accounts = list(self._accounts_cache.values())
        
        if not include_inactive:
            accounts = [acc for acc in accounts if acc.is_active]
        
        return accounts
    
    def get_account_by_id(self, account_id: str, refresh_cache: bool = False) -> Optional[Account]:
        """Get account by ID with caching.
        
        Args:
            account_id: Account ID to find.
            refresh_cache: Force refresh of accounts cache.
            
        Returns:
            Account object if found, None otherwise.
        """
        if refresh_cache or account_id not in self._accounts_cache:
            self._refresh_accounts_cache()
        
        return self._accounts_cache.get(account_id)
    
    def create_account(self, account: Account) -> bool:
        """Create a new account.
        
        Args:
            account: Account object to create.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Validate account
            if not self._validate_account(account):
                return False
            
            # Check for duplicate names (within same account type)
            existing_accounts = self.get_accounts_by_type(account.account_type)
            for existing in existing_accounts:
                if existing.name.lower() == account.name.lower() and existing.is_active:
                    print(f"❌ Account with name '{account.name}' already exists for type {account.account_type.value}")
                    return False
            
            # Create in repository
            success = self.account_repo.create_account(account)
            
            if success:
                # Update cache
                self._accounts_cache[account.id] = account
                print(f"✅ Account created successfully: {account.display_name}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error creating account: {e}")
            return False
    
    def update_account(self, account: Account) -> bool:
        """Update an existing account.
        
        Args:
            account: Account object with updated data.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            if not self._validate_account(account):
                return False
            
            # Get old account for event handling
            old_account = self.get_account_by_id(account.id)
            if not old_account:
                print(f"Account {account.id} not found for update")
                return False
            
            old_balance = old_account.current_balance
            new_balance = account.current_balance
            
            # Update in repository
            success = self.account_repo.update_account(account)
            
            if success:
                # Update cache
                self._accounts_cache[account.id] = account
                
                # Trigger balance change event if balance changed
                if old_balance != new_balance:
                    event = BalanceChangeEvent(account, old_balance, new_balance)
                    self._notify_balance_change(event)
                
                print(f"✅ Account updated successfully: {account.display_name}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error updating account: {e}")
            return False
    
    def delete_account(self, account_id: str) -> bool:
        """Delete an account (soft delete).
        
        Args:
            account_id: ID of account to delete.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            account = self.get_account_by_id(account_id)
            if not account:
                print(f"Account {account_id} not found for deletion")
                return False
            
            # Check if account has transactions
            transactions = self.transaction_repo.get_transactions_by_account(account_id, limit=1)
            if transactions:
                print(f"⚠️  Account {account.name} has transactions. Soft deleting...")
            
            # Soft delete
            success = self.account_repo.delete_account(account_id)
            
            if success:
                # Update cache
                if account_id in self._accounts_cache:
                    self._accounts_cache[account_id].is_active = False
                
                print(f"✅ Account deleted: {account.display_name}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error deleting account: {e}")
            return False
    
    def get_accounts_by_type(self, account_type: AccountType, include_inactive: bool = False) -> List[Account]:
        """Get accounts filtered by type.
        
        Args:
            account_type: Account type to filter by.
            include_inactive: Whether to include inactive accounts.
            
        Returns:
            List of accounts of the specified type.
        """
        all_accounts = self.get_all_accounts(include_inactive=include_inactive)
        return [acc for acc in all_accounts if acc.account_type == account_type]
    
    # ======================== Balance Management ========================
    
    def update_account_balance(self, account_id: str, new_balance: float, 
                             reason: str = "manual adjustment") -> bool:
        """Update account balance directly.
        
        Args:
            account_id: Account ID to update.
            new_balance: New balance amount.
            reason: Reason for balance change.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            account = self.get_account_by_id(account_id)
            if not account:
                print(f"Account {account_id} not found for balance update")
                return False
            
            old_balance = account.current_balance
            account.current_balance = new_balance
            
            # Update in repository
            success = self.account_repo.update_account(account)
            
            if success:
                # Update cache
                self._accounts_cache[account_id] = account
                
                # Trigger balance change event
                event = BalanceChangeEvent(account, old_balance, new_balance)
                self._notify_balance_change(event)
                
                print(f"💰 Balance updated for {account.name}: ${old_balance:.2f} → ${new_balance:.2f}")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error updating account balance: {e}")
            return False
    
    def process_transaction(self, transaction: Transaction) -> bool:
        """Process a transaction and update account balance(s).
        
        Args:
            transaction: Transaction to process.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Get the primary account
            account = self.get_account_by_id(transaction.account_id)
            if not account:
                print(f"Account {transaction.account_id} not found for transaction")
                return False
            
            # Calculate balance impact
            old_balance = account.current_balance
            impact_amount = transaction.impact_amount
            new_balance = old_balance + impact_amount
            
            # Handle transfers (affects two accounts)
            to_account = None
            if transaction.transaction_type == TransactionType.TRANSFER and transaction.to_account_id:
                to_account = self.get_account_by_id(transaction.to_account_id)
                if not to_account:
                    print(f"Destination account {transaction.to_account_id} not found for transfer")
                    return False
            
            # Validate sufficient funds for expenses and transfers
            if (transaction.transaction_type in [TransactionType.EXPENSE, TransactionType.TRANSFER] and
                new_balance < 0 and account.account_type != AccountType.CREDIT):
                print(f"❌ Insufficient funds in {account.name}: ${old_balance:.2f} available, ${transaction.amount:.2f} needed")
                return False
            
            # Create transaction record first
            success = self.transaction_repo.create_transaction(transaction)
            if not success:
                print(f"Failed to create transaction record")
                return False
            
            # Update primary account balance
            account.current_balance = new_balance
            success = self.account_repo.update_account(account)
            if not success:
                print(f"Failed to update primary account balance")
                return False
            
            # Update cache
            self._accounts_cache[account.id] = account
            
            # Handle transfer destination
            if to_account:
                to_account.current_balance += transaction.amount
                success = self.account_repo.update_account(to_account)
                if success:
                    self._accounts_cache[to_account.id] = to_account
                    print(f"🔄 Transfer: ${transaction.amount:.2f} from {account.name} to {to_account.name}")
                else:
                    print(f"⚠️  Transfer partially completed - destination account update failed")
            
            # Trigger balance change event
            event = BalanceChangeEvent(account, old_balance, new_balance, transaction)
            self._notify_balance_change(event)
            
            transaction_type_emoji = {
                TransactionType.INCOME: "💰",
                TransactionType.EXPENSE: "💸",
                TransactionType.TRANSFER: "🔄",
                TransactionType.ADJUSTMENT: "⚖️"
            }
            emoji = transaction_type_emoji.get(transaction.transaction_type, "📝")
            
            print(f"{emoji} Transaction processed: {transaction.description} (${transaction.amount:.2f})")
            return True
            
        except Exception as e:
            print(f"Error processing transaction: {e}")
            return False
    
    # ======================== Analytics & Insights ========================
    
    def get_total_balance(self, account_types: Optional[List[AccountType]] = None) -> float:
        """Get total balance across accounts.
        
        Args:
            account_types: Optional list of account types to include. If None, includes all.
            
        Returns:
            Total balance amount.
        """
        accounts = self.get_all_accounts(include_inactive=False)
        
        if account_types:
            accounts = [acc for acc in accounts if acc.account_type in account_types]
        
        return sum(acc.current_balance for acc in accounts)
    
    def get_liquid_balance(self) -> float:
        """Get total liquid balance (chequing + savings + cash).
        
        Returns:
            Total liquid balance amount.
        """
        liquid_types = [AccountType.CHEQUING, AccountType.SAVINGS, AccountType.CASH]
        return self.get_total_balance(liquid_types)
    
    def get_net_worth(self) -> float:
        """Calculate net worth (assets - liabilities).
        
        Returns:
            Net worth amount.
        """
        assets = self.get_total_balance([
            AccountType.CHEQUING, AccountType.SAVINGS, 
            AccountType.CASH, AccountType.INVESTMENT
        ])
        
        # Credit cards are liabilities (negative balances represent debt)
        credit_accounts = self.get_accounts_by_type(AccountType.CREDIT)
        liabilities = sum(abs(acc.current_balance) for acc in credit_accounts if acc.current_balance < 0)
        
        return assets - liabilities
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get comprehensive account summary.
        
        Returns:
            Dictionary with account summary statistics.
        """
        accounts = self.get_all_accounts()
        
        summary = {
            'total_accounts': len(accounts),
            'accounts_by_type': defaultdict(int),
            'balances_by_type': defaultdict(float),
            'total_balance': 0,
            'liquid_balance': self.get_liquid_balance(),
            'net_worth': self.get_net_worth()
        }
        
        for account in accounts:
            account_type = account.account_type.value
            summary['accounts_by_type'][account_type] += 1
            summary['balances_by_type'][account_type] += account.current_balance
            summary['total_balance'] += account.current_balance
        
        return dict(summary)
    
    # ======================== Event Management ========================
    
    def subscribe_to_balance_changes(self, callback: Callable[[BalanceChangeEvent], None]):
        """Subscribe to balance change events.
        
        Args:
            callback: Function to call when balance changes occur.
        """
        with self._lock:
            self._balance_change_subscribers.append(callback)
    
    def unsubscribe_from_balance_changes(self, callback: Callable[[BalanceChangeEvent], None]):
        """Unsubscribe from balance change events.
        
        Args:
            callback: Function to remove from subscribers.
        """
        with self._lock:
            if callback in self._balance_change_subscribers:
                self._balance_change_subscribers.remove(callback)
    
    def _notify_balance_change(self, event: BalanceChangeEvent):
        """Notify all subscribers of balance change.
        
        Args:
            event: Balance change event to broadcast.
        """
        with self._lock:
            for callback in self._balance_change_subscribers:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error in balance change callback: {e}")
    
    # ======================== Initialization & Migration ========================
    
    def initialize_default_accounts(self) -> bool:
        """Initialize default accounts for new users.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            existing_accounts = self.get_all_accounts()
            if existing_accounts:
                print(f"Accounts already exist ({len(existing_accounts)} found). Skipping default initialization.")
                return True
            
            print("🏦 Initializing default accounts...")
            default_accounts = create_default_accounts()
            
            success_count = 0
            for account in default_accounts:
                if self.create_account(account):
                    success_count += 1
            
            if success_count == len(default_accounts):
                print(f"✅ Successfully initialized {success_count} default accounts")
                return True
            else:
                print(f"⚠️  Partially initialized accounts: {success_count}/{len(default_accounts)} successful")
                return False
                
        except Exception as e:
            print(f"Error initializing default accounts: {e}")
            return False
    
    def migrate_payment_methods_to_accounts(self, payment_methods: List[str]) -> bool:
        """Migrate existing payment methods to accounts.
        
        Args:
            payment_methods: List of payment method names to migrate.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            print("🔄 Migrating payment methods to accounts...")
            
            # Mapping of payment methods to account types
            payment_method_mapping = {
                'cash': AccountType.CASH,
                'debit card': AccountType.CHEQUING,
                'credit card': AccountType.CREDIT,
                'bank transfer': AccountType.CHEQUING,
                'simplii': AccountType.CHEQUING,  # Specific bank account
                'mobile payment': AccountType.CHEQUING,  # Usually linked to chequing
            }
            
            migrated_count = 0
            for method in payment_methods:
                method_lower = method.lower().strip()
                
                # Skip if account already exists
                existing_accounts = self.get_all_accounts()
                if any(acc.name.lower() == method_lower or 
                       method_lower in acc.name.lower() for acc in existing_accounts):
                    print(f"⏭️  Skipping {method} - account already exists")
                    continue
                
                # Determine account type
                account_type = payment_method_mapping.get(method_lower, AccountType.OTHER)
                
                # Create account
                account = Account(
                    id=f"migrated_{method_lower.replace(' ', '_')}",
                    name=method,
                    account_type=account_type,
                    current_balance=0.0,
                    notes=f"Migrated from payment method: {method}"
                )
                
                if self.create_account(account):
                    migrated_count += 1
                    print(f"✅ Migrated: {method} → {account_type.value} account")
            
            print(f"🎯 Migration completed: {migrated_count} payment methods migrated to accounts")
            return True
            
        except Exception as e:
            print(f"Error migrating payment methods: {e}")
            return False
    
    # ======================== Private Helper Methods ========================
    
    def _refresh_accounts_cache(self):
        """Refresh the accounts cache from repository."""
        try:
            accounts = self.account_repo.get_all_accounts(include_inactive=True)
            self._accounts_cache = {acc.id: acc for acc in accounts}
            self._cache_last_refresh = datetime.now()
            print(f"🔄 Refreshed accounts cache: {len(accounts)} accounts loaded")
        except Exception as e:
            print(f"Error refreshing accounts cache: {e}")
    
    def _validate_account(self, account: Account) -> bool:
        """Validate account data.
        
        Args:
            account: Account to validate.
            
        Returns:
            True if valid, False otherwise.
        """
        if not account.name or not account.name.strip():
            print("❌ Account name is required")
            return False
        
        if not isinstance(account.account_type, AccountType):
            print("❌ Invalid account type")
            return False
        
        if not isinstance(account.current_balance, (int, float)):
            print("❌ Invalid balance amount")
            return False
        
        return True

