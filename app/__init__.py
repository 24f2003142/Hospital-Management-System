from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# create the db object here so models.py can import it
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # basic config
    app.config['SECRET_KEY'] = 'dev-secret-key'   # replace with env var in production
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dev.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # init extensions
    db.init_app(app)
    login_manager.init_app(app)

    # import models so they register with SQLAlchemy
    from app import models  

    return app