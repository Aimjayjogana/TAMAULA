# storage.py
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os

class CloudinaryStorage:
    def __init__(self):
        self.enabled = True  # Always enabled

    def init_app(self, app):
        # Direct credentials - no environment variables
        try:
            cloudinary.config(
                cloud_name="dvhcuyp6q",
                api_key="181853534191746", 
                api_secret="TAchVYlNJdWkhQMqqsQ7UEXFTCM",
                secure=True
            )
            # Test the connection
            cloudinary.api.ping()
            print("✅ Cloudinary connected and tested successfully!")
            self.enabled = True
        except Exception as e:
            print(f"❌ Cloudinary failed: {e}")
            self.enabled = False

    def upload_file(self, file, filename, folder='uploads'):
        if not file:
            return None
            
        try:
            # Reset file pointer
            if hasattr(file, 'seek'):
                file.seek(0)
            
            print(f"🔄 Uploading {filename} to Cloudinary folder: {folder}")
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file,
                public_id=f"{folder}/{filename}",
                overwrite=True,
                resource_type="auto"
            )
            
            cloudinary_url = result['secure_url']
            print(f"✅ Upload successful: {cloudinary_url}")
            return cloudinary_url
            
        except Exception as e:
            print(f"❌ Cloudinary upload failed: {e}")
            return None

storage = CloudinaryStorage()