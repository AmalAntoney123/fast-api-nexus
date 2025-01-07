import os
import firebase_admin
from firebase_admin import credentials, db
from appwrite.client import Client
from appwrite.services.storage import Storage
import requests
import PyPDF2
from typing import List, Dict

def init_firebase():
    """Initialize Firebase with credentials"""
    print("\n=== Initializing Firebase ===")
    try:
        cred = credentials.Certificate("magazine-nexus-firebase-adminsdk-6c4rw-a88283a8f9.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://magazine-nexus-default-rtdb.asia-southeast1.firebasedatabase.app'
        })
        print("✓ Firebase initialized successfully")
    except Exception as e:
        print(f"✗ Firebase initialization failed: {str(e)}")
        raise

def init_appwrite():
    """Initialize Appwrite client"""
    print("\n=== Initializing Appwrite ===")
    try:
        client = Client()
        client.set_endpoint('https://cloud.appwrite.io/v1')
        client.set_project('676fc20b003ccf154826')
        client.set_key('standard_9dda74e82e65484c8a2a3140109bdfca83795e99028d68491edf78d6b19a10e008e35df1926856d3419bdda3c6fd56379805d352656cc3595a9e02219c991d00efdcb5dc5b9ca68f2093e3cc5e3474140df7eaa3a86a6b77acb6a510ad2d4972f8a266b7e1faa9beca33500fdf2367ce3db72463f795aa9ba9164a6737cd5f8f')
        storage = Storage(client)
        
        print("✓ Appwrite initialized successfully")
        
        # Test the connection by trying to access storage info
        try:
            storage.list_files(bucket_id='67718396003a69711df7')
            print("✓ Storage access verified")
        except Exception as e:
            print(f"✗ Storage access failed: {str(e)}")
            raise
            
        return client, storage
    except Exception as e:
        print(f"✗ Appwrite initialization failed: {str(e)}")
        raise

def download_magazine(client, bucket_id, file_id, filename):
    """Download a single magazine if it doesn't exist locally"""
    print(f"\n=== Processing {filename} ===")
    
    # Create magazines directory
    magazines_dir = "magazines"
    if not os.path.exists(magazines_dir):
        print(f"Creating directory: {magazines_dir}")
        os.makedirs(magazines_dir)
    
    # Check if file exists
    file_path = os.path.join(magazines_dir, filename)
    if os.path.exists(file_path):
        print(f"✓ Magazine already exists at: {file_path}")
        return
    
    # Generate download URL
    project_id = '676fc20b003ccf154826'  # Your project ID
    download_url = f"{client._endpoint}/storage/buckets/{bucket_id}/files/{file_id}/download?project={project_id}"
    print(f"Download URL: {download_url}")
    
    # Download the file
    print("Downloading magazine...")
    response = requests.get(download_url)
    print(f"Response status code: {response.status_code}")
    
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            f.write(response.content)
            
        print(f"✓ Successfully downloaded to: {file_path}")
    else:
        print(f"✗ Download failed. Status code: {response.status_code}")
        print(f"Error response: {response.text}")

