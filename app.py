from flask import Flask,redirect,url_for,render_template,request,session,get_flashed_messages,flash,g
from flask_pymongo import PyMongo
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'static/images'  # Folder to save the uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}  # Allowed image file extensions


app = Flask(__name__)
app.secret_key = "123"
app.config['MONGO_URI'] = 'mongodb://localhost:27017/instagram'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mongo = PyMongo(app)
users_collection = mongo.db.users
posts_collection = mongo.db.posts


@app.route('/', methods=("POST", "GET"))
def login():
    if request.method == "POST":
        session.pop('user', None)
        email = request.form.get("email")
        password = request.form.get("password")
        
        # Check if the user exists and the password matches
        user = users_collection.find_one({"email": email, "password": password})
        if user:
            session["user"] = user["email"]
            return redirect(url_for("home"))
        else:
            flash("Incorrect email or password", "error")

    return render_template("index.html")

@app.before_request
def password_check():
    g.user = None
    if 'user' in session:
        g.user = session['user']

@app.route('/home', methods=("POST", "GET"))
def home():
    current_user_email = session.get("user")
    user_posts = posts_collection.find({"email": current_user_email})

   

    if g.user:
        user = users_collection.find_one({"email": current_user_email})
        username = user.get("username", "")
        number = user.get("number", "")
        image_path = user.get("image_path")

        return render_template("home.html", user=current_user_email, posts=user_posts, username=username, number=number, image=image_path)
    
    return redirect(url_for("index"))

@app.route('/logout')
def logout():
    # Clear the user's session
    session.pop('user', None)
    
    # Clear the image file associated with the session
    session.pop('image', None)

    return redirect(url_for("login"))

@app.route('/register', methods=["POST", "GET"])
def register():
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    if request.method == "POST":
        # Retrieve form data
        username = request.form.get("username")
        email = request.form.get("email")
        number = request.form.get("number")
        password = request.form.get("password")
        image = request.files.get("image")  # Use request.files to retrieve the uploaded file

        
        # Check if the user already exists
        existing_user = users_collection.find_one({"email": email})
        if existing_user:
            if existing_user["password"] == password:
                session["user"] = existing_user["username"]
                return redirect(url_for("home"))
            return render_template("register.html", error="Email already exists.")

        # Save the uploaded image
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Create the upload folder if it doesn't exist
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)  # Store the correct image path
        else:
            image_path = None

        # Create a new user
        new_user = {
            "username": username,
            "email": email,
            "number": number,
            "password": password,
            "image_path": image_path  # Store the image path in the user data
        }

        # Insert the new user into the MongoDB collection
        users_collection.insert_one(new_user)

        # Set the session user and redirect to the index page
        session["user"] = new_user["username"]
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route('/upload', methods=("POST", "GET"))
def upload():
   
    if request.method == "POST":
        image = request.files.get("image")
        image_content = request.form.get("image_content")

        if image:
            filename = secure_filename(image.filename)
            image.save(os.path.join("static", "image", filename))
            current_user_email = session.get("user")
            session['image'] = f"image/{filename}"
            posts_collection.insert_one({"email": current_user_email, "image": session['image'], "image_content": image_content})
            return redirect(url_for('user'))

    return render_template("upload.html")



@app.route('/user')
def user():
    
    current_user_email = session.get("user")
    user_posts = posts_collection.find({"email": current_user_email})
    
    current_user = users_collection.find_one({"email": current_user_email})
    username = current_user.get("username", "")
    number = current_user.get("number", "")
    image_path = current_user.get("image_path")  # Retrieve the image path from the user data

    return render_template("user.html",posts=user_posts, username=username, number=number, image=image_path)


@app.route('/edit/<string:image_content>', methods=["POST", "GET"])
def edit(image_content):
    if request.method == "POST":
        image_file = request.files.get("image")
        new_image_content = request.form.get("image_content")

        if image_file:
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join("static", "image", filename))
            posts_collection.update_one({"image_content": image_content}, {"$set": {"image": f"image/{filename}", "image_content": new_image_content}})
            return redirect(url_for('user'))

    data = posts_collection.find_one({"image_content": image_content})
    return render_template("edit.html", edit=data)


@app.route('/delete_item/<string:image_content>', methods=["GET"])
def delete(image_content):
    posts_collection.delete_one({"image_content": image_content})
    return redirect(url_for('user'))



if __name__=="__main__":
    app.run(debug=True)