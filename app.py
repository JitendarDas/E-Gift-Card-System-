from flask import Flask,session, render_template, request,url_for,redirect, flash
import pymysql
import random
import string
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key="Apple"

app.config['MAIL_SERVER'] = 'smtp.gmail.com'  
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'djitendar3@gmail.com'
app.config['MAIL_PASSWORD'] = 'Spider@0205'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',         
        password='Spider@0205', 
        db='egiftcards',           
        cursorclass=pymysql.cursors.DictCursor  
    )
    return connection


def check_expired_cards():
    """This function checks expired gift cards and updates their status."""
    connection = get_db_connection()
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE user_gift_cards 
            SET status = 'expired'
            WHERE expires_at < NOW() AND status != 'redeemed'
        """)
        connection.commit()
    connection.close()

# Schedule the background task to check expired cards every 24 hours
scheduler = BackgroundScheduler()
scheduler.add_job(check_expired_cards, 'interval', hours=24)  
scheduler.start()

@app.route('/')
def start():
    return redirect(url_for('signin'))
@app.route('/signup', methods= ['POST','GET'] )
def signup():
        if request.method == 'POST':
            name = request.form['name']
            password = request.form['password']
            email = request.form['email']
            signup_type = request.form.get('signup_type')
           
            connect = get_db_connection()

            if signup_type == 'user':
                with connect.cursor() as cursor:
                    cursor.execute("SELECT * FROM users WHERE email = %s",(email,))
                    existing_user=cursor.fetchone()

                if existing_user:
                    flash("Email already exixts. Please choose a different one.")
                    connect.close()
                    return render_template('signup.html')

                with connect.cursor() as cursor:
                    cursor.execute(
                        "INSERT INTO users (user_name, password,email) VALUES (%s,%s,%s)",(name,password,email) 
                    )
                    connect.commit()
                    
                flash("Signup successfully!")
                return redirect(url_for('signin'))
            
            elif signup_type == 'merchant':
                with connect.cursor() as cursor :
                    cursor.execute("SELECT * FROM merchants WHERE email=%s",(email,))
                    existing_user = cursor.fetchone()
                
                if existing_user :
                    flash("Email already exist. Please try another one.")
                    cursor.close()
                    return render_template('signup.html')

                with connect.cursor() as cursor:
                    cursor.execute("INSERT INTO merchants (merchant_name,email,password) VALUES (%s,%s,%s)",(name,email,password))
                    connect.commit()
                
                flash("Signup successfully!")
                return redirect(url_for('signin'))
            connect.close()
        return render_template('signup.html')

@app.route('/forget_password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        email = request.form['email']
        user_type = request.form.get('user_type')  
        
        
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if not user:
                cursor.execute("SELECT * FROM merchants WHERE email = %s", (email,))
                user = cursor.fetchone()

            if user:
                
                token = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                expiry_time = datetime.now() + timedelta(hours=1)

                
                cursor.execute("INSERT INTO password_reset_tokens (email, token, expiry_time) VALUES (%s, %s, %s)", 
                               (email, token, expiry_time))
                connection.commit()

                
                reset_link = url_for('reset_password', token=token, _external=True)
                msg = Message("Password Reset Request", recipients=[email])
                msg.body = f"Click the link to reset your password: {reset_link}"
                mail.send(msg)
                
                flash("Password reset link has been sent to your email.")
            else:
                flash("No account found with that email address.")
        connection.close()
        return redirect(url_for('signin'))

    return render_template('forget_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    connection = get_db_connection()
    
   
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM password_reset_tokens WHERE token = %s", (token,))
        reset_token = cursor.fetchone()

        if reset_token:
           
            if datetime.now() > reset_token['expiry_time']:
                flash("This password reset link has expired.")
                return redirect(url_for('signin'))
            
            if request.method == 'POST':
                new_password = request.form['password']
                
                
                cursor.execute("UPDATE users SET password = %s WHERE email = %s", (new_password, reset_token['email']))
                connection.commit()

                
                cursor.execute("DELETE FROM password_reset_tokens WHERE token = %s", (token,))
                connection.commit()

                flash("Your password has been reset successfully!")
                return redirect(url_for('signin'))

        else:
            flash("Invalid or expired token.")
            return redirect(url_for('signin'))
    connection.close()

    return render_template('reset_password.html', token=token)

@app.route('/signin', methods=['POST', 'GET'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        signin_type = request.form.get('signin_type')
                
        connection = get_db_connection()

        
        if signin_type == 'user':
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
                user = cursor.fetchone()

                if user:
                    
                    if user['status'] == 'suspended':
                        flash("Your account has been suspended. Please contact support.", 'danger')
                        return redirect(url_for('signin'))

                    session['id'] = user['user_id']
                    session['user_type'] = 'user'
                    flash("Login successful!")
                    return redirect(url_for('dashboard'))
                else:
                    flash("Invalid email or password. Please try again.", 'danger')
                    return redirect(url_for('signin'))

        
        elif signin_type == 'merchant':
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM merchants WHERE email = %s AND password = %s", (email, password))
                merchant = cursor.fetchone()

                if merchant:
                    
                    if merchant['status'] == 'suspended':
                        flash("Your merchant account has been suspended. Please contact support.", 'danger')
                        return redirect(url_for('signin'))

                    session['id'] = merchant['merchant_id']
                    session['user_type'] = 'merchant'
                    flash("Login successful!")
                    return redirect(url_for('dashboard'))
                else:
                    flash("Invalid email or password. Please try again.", 'danger')
                    return redirect(url_for('signin'))

        
        elif signin_type == 'admin':
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM admin WHERE email = %s AND password = %s", (email, password))
                admin = cursor.fetchone()

                if admin:
                    
                    session['id'] = admin['admin_id']
                    session['user_type'] = 'admin'
                    flash("Login successful!")
                    return redirect(url_for('dashboard'))
                else:
                    flash("Invalid email or password. Please try again.", 'danger')
                    return redirect(url_for('signin'))

        connection.close()
    
    return render_template('signin.html')

    
@app.route('/dashboard')
def dashboard():
    user_id =session.get('id')
    user_type = session.get('user_type')

    if not user_id or not user_type:
        flash("Please log in first")
        return redirect(url_for('signin'))
    
    connect = get_db_connection()

    if user_type == 'user':
        with connect.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s",(user_id))
            user_data=cursor.fetchone()
        
        connect.close()
        return render_template('dashboard.html',user_type='user',data=user_data)
    
    elif user_type == 'merchant':
        with connect.cursor() as cursor:
            cursor.execute("SELECT * FROM merchants WHERE merchant_id=%s",(user_id))
            merchant_data=cursor.fetchone()
        
        connect.close()
        return render_template('dashboard.html',user_type='merchant',data=merchant_data)
    
    elif user_type == 'admin':
        with connect.cursor() as cursor:
            cursor.execute("SELECT * FROM admin WHERE admin_id=%s",(user_id))
            admin_data = cursor.fetchone()
        connect.close()
        return render_template('dashboard.html',user_type='admin',data=admin_data)
    
@app.route('/add_gift_card', methods =['POST','GET'])
def add_gift_card():
    if request.method == 'POST':
        card_value = request.form['card_value']
        expiration_date = request.form['expiration_date']
        status =request.form['status']

        connect = get_db_connection()
        with connect.cursor() as cursor:
            cursor.execute("INSERT INTO gift_card_inventory (card_value, expires_at, status) VALUES (%s,%s,%s)",(card_value,expiration_date,status))
            connect.commit()
        connect.close()

        flash("Gift card added successfully!")
        return redirect('add_gift_card')
    return render_template('add_gift_card.html')

@app.route('/update_status', methods=['POST'])
def update_status():
    connect = get_db_connection()
    with connect.cursor() as cursor:
        cursor.execute("Select card_id from gift_card_inventory")
        cards=cursor.fetchall()
        for card in cards:
            status = request.form.get(f"status_{card['card_id']}")
            if status:
                cursor.execute(
                    "UPDATE gift_card_inventory SET status = %s WHERE card_id = %s",
                    (status, card['card_id'])
                )
        connect.commit()
    connect.close()
    
    flash('Gift card statuses updated successfully!')
    return redirect('/gift_cards')

@app.route('/gift_cards')
def giftcards():
    connect = get_db_connection()
    with connect.cursor() as cursor:
        cursor.execute("SELECT * FROM gift_card_inventory")
        cards = cursor.fetchall()
    connect.close()
    return render_template('gift_cards.html',cards=cards)

@app.route('/buy_card', methods=['POST', 'GET'])
def buy_card():
    if request.method == 'POST':
        card_id = request.form['card_id']
        user_id = session['id']
        connect = get_db_connection()
        with connect.cursor() as cursor:
            
            cursor.execute("SELECT * FROM gift_card_inventory WHERE card_id=%s AND status='available'", (card_id,))
            card = cursor.fetchone()

            if card:
                
                cursor.execute("UPDATE gift_card_inventory SET status = 'sold' WHERE card_id = %s", (card_id,))
                connect.commit()

                
                cursor.execute("INSERT INTO user_gift_cards (card_id, user_id, card_value, status) VALUES (%s, %s, %s, %s)", 
                               (card_id, user_id, card['card_value'], 'active'))
                connect.commit()

                
                cursor.execute("""
                    INSERT INTO transactions (card_id, sender_id, receiver_id, transaction_date, status)
                    VALUES (%s, %s, %s, NOW(), %s)
                """, (card_id, user_id, None, 'completed'))
                connect.commit()

                flash("Gift card purchased successfully!")
            else:
                flash("Card is not available or has already been sold.")
        connect.close()
        return redirect(url_for('buy_card'))

    
    connect = get_db_connection()
    with connect.cursor() as cursor:
        cursor.execute("SELECT * FROM gift_card_inventory WHERE status = 'available'")
        cards = cursor.fetchall()
    connect.close()

    return render_template('buy_card.html', cards=cards)


@app.route('/mycards')
def mycards():
    user_id = session['id']
    user_type = session['user_type']
    if not user_id :
        flash("Please sign in no view your gift cards")
        return redirect(url_for('signin'))
    
    connect =get_db_connection()

    with connect.cursor( ) as cursor:
        if user_type == 'user':
            cursor.execute("SELECT * FROM user_gift_cards WHERE user_id = %s",(user_id,)) 
        else:
            cursor.execute("SELECT * FROM user_gift_cards WHERE merchant_id = %s",(user_id,))
        cards = cursor.fetchall()

        card_details=[]

        for card in cards:
            cursor.execute("SELECT expires_at FROM gift_card_inventory WHERE card_id = %s", (card['card_id'],))
            ex_date = cursor.fetchone()

            card_detail = {
                'card_id': card['card_id'],
                'card_value': card['card_value'],
                'status': card['status'],
                'purchase_id': card['purchase_id'],
                'purchase_date': card['purchase_date'],
                'expires_at': ex_date['expires_at'] if ex_date else None  
            }
            card_details.append(card_detail)
    connect.close()

    return render_template('mycards.html',cards = card_details)

@app.route('/view_user',methods=['GET'])
def view_user():
    connect = get_db_connection()
    with connect.cursor() as cursor:
        cursor.execute("SELECT user_id, user_name, email, status FROM users")
        user=cursor.fetchall()
    connect.close()
    return render_template('view_user.html',users=user)


@app.route('/view_merchant',methods=['GET'])
def view_merchant():
    connect = get_db_connection()
    with connect.cursor() as cursor:
        cursor.execute("SELECT merchant_id, merchant_name, email, status FROM merchants")
        merchant=cursor.fetchall()
    connect.close()
    return render_template('view_merchant.html',merchants=merchant)
@app.route('/suspend_user/<int:user_id>', methods=['GET'])
def suspend_user(user_id):
    connect = get_db_connection()
    with connect.cursor() as cursor:
        cursor.execute("UPDATE users SET status = 'suspended' WHERE user_id = %s", (user_id,))
        connect.commit()
    connect.close()
    flash('User account has been suspended.', 'success')
    return redirect(url_for('view_users'))


@app.route('/suspend_merchant/<int:merchant_id>', methods=['GET'])
def suspend_merchant(merchant_id):
    connect = get_db_connection()
    with connect.cursor() as cursor:
        cursor.execute("UPDATE merchants SET status = 'suspended' WHERE merchant_id = %s", (merchant_id,))
        connect.commit()
    connect.close()
    flash('Merchant account has been suspended.', 'success')
    return redirect(url_for('view_merchants'))


@app.route('/delete_user/<int:user_id>', methods=['GET'])
def delete_user(user_id):
    connect = get_db_connection()
    with connect.cursor() as cursor:
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        connect.commit()
    connect.close()
    flash('User account has been deleted.', 'danger')
    return redirect(url_for('view_users'))


@app.route('/delete_merchant/<int:merchant_id>', methods=['GET'])
def delete_merchant(merchant_id):
    connect = get_db_connection()
    with connect.cursor() as cursor:
        cursor.execute("DELETE FROM merchants WHERE merchant_id = %s", (merchant_id,))
        connect.commit()
    connect.close()
    flash('Merchant account has been deleted.', 'danger')
    return redirect(url_for('view_merchants'))

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'id' in session and 'user_type' in session:
        account_id = session['id']
        user_type = session['user_type']
        
        connection = get_db_connection()
        with connection.cursor() as cursor:
            if user_type == 'user':
                
                cursor.execute("DELETE FROM users WHERE user_id = %s", (account_id,))
            elif user_type == 'merchant':
                
                cursor.execute("DELETE FROM merchants WHERE merchant_id = %s", (account_id,))
            connection.commit()
        connection.close()
        
        
        session.clear()
        flash("Your account has been deleted successfully.")
        return redirect(url_for('signin'))
    else:
        flash("You must be logged in to delete your account.")
        return redirect(url_for('signin'))

@app.route('/make_payment', methods=['GET', 'POST'])
def make_payment():
    user_id = session['id']

    if request.method == 'POST':
        card_id = request.form['card_id']
        merchant_id = request.form['merchant_id']

        connect = get_db_connection()

        try:
            
            with connect.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM user_gift_cards 
                    WHERE card_id = %s AND user_id = %s AND status = 'active'
                """, (card_id, user_id))
                card = cursor.fetchone()

                if not card:
                    flash("Invalid or already redeemed card!")
                    return redirect(url_for('make_payment'))

                
                cursor.execute("""
                    SELECT expires_at FROM gift_card_inventory 
                    WHERE card_id = %s
                """, (card_id,))
                expiry_date = cursor.fetchone()

                if expiry_date and expiry_date['expires_at'] < datetime.now():
                    flash("This gift card has expired!")
                    return redirect(url_for('make_payment'))

                
                cursor.execute("""
                    UPDATE user_gift_cards 
                    SET merchant_id = %s, status = 'redeemed'
                    WHERE card_id = %s
                """, (merchant_id, card_id))

                
                cursor.execute("""
                    INSERT INTO transactions (card_id, sender_id, receiver_id, transaction_date, status)
                    VALUES (%s, %s, %s, NOW(), 'completed')
                """, (card_id, user_id, merchant_id))

                connect.commit()

            flash("Payment successful, gift card sent to merchant!")
        except Exception as e:
            connect.rollback()
            flash(f"Error processing payment: {str(e)}")
        finally:
            connect.close()

        return redirect(url_for('make_payment'))

    connect = get_db_connection()

    with connect.cursor() as cursor:
        cursor.execute("""
            SELECT card_id, card_value, expires_at FROM user_gift_cards 
            WHERE user_id = %s AND status = 'active'
        """, (user_id,))
        cards = cursor.fetchall()

        
        cursor.execute("""
            SELECT merchant_id, merchant_name FROM merchants
        """)
        merchants = cursor.fetchall()

    connect.close()

    return render_template('make_payment.html', cards=cards, merchants=merchants)