def search_pdfs(keyword: str, magazines_data: dict, magazine_issues_data: dict) -> List[Dict]:
    """
    Search for a keyword in all downloaded PDFs
    Returns a list of dictionaries containing file and page information
    Performs case-insensitive search and strips whitespace
    """
    print(f"\n=== Searching for '{keyword}' in PDFs ===")
    results = []
    magazines_dir = "magazines"
    
    # Clean the search keyword
    keyword = keyword.lower().strip()
    
    if not os.path.exists(magazines_dir):
        print("✗ No magazines directory found")
        return results
    
    # Create a mapping of magazine IDs to titles
    magazine_titles = {id: data['title'] for id, data in magazines_data.items()}
    
    # Search through each PDF in the magazines directory
    for filename in os.listdir(magazines_dir):
        if not filename.endswith('.pdf'):
            continue
            
        file_path = os.path.join(magazines_dir, filename)
        
        # Find corresponding magazine issue data
        magazine_id = filename.split('_')[0]
        issue_data = None
        magazine_title = "Unknown Magazine"
        issue_number = "Unknown Issue"
        
        # Find the issue data that matches this file
        for issue_id, issue in magazine_issues_data.items():
            if issue['magazineId'] == magazine_id:
                issue_data = issue
                magazine_title = magazine_titles.get(magazine_id, "Unknown Magazine")
                issue_number = f"Issue {issue['issueNumber']}"
                break
        
        print(f"\nSearching in: {magazine_title} - {issue_number}")
        
        try:
            with open(file_path, 'rb') as file:
                # Create PDF reader object
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Search each page
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    
                    # Process text line by line
                    text_lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    for line_num, line in enumerate(text_lines):
                        # Case insensitive search in cleaned line
                        if keyword in line.lower().strip():
                            result = {
                                'magazine_title': magazine_title,
                                'issue_number': issue_number,
                                'page_number': page_num + 1,
                                'line_number': line_num + 1,
                                'context': line.strip()
                            }
                            results.append(result)
                            print(f"✓ Found in page {page_num + 1}, line {line_num + 1}:")
                            print(f"  {line.strip()}")
                
        except Exception as e:
            print(f"✗ Error processing {magazine_title} - {issue_number}: {str(e)}")
    
    # Print summary
    if results:
        print(f"\n=== Found {len(results)} matches for '{keyword}' ===")
        
        # Print organized summary
        print("\nSummary of findings:")
        current_magazine = None
        for result in results:
            if current_magazine != f"{result['magazine_title']} - {result['issue_number']}":
                current_magazine = f"{result['magazine_title']} - {result['issue_number']}"
                print(f"\nIn {current_magazine}:")
            print(f"  Page {result['page_number']}, Line {result['line_number']}:")
            print(f"    {result['context']}")
    else:
        print(f"\n=== No matches found for '{keyword}' ===")
    
    return results

def main():
    """Main function to fetch and download magazines"""
    print("\n====== Magazine Download Script Started ======")
    print(f"Current working directory: {os.getcwd()}")
    
    try:
        # Initialize services
        init_firebase()
        client, storage = init_appwrite()
        
        # Get all magazine issues and magazines from Firebase
        print("\n=== Fetching Data from Firebase ===")
        magazines_ref = db.reference('magazines')
        magazine_issues_ref = db.reference('magazine_issues')
        
        magazines_data = magazines_ref.get()
        magazine_issues_data = magazine_issues_ref.get()
        
        if not magazine_issues_data:
            print("✗ No magazines found in the database")
            return
        
        print(f"✓ Found {len(magazine_issues_data)} magazine issues in the database")
        
        # Process each magazine
        for issue_id, issue_data in magazine_issues_data.items():
            print(f"\n--- Processing Issue ID: {issue_id} ---")
            if 'pdfFileId' in issue_data and issue_data['pdfFileId']:
                filename = f"{issue_data['magazineId']}_{issue_data['issueNumber']}.pdf"
                magazine_title = magazines_data[issue_data['magazineId']]['title']
                print(f"Magazine: {magazine_title}")
                print(f"Issue Number: {issue_data['issueNumber']}")
                print(f"PDF File ID: {issue_data['pdfFileId']}")
                download_magazine(
                    client=client,
                    bucket_id='67718396003a69711df7',
                    file_id=issue_data['pdfFileId'],
                    filename=filename
                )
            else:
                print("✗ No PDF file ID found for this issue")
        
        # Example search
        keyword = input("\nEnter search keyword: ")
        search_results = search_pdfs(keyword, magazines_data, magazine_issues_data)
            
        print("\n====== Magazine Download and Search Process Completed ======")
        
    except Exception as e:
        print(f"\n✗ Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 