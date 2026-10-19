import pymysql
from pymysql.cursors import DictCursor
from config import Config


def conectar():
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )
