import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
from flask import Flask,request,flash,redirect,url_for,render_template,session
import random, yagmail
from datetime import datetime
import re
from flask import jsonify
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from collections import Counter

cre=credentials.Certificate(r"C:\Users\kasha\Desktop\kashmiri food\kashmiri-food-firebase-adminsdk-fbsvc-29f8fcbfd5.json")

firebase_admin.initialize_app(cre,{
    'databaseURL':'https://kashmiri-food-default-rtdb.firebaseio.com/'
})


app=Flask(__name__)
app.secret_key = "456"

@app.route('/')
def home():
    ann_ref = db.reference('announcements')
    ann = ann_ref.get() or {}
    return render_template("home.html", announcement=ann)



#services
@app.route("/services")
def services():
    return render_template("services.html")

#contact
@app.route("/contact")
def contact():
    return render_template("contact.html")




#about
@app.route("/about")
def about():
    return render_template("about.html")




#user_signup
@app.route('/user_signup', methods=['POST', 'GET'])
def user_signup():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password'].strip()

        if not name or not email or not password:
            flash("All fields are required", "error")
            return redirect(url_for('user_signup'))

        # Save to Firebase
        users_ref = db.reference('users')
        new_user_ref = users_ref.push({
            'name': name,
            'email': email,
            'password': password
        })

        # Save uid in session
        session['uid'] = new_user_ref.key

        flash("Signup successful! Please login.", "success")
        return redirect(url_for('user_login'))

    return render_template('login_signup.html')  # same file used

#user_login
@app.route('/user_login', methods=['POST', 'GET'])
def user_login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        role = request.form.get('role')

        if not email or not password or not role:
            flash("All fields are required", "error")
            return redirect(url_for('user_login'))

        if role == "user":
            users_ref = db.reference('users').get()
            if users_ref:
                for uid, user_data in users_ref.items():
                    if user_data.get('email') == email and user_data.get('password') == password:
                        session['uid'] = uid  # ✅ yahan uid save ho rahi hai
                        session['email'] = email
                        flash("Login successful!", "success")
                        return redirect(url_for('user_dashboard'))
            flash("Invalid user credentials", "error")
            return redirect(url_for('user_login'))

        elif role == "admin":
            admin_data = db.reference('admin').get()

            if admin_data:
                db_email = str(admin_data.get('email', '')).strip()
                db_password = str(admin_data.get('password', '')).strip()

                if db_email == email and db_password == password:
                    session['role'] = 'admin'
                    session['uid'] = 'admin'
                    flash("Admin login successful!", "success")
                    return redirect(url_for('admin_dashboard'))

            flash("Invalid admin credentials", "error")
            return redirect(url_for('user_login'))

    return render_template('login_signup.html')





@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("user_login"))

from firebase_admin import db

@app.route("/admin_dashboard")
def admin_dashboard():
    # ✅ Check if admin is logged in
    if "uid" not in session or session["uid"] != "admin":
        flash("Please login as admin first.", "error")
        return redirect(url_for("user_login"))  # 👈 admin login route banaya hoga

    # Users data
    users_ref = db.reference("users")
    users_data = users_ref.get() or {}

    # Menu data
    menu_ref = db.reference("menu")
    menu_data = menu_ref.get() or {}

    # Count users
    total_users = len(users_data)

    # ✅ Count menu items
    total_menu_items = len(menu_data)

    # Category counts
    category_counts = {}
    for item_id, item in menu_data.items():
        category = item.get("category", "Uncategorized")
        category_counts[category] = category_counts.get(category, 0) + 1

    # ✅ Sabse zyada wali category select karna
    featured_category = None
    featured_items = []
    if category_counts:
        featured_category = max(category_counts, key=category_counts.get)
        # us category ke items nikalna
        featured_items = [
            {"title": i.get("title", "Unnamed")}
            for i in menu_data.values()
            if i.get("category") == featured_category
        ]

    # ✅ Chats unseen counter
    chats_ref = db.reference("chats")
    chats = chats_ref.get() or {}

    unseen_count = 0
    for uid, chat in chats.items():
        messages = chat.get("messages", {})
        for mid, msg in messages.items():
            if msg.get("status") == "unseen" and msg.get("uid") != "admin":
                unseen_count += 1

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_menu_items=total_menu_items,
        category_counts=category_counts,
        featured_category=featured_category,
        featured_items=featured_items,
        unseen_count=unseen_count   # 👈 yeh bhi bhejna
    )


