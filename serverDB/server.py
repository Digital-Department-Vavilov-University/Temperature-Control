from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timezone
import threading
import logging
import time

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
DB_NAME = 'temperature_data.db'
LOCK = threading.Lock()

def init_db():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER,  -- UNIX timestamp
                    offlineTemperature REAL,
                    onlineTemperature REAL,
                    isOpen INTEGER,
                    conditionCode INTEGER
                )
            ''')
            conn.commit()
            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.get_json()
        logger.debug(f"Received data: {data}")
        
        # Проверка обязательных полей
        required_fields = ['offlineTemperature', 'onlineTemperature', 'isOpen', 'conditionCode']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.error(f"Missing fields: {', '.join(missing_fields)}")
            return jsonify({'error': f'Missing fields: {", ".join(missing_fields)}'}), 400
        
        # Извлечение значений
        offline_temp = float(data['offlineTemperature'])
        online_temp = float(data['onlineTemperature'])
        is_open = bool(data['isOpen'])
        condition_code = int(data['conditionCode'])
        
        # Текущее время в UTC как UNIX timestamp
        utc_timestamp = int(datetime.now(timezone.utc).timestamp())
        
        logger.debug(f"Values: offline={offline_temp}, online={online_temp}, open={is_open}, code={condition_code}, timestamp={utc_timestamp}")
        
        # Сохранение в БД
        with LOCK:
            try:
                with sqlite3.connect(DB_NAME) as conn:
                    c = conn.cursor()
                    c.execute('''
                        INSERT INTO readings (
                            timestamp,
                            offlineTemperature, 
                            onlineTemperature, 
                            isOpen, 
                            conditionCode
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (
                        utc_timestamp,
                        offline_temp,
                        online_temp,
                        1 if is_open else 0,
                        condition_code
                    ))
                    conn.commit()
                    logger.info("Data saved to database")
                    
            except sqlite3.Error as e:
                logger.error(f"Database error: {str(e)}")
                return jsonify({'error': 'Database operation failed'}), 500
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='192.168.1.61', port=5000, threaded=True, debug=True)