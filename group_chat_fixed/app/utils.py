import bcrypt
import random

def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

ADJECTIVES = ["Clever", "Brave", "Swift", "Silent", "Fierce", "Happy", "Lucky", "Mighty", "Wild"]
ANIMALS = ["Fox", "Eagle", "Bear", "Wolf", "Tiger", "Lion", "Hawk", "Owl", "Panther"]

def generate_anonymous_username():
    """Generates a random username like Clever_Fox_1234"""
    adj = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    number = random.randint(1000, 9999)
    return f"{adj}_{animal}_{number}"
