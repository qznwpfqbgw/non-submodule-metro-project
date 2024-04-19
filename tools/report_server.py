from flask import Flask, request, jsonify
import sqlite3
import argparse

app = Flask(__name__)

# FIXME: Don't use variable worker_id to assign id
worker_id = 0

@app.route('/register', methods=['POST'])
def register_worker():
    global worker_id
    data = request.json
    if 'config' in data and 'time' in data:
        config = data['config']
        time = data['time']
        cursor.execute("INSERT INTO worker (id, config, created_at) VALUES (?,?,?)", (worker_id, config, time))
        conn.commit()
        worker_id += 1
        return jsonify({'id': worker_id - 1}), 201
    else:
        return jsonify({'error': 'Missing parameter: config, time'}), 400

@app.route('/report', methods=['POST'])
def receive_report():
    data = request.json
    print(data)
    if 'id' in data and 'msg' in data and 'time' in data:
        worker_id = data['id']
        content = data['msg']
        time = data['time']
        cursor.execute("INSERT INTO data (user_id, content, created_at) VALUES (?,?,?)", (worker_id, content, time))
        conn.commit()
        return jsonify({'message': 'success'}), 201
    else:
        return jsonify({'error': 'Missing parameters: id or message'}), 400

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=str, help="server port", required=True)
    parser.add_argument("-d", "--db", type=str, help="sqlite db", required=True)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS `worker` (
    `id` integer PRIMARY KEY,
    `config` TEXT,
    `created_at` timestamp
    );
    ''')
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS `data` (
    `id` integer PRIMARY KEY AUTOINCREMENT,
    `content` TEXT,
    `user_id` integer,
    `created_at` timestamp,
    FOREIGN KEY (`user_id`) REFERENCES `worker` (`id`)
    );
    """)
    conn.commit()
    
    app.run(port=args.port)

