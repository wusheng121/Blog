from werkzeug.security import generate_password_hash
import sqlite3

conn = sqlite3.connect('database.db')

with open('db.sql', encoding = 'utf-8') as f:
    conn.executescript(f.read())

#创建一个执行句柄，用来执行后面的语句
cur = conn.cursor()
#插入一个用户
hashed_pw = generate_password_hash('arimakanaa')
hashed_pw2 = generate_password_hash('123456')
cur.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
           ('admin', hashed_pw, 1)
           )
cur.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
           ('user1', hashed_pw2, 0)
           )
#插入两条文章
cur.execute("INSERT INTO posts (title, content, author_id) VALUES (?, ?, ?)",
           ('学习Flask1', 'kanaa test1', 1)
           )

cur.execute("INSERT INTO posts (title, content, author_id) VALUES (?, ?, ?)",
           ('学习Flask2', 'kanaa test2', 2)
           )

conn.commit()
conn.close()
