"""
Data validation utilities
"""
import re
from typing import Optional, Tuple

class Validators:
    """Common validation functions"""
    
    @staticmethod
    def validate_amount(amount: float) -> Tuple[bool, Optional[str]]:
        """
        Validate facility amount
        
        Args:
            amount: Amount to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if amount <= 0:
            return False, "Amount must be greater than zero"
        
        if amount > 10_000_000_000:  # 10 billion
            return False, "Amount exceeds maximum limit"
        
        return True, None
    
    @staticmethod
    def validate_profit_rate(rate: float) -> Tuple[bool, Optional[str]]:
        """
        Validate profit rate
        
        Args:
            rate: Profit rate to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if rate < 0:
            return False, "Profit rate cannot be negative"
        
        if rate > 100:
            return False, "Profit rate cannot exceed 100%"
        
        return True, None
    
    @staticmethod
    def validate_tenor(tenor: int) -> Tuple[bool, Optional[str]]:
        """
        Validate tenor duration
        
        Args:
            tenor: Tenor in months
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if tenor <= 0:
            return False, "Tenor must be greater than zero"
        
        if tenor > 360:  # 30 years
            return False, "Tenor exceeds maximum allowed period"
        
        return True, None
    
    @staticmethod
    def validate_customer_name(name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate customer name
        
        Args:
            name: Customer name
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not name or len(name.strip()) == 0:
            return False, "Customer name cannot be empty"
        
        if len(name) < 2:
            return False, "Customer name too short"
        
        if len(name) > 200:
            return False, "Customer name too long"
        
        return True, None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to remove invalid characters
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')
        
        return filename
