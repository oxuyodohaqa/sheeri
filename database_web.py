"""
Database helper methods untuk Web App
Extensions untuk database_mysql.py
"""
import secrets
import string
from datetime import datetime
from typing import Optional, Dict, List

# Import Database class yang sudah ada
try:
    from database_mysql import MySQLDatabase as Database
except:
    from database_mysql import Database


class WebAppDatabase(Database):
    """Extended database class untuk web app"""
    
    def __init__(self):
        super().__init__()
        self._init_web_tables()
    
    def _init_web_tables(self):
        """Initialize additional web app tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Add email and password columns to users table if not exist
            # Try adding each column individually to handle existing columns gracefully
            for column_def in [
                "ADD COLUMN email VARCHAR(255) UNIQUE",
                "ADD COLUMN password_hash VARCHAR(255)",
                "ADD COLUMN is_admin TINYINT(1) DEFAULT 0",
                "ADD COLUMN invite_code VARCHAR(20) UNIQUE"
            ]:
                try:
                    cursor.execute(f"ALTER TABLE users {column_def}")
                except Exception:
                    pass  # Column already exists
            
            # Add index
            try:
                cursor.execute("ALTER TABLE users ADD INDEX idx_email (email)")
            except Exception:
                pass  # Index already exists
            
            # Sessions table for web auth
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id VARCHAR(255) PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    data TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    expires_at DATETIME,
                    INDEX idx_user_id (user_id),
                    INDEX idx_expires (expires_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            # Broadcasts table for admin announcements
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255),
                    message TEXT NOT NULL,
                    created_by BIGINT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_created_by (created_by)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            
            conn.commit()
        except Exception as e:
            print(f"Error initializing web tables: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def generate_invite_code(self) -> str:
        """Generate unique invite code"""
        while True:
            code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if not self.get_user_by_invite_code(code):
                return code
    
    def create_web_user(self, email: str, username: str, password_hash: str, 
                       full_name: str = '', invited_by: Optional[int] = None) -> Optional[int]:
        """Create new web user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            invite_code = self.generate_invite_code()
            
            # Generate unique user_id (for web, we use auto-increment)
            cursor.execute("""
                SELECT MAX(user_id) as max_id FROM users
            """)
            result = cursor.fetchone()
            user_id = (result[0] if result[0] else 1000000) + 1
            
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, email, password_hash, 
                                 invited_by, invite_code, balance, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (user_id, username, full_name, email, password_hash, invited_by, 
                  invite_code, REGISTER_REWARD))
            
            # Reward inviter
            if invited_by:
                cursor.execute(
                    "UPDATE users SET balance = balance + %s WHERE user_id = %s",
                    (INVITE_REWARD, invited_by)
                )
                
                cursor.execute("""
                    INSERT INTO invitations (inviter_id, invitee_id, created_at)
                    VALUES (%s, %s, NOW())
                """, (invited_by, user_id))
            
            conn.commit()
            return user_id
            
        except Exception as e:
            print(f"Create web user failed: {e}")
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM users WHERE email = %s
            """, (email,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            print(f"Get user by email failed: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM users WHERE username = %s
            """, (username,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            print(f"Get user by username failed: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_user_by_invite_code(self, invite_code: str) -> Optional[Dict]:
        """Get user by invite code"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM users WHERE invite_code = %s
            """, (invite_code,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None
            
        except Exception as e:
            print(f"Get user by invite code failed: {e}")
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_all_users(self, page: int = 1, per_page: int = 50, search: str = '') -> List[Dict]:
        """Get all users with pagination"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            offset = (page - 1) * per_page
            
            if search:
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE username LIKE %s OR email LIKE %s OR full_name LIKE %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (f'%{search}%', f'%{search}%', f'%{search}%', per_page, offset))
            else:
                cursor.execute("""
                    SELECT * FROM users 
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                """, (per_page, offset))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            print(f"Get all users failed: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_users_count(self, search: str = '') -> int:
        """Get total users count"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            if search:
                cursor.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE username LIKE %s OR email LIKE %s OR full_name LIKE %s
                """, (f'%{search}%', f'%{search}%', f'%{search}%'))
            else:
                cursor.execute("SELECT COUNT(*) FROM users")
            
            return cursor.fetchone()[0]
            
        except Exception as e:
            print(f"Get users count failed: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()
    
    def get_system_stats(self) -> Dict:
        """Get system statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Total users
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # Total verifications
            cursor.execute("SELECT COUNT(*) FROM verifications")
            total_verifications = cursor.fetchone()[0]
            
            # Successful verifications
            cursor.execute("SELECT COUNT(*) FROM verifications WHERE status = 'success'")
            successful_verifications = cursor.fetchone()[0]
            
            # Total redemption codes
            cursor.execute("SELECT COUNT(*) FROM card_keys")
            total_codes = cursor.fetchone()[0]
            
            # Active codes
            cursor.execute("""
                SELECT COUNT(*) FROM card_keys 
                WHERE current_uses < max_uses 
                AND (expire_at IS NULL OR expire_at > NOW())
            """)
            active_codes = cursor.fetchone()[0]
            
            return {
                'total_users': total_users,
                'total_verifications': total_verifications,
                'successful_verifications': successful_verifications,
                'total_codes': total_codes,
                'active_codes': active_codes
            }
            
        except Exception as e:
            print(f"Get stats failed: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()
    
    def create_broadcast(self, title: str, message: str, created_by: int) -> Optional[int]:
        """Create broadcast message"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO broadcasts (title, message, created_by, created_at)
                VALUES (%s, %s, %s, NOW())
            """, (title, message, created_by))
            
            conn.commit()
            return cursor.lastrowid
            
        except Exception as e:
            print(f"Create broadcast failed: {e}")
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()
    
    def get_blacklisted_users(self) -> List[Dict]:
        """Get all blacklisted users"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT user_id, username, email, full_name, created_at 
                FROM users 
                WHERE is_blocked = 1
                ORDER BY username
            """)
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            print(f"Get blacklisted users failed: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def set_admin_role(self, user_id: int, is_admin: bool) -> bool:
        """Set admin role for user"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE users SET is_admin = %s WHERE user_id = %s
            """, (1 if is_admin else 0, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"Set admin role failed: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def get_all_verifications(self, page: int = 1, per_page: int = 50, 
                             status: str = '', service: str = '') -> List[Dict]:
        """Get all verifications with filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            offset = (page - 1) * per_page
            query = "SELECT v.*, u.username, u.email FROM verifications v JOIN users u ON v.user_id = u.user_id WHERE 1=1"
            params = []
            
            if status:
                query += " AND v.status = %s"
                params.append(status)
            
            if service:
                query += " AND v.verification_type = %s"
                params.append(service)
            
            query += " ORDER BY v.created_at DESC LIMIT %s OFFSET %s"
            params.extend([per_page, offset])
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            print(f"Get all verifications failed: {e}")
            return []
        finally:
            cursor.close()
            conn.close()
    
    def get_verifications_count(self, status: str = '', service: str = '') -> int:
        """Get verifications count with filters"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            query = "SELECT COUNT(*) FROM verifications WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = %s"
                params.append(status)
            
            if service:
                query += " AND verification_type = %s"
                params.append(service)
            
            cursor.execute(query, params)
            return cursor.fetchone()[0]
            
        except Exception as e:
            print(f"Get verifications count failed: {e}")
            return 0
        finally:
            cursor.close()
            conn.close()

    def update_balance(self, user_id: int, new_balance: int) -> bool:
        """Update user balance directly"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE users SET balance = %s WHERE user_id = %s
            """, (new_balance, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"Update balance failed: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

# Import config values
try:
    from config import REGISTER_REWARD, INVITE_REWARD
except:
    REGISTER_REWARD = 1
    INVITE_REWARD = 2
