"""
Security Manager for IoT Box

Handles authentication, authorization, encryption, and security policies.
"""

import hashlib
import hmac
import jwt
import secrets
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from ..utils.logger import get_logger

logger = get_logger(__name__)


class SecurityLevel(Enum):
    """Security level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AccessLevel(Enum):
    """Access level enumeration"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SUPERUSER = "superuser"


@dataclass
class SecurityPolicy:
    """Security policy configuration"""
    max_login_attempts: int = 5
    lockout_duration: int = 300  # 5 minutes
    password_min_length: int = 8
    password_require_special: bool = True
    session_timeout: int = 3600  # 1 hour
    encryption_enabled: bool = True
    audit_logging: bool = True
    ip_whitelist: List[str] = None
    device_authentication: bool = True


@dataclass
class User:
    """User information"""
    id: str
    username: str
    password_hash: str
    access_level: AccessLevel
    is_active: bool = True
    last_login: Optional[float] = None
    failed_attempts: int = 0
    locked_until: Optional[float] = None


@dataclass
class DeviceAuth:
    """Device authentication information"""
    device_id: str
    device_key: str
    is_authorized: bool = True
    last_seen: Optional[float] = None
    security_level: SecurityLevel = SecurityLevel.MEDIUM


class SecurityManager:
    """Manages security, authentication, and authorization"""
    
    def __init__(self, 
                 secret_key: str,
                 encryption_key: Optional[str] = None,
                 policy: Optional[SecurityPolicy] = None):
        self.secret_key = secret_key.encode()
        self.encryption_key = self._derive_encryption_key(encryption_key)
        self.policy = policy or SecurityPolicy()
        
        self.users: Dict[str, User] = {}
        self.device_auth: Dict[str, DeviceAuth] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, List[float]] = {}
        
        self._initialize_default_users()
    
    def _derive_encryption_key(self, key: Optional[str]) -> bytes:
        """Derive encryption key from password"""
        if key:
            password = key.encode()
        else:
            password = self.secret_key
        
        salt = b'iot_box_salt'  # In production, use random salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password))
    
    def _initialize_default_users(self):
        """Initialize default users"""
        # Create default admin user
        admin_user = User(
            id="admin",
            username="admin",
            password_hash=self._hash_password("admin123"),
            access_level=AccessLevel.SUPERUSER
        )
        self.users["admin"] = admin_user
        
        # Create operator user
        operator_user = User(
            id="operator",
            username="operator",
            password_hash=self._hash_password("operator123"),
            access_level=AccessLevel.WRITE
        )
        self.users["operator"] = operator_user
        
        logger.info("Initialized default users")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using PBKDF2"""
        salt = secrets.token_hex(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return f"{salt}:{key.decode()}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, stored_key = password_hash.split(':')
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt.encode(),
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            return hmac.compare_digest(key, stored_key.encode())
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str, 
                         ip_address: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Authenticate user"""
        try:
            # Check if user exists
            if username not in self.users:
                logger.warning(f"Authentication failed: user {username} not found")
                return False, "Invalid credentials"
            
            user = self.users[username]
            
            # Check if user is active
            if not user.is_active:
                logger.warning(f"Authentication failed: user {username} is inactive")
                return False, "Account is inactive"
            
            # Check if user is locked
            if user.locked_until and time.time() < user.locked_until:
                logger.warning(f"Authentication failed: user {username} is locked")
                return False, "Account is temporarily locked"
            
            # Check IP whitelist
            if (self.policy.ip_whitelist and 
                ip_address and 
                ip_address not in self.policy.ip_whitelist):
                logger.warning(f"Authentication failed: IP {ip_address} not whitelisted")
                return False, "IP address not authorized"
            
            # Verify password
            if not self._verify_password(password, user.password_hash):
                # Increment failed attempts
                user.failed_attempts += 1
                
                # Lock account if max attempts reached
                if user.failed_attempts >= self.policy.max_login_attempts:
                    user.locked_until = time.time() + self.policy.lockout_duration
                    logger.warning(f"User {username} locked due to too many failed attempts")
                
                # Log failed attempt
                if ip_address:
                    if ip_address not in self.failed_attempts:
                        self.failed_attempts[ip_address] = []
                    self.failed_attempts[ip_address].append(time.time())
                
                logger.warning(f"Authentication failed: invalid password for user {username}")
                return False, "Invalid credentials"
            
            # Reset failed attempts on successful login
            user.failed_attempts = 0
            user.locked_until = None
            user.last_login = time.time()
            
            logger.info(f"User {username} authenticated successfully")
            return True, None
            
        except Exception as e:
            logger.error(f"Error during authentication: {e}")
            return False, "Authentication error"
    
    def create_session(self, username: str, ip_address: Optional[str] = None) -> str:
        """Create user session"""
        try:
            user = self.users[username]
            session_id = secrets.token_urlsafe(32)
            
            session_data = {
                "username": username,
                "user_id": user.id,
                "access_level": user.access_level.value,
                "created_at": time.time(),
                "last_activity": time.time(),
                "ip_address": ip_address
            }
            
            self.active_sessions[session_id] = session_data
            
            logger.info(f"Created session for user {username}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    def validate_session(self, session_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate user session"""
        try:
            if session_id not in self.active_sessions:
                return False, None
            
            session = self.active_sessions[session_id]
            
            # Check session timeout
            if (time.time() - session["last_activity"] > 
                self.policy.session_timeout):
                del self.active_sessions[session_id]
                logger.info(f"Session {session_id} expired")
                return False, None
            
            # Update last activity
            session["last_activity"] = time.time()
            
            return True, session
            
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return False, None
    
    def revoke_session(self, session_id: str):
        """Revoke user session"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            logger.info(f"Revoked session {session_id}")
    
    def revoke_user_sessions(self, username: str):
        """Revoke all sessions for a user"""
        sessions_to_remove = [
            sid for sid, session in self.active_sessions.items()
            if session["username"] == username
        ]
        
        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
        
        logger.info(f"Revoked {len(sessions_to_remove)} sessions for user {username}")
    
    def check_permission(self, session_id: str, required_level: AccessLevel) -> bool:
        """Check if session has required permission level"""
        try:
            valid, session = self.validate_session(session_id)
            if not valid or not session:
                return False
            
            user_level = AccessLevel(session["access_level"])
            
            # Define permission hierarchy
            level_hierarchy = {
                AccessLevel.READ: 1,
                AccessLevel.WRITE: 2,
                AccessLevel.ADMIN: 3,
                AccessLevel.SUPERUSER: 4
            }
            
            return level_hierarchy[user_level] >= level_hierarchy[required_level]
            
        except Exception as e:
            logger.error(f"Error checking permission: {e}")
            return False
    
    def register_device(self, device_id: str, device_key: str, 
                       security_level: SecurityLevel = SecurityLevel.MEDIUM) -> bool:
        """Register a new device"""
        try:
            device_auth = DeviceAuth(
                device_id=device_id,
                device_key=device_key,
                security_level=security_level
            )
            
            self.device_auth[device_id] = device_auth
            logger.info(f"Registered device {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering device {device_id}: {e}")
            return False
    
    def authenticate_device(self, device_id: str, device_key: str) -> bool:
        """Authenticate device"""
        try:
            if device_id not in self.device_auth:
                logger.warning(f"Device authentication failed: {device_id} not registered")
                return False
            
            device = self.device_auth[device_id]
            
            if not device.is_authorized:
                logger.warning(f"Device authentication failed: {device_id} not authorized")
                return False
            
            if not hmac.compare_digest(device.device_key, device_key):
                logger.warning(f"Device authentication failed: invalid key for {device_id}")
                return False
            
            device.last_seen = time.time()
            logger.debug(f"Device {device_id} authenticated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating device {device_id}: {e}")
            return False
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt data"""
        if not self.policy.encryption_enabled:
            return data
        
        try:
            fernet = Fernet(self.encryption_key)
            encrypted_data = fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            return data
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt data"""
        if not self.policy.encryption_enabled:
            return encrypted_data
        
        try:
            fernet = Fernet(self.encryption_key)
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            return encrypted_data
    
    def generate_jwt_token(self, username: str, expires_in: int = 3600) -> str:
        """Generate JWT token"""
        try:
            payload = {
                "username": username,
                "exp": time.time() + expires_in,
                "iat": time.time()
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm="HS256")
            return token
            
        except Exception as e:
            logger.error(f"Error generating JWT token: {e}")
            raise
    
    def validate_jwt_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return True, payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return False, None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Error validating JWT token: {e}")
            return False, None
    
    def audit_log(self, action: str, username: Optional[str] = None, 
                  device_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Log security event for audit"""
        if not self.policy.audit_logging:
            return
        
        try:
            audit_entry = {
                "timestamp": time.time(),
                "action": action,
                "username": username,
                "device_id": device_id,
                "details": details or {}
            }
            
            # In production, store in secure audit log
            logger.info(f"AUDIT: {audit_entry}")
            
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get security status"""
        return {
            "active_sessions": len(self.active_sessions),
            "registered_devices": len(self.device_auth),
            "authorized_devices": len([d for d in self.device_auth.values() if d.is_authorized]),
            "encryption_enabled": self.policy.encryption_enabled,
            "audit_logging": self.policy.audit_logging,
            "failed_attempts": len(self.failed_attempts)
        }
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        expired_sessions = [
            sid for sid, session in self.active_sessions.items()
            if current_time - session["last_activity"] > self.policy.session_timeout
        ]
        
        for session_id in expired_sessions:
            del self.active_sessions[session_id]
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def cleanup_failed_attempts(self, older_than_hours: int = 24):
        """Clean up old failed attempt records"""
        current_time = time.time()
        cutoff_time = current_time - (older_than_hours * 3600)
        
        for ip_address in list(self.failed_attempts.keys()):
            attempts = self.failed_attempts[ip_address]
            self.failed_attempts[ip_address] = [
                attempt for attempt in attempts if attempt > cutoff_time
            ]
            
            if not self.failed_attempts[ip_address]:
                del self.failed_attempts[ip_address]
