import sqlite3

conn = sqlite3.connect('database.db')
cur = conn.cursor()

# 打印所有用户
cur.execute("SELECT * FROM users")
users = cur.fetchall()
print(users)

# 打印所有用户
cur.execute("SELECT * FROM posts")
posts = cur.fetchall()
print(posts)

conn.close()
