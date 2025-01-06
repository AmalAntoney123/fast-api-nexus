import requests
import json

def test_search_api(base_url, query, limit=10):
    """
    Test the search API endpoint
    
    Args:
        base_url (str): The base URL of your API
        query (str): The search term
        limit (int): Maximum number of results to return
    """
    
    # Remove any trailing slashes from the base_url
    base_url = base_url.rstrip('/')
    
    # Construct the URL
    url = f"{base_url}/api/search/{query}"
    params = {"limit": limit}
    
    try:
        # Make the request
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse and print the results
        data = response.json()
        print(f"\nFound {data['total_results']} results for '{query}':\n")
        
        for idx, result in enumerate(data['results'], 1):
            print(f"Result {idx}:")
            print(f"Magazine ID: {result['magazine_id']}")
            print(f"Title: {result['title']}")
            print(f"Page: {result['page_number']}")
            print(f"Confidence: {result['confidence']:.2f}")
            print(f"Preview: {result['content_preview']}")
            print("-" * 80 + "\n")
            
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")

if __name__ == "__main__":
    # Remove the trailing slash from the URL
    BASE_URL = "https://fast-api-nexus-eum7r6fi7-amal-antoneys-projects.vercel.app"
    
    # Test cases
    test_search_api(BASE_URL, "technology", limit=5)
    test_search_api(BASE_URL, "science", limit=3)