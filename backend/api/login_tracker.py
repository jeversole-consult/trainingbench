"""
Track failed login attempts to prevent brute force attacks.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional

class LoginTracker:
    """Track failed login attempts by IP address."""
    
    def __init__(self, max_attempts: int = 5, lockout_duration: int = 900):
        """
        Initialize the login tracker.
        
        Args:
            max_attempts: Maximum failed attempts before lockout (default: 5)
            lockout_duration: Lockout duration in seconds (default: 900 = 15 minutes)
        """
        self.max_attempts = max_attempts
        self.lockout_duration = lockout_duration
        self.failed_attempts: Dict[str, list] = {}
        self.lockouts: Dict[str, datetime] = {}
    
    def is_locked_out(self, ip_address: str) -> bool:
        """Check if an IP address is currently locked out."""
        if ip_address in self.lockouts:
            lockout_time = self.lockouts[ip_address]
            if datetime.now() < lockout_time:
                return True
            else:
                # Lockout expired, remove it
                del self.lockouts[ip_address]
                if ip_address in self.failed_attempts:
                    del self.failed_attempts[ip_address]
        return False
    
    def get_lockout_remaining(self, ip_address: str) -> Optional[int]:
        """Get remaining lockout time in seconds."""
        if ip_address in self.lockouts:
            remaining = (self.lockouts[ip_address] - datetime.now()).total_seconds()
            return int(remaining) if remaining > 0 else None
        return None
    
    def record_failed_attempt(self, ip_address: str) -> bool:
        """
        Record a failed login attempt.
        
        Returns:
            True if the IP should be locked out, False otherwise
        """
        now = datetime.now()
        
        # Initialize or get existing attempts
        if ip_address not in self.failed_attempts:
            self.failed_attempts[ip_address] = []
        
        # Add this attempt
        self.failed_attempts[ip_address].append(now)
        
        # Remove attempts older than lockout duration
        cutoff = now - timedelta(seconds=self.lockout_duration)
        self.failed_attempts[ip_address] = [
            attempt for attempt in self.failed_attempts[ip_address]
            if attempt > cutoff
        ]
        
        # Check if we should lock out
        if len(self.failed_attempts[ip_address]) >= self.max_attempts:
            self.lockouts[ip_address] = now + timedelta(seconds=self.lockout_duration)
            return True
        
        return False
    
    def record_successful_login(self, ip_address: str):
        """Record a successful login and clear any failed attempts."""
        if ip_address in self.failed_attempts:
            del self.failed_attempts[ip_address]
        if ip_address in self.lockouts:
            del self.lockouts[ip_address]
    
    def get_attempts_remaining(self, ip_address: str) -> int:
        """Get number of attempts remaining before lockout."""
        if ip_address not in self.failed_attempts:
            return self.max_attempts
        
        # Clean old attempts first
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.lockout_duration)
        self.failed_attempts[ip_address] = [
            attempt for attempt in self.failed_attempts[ip_address]
            if attempt > cutoff
        ]
        
        current_attempts = len(self.failed_attempts[ip_address])
        return max(0, self.max_attempts - current_attempts)
