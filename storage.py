import boto3
import os
from flask import current_app
from werkzeug.utils import secure_filename

class CloudflareR2Storage:
    def _init_(self):
        self.s3_client = None
        
    def init_app(self, app):
        """Initialize the storage with app configuration"""
        try:
            # Only initialize if R2 credentials are available
            if all([os.getenv('R2_ACCESS_KEY'), os.getenv('R2_SECRET_KEY'), os.getenv('R2_ENDPOINT')]):
                self.s3_client = boto3.client('s3',
                    endpoint_url=os.getenv('R2_ENDPOINT'),
                    aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
                    aws_secret_access_key=os.getenv('R2_SECRET_KEY'),
                    region_name='auto'
                )
                self.bucket_name = os.getenv('R2_UPLOADS_BUCKET', 'tamaula-uploads')
                print("✅ Cloudflare R2 storage initialized")
            else:
                print("⚠️  R2 credentials not found, using local storage")
                self.s3_client = None
        except Exception as e:
            print(f"❌ R2 Storage initialization failed: {e}")
            self.s3_client = None
    
    def upload_file(self, file, filename, folder='uploads'):
        """Upload file to Cloudflare R2 or fallback to local storage"""
        if self.s3_client and self.bucket_name:
            # Upload to Cloudflare R2
            try:
                key = f"{folder}/{filename}"
                self.s3_client.upload_fileobj(
                    file,
                    self.bucket_name,
                    key,
                    ExtraArgs={'ContentType': file.content_type}
                )
                # Return public URL (you'll need to set up public access in R2)
                account_id = os.getenv('R2_ACCOUNT_ID', 'your-account-id')
                return f"https://pub.{account_id}.r2.dev/{key}"
            except Exception as e:
                print(f"❌ R2 upload failed: {e}")
                return self._fallback_upload(file, filename, folder)
        else:
            # Fallback to local storage
            return self._fallback_upload(file, filename, folder)
    
    def _fallback_upload(self, file, filename, folder):
        """Fallback to local file system storage"""
        try:
            upload_folder = f"static/uploads/{folder}"
            os.makedirs(upload_folder, exist_ok=True)
            file_path = f"{upload_folder}/{filename}"
            file.save(file_path)
            return f"/{file_path}"
        except Exception as e:
            print(f"❌ Local upload failed: {e}")
            return None

# Create storage instance
storage = CloudflareR2Storage()