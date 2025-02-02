#------------------------------------- IMPORTS ---------------------------------------#
import psycopg2
import os
from flask import Flask, render_template, request, flash, redirect, url_for,jsonify
from flask_sqlalchemy import SQLAlchemy
from models import db, Prompts, Users, UserWritings, Newsletter, BlogPost, CommunitySubmission
from datetime import datetime
import bcrypt
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from datetime import date
from flask_mail import Message, Mail
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, email, length, regexp, URL
#------------------------------ FLASK SETUP -----------------------------------------#

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
login_manager = LoginManager()
login_manager.init_app(app)
#------------------------------ FLASK MAIL SETUP -----------------------------------------#
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # SMTP server for Gmail
app.config['MAIL_PORT'] = 587  # Port for TLS
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME') #email address
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')  # email password
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')  # Default sender for emails
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_ASCII_ATTACHMENTS'] = False

mail = Mail(app)

#------------------------ CONTACT FORM SETUP VIA FLASKFORM------------------------------#
class ContactForm(FlaskForm):
    name = StringField(
        "Your Name",
        validators=[
            DataRequired(message="Name is required."),
            length(max=100, message="Name must be less than 100 characters.")
        ],
        render_kw={"placeholder": "Enter your name", "class": "form-control", "id": "userName"}
    )
    email = StringField(
        "Your Email",
        validators=[
            DataRequired(message="Email is required."),
            email(message="Enter a valid email address.")
        ],
        render_kw={"placeholder": "Enter your email", "class": "form-control", "id": "userEmail"}
    )
    message = TextAreaField(
        "Message",
        validators=[
            DataRequired(message="Message is required."),
            length(max=1000, message="Message must be less than 1000 characters.")
        ],
        render_kw={
            "placeholder": "Type your message here",
            "class": "form-control",
            "id": "userMessage",
            "rows": 5
        }
    )
    submit = SubmitField("Send Message", render_kw={"class": "btn btn-primary d-grid"})


#------------------------------DATABASE CONNECTION SETTINGS-----------------------------------#

# Settings

DB_USERNAME = 'postgres'
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'default_password')  # Fallback to 'default_password' if not set
DB_NAME = 'red_ink'
DB_HOST = 'localhost'

# PostgreSQL Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db.init_app(app)

# # Create tables
# with app.app_context():
#     db.create_all()
#     print("Tables created successfully!")



#------------------------PASSWORD HASHING ----------------------------#
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Verify password
def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


# --------------------------- HOMEPAGE ---------------------------------#
@app.route('/')
def home():
    return render_template('index.html')

# --------------------------- CONTACT PAGE ---------------------------------#
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()

    if request.method == 'POST':  # Only process if the form is submitted
        if form.validate_on_submit():
            name = form.name.data
            email = form.email.data
            message = form.message.data

            # Debug: Print data to console
            print(f"Name: {name}, Email: {email}, Message: {message}")

            # Create email message
            msg = Message(
                subject="RedInk Contact Form Submission",
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[app.config['MAIL_USERNAME']],
                body=f"Name: {name}\nEmail: {email}\n\nMessage:\n {message}"
            )

            # Send the email
            try:
                mail.send(msg)
                flash("Your message has been sent successfully!", "success")
                # print("Email sent successfully.")
            except Exception as e:
                # print(f"Error sending email: {e}")  # Print error to console
                flash(f"Failed to send message: {e}", "danger")

            return redirect(url_for('contact'))
        else:
            # Form submission, but validation failed
            # print("Form validation failed.")
            flash("Form validation failed. Please check your inputs.", "danger")

    # For GET request or after redirect, render the form
    return render_template('contact.html', form=form)


# --------------------------- ABOUT PAGE ---------------------------------#

@app.route('/about')
def about():
    return render_template('about.html')


# --------------------------- BLOG PAGE ---------------------------------#

@app.route('/blog')
def blog():
    # Get the current page number from query parameters (default to 1)
    page = request.args.get('page', 1, type=int)

    # Query the blog posts, order by most recent, and paginate
    per_page = 1  # Number of posts per page
    pagination = BlogPost.query.order_by(BlogPost.created_at.desc()).paginate(page=page, per_page=per_page)

    # Pass the pagination object to the template
    return render_template('blog.html', pagination=pagination)


# --------------------------- CATEGORY PAGE ---------------------------------#

