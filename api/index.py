from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import fitz  # PyMuPDF
import firebase_admin
from firebase_admin import credentials, db
import re
import io
import httpx
import json
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS to allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Firebase credentials as a dictionary
FIREBASE_CREDENTIALS = {
    "type": "service_account",
    "project_id": "magazine-nexus",
    "private_key_id": "761f6d9b91ce39e846851d14a073e18ac69b85f8",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC3reznL3ozrwoE\nl4FYCkMek90HR0zdVOoziKtn1ZE1KajqDxHXmokjYS7PRN430oRcNroSzCBafySv\nM6BXvRo+ECOTg/T+5W2khq3Udkx+otf6oJWQcjFEPQg9wFom8QxP2+oMuwZ6y4Z4\nduM4K/X6sI+MctwRNbRgynISIpMwKQqR3dZ8ruKmvcjCEPCYtP66aRzzf8fX8giR\nU1h+r70clqbaYcw1rEpYcp86gXItWZ8JhCvgcpGYz6hAOvRlBQ45g8IMSoe6ttx1\noJAecIcjl4wzslpMu0AeIuoPwHfvixzdH3ACrdke6Nu31w+MMjeMTQxhuLMdZnC4\nzueDmg3nAgMBAAECggEABpwo5YrETsV556Jl9U0J+ApeulslJisB2vxdqDMHbNGH\nniyzBZW6MvXVigvJ9fzcFOaMX4LNOojazNXT9xdBVDxwoSHAdZiNso2UY1H25Xx+\nM0J7+ZcJtHojP+COqZ/pzz2LlbAP3kULHSiwqePUkDcPTCPMNfttyG8DjG76pB0T\neKdvoaSREjfPIxKCq5eMc4TyVZht2Skbv5NR0v1lzZtuWxPm4MKDCLm9vOdvQxs4\nTTrRI/qEQ6vthXaOD9Q+vWZcv3aBF+N8ujCfm19Kg4dmFngs+/cv7/2slqNCXlX8\ndGpfoF0ZUI1ZB5JU312xeMTbkF4D28R7oZgFa5LKwQKBgQDaRy0Q9p4XMDDvWLtC\nGWK3hfaR8DqyrWIpFGuxLaOEGlYoKZ/N5GBPMocW20UE1XUXATV1gUO2QzbEg0hY\nu/Xtwtb4/HudiaK3IoEPJ+gI7dHguyAG/+XJAczjMn/O5FIWEStNbETwBw5eisR6\n87W7VX4ya+d1oCCOa+LsZCbphwKBgQDXbBLL+oD0F6ehocHrcw09CJ7xt5H0M/sG\n/k295mRxhWYk/wpjaQktw4r5tmOsSlniV8yibnTDbxMhayzH58Ph5Bj9SAR0zSTQ\nkNt6QN5QzuPloFR0V4WTikkdtrxDeCT1XbWq3tbuieH+kjzGt6WDaq/Ke5xsS87k\n92BPjmFQoQKBgQDZM8ZWgPFjZaLsKMF9zsD6miV3pzLhpcJt2lInZqC1zXc6U+Ef\nAkgLxt3CEsMlQjtXfu5xVQXKEiwnc/PDyJW52A4OiT+AzfrKfV0rdaxhZjVYiRwf\nmvhPAqmc0x13BJ/iMYeDbV9T8dGMpk1Jg8Ws+i+vgMw7sfFzh0uxqx9FdQKBgDMD\nxO/JQwCLGYeNZv77IAd0Iy/a6RWLucbOMlrmVKMNlELuoucn2KSdyiuYpcIHWYHg\niPVucvhVNZKUbuZoXFsCSWixxVxjuHQr2c35zqwUUqPudBGZKGjoNqhyveK8cQQq\nTPtKClwzCvHeb8Yfd3LHsRmibEi5KyXN72DntuQBAoGAIt5/sKUYI3R4LB+z/Jh7\nbJTk9SbejL6YSsC4JlG0P+MjsJo4RmM5xpS6ctaUbqqx2Ah7s3DY8PQ5g5SpHrKk\n+v68TrBamcKZj5JdPJV327jO60swtGHtU6GIzuGjmZogxS5WTGmk5uw9l4ceeAm5\njejX5R0bB9eXoT2InXoPr1w=\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-6c4rw@magazine-nexus.iam.gserviceaccount.com",
    "client_id": "113464350745429511304",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-6c4rw%40magazine-nexus.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

# Initialize Firebase only if it hasn't been initialized yet
if not firebase_admin._apps:
    try:
        # Initialize Firebase with the embedded credentials
        cred = credentials.Certificate(FIREBASE_CREDENTIALS)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://magazine-nexus-default-rtdb.asia-southeast1.firebasedatabase.app'
        })
        print("Firebase initialized successfully")
        
    except Exception as e:
        print(f"Firebase initialization error: {str(e)}")
        raise

# Add Appwrite configuration
APPWRITE_ENDPOINT = "https://cloud.appwrite.io/v1"
APPWRITE_PROJECT_ID = "676fc20b003ccf154826"
MAGAZINE_BUCKET_ID = "67718396003a69711df7"

async def get_pdf_content(file_id: str) -> bytes:
    """Helper function to fetch PDF content from Appwrite"""
    url = f"{APPWRITE_ENDPOINT}/storage/buckets/{MAGAZINE_BUCKET_ID}/files/{file_id}/download"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={
                "X-Appwrite-Project": APPWRITE_PROJECT_ID,
            }
        )
        response.raise_for_status()
        return response.content

class SearchResult(BaseModel):
    magazine_id: str
    title: str
    page_number: int
    content_preview: str
    confidence: float

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int

@app.get("/")
async def root():
    return {"message": "Magazine Nexus API is running"}

@app.get("/api/search/{query}", response_model=SearchResponse)
async def search_magazines(query: str, limit: Optional[int] = 10):
    try:
        # Get magazines from Firebase
        magazines_ref = db.reference('magazines')
        magazines = magazines_ref.get()
        
        results = []
        
        for magazine_id, magazine_data in magazines.items():
            if not magazine_data.get('pdfFileId'):
                continue
                
            try:
                # Get PDF content from Appwrite
                pdf_content = await get_pdf_content(magazine_data['pdfFileId'])
                doc = fitz.open(stream=pdf_content, filetype="pdf")
                
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()
                    
                    # Search for query in text
                    matches = re.finditer(query.lower(), text.lower())
                    
                    for match in matches:
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        preview = text[start:end].replace('\n', ' ').strip()
                        
                        # Calculate simple confidence score based on word proximity
                        words = query.lower().split()
                        confidence = 1.0
                        if len(words) > 1:
                            positions = [text.lower().find(word) for word in words]
                            max_dist = max(positions) - min(positions)
                            confidence = 1.0 / (1.0 + max_dist/100.0)
                        
                        results.append(SearchResult(
                            magazine_id=magazine_id,
                            title=magazine_data['title'],
                            page_number=page_num + 1,
                            content_preview=f"...{preview}...",
                            confidence=confidence
                        ))
                
                doc.close()
                
            except Exception as e:
                print(f"Error processing PDF {magazine_id}: {str(e)}")
                continue
        
        # Sort results by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        # Limit results
        results = results[:limit]
        
        return SearchResponse(
            results=results,
            total_results=len(results)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# This is important for Vercel
app = app