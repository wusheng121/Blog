from flask import Flask, render_template, request, url_for, flash, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
import sqlite3
import os
import uuid
from typing import Any

app = Flask(__name__)
app.config['SECRET_KEY'] = 'arimakanaa'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_db_conn():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

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
    conn.close()
    return post

@app.route('/posts/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    conn = get_db_conn()
    post = conn.execute('select p.*, u.username from posts p left join users u on p.author_id = u.id where p.id = ?',
                        (post_id,)).fetchone()
    if post is None:
        conn.close()
        flash('文章不存在')
        return redirect(url_for('index'))

    like_count = conn.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (post_id,)).fetchone()[0]

    author = conn.execute('select * from users where id = ?', (post['author_id'],)).fetchone()

    followed = False
    if session.get('user_id') and author and session['user_id'] != author['id']:
        followed = conn.execute(
            'SELECT 1 FROM follows WHERE follower_id = ? AND followed_id = ?',
            (session['user_id'], author['id'])
        ).fetchone() is not None

    tags = conn.execute('SELECT name FROM tags WHERE post_id = ?', (post_id,)).fetchall()

    favorited = conn.execute('SELECT 1 FROM favorites WHERE post_id = ? AND user_id = ?', (post_id, session.get('user_id', 0))).fetchone() is not None

    favorite_count = conn.execute('SELECT COUNT(*) FROM favorites WHERE post_id = ?', (post_id,)).fetchone()[0]

    repost_count = conn.execute('SELECT COUNT(*) FROM reposts WHERE original_post_id = ?', (post_id,)).fetchone()[0]

    comment_count = conn.execute('SELECT COUNT(*) FROM comments WHERE post_id = ?', (post_id,)).fetchone()[0]

    if request.method == 'POST':
        if 'user_id' not in session:
            flash('请先登录后评论')
            return redirect(url_for('login'))
        content = request.form.get('content', '').strip()
        parent_id = request.form.get('parent_id')
        image = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image = filename
        if not content and not image:
            flash('评论不能为空！！！')
        else:
            conn.execute('INSERT INTO comments(post_id, user_id, content, parent_id, image) VALUES (?, ?, ?, ?, ?)',
                         (post_id, session['user_id'], content, parent_id, image))
            conn.commit()
            # 通知作者或被回复者
            if parent_id:
                parent_comment = conn.execute('SELECT user_id FROM comments WHERE id = ?', (parent_id,)).fetchone()
                if parent_comment and parent_comment['user_id'] != session['user_id']:
                    conn.execute('INSERT INTO notifications (user_id, message) VALUES (?, ?)',
                                 (parent_comment['user_id'], f"{session['username']} 回复了你的评论"))
                    conn.commit()
            elif post['author_id'] != session['user_id']:
                conn.execute('INSERT INTO notifications (user_id, message) VALUES (?, ?)',
                             (post['author_id'], f"{session['username']} 评论了你的文章 '{post['title']}'"))
                conn.commit()
            flash('评论成功')
            return redirect(url_for('post', post_id=post_id))
    comments = conn.execute('''
                SELECT c.*, u.username, u.avatar FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = ? AND c.parent_id IS NULL
                order by c.created DESC
            ''', (post_id,)).fetchall()
    current_user_id_for_like: Any = session.get('user_id', 0)
    enriched_comments: list[dict[str, Any]] = []
    for comment_row in comments:
        comment: dict[str, Any] = dict(comment_row)
        replies = conn.execute('''
            SELECT c.*, u.username, u.avatar FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.parent_id = ?
            ORDER BY c.created ASC
        ''', (comment['id'],)).fetchall()
        comment_replies: list[dict[str, Any]] = []
        for reply_row in replies:
            reply: dict[str, Any] = dict(reply_row)
            reply['like_count'] = conn.execute(
                'SELECT COUNT(*) FROM comment_likes WHERE comment_id = ?',
                (reply['id'],)
            ).fetchone()[0]
            reply['liked'] = conn.execute(
                'SELECT 1 FROM comment_likes WHERE comment_id = ? AND user_id = ?',
                (reply['id'], current_user_id_for_like)
            ).fetchone() is not None
            reply['reply_count'] = 0
            comment_replies.append(reply)

        comment['replies'] = comment_replies
        comment['like_count'] = conn.execute('SELECT COUNT(*) FROM comment_likes WHERE comment_id = ?', (comment['id'],)).fetchone()[0]
        comment['liked'] = conn.execute('SELECT 1 FROM comment_likes WHERE comment_id = ? AND user_id = ?', (comment['id'], current_user_id_for_like)).fetchone() is not None
        comment['reply_count'] = len(comment_replies)
        enriched_comments.append(comment)
    conn.close()
    return render_template('post.html', post=post, comments=enriched_comments, like_count=like_count, author=author, tags=tags, favorited=favorited, repost_count=repost_count, comment_count=comment_count, favorite_count=favorite_count, followed=followed)


