# storage.py
import cloudinary
import cloudinary.uploader
import os

class CloudinaryStorage:
    def __init__(self):
        self.enabled = False

    def init_app(self, app):
        # FIXED: Direct credentials - no environment variables needed
        cloud_name = "tamaula-photos"
        api_key = "181853534191746"
        api_secret = "TAchVYlNJdWkhQMqqsQ7UEXFTCM"
        
        # Always enable Cloudinary with direct credentials
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        self.enabled = True
        print("✅ Cloudinary connected with direct credentials!")

    def upload_file(self, file, filename, folder='uploads'):
        if file and file.filename:
            try:
                # Reset file pointer
                if hasattr(file, 'seek'):
                    file.seek(0)
                
                print(f"🔄 Uploading to Cloudinary: {filename} in folder {folder}")
                    
                result = cloudinary.uploader.upload(
                    file,
                    folder=folder,
                    public_id=filename,
                    overwrite=True,
                    resource_type="auto"
                )
                print(f"✅ Cloudinary upload successful: {result['secure_url']}")
                return result['secure_url']
            except Exception as e:
                print(f"❌ Cloudinary upload failed: {e}")
                # Return None to use default image
                return None
        
        return None

storage = CloudinaryStorage()