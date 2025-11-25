# storage.py
import cloudinary
import cloudinary.uploader
import os

class CloudinaryStorage:
    def __init__(self):
        self.enabled = False

    def init_app(self, app):
        # FIXED: Use correct environment variable names
        cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME')
        api_key = os.getenv('CLOUDINARY_API_KEY')
        api_secret = os.getenv('CLOUDINARY_API_SECRET')
        
        # Only activate Cloudinary if all credentials are present
        if cloud_name and api_key and api_secret:
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )
            self.enabled = True
            print("✅ Cloudinary connected successfully!")
        else:
            print("⚠️ Cloudinary not configured → using local storage fallback")

    def upload_file(self, file, filename, folder='uploads'):
        if self.enabled and file:
            try:
                # Reset file pointer
                if hasattr(file, 'seek'):
                    file.seek(0)
                    
                result = cloudinary.uploader.upload(
                    file,
                    folder=folder,
                    public_id=filename.rsplit('.', 1)[0],
                    overwrite=True,
                    resource_type="auto"  # Changed to "auto" for all file types
                )
                return result['secure_url']
            except Exception as e:
                print(f"❌ Cloudinary upload failed: {e}")
                return None

        # If Cloudinary not enabled, return None to use default image
        return None

storage = CloudinaryStorage()