@app.route('/posts/new', methods=['GET', 'POST'])
@login_required
def new():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        tags = request.form.get('tags', '').split(',')
        author_id = session.get('user_id')

        # 处理图片上传
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                img_url = url_for('static', filename='uploads/' + filename)
                content += f'<img src="{img_url}" alt="图片" style="max-width: 100%;">'

        if not title:
            flash('标题不能为空！！！')
        elif not content:
            flash('内容不能为空！！！')
        else:
            conn = get_db_conn()
            conn.execute('insert into posts (title, content, author_id) values (?, ?, ?)', (title, content, author_id))
            conn.commit()
            post_id = conn.execute('select id from posts where title = ?', (title,)).fetchone()[0]
            for tag in tags:
                tag = tag.strip()
                if tag:
                    conn.execute('INSERT INTO tags (name, post_id) VALUES (?, ?)', (tag, post_id))
            conn.commit()
            conn.close()
            flash('文章上传成功！！！')
            return redirect(url_for('post', post_id=post_id))

    return render_template('new.html')

@app.route('/posts/<int:post_id>/edit', methods=('GET', 'POST'))
@login_required
def edit(post_id):
    post = get_post(post_id)
    if post is None:
        flash('文章不存在')
        return redirect(url_for('index'))

    if post['author_id'] != session.get('user_id') and not session.get('is_admin'):
        flash('没有编辑权限!!!')
        return redirect(url_for('post', post_id=post_id))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        tags = request.form.get('tags', '').split(',')

        # 处理图片上传
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                img_url = url_for('static', filename='uploads/' + filename)
                content += f'<img src="{img_url}" alt="图片" style="max-width: 100%;">'

        if not title:
            flash('标题不能为空！！！')
        elif not content:
            flash('内容不能为空！！！')
        else:
            conn = get_db_conn()
            conn.execute('update posts set title = ?, content = ? where id = ?',
                         (title, content, post_id))
            conn.execute('DELETE FROM tags WHERE post_id = ?', (post_id,))
            for tag in tags:
                tag = tag.strip()
                if tag:
                    conn.execute('INSERT INTO tags (name, post_id) VALUES (?, ?)', (tag, post_id))
            conn.commit()
            conn.close()
            flash('修改成功！！！')
            return redirect(url_for('post', post_id=post_id))

    conn = get_db_conn()
    tags = conn.execute('SELECT name FROM tags WHERE post_id = ?', (post_id,)).fetchall()
    conn.close()
    tag_string = ', '.join([tag['name'] for tag in tags])
    return render_template('edit.html', post=post, tags=tag_string)

@app.route('/posts/<int:post_id>/delete', methods=['POST',])
@login_required
def delete(post_id):
    post = get_post(post_id)
    if post is None:
        flash('文章不存在')
        return redirect(url_for('index'))

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
        # 通知作者
        post = conn.execute('SELECT author_id, title FROM posts WHERE id = ?', (post_id,)).fetchone()
        if post['author_id'] != session['user_id']:
            conn.execute('INSERT INTO notifications (user_id, message) VALUES (?, ?)',
                         (post['author_id'], f"{session['username']} 点赞了你的文章 '{post['title']}'"))
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

    followings = conn.execute('''
        SELECT u.id, u.username
        FROM follows f
        JOIN users u ON f.followed_id = u.id
        WHERE f.follower_id = ?
    ''', (user_id,)).fetchall()

    followers = conn.execute('''
        SELECT u.id, u.username
        FROM follows f
        JOIN users u ON f.follower_id = u.id
        WHERE f.followed_id = ?
    ''', (user_id,)).fetchall()

    conn.close()
    return render_template('personal.html', user = user, posts=posts, comments=comments, likes=likes, followings=followings, followers=followers)

