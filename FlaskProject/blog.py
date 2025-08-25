from flask import Flask, render_template, request, url_for, flash, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'arimakanaa'

def get_db_conn():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# def get_userdb_conn():
#     conn = sqlite3.connect('users.db')
#     conn.row_factory = sqlite3.Row
#     return conn

def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if'user_id' not in session:
            flash('请先登录')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('需要管理员权限')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
@app.route('/')
def index():  # put application's code here
    conn = get_db_conn()
    posts = conn.execute("SELECT * FROM posts order by created desc").fetchall()
    return render_template('index.html', posts=posts)

def get_post(post_id):
    conn = get_db_conn()
    post = conn.execute('select * from posts where id = ?', (post_id,)).fetchone()
    return post

@app.route('/posts/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    conn = get_db_conn()
    post = conn.execute('select p.*, u.username from posts p left join users u on p.author_id = u.id where p.id = ?',
                        (post_id,)).fetchone()

    like_count = conn.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (post_id,)).fetchone()[0]

    if request.method == 'POST':
        if 'user_id' not in session:
            flash('请先登录后评论')
            return redirect(url_for('login'))
        content = request.form['content']
        if not content:
            flash('不能发送空评论！！！')
        else:
            conn.execute('INSERT INTO comments(post_id, user_id, content) VALUES (?, ?, ?)',
                         (post_id, session['user_id'], content))
            conn.commit()
            flash('评论成功')
            return redirect(url_for('post', post_id=post_id))
    comments = conn.execute('''
                SELECT c.*, u.username FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = ?
                order by c.created DESC
            ''', (post_id,)).fetchall()
    conn.close()
    return render_template('post.html', post=post, comments=comments, like_count=like_count)


@app.route('/posts/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author_id = session.get('user_id')
        #username = request.form['username']

        if not title:
            flash('标题不能为空！！！')
        elif not content:
            flash('内容不能为空！！！')
        else:
            conn = get_db_conn()
            conn.execute('insert into posts (title, content, author_id) values (?, ?, ?)', (title, content, author_id))
            conn.commit()
            post_id = conn.execute('select id from posts where title = ?', (title,)).fetchone()[0]
            conn.close()
            flash('文章上传成功！！！')
            return redirect(url_for('post', post_id=post_id))

    return render_template('new.html')

@app.route('/posts/<int:post_id>/edit', methods=('GET', 'POST'))
@login_required
def edit(post_id):
    post = get_post(post_id)

    if post['author_id'] != session.get('user_id') and not session.get('is_admin'):
        flash('没有编辑权限!!!')
        return redirect(url_for('post', post_id=post_id))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('标题不能为空！！！')
        elif not content:
            flash('内容不能为空！！！')
        else:
            conn = get_db_conn()
            conn.execute('update posts set title = ?, content = ?'
                         'where id = ?',
                         (title, content, post_id))
            conn.commit()
            conn.close()
            flash('修改成功！！！')
            return redirect(url_for('post', post_id=post_id))

    return render_template('edit.html', post=post)

@app.route('/posts/<int:post_id>/delete', methods=['POST',])
@login_required
def delete(post_id):
    post = get_post(post_id)

    if post['author_id'] != session.get('user_id') and not session.get('is_admin'):
        flash('没有删除权限!!!')
        return redirect(url_for('post', post_id=post_id))

    conn = get_db_conn()
    conn.execute('delete from posts where id = ?', (post_id,))
    conn.commit()
    conn.close()
    flash('"{}"删除成功！！！'.format(post['title']))
    return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed_pw = generate_password_hash(password)

        if not username:
            flash('用户名不能为空！！！')
        elif not password:
            flash('用户密码不能为空！！！')
        else:
            conn = get_db_conn()
            user = conn.execute('select * from users where username = ?', (username,)).fetchone()
            if user:
                flash('用户名已存在！！！')
            else:
                conn.execute('insert into users(username, password) values (?, ?)', (username, hashed_pw))
                conn.commit()
                conn.close()
                flash('注册成功，请登录')
                return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username:
            flash('用户名不能为空！！！')
        elif not password:
            flash('密码不能为空！！！')
        else:
            conn = get_db_conn()
            user = conn.execute('select * from users where username = ?', (username,)).fetchone()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = user['is_admin']
                flash('登录成功')
                return redirect(url_for('index'))
            else:
                flash('用户名或密码错误')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录')
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin():
    user_conn = get_db_conn()
    users = user_conn.execute('select * from users').fetchall()

    post_conn = get_db_conn()
    posts = post_conn.execute("SELECT * FROM posts order by created desc").fetchall()

    return render_template('admin.html', users=users, posts=posts)


@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    conn = get_db_conn()
    conn.execute('delete from users where id = ?', (user_id,))
    conn.commit()
    flash('用户已删除')
    return redirect(url_for('admin'))


@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like(post_id):
    conn = get_db_conn()
    try:
        conn.execute('INSERT INTO likes(post_id, user_id) VALUES (?, ?)', (post_id, session['user_id']))
        conn.commit()
        flash('点赞成功！')
    except sqlite3.IntegrityError:
        flash('你已经点过赞了！')
    finally:
        conn.close()
    return redirect(url_for('post', post_id=post_id))


@app.route('/personal')
@login_required
def personal():
    conn = get_db_conn()
    user_id = session.get('user_id')
    user = conn.execute('select * from users where id = ?', (user_id,)).fetchone()
    posts = conn.execute('select * from posts where author_id = ? order by created desc', (user_id,)).fetchall()
    comments = conn.execute('''
        select c.content, c.created,p.title, p.id as post_id from comments c
        join posts p on c.post_id=p.id
        where c.user_id = ?
        order by c.created desc
    ''', (user_id,)).fetchall()

    likes = conn.execute('''
        select p.title, p.id as post_id from likes l 
        join posts p on l.post_id = p.id
        where l.user_id = ?
    ''', (user_id,)).fetchall()
    conn.close()
    return render_template('personal.html', user = user, posts=posts, comments=comments, likes=likes)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
