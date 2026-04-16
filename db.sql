DROP TABLE IF EXISTS users;
CREATE TABLE users
(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    avatar TEXT
);


DROP TABLE IF EXISTS posts;
CREATE TABLE posts
(
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title   TEXT      NOT NULL,
    content TEXT      NOT NULL,
    author_id INTEGER,
    FOREIGN KEY (author_id) REFERENCES users(id)
);

DROP TABLE IF EXISTS comments;
CREATE TABLE comments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    image TEXT,
    parent_id INTEGER REFERENCES comments(id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

DROP TABLE IF EXISTS likes;
CREATE TABLE likes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    UNIQUE(post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS follows(
    follower_id INTEGER NOT NULL,
    followed_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (follower_id, followed_id),
    FOREIGN KEY (follower_id) REFERENCES users (id),
    FOREIGN KEY (followed_id) REFERENCES users (id)
);

DROP TABLE IF EXISTS tags;
CREATE TABLE tags(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    post_id INTEGER NOT NULL,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);

DROP TABLE IF EXISTS notifications;
CREATE TABLE notifications(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

DROP TABLE IF EXISTS reposts;
CREATE TABLE reposts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (original_post_id) REFERENCES posts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

DROP TABLE IF EXISTS favorites;
CREATE TABLE favorites(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    UNIQUE(post_id, user_id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

DROP TABLE IF EXISTS comment_likes;
CREATE TABLE comment_likes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    comment_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    UNIQUE(comment_id, user_id),
    FOREIGN KEY (comment_id) REFERENCES comments(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

DROP TABLE IF EXISTS messages;
CREATE TABLE messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0,
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id)
);