@app.route('/change_password', methods=['POST', 'GET'])
@login_required
def change_password():
    user_id = session.get('user_id')
    conn = get_db_conn()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if request.method == 'POST':
        old_pw = request.form['old_password']
        new_pw = request.form['new_password']
        confirm_pw = request.form['confirm_password']

        #验证原密码
        if not check_password_hash(user['password'], old_pw):
            flash('原密码错误！')
        elif new_pw != confirm_pw:
            flash('两次输入的密码不一致！')
        else:
            hashed_pw = generate_password_hash(new_pw)
            conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_pw, user_id))
            conn.commit()
            flash('密码修改成功，请重新登录')
            conn.close()
            session.clear()
            return redirect(url_for('login'))

    conn.close()
    return render_template('change_password.html')

@app.route('/follow/<int:user_id>', methods=['POST'])
@login_required
def follow(user_id):
    current_user_id = session['user_id']
    if current_user_id == user_id:
        flash('不能关注自己！')
        return redirect(request.referrer or url_for('personal'))
    conn = get_db_conn()
    try:
        conn.execute('INSERT INTO follows (follower_id, followed_id) VALUES (?, ?)',
                     (current_user_id, user_id))
        conn.commit()
        # 通知被关注者
        conn.execute('INSERT INTO notifications (user_id, message) VALUES (?, ?)',
                     (user_id, f"{session['username']} 关注了你"))
        conn.commit()
        flash('关注成功！')
    except sqlite3.IntegrityError:
        flash('你已经关注过这个用户了！')
    finally:
        conn.close()
    return redirect(request.referrer or url_for('personal'))

