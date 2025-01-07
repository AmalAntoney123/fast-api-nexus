from fastapi import FastAPI, HTTPException
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db
from appwrite.client import Client
from appwrite.services.storage import Storage
import requests
import PyPDF2
from pydantic import BaseModel
import json

# Load environment variables from .env file
load_dotenv()

# Debug: Print all environment variables
print("Available environment variables:", [key for key in os.environ.keys()])

# Initialize FastAPI
app = FastAPI()

# Initialize Firebase Admin with better error handling
private_key = os.environ.get("FIREBASE_PRIVATE_KEY")
if private_key:
    # Check if the key is already properly formatted (has actual newlines)
    if "-----BEGIN PRIVATE KEY-----\n" in private_key:
        # Key is already properly formatted, use as is
        pass
    else:
        # Key needs newline conversion
        private_key = private_key.replace('\\n', '\n')

cred_dict = {
    "type": "service_account",
    "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
    "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": private_key,
    "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
    "auth_uri": os.environ.get("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
    "token_uri": os.environ.get("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
    "auth_provider_x509_cert_url": os.environ.get("FIREBASE_AUTH_PROVIDER_CERT_URL", "https://www.googleapis.com/oauth2/v1/certs"),
    "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL")
}

# Debug: Print the actual private key format
print("Private key format check:")
print("First line:", private_key.split("\n")[0] if private_key else "No private key found")
print("Number of lines:", len(private_key.split("\n")) if private_key else 0)

if not private_key:
    raise ValueError("FIREBASE_PRIVATE_KEY environment variable is not set!")

try:
    cred = credentials.Certificate(cred_dict)
except ValueError as e:
    print("Error initializing Firebase credentials:", str(e))
    print("Private key starts with:", private_key[:50] if private_key else "None")
    raise

firebase_admin.initialize_app(cred, {
    'databaseURL': os.environ.get('FIREBASE_DATABASE_URL', 'https://magazine-nexus-default-rtdb.asia-southeast1.firebasedatabase.app')
})

# Initialize Appwrite
client = Client()
client.set_endpoint('https://cloud.appwrite.io/v1')
client.set_project('676fc20b003ccf154826')
client.set_key('standard_9dda74e82e65484c8a2a3140109bdfca83795e99028d68491edf78d6b19a10e008e35df1926856d3419bdda3c6fd56379805d352656cc3595a9e02219c991d00efdcb5dc5b9ca68f2093e3cc5e3474140df7eaa3a86a6b77acb6a510ad2d4972f8a266b7e1faa9beca33500fdf2367ce3db72463f795aa9ba9164a6737cd5f8f')
storage = Storage(client)

class SearchResult(BaseModel):
    magazine_id: str
    magazine_title: str
    file_id: str
    page_number: int
    line_number: int
    context: str
    issue_id: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_matches: int

def download_magazine(bucket_id: str, file_id: str, filename: str) -> bool:
    """Download a single magazine if it doesn't exist locally"""
    magazines_dir = "magazines"
    if not os.path.exists(magazines_dir):
        os.makedirs(magazines_dir)
    
    file_path = os.path.join(magazines_dir, filename)
    if os.path.exists(file_path):
        return False  # Magazine already exists
    
    download_url = f"{client._endpoint}/storage/buckets/{bucket_id}/files/{file_id}/download?project={client.get_project()}"
    
    response = requests.get(download_url)
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return True  # Successfully downloaded
    return False

def sync_magazines() -> Dict[str, int]:
    """Sync magazines from Firebase/Appwrite and return stats"""
    stats = {"new_downloads": 0, "total_magazines": 0}
    
    try:
        magazines_ref = db.reference('magazines')
        magazine_issues_ref = db.reference('magazine_issues')
        
        magazines_data = magazines_ref.get()
        magazine_issues_data = magazine_issues_ref.get()
        
        if not magazine_issues_data:
            return stats
        
        stats["total_magazines"] = len(magazine_issues_data)
        
        for issue_id, issue_data in magazine_issues_data.items():
            if 'pdfFileId' in issue_data and issue_data['pdfFileId']:
                filename = f"{issue_data['magazineId']}_{issue_data['issueNumber']}.pdf"
                if download_magazine(
                    bucket_id='67718396003a69711df7',
                    file_id=issue_data['pdfFileId'],
                    filename=filename
                ):
                    stats["new_downloads"] += 1
                    
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def search_pdfs(keyword: str) -> List[SearchResult]:
    """Search for keyword in PDFs and return results"""
    results = []
    magazines_dir = "magazines"
    keyword = keyword.lower().strip()
    
    # Get Firebase data for magazine details
    magazines_data = db.reference('magazines').get()
    magazine_issues_data = db.reference('magazine_issues').get()
    
    if not os.path.exists(magazines_dir):
        return results
    
    magazine_titles = {id: data['title'] for id, data in magazines_data.items()}
    
    # Create a mapping of magazine_id_issue_number to issue data
    issue_mapping = {
        f"{issue['magazineId']}_{issue['issueNumber']}": {
            'issue_id': issue_id,
            'file_id': issue['pdfFileId']
        }
        for issue_id, issue in magazine_issues_data.items()
        if 'pdfFileId' in issue
    }
    
    for filename in os.listdir(magazines_dir):
        if not filename.endswith('.pdf'):
            continue
            
        magazine_id = filename.split('_')[0]
        issue_number = filename.split('_')[1].replace('.pdf', '')
        magazine_title = magazine_titles.get(magazine_id, "Unknown Magazine")
        
        # Get the issue data from our mapping
        issue_data = issue_mapping.get(f"{magazine_id}_{issue_number}", {
            'issue_id': 'unknown',
            'file_id': 'unknown'
        })
        
        try:
            with open(os.path.join(magazines_dir, filename), 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num in range(len(pdf_reader.pages)):
                    text = pdf_reader.pages[page_num].extract_text()
                    text_lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    for line_num, line in enumerate(text_lines):
                        if keyword in line.lower():
                            results.append(SearchResult(
                                magazine_id=magazine_id,
                                magazine_title=magazine_title,
                                file_id=issue_data['file_id'],
                                page_number=page_num + 1,
                                line_number=line_num + 1,
                                context=line.strip(),
                                issue_id=issue_data['issue_id']
                            ))
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
    
    return results

@app.get("/sync")
async def sync_endpoint():
    """Endpoint to sync magazines"""
    stats = sync_magazines()
    return {
        "status": "success",
        "new_downloads": stats["new_downloads"],
        "total_magazines": stats["total_magazines"]
    }

@app.get("/search/{keyword}", response_model=SearchResponse)
async def search_endpoint(keyword: str):
    """Endpoint to search magazines"""
    # First sync to get any new magazines
    sync_magazines()
    
    # Then perform the search
    results = search_pdfs(keyword)
    
    # Ensure the response matches our model
    response = SearchResponse(
        results=results,
        total_matches=len(results)
    )
    
    print("Response data:", response.dict())  # Debug print
    return response

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)