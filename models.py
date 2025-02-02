from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin



# Initialize SQLAlchemy
db = SQLAlchemy()


# Prompts Table
class Prompts(db.Model):
    __tablename__ = 'prompts'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    recommended_length = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user_writings = db.relationship('UserWritings', backref='prompt', lazy=True, cascade="all, delete-orphan")
    community_entries = db.relationship('CommunitySubmission', backref='prompt', lazy=True, cascade="all, delete-orphan")

    # Enforce unique constraints
    __table_args__ = (
        db.UniqueConstraint('category', 'title', 'content', name='unique_prompt_constraint'),
    )

    def __repr__(self):
        return f'<Prompt id={self.id}, category={self.category}, title={self.title}>'


# Users Table
class Users(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.LargeBinary, nullable=False)  # Store the hash as bytes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    writings = db.relationship('UserWritings', backref='user', lazy=True, cascade="all, delete-orphan")
    community_submissions = db.relationship('CommunitySubmission', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User id={self.id}, username={self.username}, email={self.email}>'


# User Writings Table
class UserWritings(db.Model):
    __tablename__ = 'user_writings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    prompt_id = db.Column(db.Integer, db.ForeignKey('prompts.id', ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<UserWriting {self.title}>'


# Community Submissions Table
class CommunitySubmission(db.Model):
    __tablename__ = 'community_submissions'

    id = db.Column(db.Integer, primary_key=True)
    prompt_id = db.Column(db.Integer, db.ForeignKey('prompts.id', ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False)  # The prompt category (e.g., Reflection, Sci-Fi)
    content = db.Column(db.Text, nullable=False)  # User's completed entry
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp of submission

    def __repr__(self):
        return f"<CommunitySubmission {self.id} - User {self.user.username} - Prompt {self.prompt_id}>"




class Newsletter(db.Model):
    __tablename__ = 'newsletter'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class BlogPost(db.Model):
    __tablename__ = 'blog_posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), default='Red Ink')
    category = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