@app.route('/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow(user_id):
    current_user_id = session['user_id']
    conn = get_db_conn()
    conn.execute('DELETE FROM follows WHERE follower_id = ? AND followed_id = ?',
                 (current_user_id, user_id))
    conn.commit()
    conn.close()
    flash('取消关注成功！')
    return redirect(request.referrer or url_for('personal'))

@app.route('/user/<int:user_id>')
@login_required
def view_user(user_id):
    conn = get_db_conn()
    user = conn.execute('SELECT *FROM users WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        conn.close()
        flash('用户不存在')
        return redirect(url_for('index'))

    posts = conn.execute('SELECT * FROM posts WHERE author_id = ?', (user_id,)).fetchall()

    followed = conn.execute(
        'SELECT 1 FROM follows WHERE follower_id = ? AND followed_id = ?', (session['user_id'], user_id)
    ).fetchone() is not None

    conn.close()
    return render_template('user.html', user=user, posts=posts, followed=followed)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    if not query:
        flash('请输入搜索关键词')
        return redirect(url_for('index'))
    conn = get_db_conn()
    posts = conn.execute("SELECT * FROM posts WHERE title LIKE ? OR content LIKE ? ORDER BY created DESC",
                         ('%' + query + '%', '%' + query + '%')).fetchall()
    conn.close()
    return render_template('index.html', posts=posts, search_query=query)

@app.route('/notifications')
@login_required
def notifications():
    conn = get_db_conn()
    user_id = session['user_id']
    notifications = conn.execute('SELECT * FROM notifications WHERE user_id = ? ORDER BY created DESC', (user_id,)).fetchall()
    conn.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return render_template('notifications.html', notifications=notifications)

@app.route('/repost/<int:post_id>', methods=['POST'])
@login_required
def repost(post_id):
    conn = get_db_conn()
    try:
        conn.execute('INSERT INTO reposts (original_post_id, user_id) VALUES (?, ?)', (post_id, session['user_id']))
        conn.commit()
        flash('转发成功！')
    except sqlite3.IntegrityError:
        flash('你已经转发过这篇文章了！')
    finally:
        conn.close()
    return redirect(url_for('post', post_id=post_id))

@app.route('/upload_avatar', methods=['GET', 'POST'])
@login_required
def upload_avatar():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('没有文件')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('没有选择文件')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            conn = get_db_conn()
            conn.execute('UPDATE users SET avatar = ? WHERE id = ?', (filename, session['user_id']))
            conn.commit()
            conn.close()
            flash('头像上传成功')
            return redirect(url_for('personal'))
        else:
            flash('文件类型不允许')
            return redirect(request.url)
    return render_template('upload_avatar.html')

@app.route('/favorite/<int:post_id>', methods=['POST'])
@login_required
def favorite(post_id):
    conn = get_db_conn()
    try:
        conn.execute('INSERT INTO favorites(post_id, user_id) VALUES (?, ?)', (post_id, session['user_id']))
        conn.commit()
        flash('收藏成功！')
    except sqlite3.IntegrityError:
        flash('你已经收藏过这篇文章了！')
    finally:
        conn.close()
    return redirect(url_for('post', post_id=post_id))

@app.route('/like_comment/<int:comment_id>', methods=['POST'])
@login_required
def like_comment(comment_id):
    conn = get_db_conn()
    try:
        conn.execute('INSERT INTO comment_likes(comment_id, user_id) VALUES (?, ?)', (comment_id, session['user_id']))
        conn.commit()
        flash('点赞评论成功！')
    except sqlite3.IntegrityError:
        flash('你已经点赞过这条评论了！')
    finally:
        conn.close()
    return redirect(request.referrer or url_for('index'))

@app.route('/messages')
@login_required
def messages():
    conn = get_db_conn()
    user_id = session['user_id']
    # 获取最近联系的用户
    contacts = conn.execute('''
        SELECT DISTINCT u.id, u.username, u.avatar,
               (SELECT content FROM messages WHERE (sender_id = u.id AND receiver_id = ?) OR (sender_id = ? AND receiver_id = u.id) ORDER BY created DESC LIMIT 1) as last_message,
               (SELECT created FROM messages WHERE (sender_id = u.id AND receiver_id = ?) OR (sender_id = ? AND receiver_id = u.id) ORDER BY created DESC LIMIT 1) as last_time
        FROM users u
        JOIN messages m ON (m.sender_id = u.id OR m.receiver_id = u.id)
        WHERE (m.sender_id = ? OR m.receiver_id = ?) AND u.id != ?
        GROUP BY u.id
        ORDER BY last_time DESC
    ''', (user_id, user_id, user_id, user_id, user_id, user_id, user_id)).fetchall()
    conn.close()
    return render_template('messages.html', contacts=contacts)

@app.route('/send_message/<int:user_id>', methods=['GET', 'POST'])
@login_required
def send_message(user_id):
    if user_id == session['user_id']:
        flash('不能给自己发送私信')
        return redirect(url_for('messages'))

    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash('内容不能为空')
            return redirect(url_for('send_message', user_id=user_id))
        conn = get_db_conn()
        conn.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)',
                     (session['user_id'], user_id, content))
        conn.commit()
        conn.close()
        flash('私信发送成功')
        return redirect(url_for('send_message', user_id=user_id))
    conn = get_db_conn()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        conn.close()
        flash('用户不存在')
        return redirect(url_for('messages'))

    contacts = conn.execute('''
        SELECT DISTINCT u.id, u.username, u.avatar,
               (SELECT content FROM messages WHERE (sender_id = u.id AND receiver_id = ?) OR (sender_id = ? AND receiver_id = u.id) ORDER BY created DESC LIMIT 1) as last_message,
               (SELECT created FROM messages WHERE (sender_id = u.id AND receiver_id = ?) OR (sender_id = ? AND receiver_id = u.id) ORDER BY created DESC LIMIT 1) as last_time
        FROM users u
        JOIN messages m ON (m.sender_id = u.id OR m.receiver_id = u.id)
        WHERE (m.sender_id = ? OR m.receiver_id = ?) AND u.id != ?
        GROUP BY u.id
        ORDER BY last_time DESC
    ''', (session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id'], session['user_id'])).fetchall()

    # Ensure the active chat user is visible in sidebar even without prior messages.
    contact_ids = {row['id'] for row in contacts}
    if user['id'] not in contact_ids:
        current_contact = {
            'id': user['id'],
            'username': user['username'],
            'avatar': user['avatar'],
            'last_message': '',
            'last_time': ''
        }
        contacts = [current_contact] + [dict(row) for row in contacts]

    # 获取与该用户的消息历史
    messages = conn.execute('''
        SELECT m.*, u.username as sender_username
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?) OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.created ASC
    ''', (session['user_id'], user_id, user_id, session['user_id'])).fetchall()
    conn.close()
    return render_template('send_message.html', user=user, messages=messages, contacts=contacts)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
