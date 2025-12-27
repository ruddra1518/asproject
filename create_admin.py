from werkzeug.security import generate_password_hash
from datetime import datetime
from database import get_container_from_env

teachers = get_container_from_env(container_name="teachers")

admin = {
    "id": "admin",
    "password_hash": generate_password_hash("admin123"),
    "role": "admin",
    "created_at": datetime.utcnow().isoformat()
}

teachers.upsert_item(admin)
print("✅ Admin user created successfully")
