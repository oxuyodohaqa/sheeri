"""
API Routes untuk Verification
"""
import asyncio
import logging
from flask import Blueprint, request, jsonify, session
from functools import wraps

from database_mysql import Database
from config import VERIFY_COST
from one.sheerid_verifier import SheerIDVerifier as OneVerifier
from k12.sheerid_verifier import SheerIDVerifier as K12Verifier
from spotify.sheerid_verifier import SheerIDVerifier as SpotifyVerifier
from youtube.sheerid_verifier import SheerIDVerifier as YouTubeVerifier
from Boltnew.sheerid_verifier import SheerIDVerifier as BoltnewVerifier

logger = logging.getLogger(__name__)

# Create blueprint
api_verify = Blueprint('api_verify', __name__, url_prefix='/api/verify')

# Database instance
db = Database()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def run_async(coro):
    """Helper to run async functions"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ==================== VERIFY 1: Gemini One Pro ====================

@api_verify.route('/gemini', methods=['POST'])
@login_required
def verify_gemini():
    """Verify Gemini One Pro (Teacher)"""
    try:
        data = request.get_json()
        url = data.get('url')
        user_id = session['user_id']
        
        if not url:
            return jsonify({'success': False, 'message': 'SheerID URL is required'}), 400
        
        if db.is_user_blocked(user_id):
            return jsonify({'success': False, 'message': 'Your account has been blocked'}), 403
        
        user = db.get_user(user_id)
        if user['balance'] < VERIFY_COST:
            return jsonify({
                'success': False,
                'message': f'Insufficient balance. You need {VERIFY_COST} points. Current balance: {user["balance"]} points'
            }), 400
        
        verification_id = OneVerifier.parse_verification_id(url)
        if not verification_id:
            return jsonify({'success': False, 'message': 'Invalid SheerID link'}), 400
        
        # Deduct balance
        if not db.deduct_balance(user_id, VERIFY_COST):
            return jsonify({'success': False, 'message': 'Failed to deduct balance'}), 500
        
        try:
            # Run verification
            verifier = OneVerifier(verification_id)
            result = verifier.verify()
            
            # Save to database
            db.add_verification(
                user_id,
                "gemini_one_pro",
                url,
                "success" if result["success"] else "failed",
                str(result),
            )
            
            if result["success"]:
                response_message = "✅ Verification successful!"
                if result.get("pending"):
                    response_message += "\n\nDocument submitted, pending manual review."
                if result.get("redirect_url"):
                    response_message += f"\n\nRedirect URL: {result['redirect_url']}"
                
                return jsonify({
                    'success': True,
                    'message': response_message,
                    'result': result
                })
            else:
                # Refund on failure
                db.add_balance(user_id, VERIFY_COST)
                return jsonify({
                    'success': False,
                    'message': f"Verification failed: {result.get('message', 'Unknown error')}",
                    'refunded': True
                }), 400
                
        except Exception as e:
            logger.error(f"Verification error: {e}")
            db.add_balance(user_id, VERIFY_COST)
            return jsonify({
                'success': False,
                'message': f'Error during verification: {str(e)}',
                'refunded': True
            }), 500
            
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== VERIFY 2: ChatGPT Teacher K12 ====================

@api_verify.route('/chatgpt', methods=['POST'])
@login_required
def verify_chatgpt():
    """Verify ChatGPT Teacher K12"""
    try:
        data = request.get_json()
        url = data.get('url')
        user_id = session['user_id']
        
        if not url:
            return jsonify({'success': False, 'message': 'SheerID URL is required'}), 400
        
        if db.is_user_blocked(user_id):
            return jsonify({'success': False, 'message': 'Your account has been blocked'}), 403
        
        user = db.get_user(user_id)
        if user['balance'] < VERIFY_COST:
            return jsonify({
                'success': False,
                'message': f'Insufficient balance. You need {VERIFY_COST} points. Current balance: {user["balance"]} points'
            }), 400
        
        verification_id = K12Verifier.parse_verification_id(url)
        if not verification_id:
            return jsonify({'success': False, 'message': 'Invalid SheerID link'}), 400
        
        if not db.deduct_balance(user_id, VERIFY_COST):
            return jsonify({'success': False, 'message': 'Failed to deduct balance'}), 500
        
        try:
            verifier = K12Verifier(verification_id)
            result = verifier.verify()
            
            db.add_verification(
                user_id,
                "chatgpt_teacher_k12",
                url,
                "success" if result["success"] else "failed",
                str(result),
            )
            
            if result["success"]:
                response_message = "✅ Verification successful!"
                if result.get("pending"):
                    response_message += "\n\nDocument submitted, pending manual review."
                if result.get("redirect_url"):
                    response_message += f"\n\nRedirect URL: {result['redirect_url']}"
                
                return jsonify({
                    'success': True,
                    'message': response_message,
                    'result': result
                })
            else:
                db.add_balance(user_id, VERIFY_COST)
                return jsonify({
                    'success': False,
                    'message': f"Verification failed: {result.get('message', 'Unknown error')}",
                    'refunded': True
                }), 400
                
        except Exception as e:
            logger.error(f"Verification error: {e}")
            db.add_balance(user_id, VERIFY_COST)
            return jsonify({
                'success': False,
                'message': f'Error during verification: {str(e)}',
                'refunded': True
            }), 500
            
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== VERIFY 3: Spotify Student ====================

@api_verify.route('/spotify', methods=['POST'])
@login_required
def verify_spotify():
    """Verify Spotify Student"""
    try:
        data = request.get_json()
        url = data.get('url')
        user_id = session['user_id']
        
        if not url:
            return jsonify({'success': False, 'message': 'SheerID URL is required'}), 400
        
        if db.is_user_blocked(user_id):
            return jsonify({'success': False, 'message': 'Your account has been blocked'}), 403
        
        user = db.get_user(user_id)
        if user['balance'] < VERIFY_COST:
            return jsonify({
                'success': False,
                'message': f'Insufficient balance. You need {VERIFY_COST} points. Current balance: {user["balance"]} points'
            }), 400
        
        verification_id = SpotifyVerifier.parse_verification_id(url)
        if not verification_id:
            return jsonify({'success': False, 'message': 'Invalid SheerID link'}), 400
        
        if not db.deduct_balance(user_id, VERIFY_COST):
            return jsonify({'success': False, 'message': 'Failed to deduct balance'}), 500
        
        try:
            verifier = SpotifyVerifier(verification_id)
            result = verifier.verify()
            
            db.add_verification(
                user_id,
                "spotify_student",
                url,
                "success" if result["success"] else "failed",
                str(result),
            )
            
            if result["success"]:
                response_message = "✅ Verification successful!"
                if result.get("pending"):
                    response_message += "\n\nDocument submitted, pending manual review."
                if result.get("redirect_url"):
                    response_message += f"\n\nRedirect URL: {result['redirect_url']}"
                
                return jsonify({
                    'success': True,
                    'message': response_message,
                    'result': result
                })
            else:
                db.add_balance(user_id, VERIFY_COST)
                return jsonify({
                    'success': False,
                    'message': f"Verification failed: {result.get('message', 'Unknown error')}",
                    'refunded': True
                }), 400
                
        except Exception as e:
            logger.error(f"Verification error: {e}")
            db.add_balance(user_id, VERIFY_COST)
            return jsonify({
                'success': False,
                'message': f'Error during verification: {str(e)}',
                'refunded': True
            }), 500
            
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== VERIFY 4: Bolt.new Teacher ====================

@api_verify.route('/boltnew', methods=['POST'])
@login_required
def verify_boltnew():
    """Verify Bolt.new Teacher"""
    try:
        data = request.get_json()
        url = data.get('url')
        user_id = session['user_id']
        
        if not url:
            return jsonify({'success': False, 'message': 'SheerID URL is required'}), 400
        
        if db.is_user_blocked(user_id):
            return jsonify({'success': False, 'message': 'Your account has been blocked'}), 403
        
        user = db.get_user(user_id)
        if user['balance'] < VERIFY_COST:
            return jsonify({
                'success': False,
                'message': f'Insufficient balance. You need {VERIFY_COST} points. Current balance: {user["balance"]} points'
            }), 400
        
        verification_id = BoltnewVerifier.parse_verification_id(url)
        if not verification_id:
            return jsonify({'success': False, 'message': 'Invalid SheerID link'}), 400
        
        if not db.deduct_balance(user_id, VERIFY_COST):
            return jsonify({'success': False, 'message': 'Failed to deduct balance'}), 500
        
        try:
            verifier = BoltnewVerifier(verification_id)
            result = verifier.verify()
            
            db.add_verification(
                user_id,
                "boltnew_teacher",
                url,
                "success" if result["success"] else "failed",
                str(result),
            )
            
            if result["success"]:
                response_message = "✅ Verification successful!"
                if result.get("pending"):
                    response_message += "\n\nDocument submitted, pending manual review."
                if result.get("redirect_url"):
                    response_message += f"\n\nRedirect URL: {result['redirect_url']}"
                if result.get("verification_code"):
                    response_message += f"\n\nVerification Code: {result['verification_code']}"
                
                return jsonify({
                    'success': True,
                    'message': response_message,
                    'result': result
                })
            else:
                db.add_balance(user_id, VERIFY_COST)
                return jsonify({
                    'success': False,
                    'message': f"Verification failed: {result.get('message', 'Unknown error')}",
                    'refunded': True
                }), 400
                
        except Exception as e:
            logger.error(f"Verification error: {e}")
            db.add_balance(user_id, VERIFY_COST)
            return jsonify({
                'success': False,
                'message': f'Error during verification: {str(e)}',
                'refunded': True
            }), 500
            
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== VERIFY 5: YouTube Premium Student ====================

@api_verify.route('/youtube', methods=['POST'])
@login_required
def verify_youtube():
    """Verify YouTube Premium Student"""
    try:
        data = request.get_json()
        url = data.get('url')
        user_id = session['user_id']
        
        if not url:
            return jsonify({'success': False, 'message': 'SheerID URL is required'}), 400
        
        if db.is_user_blocked(user_id):
            return jsonify({'success': False, 'message': 'Your account has been blocked'}), 403
        
        user = db.get_user(user_id)
        if user['balance'] < VERIFY_COST:
            return jsonify({
                'success': False,
                'message': f'Insufficient balance. You need {VERIFY_COST} points. Current balance: {user["balance"]} points'
            }), 400
        
        verification_id = YouTubeVerifier.parse_verification_id(url)
        if not verification_id:
            return jsonify({'success': False, 'message': 'Invalid SheerID link'}), 400
        
        if not db.deduct_balance(user_id, VERIFY_COST):
            return jsonify({'success': False, 'message': 'Failed to deduct balance'}), 500
        
        try:
            verifier = YouTubeVerifier(verification_id)
            result = verifier.verify()
            
            db.add_verification(
                user_id,
                "youtube_student",
                url,
                "success" if result["success"] else "failed",
                str(result),
            )
            
            if result["success"]:
                response_message = "✅ Verification successful!"
                if result.get("pending"):
                    response_message += "\n\nDocument submitted, pending manual review."
                if result.get("redirect_url"):
                    response_message += f"\n\nRedirect URL: {result['redirect_url']}"
                
                return jsonify({
                    'success': True,
                    'message': response_message,
                    'result': result
                })
            else:
                db.add_balance(user_id, VERIFY_COST)
                return jsonify({
                    'success': False,
                    'message': f"Verification failed: {result.get('message', 'Unknown error')}",
                    'refunded': True
                }), 400
                
        except Exception as e:
            logger.error(f"Verification error: {e}")
            db.add_balance(user_id, VERIFY_COST)
            return jsonify({
                'success': False,
                'message': f'Error during verification: {str(e)}',
                'refunded': True
            }), 500
            
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== GET BOLT.NEW CODE ====================

@api_verify.route('/boltnew/code', methods=['POST'])
@login_required
def get_boltnew_code():
    """Get Bolt.new verification code"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'success': False, 'message': 'SheerID URL is required'}), 400
        
        verification_id = BoltnewVerifier.parse_verification_id(url)
        if not verification_id:
            return jsonify({'success': False, 'message': 'Invalid SheerID link'}), 400
        
        # This endpoint doesn't cost points, just retrieves the code
        verifier = BoltnewVerifier(verification_id)
        code = verifier.get_verification_code()
        
        if code:
            return jsonify({
                'success': True,
                'code': code,
                'message': f'Verification code: {code}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to retrieve verification code'
            }), 400
            
    except Exception as e:
        logger.error(f"Get code error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