@app.route('/category/<category_name>', defaults={'page': 1})
@app.route('/category/<category_name>/page/<int:page>')
def category_prompts(category_name, page):
    # Number of prompts per page
    per_page = 9

    # Query prompts for the given category
    prompts_query = Prompts.query.filter_by(category=category_name)
    total_prompts = prompts_query.count()

    # Fetch the prompts for the current page
    prompts = prompts_query.paginate(page=page, per_page=per_page, error_out=False).items

    # Get user writings is authenticated
    user_writings = []
    if current_user.is_authenticated:
        user_writings = UserWritings.query.filter_by(user_id=current_user.id).all()



    # Calculate total pages for pagination
    total_pages = (total_prompts + per_page - 1) // per_page

    return render_template(
        'category.html',
        prompts=prompts,
        category_name=category_name,
        page=page,
        user_writings=user_writings,
        total_pages=total_pages
    )
# --------------------------- PROMPT PAGE ---------------------------------#

@app.route('/prompt/<string:prompt_title>', methods=['GET', 'POST'])
def prompt(prompt_title):
    # Fetch the prompt from the database
    prompt = Prompts.query.filter_by(title=prompt_title).first()


    # Fetch the user's existing entry for the prompt
    entry = db.session.query(UserWritings).filter_by(user_id=current_user.id, prompt_id=prompt.id).first()
    print(entry.content) if entry else print("No entry found")

    if not prompt:
        flash("Prompt not found!", "error")
        return redirect(url_for('home'))

    if request.method == 'POST':
        # Ensure the user is logged in
        if not current_user.is_authenticated:
            flash("You must be logged in to submit a response.", "error")
            return redirect(url_for('login_page'))

        # Get user response from form
        user_response = request.form.get('user_response')
        if not user_response:
            flash("Response cannot be empty.", "error")
            return render_template('prompt.html', prompt=prompt, entry=entry)

        # Save the user's response to the database
        try:
            if entry:
                # Update existing entry
                entry.content = user_response
                entry.updated_at = datetime.utcnow()

            else:
                # Create new entry
                user_writing = UserWritings(
                    user_id=current_user.id,
                    prompt_id=prompt.id,
                    title=prompt.title,
                    content=user_response
                )
                db.session.add(user_writing)
            db.session.commit()
            flash("Your response has been saved successfully!", "success")
            return redirect(url_for('portfolio'))  # Redirect to the user's portfolio or another page
        except Exception as e:
            db.session.rollback()
            print(f"Error saving response: {e}")
            flash("An error occurred while saving your response. Please try again.", "error")

    # Render the prompt page for GET requests
    return render_template('prompt.html', prompt=prompt, entry=entry)


# --------------------------- PROMPT ENTRY PAGE ---------------------------------#
@app.route('/prompt/<prompt_title>/<int:user_id>', methods=['GET'])
def entry_page(prompt_title, user_id):
    # Query the prompt details
    prompt = db.session.query(Prompts).filter_by(title=prompt_title).first()
    if not prompt:
        flash("Prompt not found!", "error")
        return redirect(url_for('portfolio'))

    # Query the user’s specific entry
    entry = db.session.query(UserWritings).filter_by(user_id=user_id, prompt_id=prompt.id).first()
    if not entry:
        flash("No entry found for this prompt.", "warning")
        return redirect(url_for('portfolio'))

    # Check if the entry is in the community page
    in_community = db.session.query(CommunitySubmission).filter_by(user_id=user_id, prompt_id=prompt.id).first() is not None


    return render_template('entry.html', prompt=prompt, entry=entry, in_community=in_community)

# --------------------------- DELETE ENTRY ---------------------------------#
@app.route('/prompt/<prompt_title>/<int:user_id>/delete', methods=['POST'])
def delete_entry(prompt_title, user_id):
    # Query the prompt
    prompt = db.session.query(Prompts).filter_by(title=prompt_title).first()

    # Query the user's specific entry
    entry = db.session.query(UserWritings).filter_by(user_id=user_id, prompt_id=prompt.id).first()

    # If no entry is found, handle the case (optional)
    if not entry:
        flash("No entry found to delete.", "warning")
        return redirect(url_for('entry_page', prompt_title=prompt_title, user_id=user_id))

    # Delete the entry
    db.session.delete(entry)
    db.session.commit()

    # Flash a success message
    flash("Your entry has been successfully deleted.", "success")
    return redirect(url_for('portfolio'))

