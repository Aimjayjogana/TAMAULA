# storage.py
import cloudinary
import cloudinary.uploader
import os
from flask import current_app

class CloudinaryStorage:
    def __init__(self):
        self.enabled = False

    def init_app(self, app):
        # Only activate Cloudinary if all credentials are present
        if (os.getenv('CLOUDINARY_CLOUD_NAME') and 
            os.getenv('CLOUDINARY_API_KEY') and 
            os.getenv('CLOUDINARY_API_SECRET')):
            
            cloudinary.config(
                cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
                api_key=os.getenv('CLOUDINARY_API_KEY'),
                api_secret=os.getenv('CLOUDINARY_API_SECRET'),
                secure=True
            )
            self.enabled = True
            print("✅ Cloudinary connected successfully!")
        else:
            print("⚠️ Cloudinary not configured → using local storage fallback")

    def upload_file(self, file, filename, folder='uploads'):
        if self.enabled and file:
            try:
                # Cloudinary does everything: resize, optimize, CDN
                result = cloudinary.uploader.upload(
                    file,
                    folder=folder,
                    public_id=filename.rsplit('.', 1)[0],  # remove extension
                    overwrite=True,
                    resource_type="image",
                    format="webp"  # optional: forces modern format
                )
                return result['secure_url']  # e.g. https://res.cloudinary.com/.../uploads/photo123.webp
            except Exception as e:
                print(f"❌ Cloudinary upload failed: {e}")

        # ───── FALLBACK TO LOCAL (same as your old code) ─────
        upload_folder = os.path.join('static', 'uploads', folder)
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        return f"/static/uploads/{folder}/{filename}"

# Keep the same name your app expects
storage = CloudinaryStorage()