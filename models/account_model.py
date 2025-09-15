"""
Account Management Models
Data structures for account management, transactions, and balance tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid


class AccountType(Enum):
    """Types of financial accounts."""
    CHEQUING = "chequing"
    SAVINGS = "savings"
    CREDIT = "credit"
    CASH = "cash"
    INVESTMENT = "investment"
    OTHER = "other"


class TransactionType(Enum):
    """Types of financial transactions."""
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"  # For balance corrections


class Currency(Enum):
    """Supported currencies."""
    CAD = "CAD"
    USD = "USD"
    EUR = "EUR"


@dataclass
class Account:
    """Core account entity representing a financial account."""
    
    id: str
    name: str                           # "TD Chequing", "Scotia Savings"
    account_type: AccountType           # CHEQUING, SAVINGS, CREDIT, CASH
    current_balance: float
    currency: Currency = Currency.CAD
    institution: Optional[str] = None   # "TD Bank", "Scotia Bank"
    account_number: Optional[str] = None # Masked: "****1234"
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.id:
            self.id = f"acc_{uuid.uuid4().hex[:8]}"
        
        if isinstance(self.account_type, str):
            self.account_type = AccountType(self.account_type)
        
        if isinstance(self.currency, str):
            self.currency = Currency(self.currency)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'account_type': self.account_type.value,
            'current_balance': self.current_balance,
            'currency': self.currency.value,
            'institution': self.institution,
            'account_number': self.account_number,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Account':
        """Create from dictionary."""
        # Parse dates
        created_at = None
        if data.get('created_at'):
            created_at = datetime.fromisoformat(data['created_at'])
            
        updated_at = None
        if data.get('updated_at'):
            updated_at = datetime.fromisoformat(data['updated_at'])
        
        return cls(
            id=data['id'],
            name=data['name'],
            account_type=AccountType(data['account_type']),
            current_balance=float(data['current_balance']),
            currency=Currency(data.get('currency', 'CAD')),
            institution=data.get('institution'),
            account_number=data.get('account_number'),
            is_active=data.get('is_active', True),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            notes=data.get('notes')
        )

    @property
    def display_name(self) -> str:
        """User-friendly display name."""
        if self.institution:
            return f"{self.institution} - {self.name}"
        return self.name
    
    @property
    def masked_account_number(self) -> str:
        """Return masked account number for display."""
        if not self.account_number:
            return "N/A"
        
        if len(self.account_number) <= 4:
            return self.account_number
        
        return f"****{self.account_number[-4:]}"


@dataclass
class Transaction:
    """Universal transaction record for income, expenses, and transfers."""
    
    id: str
    date: datetime
    description: str
    amount: float                       # Always positive - type determines impact
    transaction_type: TransactionType   # INCOME, EXPENSE, TRANSFER
    category: str
    account_id: str                     # Primary account affected
    to_account_id: Optional[str] = None # For transfers
    payment_method: Optional[str] = None # For backward compatibility
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    reference_id: Optional[str] = None  # External reference (receipt, invoice)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.id:
            self.id = f"txn_{uuid.uuid4().hex[:8]}"
            
        if isinstance(self.transaction_type, str):
            self.transaction_type = TransactionType(self.transaction_type)
        
        # Ensure amount is positive
        self.amount = abs(self.amount)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'amount': self.amount,
            'transaction_type': self.transaction_type.value,
            'category': self.category,
            'account_id': self.account_id,
            'to_account_id': self.to_account_id,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'tags': ','.join(self.tags) if self.tags else '',
            'reference_id': self.reference_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        """Create from dictionary."""
        # Parse dates
        date = datetime.fromisoformat(data['date']) if data.get('date') else datetime.now()
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        
        # Parse tags
        tags = []
        if data.get('tags'):
            tags = [tag.strip() for tag in data['tags'].split(',') if tag.strip()]
        
        return cls(
            id=data['id'],
            date=date,
            description=data['description'],
            amount=float(data['amount']),
            transaction_type=TransactionType(data['transaction_type']),
            category=data['category'],
            account_id=data['account_id'],
            to_account_id=data.get('to_account_id'),
            payment_method=data.get('payment_method'),
            notes=data.get('notes'),
            tags=tags,
            reference_id=data.get('reference_id'),
            created_at=created_at
        )
    
    @property
    def impact_amount(self) -> float:
        """Get the impact amount based on transaction type."""
        if self.transaction_type == TransactionType.INCOME:
            return self.amount  # Positive impact
        elif self.transaction_type == TransactionType.EXPENSE:
            return -self.amount  # Negative impact
        else:
            return 0  # Transfers are handled separately


@dataclass
class AccountSnapshot:
    """Audit trail for account balance changes."""
    
    id: str
    account_id: str
    balance_before: float
    balance_after: float
    transaction_id: Optional[str] = None
    change_reason: str = "transaction"  # "transaction", "adjustment", "correction"
    timestamp: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.id:
            self.id = f"snap_{uuid.uuid4().hex[:8]}"
    
    @property
    def balance_change(self) -> float:
        """Calculate the balance change."""
        return self.balance_after - self.balance_before
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'account_id': self.account_id,
            'balance_before': self.balance_before,
            'balance_after': self.balance_after,
            'transaction_id': self.transaction_id,
            'change_reason': self.change_reason,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountSnapshot':
        """Create from dictionary."""
        timestamp = datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else datetime.now()
        
        return cls(
            id=data['id'],
            account_id=data['account_id'],
            balance_before=float(data['balance_before']),
            balance_after=float(data['balance_after']),
            transaction_id=data.get('transaction_id'),
            change_reason=data.get('change_reason', 'transaction'),
            timestamp=timestamp,
            notes=data.get('notes')
        )


@dataclass
class AccountGroup:
    """Group of accounts for organizational purposes (Personal, Business, etc.)."""
    
    id: str
    name: str                          # "Personal", "Business", "Joint"
    description: Optional[str] = None
    account_ids: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.id:
            self.id = f"grp_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'account_ids': self.account_ids,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AccountGroup':
        """Create from dictionary."""
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        
        return cls(
            id=data['id'],
            name=data['name'],
            description=data.get('description'),
            account_ids=data.get('account_ids', []),
            is_active=data.get('is_active', True),
            created_at=created_at
        )


# Helper functions for account management
def create_default_accounts() -> List[Account]:
    """Create default accounts for a new user."""
    return [
        Account(
            id="cash_account",
            name="Cash Wallet",
            account_type=AccountType.CASH,
            current_balance=0.0,
            notes="Physical cash on hand"
        ),
        Account(
            id="primary_chequing",
            name="Primary Chequing",
            account_type=AccountType.CHEQUING,
            current_balance=0.0,
            notes="Main chequing account for daily expenses"
        ),
        Account(
            id="primary_savings",
            name="Primary Savings",
            account_type=AccountType.SAVINGS,
            current_balance=0.0,
            notes="Main savings account for emergency funds"
        )
    ]


def get_account_type_display_name(account_type: AccountType) -> str:
    """Get user-friendly display name for account types."""
    display_names = {
        AccountType.CHEQUING: "Chequing Account",
        AccountType.SAVINGS: "Savings Account", 
        AccountType.CREDIT: "Credit Card",
        AccountType.CASH: "Cash",
        AccountType.INVESTMENT: "Investment Account",
        AccountType.OTHER: "Other Account"
    }
    return display_names.get(account_type, account_type.value.title())