# Upload config
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif','jfif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/add_menu', methods=['GET', 'POST'])
def add_menu():
    if request.method == 'POST':
        category = request.form.get('category')
        title = request.form.get('title')
        price = request.form.get('price')
        image = request.files.get('image')

        if not category or not title or not price or not image:
            return render_template('add_menu.html', error="Please fill in all fields and upload an image.")

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)

            menu_ref = db.reference('menu')
            new_menu = menu_ref.push({
                'category': category,
                'title': title,
                'price': price,
                'image': image_path
            })
            return render_template('add_menu.html', success="✅ Menu item added successfully!")

        else:
            return render_template('add_menu.html', error="Invalid image format. Please upload PNG, JPG, or JPEG.")

    return render_template('add_menu.html')

#edit menu for admin
@app.route('/edit_menu', methods=['GET', 'POST'])
def edit_menu():
    menu_ref = db.reference("menu")
    menu_data = menu_ref.get()

    if request.method == "POST":
        category = request.form.get("category")
        title = request.form.get("title")

        new_title = request.form.get("new_title")
        new_category = request.form.get("new_category")
        new_price = request.form.get("price")
        new_image = request.files.get("image")  # ✅ file se image

        if not (category and title):
            return render_template('edit_menu.html', error="Please enter current category and title.", menus=menu_data)

        if not menu_data:
            return render_template('edit_menu.html', error="Menu is empty.", menus={})

        updated = False
        for key, item in menu_data.items():
            if item.get("category") == category and item.get("title") == title:
                update_data = {}
                if new_title: update_data["title"] = new_title
                if new_category: update_data["category"] = new_category
                if new_price: update_data["price"] = new_price

                # ✅ Image handling
                if new_image and allowed_file(new_image.filename):
                    filename = secure_filename(new_image.filename)
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    new_image.save(image_path)
                    update_data["image"] = image_path

                if update_data:
                    menu_ref.child(key).update(update_data)
                    updated = True
                break

        if updated:
            return render_template('edit_menu.html', success="✅ Item updated successfully!", menus=menu_data)
        else:
            return render_template('edit_menu.html', error="Item not found.", menus=menu_data)

    return render_template("edit_menu.html", menus=menu_data)


#delete menu
@app.route("/delete_menu", methods=["GET", "POST"])
def delete_menu():
    menu_ref = db.reference("menu")
    menu_data = menu_ref.get() or {}

    error, success = None, None

    if request.method == "POST":
        delete_type = request.form.get("delete_type")

        # 🔴 Delete Category
        if delete_type == "category":
            category_to_delete = request.form.get("category_name")
            found = False
            for key, item in list(menu_data.items()):
                if item.get("category", "").lower() == category_to_delete.lower():
                    menu_ref.child(key).delete()
                    found = True
            if found:
                success = f"Category '{category_to_delete}' deleted with all its cards."
            else:
                error = f"No category found with name '{category_to_delete}'."

        # 🔴 Delete Single Card
        elif delete_type == "card":
            category_name = request.form.get("category_name")
            card_title = request.form.get("card_title")
            found = False
            for key, item in list(menu_data.items()):
                if (item.get("category", "").lower() == category_name.lower() and
                    item.get("title", "").lower() == card_title.lower()):
                    menu_ref.child(key).delete()
                    found = True
                    success = f"Card '{card_title}' deleted from category '{category_name}'."
                    break
            if not found:
                error = f"No card titled '{card_title}' found in category '{category_name}'."

    return render_template("delete_menu.html", error=error, success=success)



@app.route('/menu')
def menu():
    menu_ref = db.reference('menu')
    menu_data = menu_ref.get()

    menus_by_category = {}
    all_items = []   # ✅ saare items search ke liye
    if menu_data:
        for key, item in menu_data.items():
            category = item.get("category") or "Uncategorized"
            if category not in menus_by_category:
                menus_by_category[category] = []
            menus_by_category[category].append({
                "id": key,
                "title": item.get("title", "No Title"),
                "price": item.get("price", "No Price"),
                "image": item.get("image", None)
            })
            all_items.append({
                "id": key,
                "title": item.get("title", "No Title"),
                "category": category
            })

    # ✅ Featured Food logic
    category_counts = {cat: len(items) for cat, items in menus_by_category.items() if items}
    top_categories = sorted(category_counts, key=category_counts.get, reverse=True)[:1]
    featured_menus = {cat: menus_by_category[cat] for cat in top_categories}

    return render_template(
        "menu.html",
        menus=menus_by_category,
        featured_menus=featured_menus,
        category_counts=category_counts or {},
        all_items=all_items   # ✅ send to template
    )





