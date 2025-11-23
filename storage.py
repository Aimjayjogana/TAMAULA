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
                result = cloudinary.uploader.upload(
                    file,
                    folder=folder,
                    public_id=filename.rsplit('.', 1)[0],
                    overwrite=True,
                    resource_type="image",
                    format="webp"
                )
                return result['secure_url']
            except Exception as e:
                print(f"❌ Cloudinary upload failed: {e}")

        # FIXED: Consistent path for all uploads
        upload_folder = os.path.join('static', 'images', 'uploads', folder)
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        
        # Return consistent URL path
        return f"/static/images/uploads/{folder}/{filename}"

storage = CloudinaryStorage()