# --------------------------- ADD ENTRY TO COMMUNITY PAGE ---------------------------------## --------------------------- ADD/REMOVE ENTRY FROM COMMUNITY PAGE ---------------------------------#
@app.route('/prompt/<prompt_title>/<int:user_id>/toggle', methods=['POST'])
def toggle_community_entry(prompt_title, user_id):
    # Query the prompt
    prompt = db.session.query(Prompts).filter_by(title=prompt_title).first()

    if not prompt:
        flash("Prompt not found.", "error")
        return redirect(url_for('entry_page', prompt_title=prompt_title, user_id=user_id))

    # Query the user's specific post
    entry = db.session.query(UserWritings).filter_by(user_id=user_id, prompt_id=prompt.id).first()

    if not entry:
        flash("No entry found for this prompt.", "warning")
        return redirect(url_for('entry_page', prompt_title=prompt_title, user_id=user_id))

    # Check if the entry already exists in the community page
    existing_submission = db.session.query(CommunitySubmission).filter_by(user_id=user_id, prompt_id=prompt.id).first()

    if existing_submission:
        # If the entry exists, remove it
        db.session.delete(existing_submission)
        db.session.commit()
        flash("Your entry has been removed from the community page.", "info")
    else:
        # If the entry does not exist, add it
        new_submission = CommunitySubmission(
            prompt_id=prompt.id,
            user_id=user_id,
            category=prompt.category,
            content=entry.content
        )

        db.session.add(new_submission)
        db.session.commit()
        flash("Your entry has been posted to the community page!", "success")

    return redirect(url_for('entry_page', prompt_title=prompt_title, user_id=user_id))



# --------------------------- COMMUNITY PAGE ROUTE ---------------------------------#
@app.route('/community', defaults={'page': 1})
@app.route('/community/page/<int:page>')
def community(page):
    # Number of prompts per page
    per_page = 9


    # Query prompts for the given category
    paginated_writings = (
        CommunitySubmission.query
        .order_by(CommunitySubmission.created_at.desc())
        .paginate(page=page, per_page=per_page)
    )


    return render_template(
        'community.html',
        writings=paginated_writings.items,
        page=page,
        total_pages = paginated_writings.pages
    )

# --------------------------- COMMUNITY POST ROUTE ---------------------------------#
@app.route('/community/<prompt_title>/<int:user_id>', methods=['GET'])
def community_post(prompt_title, user_id):
    # Query the prompt details
    prompt = db.session.query(Prompts).filter_by(title=prompt_title).first()
    if not prompt:
        flash("Prompt not found!", "error")
        return redirect(url_for('community'))

    # Query the user’s specific entry
    entry = db.session.query(UserWritings).filter_by(user_id=user_id, prompt_id=prompt.id).first()
    if not entry:
        flash("No entry found for this prompt.", "warning")
        return redirect(url_for('community'))

    # Check if the entry is in the community page
    in_community = db.session.query(CommunitySubmission).filter_by(user_id=user_id, prompt_id=prompt.id).first() is not None


    return render_template('community_post.html', prompt=prompt, entry=entry, in_community=in_community)

# --------------------------- NEWSLETTER ROUTE ---------------------------------#

@app.route('/newsletter', methods=['POST'])
def newsletter_signup():
    email = request.form.get('EMAIL')

    if not email:
        return jsonify({'message': 'Please provide a valid email address.', 'category': 'error'})

    # Check if the email already exists
    existing_email = Newsletter.query.filter_by(email=email).first()
    if existing_email:
        return jsonify({'message': 'This email is already subscribed to the newsletter.', 'category': 'info'})

    # Add the email to the database
    try:
        new_subscription = Newsletter(email=email)
        db.session.add(new_subscription)
        db.session.commit()
        return jsonify({'message': 'Thank you for subscribing to our newsletter!', 'category': 'success'})
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'message': 'An error occurred while saving your subscription. Please try again.', 'category': 'error'})



# --------------------------- SIGNUP ROUTE ---------------------------------#

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    # USERNAME
    username = request.form.get('USERNAME')
    if not username:
        return jsonify({'message': 'Please provide a valid username.', 'category': 'error'})
        # Check if the username already exists
    existing_username = Users.query.filter_by(username=username).first()
    if existing_username:
        return jsonify({'message': f'Username "{ username }" is taken. Please try again.', 'category': 'info'})

    #PASSWORD
    password = request.form.get('SPASS')
    if not password:
        return jsonify({'message': 'Please provide a valid password.', 'category': 'error'})

    password_verify = request.form.get('SPASSV')
    if not password_verify:
        return jsonify({'message': 'Please re-type password.', 'category': 'error'})

    if password_verify != password:
        return jsonify({'message': 'Passwords do not match. Try again.', 'category': 'error'})



    #EMAIL
    email = request.form.get('SEMAIL')
    if not email:
        return jsonify({'message': 'Please provide a valid username.', 'category': 'error'})

    # Check if the email already exists
    existing_email = Users.query.filter_by(email=email).first()
    if existing_email:
        return jsonify({'message': 'This email is already linked to an account.', 'category': 'info'})

    # Hash the password
    hashed_password = hash_password(password)


    # Add the account to the User database
    try:
        new_account = Users(email=email, username=username, password_hash=hashed_password)
        db.session.add(new_account)
        db.session.commit()

        # Add the user to the newsletter
        new_subscription = Newsletter(email=email)
        db.session.add(new_subscription)
        db.session.commit()
        return jsonify({'message': 'Account created! Please log in.', 'category': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f"Error creating account: {str(e)}", 'category': 'error'})



