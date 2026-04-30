import os

class Config:
    SECRET_KEY = 'secret123'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost/agrichain_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join('static', 'uploads') 
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_MASTER_KEY = os.environ.get('ADMIN_MASTER_KEY', 'agrichain123')
