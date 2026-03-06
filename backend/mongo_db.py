import os
from mongoengine import connect

def init_mongodb(app=None):
    """
    Initialize MongoDB using the MONGODB_URI from the environment.
    """
    mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/resume-analyzer")
    # Connect using MongoEngine
    connect(host=mongo_uri)
    print(f"[DB] MongoDB connected via MongoEngine ({mongo_uri})")