@app.route('/convert_amt',methods = ['POST','GET'])
def convert_amt():
    if request.method == 'POST':
        card_id = request.form['card_id']
        merchant_id = session['id']

        connect = get_db_connection()
        with connect.cursor() as cursor:
            cursor.execute("SELECT card_value, status FROM user_gift_cards WHERE merchant_id = %s AND card_id = %s AND status = 'active'",(merchant_id, card_id))
            card = cursor.fetchone()

            if card:
                cursor.execute("UPDATE merchants SET balance = balance + %s WHERE merchant_id = %s",(card['card_value'],merchant_id))
                cursor.execute("UPDATE user_gift_cards SET status = 'redeemed' WHERE card_id = %s",(card_id,))
                connect.commit()
                flash("Gift card value has been added to your balance.")
            else:
                flash("Invalid card or already redeemed!")
            
        connect.close()
        return redirect('convert_amt')

    connect = get_db_connection()

    with connect.cursor() as cursor:
        cursor.execute("SELECT * FROM user_gift_cards WHERE merchant_id=%s",(session['id'],))
        cards = cursor.fetchall()
    connect.close()

    return render_template('convert_amt.html', cards=cards)


@app.route('/transaction_history')
def transaction_history():
    user_id = session['id']
    user_type = session['user_type']
    connect = get_db_connection()

    with connect.cursor() as cursor:
        if user_type == 'user':
           
            cursor.execute("""
                SELECT 
                    t.card_id, 
                    g.card_value, 
                    t.transaction_date AS purchase_date, 
                    g.expires_at,  -- Using expires_at from gift_card_inventory
                    u.user_name AS user_name, 
                    m.merchant_name AS merchant_name
                FROM transactions t
                LEFT JOIN users u ON u.user_id = t.sender_id
                LEFT JOIN merchants m ON m.merchant_id = t.receiver_id
                LEFT JOIN gift_card_inventory g ON g.card_id = t.card_id
                WHERE t.sender_id = %s OR t.receiver_id = %s
            """, (user_id, user_id))

        elif user_type == 'merchant':
            
            cursor.execute("""
                SELECT 
                    t.card_id, 
                    g.card_value, 
                    t.transaction_date AS purchase_date, 
                    g.expires_at, 
                    u.user_name AS user_name, 
                    m.merchant_name AS merchant_name
                FROM transactions t
                LEFT JOIN users u ON u.user_id = t.sender_id
                LEFT JOIN merchants m ON m.merchant_id = t.receiver_id
                LEFT JOIN gift_card_inventory g ON g.card_id = t.card_id
                WHERE t.receiver_id = %s
            """, (user_id,))

        elif user_type == 'admin':
           
            cursor.execute("""
                SELECT 
                    t.card_id, 
                    g.card_value, 
                    t.transaction_date AS purchase_date, 
                    g.expires_at, 
                    u.user_name AS user_name, 
                    m.merchant_name AS merchant_name
                FROM transactions t
                LEFT JOIN users u ON u.user_id = t.sender_id
                LEFT JOIN merchants m ON m.merchant_id = t.receiver_id
                LEFT JOIN gift_card_inventory g ON g.card_id = t.card_id
            """)

        
        transactions = cursor.fetchall()
        for transaction in transactions:
            if transaction['merchant_name'] is None:  
                transaction['merchant_name'] = 'System'

    connect.close()
    return render_template('transaction_history.html', transactions=transactions, user_type=user_type)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully. ")
    return redirect(url_for('signin'))

if __name__ == '__main__':
    app.run(debug=True)
