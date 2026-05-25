import sys
print("Starting debug")
try:
    print("Importing models")
    from app import models
    print("Importing database")
    from app import database
    print("Creating tables")
    models.Base.metadata.create_all(bind=database.engine)
    print("Tables created")
    print("Importing main")
    from app import main
    print("Main imported")
except Exception as e:
    print("Error:", e)
