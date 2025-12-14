"""
SheerID Auto-Verification Web Application
Modern web app untuk verifikasi SheerID student/teacher
"""
import os
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from functools import wraps
from datetime import datetime, timedelta

from database_web import WebAppDatabase as Database
from config import SECRET_KEY, VERIFY_COST, CHECKIN_REWARD, INVITE_REWARD, REGISTER_REWARD, DEFAULT_ADMIN_EMAIL

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['HELP_URL'] = os.getenv('HELP_URL', 'https://whatsapp.com/channel/0029VakVntuKgsNz5QgqU30C')
CORS(app)

# Initialize database
db = Database()

# Import and register blueprints
from api_verify import api_verify
from api_admin import api_admin

app.register_blueprint(api_verify)
app.register_blueprint(api_admin)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Check if it's an API call
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            # Redirect to login for page requests
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Check if it's an API call
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            # Redirect to login for page requests
            return redirect(url_for('login_page'))
        
        user = db.get_user(session['user_id'])
        if not user or not user.get('is_admin'):
            # Check if it's an API call
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Admin access required'}), 403
            # Show access denied page
            return render_template('error.html', 
                                 error_code=403,
                                 error_title='Access Denied',
                                 error_message='You need admin privileges to access this page.'), 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== FRONTEND ROUTES ====================

@app.route('/')
def index():
    """Homepage"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    user = db.get_user(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/verify')
@login_required
def verify_page():
    """Verification page"""
    user = db.get_user(session['user_id'])
    return render_template('verify.html', user=user)

@app.route('/admin')
@admin_required
def admin_panel():
    """Admin panel"""
    return render_template('admin.html')

@app.route('/login')
def login_page():
    """Login page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register_page():
    """Register page"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/how-to-use')
def how_to_use():
    """How to use guide"""
    return render_template('how_to_use.html')

# ==================== API ROUTES - AUTH ====================

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """Register new user"""
    try:
        data = request.get_json()
        email = data.get('email')
        username = data.get('username')
        password = data.get('password')
        full_name = data.get('full_name', '')
        invite_code = data.get('invite_code')
        
        if not all([email, username, password]):
            return jsonify({'success': False, 'message': 'Email, username, and password are required'}), 400
        
        # Check if user exists
        if db.get_user_by_email(email):
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        if db.get_user_by_username(username):
            return jsonify({'success': False, 'message': 'Username already taken'}), 400
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        # Handle invite code
        invited_by = None
        if invite_code:
            inviter = db.get_user_by_invite_code(invite_code)
            if inviter:
                invited_by = inviter['id']
        
        # Create user
        user_id = db.create_web_user(email, username, password_hash, full_name, invited_by)
        
        if user_id:
            # Set admin role if email matches DEFAULT_ADMIN_EMAIL
            if email == DEFAULT_ADMIN_EMAIL:
                db.set_admin_role(user_id, True)
            
            session['user_id'] = user_id
            session.permanent = True
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': {
                    'id': user_id,
                    'username': username,
                    'email': email,
                    'full_name': full_name
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Registration failed'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """User login"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password required'}), 400
        
        user = db.get_user_by_email(email)
        
        if not user:
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        
        # Check if user is blocked
        if user.get('is_blocked', 0) == 1:
            return jsonify({'success': False, 'message': 'Your account has been blocked'}), 403
        
        if not check_password_hash(user.get('password_hash', ''), password):
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        
        session['user_id'] = user.get('user_id')
        session.permanent = True
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user.get('user_id'),
                'username': user.get('username', ''),
                'email': user.get('email', ''),
                'full_name': user.get('full_name', ''),
                'balance': user.get('balance', 0),
                'is_admin': user.get('is_admin', 0)
            }
        })
        
    except Exception as e:
        import traceback
        print(f"Login error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """User logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/auth/me', methods=['GET'])
@login_required
def api_get_current_user():
    """Get current user info"""
    user = db.get_user(session['user_id'])
    if user:
        return jsonify({
            'success': True,
            'user': {
                'id': user['user_id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user.get('full_name', ''),
                'balance': user['balance'],
                'is_admin': user.get('is_admin', 0),
                'invite_code': user.get('invite_code', ''),
                'created_at': user.get('created_at', '')
            }
        })
    return jsonify({'success': False, 'message': 'User not found'}), 404

# ==================== API ROUTES - USER ====================

@app.route('/api/user/balance', methods=['GET'])
@login_required
def api_get_balance():
    """Get user balance"""
    user = db.get_user(session['user_id'])
    return jsonify({
        'success': True,
        'balance': user['balance']
    })

@app.route('/api/user/checkin', methods=['POST'])
@login_required
def api_checkin():
    """Daily check-in"""
    user_id = session['user_id']
    
    if db.is_user_blocked(user_id):
        return jsonify({'success': False, 'message': 'Your account has been blocked'}), 403
    
    result = db.checkin(user_id)
    
    if result['success']:
        return jsonify({
            'success': True,
            'message': f'Check-in successful! Earned {CHECKIN_REWARD} points',
            'points_earned': CHECKIN_REWARD,
            'new_balance': result['new_balance']
        })
    else:
        return jsonify({
            'success': False,
            'message': result.get('message', 'Already checked in today')
        }), 400

@app.route('/api/user/redeem', methods=['POST'])
@login_required
def api_redeem_code():
    """Redeem code"""
    try:
        data = request.get_json()
        code = data.get('code')
        
        if not code:
            return jsonify({'success': False, 'message': 'Code is required'}), 400
        
        user_id = session['user_id']
        
        if db.is_user_blocked(user_id):
            return jsonify({'success': False, 'message': 'Your account has been blocked'}), 403
        
        result = db.use_redemption_code(user_id, code)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': f'Code redeemed successfully! Earned {result["points"]} points',
                'points_earned': result['points'],
                'new_balance': result['new_balance']
            })
        else:
            return jsonify({
                'success': False,
                'message': result.get('message', 'Invalid or already used code')
            }), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== HEALTH & STATUS ====================

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.get_connection().close()
        return jsonify({
            'success': True,
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/status')
def api_status():
    """API status and available routes"""
    routes = {
        'auth': [
            '/api/auth/register (POST)',
            '/api/auth/login (POST)',
            '/api/auth/logout (POST)',
            '/api/auth/me (GET)',
        ],
        'user': [
            '/api/user/balance (GET)',
            '/api/user/checkin (POST)',
            '/api/user/redeem (POST)',
        ],
        'verify': [
            '/api/verify/gemini (POST)',
            '/api/verify/chatgpt (POST)',
            '/api/verify/spotify (POST)',
            '/api/verify/boltnew (POST)',
            '/api/verify/youtube (POST)',
            '/api/verify/boltnew/code (POST)',
        ],
        'admin': [
            '/api/admin/users (GET)',
            '/api/admin/users/:id (GET)',
            '/api/admin/users/:id/balance (POST)',
            '/api/admin/users/:id/block (POST)',
            '/api/admin/users/:id/unblock (POST)',
            '/api/admin/codes (GET)',
            '/api/admin/codes/generate (POST)',
            '/api/admin/codes/:id (DELETE)',
            '/api/admin/stats (GET)',
            '/api/admin/verifications (GET)',
            '/api/admin/broadcast (POST)',
            '/api/admin/blacklist (GET)',
        ]
    }
    return jsonify({
        'success': True,
        'status': 'online',
        'version': '1.0.0',
        'routes': routes,
        'timestamp': datetime.now().isoformat()
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
