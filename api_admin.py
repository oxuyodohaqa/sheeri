"""
API Routes untuk Admin
"""
import logging
from flask import Blueprint, request, jsonify, session
from functools import wraps

from database_web import WebAppDatabase as Database

logger = logging.getLogger(__name__)

# Create blueprint
api_admin = Blueprint('api_admin', __name__, url_prefix='/api/admin')

# Database instance
db = Database()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        user = db.get_user(session['user_id'])
        if not user or not user.get('is_admin'):
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== USER MANAGEMENT ====================

@api_admin.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Get all users"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        search = request.args.get('search', '')
        
        users = db.get_all_users(page, per_page, search)
        total = db.get_users_count(search)
        
        return jsonify({
            'success': True,
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        logger.error(f"Get users error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_admin.route('/users', methods=['POST'])
@admin_required
def create_user():
    """Create new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not all(k in data for k in ['email', 'username', 'password']):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Check if user already exists
        if db.get_user_by_email(data['email']):
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        if db.get_user_by_username(data['username']):
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        # Hash password
        from werkzeug.security import generate_password_hash
        password_hash = generate_password_hash(data['password'])
        
        # Create user
        user_id = db.create_web_user(
            email=data['email'],
            username=data['username'],
            password_hash=password_hash,
            full_name=data.get('full_name', ''),
            invited_by=None
        )
        
        if user_id:
            # Set additional properties if provided
            if data.get('is_admin'):
                db.set_admin_role(user_id, True)
            
            if data.get('balance'):
                db.update_balance(user_id, int(data['balance']))
            
            return jsonify({
                'success': True,
                'message': 'User created successfully',
                'user_id': user_id
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to create user'}), 500
            
    except Exception as e:
        logger.error(f"Create user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_admin.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_details(user_id):
    """Get user details"""
    try:
        user = db.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Remove sensitive data
        user.pop('password_hash', None)
        
        return jsonify({
            'success': True,
            'user': user
        })
    except Exception as e:
        logger.error(f"Get user details error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_admin.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user details"""
    try:
        user = db.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update user fields
        conn = db.get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if 'email' in data:
            updates.append("email = %s")
            params.append(data['email'])
        
        if 'username' in data:
            updates.append("username = %s")
            params.append(data['username'])
        
        if 'full_name' in data:
            updates.append("full_name = %s")
            params.append(data['full_name'])
        
        if 'balance' in data:
            updates.append("balance = %s")
            params.append(int(data['balance']))
        
        if 'is_admin' in data:
            updates.append("is_admin = %s")
            params.append(1 if data['is_admin'] else 0)
        
        if 'is_blocked' in data:
            updates.append("is_blocked = %s")
            params.append(1 if data['is_blocked'] else 0)
        
        if not updates:
            return jsonify({'success': False, 'message': 'No fields to update'}), 400
        
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s"
        
        cursor.execute(query, tuple(params))
        conn.commit()
        cursor.close()
        conn.close()
        
        updated_user = db.get_user(user_id)
        updated_user.pop('password_hash', None)
        
        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': updated_user
        })
        
    except Exception as e:
        logger.error(f"Update user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_admin.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Delete user"""
    try:
        # Check if user exists
        user = db.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        # Prevent deleting yourself
        if user_id == session.get('user_id'):
            return jsonify({'success': False, 'message': 'You cannot delete your own account'}), 400
        
        # Delete user
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_admin.route('/users/<int:user_id>/balance', methods=['POST'])
@admin_required
def modify_user_balance(user_id):
    """Add or deduct user balance"""
    try:
        data = request.get_json()
        amount = data.get('amount', 0)
        reason = data.get('reason', '')
        
        if amount == 0:
            return jsonify({'success': False, 'message': 'Amount cannot be zero'}), 400
        
        user = db.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        if amount > 0:
            db.add_balance(user_id, amount)
            action = 'added'
        else:
            db.deduct_balance(user_id, abs(amount))
            action = 'deducted'
        
        updated_user = db.get_user(user_id)
        
        return jsonify({
            'success': True,
            'message': f'{abs(amount)} points {action}',
            'new_balance': updated_user['balance']
        })
    except Exception as e:
        logger.error(f"Modify balance error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_admin.route('/users/<int:user_id>/block', methods=['POST'])
@admin_required
def block_user(user_id):
    """Block user"""
    try:
        user = db.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        db.block_user(user_id)
        
        return jsonify({
            'success': True,
            'message': f'User {user["username"]} has been blocked'
        })
    except Exception as e:
        logger.error(f"Block user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_admin.route('/users/<int:user_id>/unblock', methods=['POST'])
@admin_required
def unblock_user(user_id):
    """Unblock user"""
    try:
        user = db.get_user(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        db.unblock_user(user_id)
        
        return jsonify({
            'success': True,
            'message': f'User {user["username"]} has been unblocked'
        })
    except Exception as e:
        logger.error(f"Unblock user error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== REDEMPTION CODES ====================

@api_admin.route('/codes', methods=['GET'])
@admin_required
def get_codes():
    """Get all redemption codes"""
    try:
        codes = db.get_all_redemption_codes()
        return jsonify({
            'success': True,
            'codes': codes
        })
    except Exception as e:
        logger.error(f"Get codes error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_admin.route('/codes/generate', methods=['POST'])
@admin_required
def generate_code():
    """Generate new redemption code"""
    try:
        data = request.get_json()
        points = data.get('points', 10)
        max_uses = data.get('max_uses', 1)
        description = data.get('description', '')
        
        if points <= 0:
            return jsonify({'success': False, 'message': 'Points must be greater than 0'}), 400
        
        if max_uses <= 0:
            return jsonify({'success': False, 'message': 'Max uses must be greater than 0'}), 400
        
        code = db.generate_redemption_code(points, max_uses, description)
        
        if code:
            return jsonify({
                'success': True,
                'message': 'Code generated successfully',
                'code': code
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to generate code'}), 500
            
    except Exception as e:
        logger.error(f"Generate code error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_admin.route('/codes/<code_id>', methods=['DELETE'])
@admin_required
def delete_code(code_id):
    """Delete redemption code"""
    try:
        db.delete_redemption_code(code_id)
        return jsonify({
            'success': True,
            'message': 'Code deleted successfully'
        })
    except Exception as e:
        logger.error(f"Delete code error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== STATISTICS ====================

@api_admin.route('/stats', methods=['GET'])
@admin_required
def get_stats():
    """Get system statistics"""
    try:
        stats = db.get_system_stats()
        
        # Calculate success rate
        success_rate = 0
        if stats.get('total_verifications', 0) > 0:
            success_rate = round((stats.get('successful_verifications', 0) / stats['total_verifications']) * 100, 1)
        
        # Get recent verifications
        recent_verifications = db.get_all_verifications(page=1, per_page=10, status='', service='')
        
        # Add user emails to verifications
        for v in recent_verifications:
            user = db.get_user(v['user_id'])
            v['user_email'] = user['email'] if user else 'Unknown'
        
        return jsonify({
            'success': True,
            'total_users': stats.get('total_users', 0),
            'total_verifications': stats.get('total_verifications', 0),
            'total_points': stats.get('total_users', 0),  # Points distributed = users * initial bonus
            'success_rate': success_rate,
            'recent_verifications': recent_verifications
        })
    except Exception as e:
        logger.error(f"Get stats error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== VERIFICATIONS ====================

@api_admin.route('/verifications', methods=['GET'])
@admin_required
def get_all_verifications():
    """Get all verifications"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))
        status = request.args.get('status', '')
        service = request.args.get('service', '')
        
        verifications = db.get_all_verifications(page, per_page, status, service)
        total = db.get_verifications_count(status, service)
        
        return jsonify({
            'success': True,
            'verifications': verifications,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })
    except Exception as e:
        logger.error(f"Get verifications error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== BROADCAST ====================

@api_admin.route('/broadcast', methods=['POST'])
@admin_required
def broadcast_message():
    """Broadcast message to all users (via email or notification)"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        title = data.get('title', '')
        
        if not message:
            return jsonify({'success': False, 'message': 'Message is required'}), 400
        
        # Save broadcast to database
        broadcast_id = db.create_broadcast(title, message, session['user_id'])
        
        # In a real app, you would send emails or push notifications here
        # For now, we just save to database
        
        return jsonify({
            'success': True,
            'message': 'Broadcast saved successfully',
            'broadcast_id': broadcast_id
        })
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_admin.route('/blacklist', methods=['GET'])
@admin_required
def get_blacklist():
    """Get blacklisted users"""
    try:
        blacklisted = db.get_blacklisted_users()
        return jsonify({
            'success': True,
            'blacklisted_users': blacklisted
        })
    except Exception as e:
        logger.error(f"Get blacklist error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
