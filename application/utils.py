import logging
from pymongo import MongoClient

#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 定义MongoDB数据库连接URL
mongo_url = "mongodb://127.0.0.1:27017/"

# 全局变量，用于保存 MongoDB 连接
client = None

# 全局变量，用于保存用户信息
users = []

def connect_to_mongodb():
    global client
    try:
        # 连接到MongoDB数据库
        client = MongoClient(mongo_url)
        logging.debug("Connected to MongoDB successfully")
        return client
    except Exception as e:
        logging.error(f"Error connecting to MongoDB: {e}")
        return None

def close_mongodb_connection():
    global client
    if client:
        client.close()
        logging.debug("MongoDB connection closed")

def read_mongo_data(collection):
    try:
        data = list(collection.find({}, {"_id": 0}))  # 不返回_id字段
        logging.debug(f"Read {len(data)} documents from collection {collection.name}")
        return data if data else []
    except Exception as e:
        logging.error(f"Error reading from MongoDB collection {collection.name}: {e}")
        return []

def write_mongo_data(collection, data):
    try:
        # 插入或更新数据
        result = collection.insert_one(data)
        logging.debug(f"Data saved to collection {collection.name}, inserted_id: {result.inserted_id}")
        return True
    except Exception as e:
        logging.error(f"Error writing to MongoDB collection {collection.name}: {e}")
        return False

def register_user(username, password):
    global users
    try:
        # 检查用户名是否已存在
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            logging.debug(f"User {username} already exists")
            return False
        
        # 插入新用户数据
        user_data = {"username": username, "password": password}
        users_collection.insert_one(user_data)
        logging.debug(f"User {username} registered successfully")
        
        # 更新 users 列表
        users = read_mongo_data(users_collection)
        
        return True
    except Exception as e:
        logging.error(f"Error writing to MongoDB collection users: {e}")
        return False

# 在程序启动时连接 MongoDB
connect_to_mongodb()

# 选择数据库和集合
if client:
    db = client['BackTest']
    users_collection = db['users']
    questions_collection = db['questions']
    questions_train_collection = db['questions_train']
    save_collection = db['save']
    deliver_score_collection = db['deliver_score']
    deliver_score_train_collection = db['deliver_score_train']
    images_collection = db['images']
    aiTips_collection = db['aiTips']
    userinfo_collection = db['userinfo']
    doctor_patient_collection = db['doctor_patient']

    # 从MongoDB中读取
    users = read_mongo_data(users_collection)
    questions = read_mongo_data(questions_collection)
    questions_train = read_mongo_data(questions_train_collection)
    aiTips = read_mongo_data(aiTips_collection)
