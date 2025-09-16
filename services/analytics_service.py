"""
Analytics Service
Handles data aggregation and analysis for visualizations.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict

from services.cached_sheets_service import CachedGoogleSheetsService


@dataclass
class MonthlySpending:
    """Data model for monthly spending analysis."""
    month: str  # "2025-01"
    month_name: str  # "January 2025"
    total_amount: float
    expense_count: int
    categories: Dict[str, float]  # category -> amount
    accounts: Dict[str, float]  # account -> amount
    daily_amounts: Dict[str, float]  # date -> amount
    avg_per_day: float
    top_expense: Optional[Dict[str, Any]]  # largest single expense


class AnalyticsService:
    """Service for generating analytics data from expense sheets."""
    
    def __init__(self, sheets_service: CachedGoogleSheetsService, spreadsheet_id: str):
        self.sheets_service = sheets_service
        self.spreadsheet_id = spreadsheet_id
    
    def get_available_months(self) -> List[str]:
        """Get list of available expense sheet months.
        
        Returns:
            List of sheet names that look like month-year sheets.
        """
        try:
            all_sheets = self.sheets_service.get_sheet_names(self.spreadsheet_id)
            
            # Filter for sheets that look like "Month Year" format
            month_sheets = []
            for sheet_name in all_sheets:
                if self._is_month_sheet(sheet_name):
                    month_sheets.append(sheet_name)
            
            # Sort by date (most recent first)
            return self._sort_sheets_by_date(month_sheets)
            
        except Exception as e:
            print(f"Error getting available months: {e}")
            return []
    
    def get_monthly_spending(self, sheet_name: str) -> Optional[MonthlySpending]:
        """Get spending analysis for a specific month.
        
        Args:
            sheet_name: Name of the month sheet (e.g., "January 2025").
            
        Returns:
            MonthlySpending object with analysis data.
        """
        try:
            # Get expense data for the month
            range_name = f"'{sheet_name}'!A:Z"
            df = self.sheets_service.get_data_as_dataframe(
                self.spreadsheet_id, range_name
            )
            
            if df.empty:
                print(f"No data found for sheet '{sheet_name}'")
                return self._empty_monthly_spending(sheet_name)
            
            print(f"Raw data for '{sheet_name}': {df.shape[0]} rows, {df.shape[1]} columns")
            
            # Clean and validate data
            df = self._clean_expense_data(df)
            if df.empty:
                print(f"No valid data after cleaning for sheet '{sheet_name}'")
                return self._empty_monthly_spending(sheet_name)
            
            # Calculate analytics
            return self._analyze_monthly_data(sheet_name, df)
            
        except Exception as e:
            print(f"Error analyzing {sheet_name}: {e}")
            import traceback
            traceback.print_exc()
            return self._empty_monthly_spending(sheet_name)
    
    def get_recent_months_spending(self, count: int = 3) -> List[MonthlySpending]:
        """Get spending data for the most recent N months.
        
        Args:
            count: Number of recent months to analyze.
            
        Returns:
            List of MonthlySpending objects, most recent first.
        """
        available_months = self.get_available_months()
        recent_months = available_months[:count]
        
        results = []
        for sheet_name in recent_months:
            spending_data = self.get_monthly_spending(sheet_name)
            if spending_data:
                results.append(spending_data)
        
        return results
    
    def get_last_three_months_spending(self) -> List[MonthlySpending]:
        """Get spending data for the last 3 calendar months (July, Aug, Sept 2025).
        
        Returns:
            List of MonthlySpending objects for July, August, September 2025.
        """
        from datetime import datetime
        
        # Define the specific months we want (most recent 3)
        target_months = ["July 2025", "August 2025", "September 2025"]
        
        print(f"🔍 Looking for spending data in months: {target_months}")
        
        results = []
        for month_name in target_months:
            print(f"\n📊 Analyzing {month_name}:")
            spending_data = self.get_monthly_spending(month_name)
            
            if spending_data and spending_data.total_amount > 0:
                print(f"  ✅ Found data: ${spending_data.total_amount:.2f} total, {spending_data.expense_count} expenses")
                print(f"  📋 Categories: {list(spending_data.categories.keys())}")
                print(f"  🏦 Accounts: {list(spending_data.accounts.keys())}")
                results.append(spending_data)
            else:
                print(f"  ❌ No spending data found for {month_name}")
                # Still add empty data for consistent chart display
                empty_data = self._empty_monthly_spending(month_name)
                results.append(empty_data)
        
        print(f"\n📈 Summary: Found data for {len([r for r in results if r.total_amount > 0])}/{len(target_months)} months")
        return results
    
    def get_spending_trend(self, months: int = 6) -> Dict[str, List[float]]:
        """Get spending trend data for charts.
        
        Args:
            months: Number of months to include in trend.
            
        Returns:
            Dict with 'months' and 'amounts' lists for charting.
        """
        spending_data = self.get_recent_months_spending(months)
        
        # Reverse to show chronological order
        spending_data.reverse()
        
        return {
            'months': [data.month_name for data in spending_data],
            'amounts': [data.total_amount for data in spending_data],
            'counts': [data.expense_count for data in spending_data]
        }
    
    def get_category_breakdown(self, sheet_name: str) -> Dict[str, float]:
        """Get category spending breakdown for a specific month.
        
        Args:
            sheet_name: Name of the month sheet.
            
        Returns:
            Dict mapping category names to amounts spent.
        """
        spending_data = self.get_monthly_spending(sheet_name)
        return spending_data.categories if spending_data else {}
    
    def _is_month_sheet(self, sheet_name: str) -> bool:
        """Check if sheet name looks like a month sheet."""
        # Simple heuristic: contains a month name and year
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                 'July', 'August', 'September', 'October', 'November', 'December']
        
        return any(month in sheet_name for month in months) and any(char.isdigit() for char in sheet_name)
    
    def _sort_sheets_by_date(self, sheet_names: List[str]) -> List[str]:
        """Sort sheet names by date (most recent first)."""
        def parse_sheet_date(sheet_name: str) -> datetime:
            try:
                # Parse "Month Year" format
                return datetime.strptime(sheet_name, "%B %Y")
            except ValueError:
                # Fallback: return very old date for unparseable sheets
                return datetime(1900, 1, 1)
        
        return sorted(sheet_names, key=parse_sheet_date, reverse=True)
    
    def _clean_expense_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate expense data with flexible column handling."""
        if df.empty:
            return pd.DataFrame()
        
        # Ensure minimum required columns
        if len(df.columns) < 3:
            print(f"Warning: Sheet has only {len(df.columns)} columns, need at least 3 (Date, Description, Amount)")
            return pd.DataFrame()
        
        # Convert column headers to strings and clean them
        # Convert column names to strings and handle duplicates
        df.columns = df.columns.astype(str)
        
        # Fix duplicate column names by adding suffix
        columns = list(df.columns)
        seen_columns = {}
        unique_columns = []
        
        for col in columns:
            if col in seen_columns:
                seen_columns[col] += 1
                unique_columns.append(f"{col}_{seen_columns[col]}")
            else:
                seen_columns[col] = 0
                unique_columns.append(col)
        
        df.columns = unique_columns
        print(f"🔧 Fixed duplicate columns. Original: {len(columns)}, Unique: {len(unique_columns)}")
        print(f"📋 Updated columns: {list(df.columns)}")
        
        # Standard column mapping (flexible based on actual column count)
        standard_names = ['Date', 'Description', 'Amount', 'Category', 'Account', 'Notes']
        
        # Create mapping only for columns that exist
        col_mapping = {}
        actual_columns = min(len(df.columns), len(standard_names))
        
        for i in range(actual_columns):
            original_col = df.columns[i]
            standard_col = standard_names[i]
            col_mapping[original_col] = standard_col
        
        # Apply column mapping
        df = df.rename(columns=col_mapping)
        
        # Ensure we have required columns
        required_columns = ['Date', 'Description', 'Amount']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Warning: Missing required columns: {missing_columns}")
            return pd.DataFrame()
        
        # Remove rows with empty required fields
        df = df.dropna(subset=['Description', 'Amount'])
        
        # Convert amount to float with error handling
        try:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
            df = df.dropna(subset=['Amount'])
            df = df[df['Amount'] > 0]  # Remove negative or zero amounts
        except Exception as e:
            print(f"Warning: Error converting amounts to numeric: {e}")
            return pd.DataFrame()
        
        # Add missing optional columns with defaults
        if 'Category' not in df.columns:
            df['Category'] = 'Uncategorized'
        else:
            df['Category'] = df['Category'].fillna('Uncategorized')
        
        if 'Account' not in df.columns:
            df['Account'] = 'Unknown'
        else:
            df['Account'] = df['Account'].fillna('Unknown')
        
        if 'Notes' not in df.columns:
            df['Notes'] = ''
        else:
            df['Notes'] = df['Notes'].fillna('')
        
        # Debug: Show sample of cleaned data and total
        total_amount = df['Amount'].sum() if len(df) > 0 else 0
        print(f"✅ Successfully processed {len(df)} expense records with {len(df.columns)} columns")
        print(f"📋 Final columns: {list(df.columns)}")
        print(f"💰 TOTAL AMOUNT CALCULATED: ${total_amount:.2f}")
        
        if len(df) > 0:
            print(f"📊 Sample data (first 3 rows):")
            for i, (_, row) in enumerate(df.head(3).iterrows()):
                print(f"  Row {i+1}: Date='{row['Date']}', Desc='{row['Description']}', Amount=${row['Amount']}, Cat='{row['Category']}', Account='{row['Account']}'")
        else:
            print("❌ No valid expense records found after cleaning")
        
        return df
    
    def _analyze_monthly_data(self, sheet_name: str, df: pd.DataFrame) -> MonthlySpending:
        """Analyze expense data for a month."""
        print(f"🔍 Analyzing monthly data for {sheet_name}")
        print(f"📊 DataFrame shape: {df.shape}")
        print(f"📋 Columns: {list(df.columns)}")
        
        # Basic calculations
        total_amount = float(df['Amount'].sum())
        expense_count = len(df)
        
        print(f"💰 CALCULATED TOTAL: ${total_amount:.2f} from {expense_count} expenses")
        
        # Category breakdown
        print(f"📈 Grouping by Category...")
        categories = df.groupby('Category')['Amount'].sum().to_dict()
        categories = {k: float(v) for k, v in categories.items()}
        print(f"📊 Categories breakdown: {categories}")
        
        # Account breakdown
        print(f"📈 Grouping by Account...")
        accounts = df.groupby('Account')['Amount'].sum().to_dict()
        accounts = {k: float(v) for k, v in accounts.items()}
        print(f"🏦 Accounts breakdown: {accounts}")
        
        # Daily amounts (if date parsing works)
        daily_amounts = {}
        try:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            daily_data = df.groupby(df['Date'].dt.date)['Amount'].sum()
            daily_amounts = {str(date): float(amount) for date, amount in daily_data.items() if pd.notna(date)}
        except Exception:
            daily_amounts = {}
        
        # Calculate average per day
        days_in_month = len(daily_amounts) if daily_amounts else expense_count
        avg_per_day = total_amount / max(days_in_month, 1)
        
        # Find top expense
        top_expense = None
        if not df.empty:
            max_idx = df['Amount'].idxmax()
            top_expense = {
                'description': df.loc[max_idx, 'Description'],
                'amount': float(df.loc[max_idx, 'Amount']),
                'category': df.loc[max_idx, 'Category'],
                'date': str(df.loc[max_idx, 'Date'])
            }
        
        # Parse month info
        month_date = self._parse_sheet_month(sheet_name)
        
        return MonthlySpending(
            month=month_date.strftime("%Y-%m") if month_date else "unknown",
            month_name=sheet_name,
            total_amount=total_amount,
            expense_count=expense_count,
            categories=categories,
            accounts=accounts,
            daily_amounts=daily_amounts,
            avg_per_day=avg_per_day,
            top_expense=top_expense
        )
    
    def _empty_monthly_spending(self, sheet_name: str) -> MonthlySpending:
        """Create empty MonthlySpending object."""
        month_date = self._parse_sheet_month(sheet_name)
        
        return MonthlySpending(
            month=month_date.strftime("%Y-%m") if month_date else "unknown",
            month_name=sheet_name,
            total_amount=0.0,
            expense_count=0,
            categories={},
            accounts={},
            daily_amounts={},
            avg_per_day=0.0,
            top_expense=None
        )
    
    def _parse_sheet_month(self, sheet_name: str) -> Optional[datetime]:
        """Parse month from sheet name."""
        try:
            return datetime.strptime(sheet_name, "%B %Y")
        except ValueError:
            return None