@app.context_processor
def cart_count():
    cart = session.get("cart", {})
    count = sum(item["quantity"] for item in cart.values())
    return dict(cart_count=count)

@app.route('/menu_view/<menu_id>')
def menu_view(menu_id):
    menu_ref = db.reference('menu').child(menu_id)
    menu_item = menu_ref.get()

    if not menu_item:
        return "Menu item not found", 404

    # item id add kardo (firebase me by default key hota hai)
    menu_item["id"] = menu_id
    return render_template("menu_view.html", item=menu_item)

@app.route('/add_to_cart/<menu_id>', methods=['POST'])
def add_to_cart(menu_id):
    qty = int(request.form.get("quantity", 1))
    menu_ref = db.reference('menu').child(menu_id)
    menu_item = menu_ref.get()

    if not menu_item:
        return "Item not found", 404

    cart = session.get("cart", {})

    if menu_id in cart:
        cart[menu_id]["quantity"] += qty
    else:
        cart[menu_id] = {
            "title": menu_item["title"],
            "price": float(menu_item["price"]),
            "quantity": qty
        }

    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route('/cart')
def cart():
    cart = session.get("cart", {})
    subtotal = sum(item["price"] * item["quantity"] for item in cart.values())
    return render_template("cart.html", cart=cart, subtotal=subtotal)


@app.route("/remove_from_cart/<item_id>", methods=["POST"])
def remove_from_cart(item_id):
    cart = session.get("cart", {})

    if item_id in cart:
        # agar quantity > 1 to ek kam karo
        if cart[item_id]["quantity"] > 1:
            cart[item_id]["quantity"] -= 1
        else:
            # warna item completely hata do
            del cart[item_id]

    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route('/payment')
def payment():
    cart = session.get('cart', {})  # session se cart lelo
    if not cart:
        return render_template("payment.html", cart={}, total=0, delivery_charges=99, subtotal=99)

    # total price nikalna
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    delivery_charges = 99
    subtotal = total + delivery_charges

    return render_template("payment.html", cart=cart, total=total,
                           delivery_charges=delivery_charges, subtotal=subtotal)


#place order
@app.route('/place_order', methods=['POST'])
def place_order():
    cart = session.get('cart', {})
    if not cart:
        return "No items in cart"

    # Total calculate
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    delivery_charges = 99
    subtotal = total + delivery_charges

    # Random Order ID
    order_number = random.randint(100000, 999999)

    # User email (assuming user login system)
    user_email = session.get('email', None)  # tumne login mai email session me store karna hoga

    # Order object
    order = {
        "order_number": order_number,
        "cart": cart,
        "total": total,
        "delivery_charges": delivery_charges,
        "subtotal": subtotal,
        "email": user_email
    }

    # Save order in session (or DB)
    orders = session.get('orders', [])
    orders.append(order)
    session['orders'] = orders

    # Clear cart
    session.pop('cart', None)

    # Send Email to user
    if user_email:
        yag = yagmail.SMTP("saharax191@gmail.com", "ctravpkafztcmjiu")
        subject = f"Order Confirmation - #{order_number}"
        body = f"Thank you for your order!\n\nOrder Number: {order_number}\nTotal: Rs. {subtotal}\n\nYour order will be delivered soon."
        yag.send(user_email, subject, body)

    # Redirect to order summary page
    return render_template("order_summary.html", order=order)



@app.route('/view_users')
def view_users():
    # if 'role' not in session or session['role'] != 'admin':
    #     flash("Please log in as admin first", "error")
    #     return redirect(url_for('user_login'))

    users_ref = db.reference('users')
    users_data = users_ref.get() or {}

    return render_template('view_users.html', users=users_data)