#---------------------------- LOG IN / LOG OUT SET UP ---------------------#

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# --------------------------- LOGIN ROUTE ---------------------------------#

# Route to render the login page
@app.route('/login')
def login_page():
    return render_template('login.html')

# Route to handle the login form submission (POST method)
@app.route('/login', methods=['POST'])
def login():
    try:
        email = request.form.get('LEMAIL')
        password = request.form.get('LPASS')

        # Validation
        if not email:
            return jsonify({'message': 'Please enter your email.', 'category': 'error'})
        if not password:
            return jsonify({'message': 'Please enter your password.', 'category': 'error'})

        # Fetch user from database
        user = Users.query.filter_by(email=email).first()
        if user and verify_password(password, user.password_hash):
            login_user(user)  # This marks the user as logged in
            return jsonify({'message': 'Login successful!', 'category': 'success'})
        return jsonify({'message': 'Invalid email or password.', 'category': 'error'})
    except Exception as e:
        print(f"Error: {e}")


# --------------------------- DASHBOARD ROUTE ---------------------------------#
@app.route('/dashboard')
@login_required
def dashboard():
    # Get today's date
    today = date.today()
    today_str = today.strftime('%B %d, %Y')  # Format: "January 27, 2025"

    # Get all prompts
    prompts = Prompts.query.order_by(Prompts.id).all()
    prompt_count = len(prompts)
    if prompt_count == 0:
        flash("No prompts available. Please add prompts to the database.", "warning")
        return render_template('dashboard.html', user=current_user, today=today_str, daily_prompt=None, user_writing=None)

    # Calculate the daily prompt index
    daily_prompt_index = today.toordinal() % prompt_count
    daily_prompt = prompts[daily_prompt_index]  # Select the daily prompt

    # Check if the user has already submitted for today's prompt
    user_writing = UserWritings.query.filter_by(
        user_id=current_user.id,
        prompt_id=daily_prompt.id
    ).first()

    # Pass data to the template
    return render_template(
        'dashboard.html',
        user=current_user,
        today=today_str,
        daily_prompt=daily_prompt,
        user_writing=user_writing
    )


@app.route('/submit_prompt/<int:prompt_id>', methods=['POST'])
@login_required
def submit_prompt(prompt_id):
    content = request.form.get('user_response')

    # Fetch the prompt to get its title
    prompt = Prompts.query.get(prompt_id)
    if not prompt:
        flash('Prompt not found!', 'error')
        return redirect(url_for('dashboard'))

    # Check if the user has already written for this prompt
    user_writing = UserWritings.query.filter_by(
        user_id=current_user.id,
        prompt_id=prompt_id
    ).first()

    if user_writing:
        # Update only the `content` and `updated_at` fields
        user_writing.content = content
        user_writing.updated_at = datetime.utcnow()
    else:
        # Create a new entry
        user_writing = UserWritings(
            user_id=current_user.id,
            prompt_id=prompt_id,
            title=prompt.title,  # Use the prompt title for the writing's title
            content=content
        )
        db.session.add(user_writing)

    db.session.commit()
    flash('Your response has been saved!', 'success')
    return redirect(url_for('dashboard'))



# --------------------------- PORTFOLIO ROUTE ---------------------------------#
@app.route('/portfolio', defaults={'page': 1})
@app.route('/portfolio/page/<int:page>')
@login_required
def portfolio(page):
    per_page = 9  # Number of writings per page
    # Fetch the user's writings and sort by `created_at`
    paginated_writings = (
        UserWritings.query.filter_by(user_id=current_user.id)
        .order_by(UserWritings.created_at.desc())  # Ensure consistent order
        .paginate(page=page, per_page=per_page)
    )



    # ------------ TESTING PUTTING STAR EMOJI NEXT TO PUBLISHED ENTRIES -----------------------#
    in_community = db.session.query(CommunitySubmission).filter_by(user_id=current_user.id).all()
    community_prompt_ids = [entry.prompt_id for entry in in_community]
    for writing in paginated_writings:
        if writing.prompt_id in community_prompt_ids:
            print(writing.prompt_id)






    # ------------ TESTING PUTTING STAR EMOJI NEXT TO PUBLISHED ENTRIES -----------------------#


    return render_template(
        'portfolio.html',
        writings=paginated_writings.items,
        community_prompt_ids=community_prompt_ids,
        page=page,
        total_pages=paginated_writings.pages
    )

# --------------------------- CLOSING FLASK ---------------------------------#
if __name__ == '__main__':
    app.run(debug=True, port=5001)