"""
Expense Data Model
Data structures and utilities for expense data handling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd


@dataclass
class ExpenseRecord:
    """Individual expense record."""
    id: str
    date: datetime
    description: str
    amount: float
    category: str
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'amount': self.amount,
            'category': self.category,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'tags': ','.join(self.tags) if self.tags else ''
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExpenseRecord':
        """Create from dictionary."""
        date = datetime.fromisoformat(data['date']) if data.get('date') else datetime.now()
        tags = data.get('tags', '').split(',') if data.get('tags') else []
        
        return cls(
            id=data['id'],
            date=date,
            description=data['description'],
            amount=float(data['amount']),
            category=data['category'],
            payment_method=data.get('payment_method'),
            notes=data.get('notes'),
            tags=[tag.strip() for tag in tags if tag.strip()]
        )


@dataclass
class ExpenseAnalytics:
    """Analytics and summary data for expenses."""
    total_amount: float
    record_count: int
    date_range: tuple
    top_categories: Dict[str, float]
    monthly_totals: Dict[str, float]
    average_per_day: float
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> 'ExpenseAnalytics':
        """Generate analytics from DataFrame."""
        if df.empty:
            return cls(
                total_amount=0,
                record_count=0,
                date_range=(None, None),
                top_categories={},
                monthly_totals={},
                average_per_day=0
            )
        
        # Ensure we have required columns (adapt to your sheet structure)
        amount_col = None
        date_col = None
        category_col = None
        
        # Try to find amount column
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['amount', 'cost', 'price', 'total']):
                amount_col = col
                break
        
        # Try to find date column  
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['date', 'time', 'when']):
                date_col = col
                break
                
        # Try to find category column
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['category', 'type', 'kind']):
                category_col = col
                break
        
        # Convert amount column to numeric
        total_amount = 0
        if amount_col:
            numeric_amounts = pd.to_numeric(df[amount_col], errors='coerce').fillna(0)
            total_amount = numeric_amounts.sum()
        
        # Calculate top categories
        top_categories = {}
        if category_col and amount_col:
            try:
                category_totals = df.groupby(category_col)[amount_col].apply(
                    lambda x: pd.to_numeric(x, errors='coerce').fillna(0).sum()
                ).sort_values(ascending=False).head(10)
                top_categories = category_totals.to_dict()
            except:
                pass
        
        # Date range analysis
        date_range = (None, None)
        monthly_totals = {}
        if date_col:
            try:
                # Try to parse dates
                dates = pd.to_datetime(df[date_col], errors='coerce').dropna()
                if not dates.empty:
                    date_range = (dates.min(), dates.max())
                    
                    # Monthly totals
                    if amount_col:
                        df_with_dates = df.copy()
                        df_with_dates['parsed_date'] = pd.to_datetime(df_with_dates[date_col], errors='coerce')
                        df_with_dates['amount_numeric'] = pd.to_numeric(df_with_dates[amount_col], errors='coerce').fillna(0)
                        df_with_dates = df_with_dates.dropna(subset=['parsed_date'])
                        
                        monthly = df_with_dates.groupby(df_with_dates['parsed_date'].dt.to_period('M'))['amount_numeric'].sum()
                        monthly_totals = {str(k): v for k, v in monthly.to_dict().items()}
            except:
                pass
        
        # Average per day
        average_per_day = 0
        if date_range[0] and date_range[1] and total_amount > 0:
            days_diff = (date_range[1] - date_range[0]).days + 1
            average_per_day = total_amount / days_diff if days_diff > 0 else 0
        
        return cls(
            total_amount=total_amount,
            record_count=len(df),
            date_range=date_range,
            top_categories=top_categories,
            monthly_totals=monthly_totals,
            average_per_day=average_per_day
        )


class ExpenseDataProcessor:
    """Utility class for processing expense data."""
    
    @staticmethod
    def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize expense data."""
        if df.empty:
            return df
        
        cleaned_df = df.copy()
        
        # Remove completely empty rows
        cleaned_df = cleaned_df.dropna(how='all')
        
        # Strip whitespace from string columns
        for col in cleaned_df.select_dtypes(include=['object']).columns:
            cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
            # Replace 'nan' strings with actual NaN
            cleaned_df[col] = cleaned_df[col].replace('nan', pd.NA)
        
        return cleaned_df
    
    @staticmethod
    def detect_column_types(df: pd.DataFrame) -> Dict[str, str]:
        """Detect likely column types based on content."""
        if df.empty:
            return {}
        
        column_types = {}
        
        for col in df.columns:
            col_lower = col.lower()
            
            # Amount/numeric columns
            if any(keyword in col_lower for keyword in ['amount', 'cost', 'price', 'total', 'value']):
                column_types[col] = 'amount'
            # Date columns
            elif any(keyword in col_lower for keyword in ['date', 'time', 'when']):
                column_types[col] = 'date'
            # Category columns
            elif any(keyword in col_lower for keyword in ['category', 'type', 'kind', 'group']):
                column_types[col] = 'category'
            # Description columns
            elif any(keyword in col_lower for keyword in ['description', 'desc', 'name', 'item', 'note']):
                column_types[col] = 'description'
            # Default to text
            else:
                column_types[col] = 'text'
        
        return column_types
    
    @staticmethod
    def get_summary_stats(df: pd.DataFrame) -> Dict[str, Any]:
        """Get summary statistics for the dataframe."""
        if df.empty:
            return {}
        
        stats = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'columns': list(df.columns),
            'column_types': ExpenseDataProcessor.detect_column_types(df)
        }
        
        # Add numeric summaries for amount columns
        for col, col_type in stats['column_types'].items():
            if col_type == 'amount':
                numeric_data = pd.to_numeric(df[col], errors='coerce')
                stats[f'{col}_sum'] = numeric_data.sum()
                stats[f'{col}_mean'] = numeric_data.mean()
                stats[f'{col}_count'] = numeric_data.count()
        
        return stats
