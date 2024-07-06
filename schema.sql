CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    balance REAL NOT NULL DEFAULT 0,
    is_banned BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    balance REAL NOT NULL DEFAULT 0,
    is_admin BOOLEAN NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS donation_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    amount REAL NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    FOREIGN KEY (username) REFERENCES users(username)
);

INSERT OR IGNORE INTO admin_users (username, password, balance, is_admin) VALUES ('admin', 'admin', 10000000000000000.0, 1);
INSERT OR IGNORE INTO users (username, password, balance) VALUES ('testuser', 'password123', 1000.00);