@app.route('/edit_admin', methods=['GET', 'POST'])
def edit_admin():
    if 'role' not in session or session['role'] != 'admin':
        flash("Unauthorized access", "error")
        return redirect(url_for('user_login'))

    admin_ref = db.reference('admin')
    admin_data = admin_ref.get() or {}

    if request.method == 'POST':
        new_email = request.form['email'].strip()
        new_password = request.form['password'].strip()

        # Update Firebase
        admin_ref.update({
            'email': new_email,
            'password': new_password
        })

        flash("Admin info updated successfully", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template(
        'edit_admin.html',
        admin_email=admin_data.get('email', ''),
        admin_password=admin_data.get('password', '')
    )

@app.route('/add_announcement', methods=['GET', 'POST'])
def add_announcement():
    if request.method == 'POST':
        text = request.form.get('text')

        if not text:
            return render_template("add_announcement.html", error="Please enter announcement text.")

        # Save in Firebase
        ann_ref = db.reference('announcements')
        ann_ref.set({
            "text": text
        })

        return render_template("add_announcement.html", success="✅ Announcement added successfully!")

    return render_template("add_announcement.html")

@app.route("/complain", methods=["GET", "POST"])
def complain():
        # ✅ Pehle check karo user login hai ya nahi
        if "uid" not in session:
            flash("Please login first to submit a complaint.", "error")
            return redirect(url_for("user_login"))

        if request.method == "POST":
            # User ki complain form se nikaal lo
            complain_text = request.form.get("complain", "").strip()

            if not complain_text:
                flash("Complain cannot be empty!", "error")
                return redirect(url_for("complain"))

            # Session se user email nikal lo (tumne pehle save karwaya tha)
            user_email = session.get("email", "Unknown User")

            # Random complain ID
            complain_id = f"cmp-{random.randint(1000, 9999)}"

            # Firebase me save karo
            complain_ref = db.reference("complains")
            complain_ref.child(complain_id).set({
                "complain": complain_text,
                "user_email": user_email,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            # Admin ko email bhejo
            try:
                yag = yagmail.SMTP("saharax191@gmail.com", "ctravpkafztcmjiu")
                yag.send(
                    to="saharax191@gmail.com",
                    subject="New User Complain Received",
                    contents=f"""
                    A new complain has been submitted:

                    From: {user_email}
                    Complain ID: {complain_id}
                    Message: {complain_text}

                    Please check the admin dashboard for details.
                    """
                )
            except Exception as e:
                print("Email error:", e)

            # User ko success message dikhado
            flash("Your complain has been submitted successfully!", "success")
            return redirect(url_for("complain"))

        return render_template("complain.html")


@app.route("/get_complains")
def get_complains():
    complain_ref = db.reference("complains")
    complains = complain_ref.get() or {}

    # Complains ko list bana lo
    complain_list = []
    for cid, data in complains.items():
        complain_list.append({
            "id": cid,
            "complain": data.get("complain", ""),
            "user_email": data.get("user_email", ""),
            "timestamp": data.get("timestamp", ""),
            "seen": data.get("seen", False)
        })

    return {"complains": complain_list}

#Review Route for complaisn
@app.route("/review_complain/<cid>")
def review_complain(cid):
    complain_ref = db.reference(f"complains/{cid}")
    complain = complain_ref.get()

    if not complain:
        return "Complain not found", 404

    # Mark as seen
    complain_ref.update({"seen": True})

    return render_template("review_complain.html", complain=complain, cid=cid)


#Backend: mark complaints as seen
@app.route("/mark_complains_seen", methods=["POST"])
def mark_complains_seen():
    complain_ref = db.reference("complains")
    complains = complain_ref.get() or {}

    for cid, data in complains.items():
        complain_ref.child(cid).update({"seen": True})

    return {"status": "ok"}

# # Get unseen complaints count only
# @app.route("/get_unseen_count")
# def get_unseen_count():
#     complain_ref = db.reference("complains")
#     complains = complain_ref.get() or {}
#
#     unseen_count = sum(1 for c in complains.values() if not c.get("seen", False))
#     return {"unseen_count": unseen_count}



@app.route("/get_recent_complains")
def get_recent_complains():
    complain_ref = db.reference("complains")
    complains = complain_ref.get() or {}

    # Complains ko list me convert karke sort karein timestamp ke hisaab se (latest first)
    complain_list = []
    for cid, data in complains.items():
        complain_list.append({
            "id": cid,
            "complain": data.get("complain", ""),
            "user_email": data.get("user_email", ""),
            "timestamp": data.get("timestamp", "")
        })

    # Latest 5 hi bhejna
    complain_list = sorted(
        complain_list,
        key=lambda x: x["timestamp"],
        reverse=True
    )[:5]

    return {"complains": complain_list}


@app.route("/search_menu")
def search_menu():
    query = request.args.get("q", "").lower()
    if not query:
        return {"results": []}

    menu_ref = db.reference("menu")
    menu_items = menu_ref.get() or {}

    results = []
    for mid, item in menu_items.items():
        title = item.get("title", "").lower()
        category = item.get("category", "").lower()

        # Agar query title ya category me milti ho
        if query in title or query in category:
            results.append({
                "id": mid,
                "title": item.get("title", ""),
                "category": item.get("category", ""),
                "price": item.get("price", ""),
                "image": item.get("image", "")
            })

    return {"results": results}


# wallet route
# wallet route
@app.route('/wallet', methods=['GET', 'POST'])
def wallet():
    if 'uid' not in session:   # check user login
        flash("Please login first", "error")
        return redirect(url_for('user_login'))

    # user_id=session['uid']


    if request.method == 'POST':
        name = request.form['name'].strip()
        amount = request.form['amount'].strip()
        cnic = request.form['cnic'].strip()
        image = request.files['image']

        if not name or not amount or not cnic or not image:
            flash("All fields are required", "error")
            return redirect(url_for('wallet'))

        # Save image
        image_filename = image.filename
        image.save("static/uploads/" + image_filename)

        # get uid from session
        uid = session['uid']

        # current date and time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # save to firebase db
        wallet_ref = db.reference('wallet')
        wallet_ref.push({
            'name': name,
            'amount': amount,
            'cnic': cnic,
            'image': image_filename,
            'user_id': uid,
            'datetime': current_time
        })

        flash("Wallet data saved successfully!", "success")
        return redirect(url_for('wallet'))

    return render_template('wallet.html')





#
# -------------------
# EMAIL SENDER FUNCTION
# -------------------
def send_email_yagmail(to_email, username, status, amount=None):
    try:
        yag = yagmail.SMTP("saharax191@gmail.com", "ctravpkafztcmjiu")

        if status == "approved":
            subject = "Wallet Approved ✅"
            contents = f"""
            Dear {username},

            Your wallet has been APPROVED successfully.

            Approved Amount: {amount}

            You can now use your approved balance.

            Regards,
            Admin
            """
        elif status == "rejected":
            subject = "Wallet Rejected ❌"
            contents = f"""
            Dear {username},

            Unfortunately, your wallet request has been REJECTED.

            Please contact support for more details.

            Regards,
            Admin
            """
        else:
            subject = "Wallet Update"
            contents = f"Hello {username}, your wallet status is updated to {status}."

        yag.send(to=to_email, subject=subject, contents=contents)
        print(f"Email sent to {to_email} with status {status}")
    except Exception as e:
        print("Email error:", e)


# -------------------
# WALLET VIEW ROUTE
# -------------------
@app.route('/wallet_view', methods=['GET', 'POST'])
def wallet_view():
    wallets_ref = db.reference('wallet')
    wallets_data = wallets_ref.get()

    if not wallets_data:
        flash("⚠ No wallet data found.", "error")
        return render_template("wallet_view.html", wallets=[])

    merged_wallets = []

    for wallet_id, wallet in wallets_data.items():
        user_id = wallet.get("user_id")

        # Related user fetch karo
        user_data = None
        if user_id:
            user_data = db.reference('users').child(user_id).get()

        # Agar POST request hai aur button press hua
        if request.method == "POST":
            action = request.form.get("action")
            target_wallet_id = request.form.get("wallet_id")

            if wallet_id == target_wallet_id and user_data:
                if action == "approved":
                    amount = wallet.get("amount", 0)
                    db.reference('wallet').child(wallet_id).update({
                        "status": "approved",
                        "approved_amount": amount
                    })
                    flash("Wallet approved successfully!", "success")

                    # Email bhejna
                    send_email_yagmail(
                        user_data["email"],
                        user_data.get("name", "User"),
                        "approved",
                        amount
                    )

                elif action == "rejected":
                    db.reference('wallet').child(wallet_id).update({
                        "status": "rejected"
                    })
                    flash("Wallet rejected successfully!", "error")

                    # Email bhejna
                    send_email_yagmail(
                        user_data["email"],
                        user_data.get("name", "User"),
                        "rejected"
                    )

                # Data refresh karo
                wallet = db.reference('wallet').child(wallet_id).get()

        merged_wallets.append({
            "wallet_id": wallet_id,
            "amount": wallet.get("amount"),
            "cnic": wallet.get("cnic"),
            "image": wallet.get("image"),
            "datetime": wallet.get("datetime"),
            "status": wallet.get("status", "pending"),
            "approved_amount": wallet.get("approved_amount", None),
            "user": {
                "name": user_data.get("name") if user_data else "Unknown",
                "email": user_data.get("email") if user_data else "Unknown"
            }
        })

    return render_template("wallet_view.html", wallets=merged_wallets)


@app.route('/my_wallet')
def my_wallet():
    if 'uid' not in session:
        flash("Please login first", "error")
        return redirect(url_for('user_login'))

    uid = session['uid']

    # Wallet entries for this user
    wallets_ref = db.reference('wallet')
    wallets_data = wallets_ref.order_by_child("user_id").equal_to(uid).get()

    if not wallets_data:
        flash("⚠ No wallet data found for this account.", "error")
        return render_template("wallet_user_view.html",
                               approved_wallets=[],
                               pending_wallets=[],
                               rejected_wallets=[],
                               total_balance=0)
    approved_wallets = []
    pending_wallets = []
    rejected_wallets = []
    total_balance = 0

    # Categorize wallets
    for wallet_id, wallet in wallets_data.items():
        status = wallet.get("status", "pending")
        approved_amount = float(wallet.get("approved_amount", 0)) if wallet.get("approved_amount") else 0

        wallet_entry = {
            "wallet_id": wallet_id,
            "amount": wallet.get("amount"),
            "approved_amount": approved_amount,
            "cnic": wallet.get("cnic"),
            "image": wallet.get("image"),
            "datetime": wallet.get("datetime"),
            "status": status
        }

        if status == "approved":
            approved_wallets.append(wallet_entry)
            total_balance += approved_amount
        elif status == "rejected":
            rejected_wallets.append(wallet_entry)
        else:
            pending_wallets.append(wallet_entry)

    return render_template("wallet_user_view.html",
                           approved_wallets=approved_wallets,
                           pending_wallets=pending_wallets,
                           rejected_wallets=rejected_wallets,
                           total_balance=total_balance)


from datetime import datetime

@app.route("/place_order_wallet", methods=["POST"])
def place_order_wallet():
    if 'uid' not in session:
        flash("Please login first", "error")
        return redirect(url_for("user_login"))

    uid = session['uid']
    cart = session.get("cart", {})

    if not cart:
        flash("❌ Your cart is empty.", "error")
        return redirect(url_for("cart"))

    # Cart se subtotal nikal lo
    subtotal = sum(item['price'] * item['quantity'] for item in cart.values())
    delivery_charges = 99
    total = subtotal + delivery_charges

    # Wallet balance check
    wallets_ref = db.reference("wallet")
    wallets_data = wallets_ref.order_by_child("user_id").equal_to(uid).get()

    total_balance = 0
    wallet_ids = []

    if wallets_data:
        for wallet_id, wallet in wallets_data.items():
            if wallet.get("status") == "approved":
                total_balance += float(wallet.get("approved_amount", 0) or 0)
                wallet_ids.append(wallet_id)

    if total_balance < subtotal:
        flash("❌ Insufficient wallet balance. Please recharge wallet.", "error")
        return redirect(url_for("cart"))

    # Deduct balance
    remaining = subtotal
    for wid in wallet_ids:
        wallet = wallets_data[wid]
        approved_amount = float(wallet.get("approved_amount", 0) or 0)

        if approved_amount >= remaining:
            new_amount = approved_amount - remaining
            db.reference(f"wallet/{wid}").update({"approved_amount": new_amount})
            remaining = 0
            break
        else:
            db.reference(f"wallet/{wid}").update({"approved_amount": 0})
            remaining -= approved_amount

    # ✅ Save order in database
    order_data = {
        "user_id": uid,
        "items": cart,
        "subtotal": subtotal,
        "delivery_charges": delivery_charges,
        "total": total,
        "payment_method": "Wallet",
        "status": "pending",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    orders_ref = db.reference("orders")
    orders_ref.push(order_data)

    # Cart clear kar do
    session["cart"] = {}

    flash("✅ Order placed successfully using Wallet.", "success")
    return redirect(url_for("user_orders"))

@app.route("/user_orders")
def user_orders():
    if "uid" not in session:
        flash("Please login first", "error")
        return redirect(url_for("user_login"))

    uid = session["uid"]
    orders_ref = db.reference("orders")
    orders_data = orders_ref.order_by_child("user_id").equal_to(uid).get() or {}

    orders = []
    for oid, odata in orders_data.items():
        orders.append({
            "id": oid,
            "cart": odata.get("cart", {}),
            "subtotal": odata.get("subtotal", 0),
            "delivery_charges": odata.get("delivery_charges", 0),
            "total": odata.get("total", 0),
            "status": odata.get("status", "pending"),
            "payment_method": odata.get("payment_method", "N/A")
        })

    return render_template("user_orders.html", orders=orders)



#routers for chat system
# ✅ Chat Room (user + admin dono ke liye)
@app.route("/chat_room/<uid>", methods=["GET", "POST"])
def chat_room(uid):
    # Agar login nahi hai to redirect
    if "uid" not in session and session.get("role") != "admin":
        return redirect(url_for("user_login"))

    chat_ref = db.reference(f"chats/{uid}/messages")

    # ✅ Message bhejne ka logic
    if request.method == "POST":
        message_text = request.form.get("message")
        if message_text:
            sender_uid = "admin" if session.get("role") == "admin" else session["uid"]
            chat_ref.push({
                "uid": sender_uid,
                "message": message_text,
                "status": "unseen" if sender_uid != "admin" else "seen"
            })

        return redirect(url_for("chat_room", uid=uid))

    # ✅ Messages load karna
    messages = chat_ref.get() or {}

    # ✅ Seen logic: agar admin open kare to unseen msgs -> seen
    if session.get("role") == "admin":
        for mid, msg in messages.items():
            if msg.get("uid") != "admin" and msg.get("status") == "unseen":
                chat_ref.child(mid).update({"status": "seen"})

    return render_template(
        "chat_room.html",
        messages=messages,
        current_uid=session.get("uid"),
        is_admin=True if session.get("role") == "admin" else False
    )


# ✅ Chat Room (user + admin dono ke liye)
@app.route("/chat_room/", methods=["GET", "POST"])
def chat_room1():
        return redirect(url_for("user_login"))



# ✅ Admin chats list
@app.route("/admin_chats")
def admin_chats():
    if session.get("role") != "admin":
        return redirect(url_for("user_login"))

    chats_ref = db.reference("chats")
    chats = chats_ref.get() or {}

    users_ref = db.reference("users")
    users = users_ref.get() or {}

    chat_list = []
    for uid, chat in chats.items():
        user = users.get(uid, {})
        name = user.get("name", "Unknown")
        email = user.get("email", "")
        messages = chat.get("messages", {})
        last_msg = list(messages.values())[-1]["message"] if messages else "No message"
        chat_list.append({"uid": uid, "name": name, "email": email, "last_msg": last_msg})

    return render_template("admin_chats.html", chat_list=chat_list)




    # mark unseen -> seen for user messages
    messages = chat_ref.get() or {}
    for mid, msg in messages.items():
        if msg.get("uid") != "admin" and msg.get("status") == "unseen":
            chat_ref.child(mid).update({"status": "seen"})

    messages = chat_ref.get() or {}
    return render_template("chat_room.html", messages=messages, is_admin=True, uid=uid)






# User Dashboard Route
@app.route('/user_dashboard')
def user_dashboard():
    if 'uid' not in session:   # ✅ check login
        flash("Please login first", "error")
        return redirect(url_for('user_login'))
    return render_template('user_dashboard.html')


@app.route('/edit_user', methods=['GET', 'POST'])
def edit_user():
    if 'uid' not in session:
        flash("Please login first", "error")
        return redirect(url_for('user_login'))

    uid = session['uid']
    user_ref = db.reference(f'users/{uid}')

    if request.method == 'POST':
        new_email = request.form.get('email', '').strip()
        new_password = request.form.get('password', '').strip()

        if new_email and new_password:
            user_ref.update({
                "email": new_email,
                "password": new_password
            })
            session['email'] = new_email  # ✅ update session too
            flash("Profile updated successfully!", "success")
            return redirect(url_for('edit_user'))
        else:
            flash("Both fields are required", "error")

    # show current data
    user_data = user_ref.get()
    return render_template('edit_user.html', user=user_data)


@app.route('/user_logout')
def user_logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for('user_login'))





# if __name__=='__main__':
#     app.run(debug=True)


if __name__=='__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)