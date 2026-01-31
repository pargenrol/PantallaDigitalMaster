from flask_sqlalchemy import SQLAlchemy

#Database module for Flask application.
#This module initializes and configures the SQLAlchemy ORM (Object-Relational Mapping) instance for the Flask application. 
#It provides a centralized database object that can be used throughout the application to define models and perform database operations.

db = SQLAlchemy()