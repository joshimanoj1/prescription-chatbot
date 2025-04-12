# web_search.py
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests
from bs4 import BeautifulSoup

# Path to the Service Account key JSON file
SERVICE_ACCOUNT_FILE = "/users/manojjoshi/desktop/credentials/PP/prescriptionchatbot-051c305ca680.json"
#SERVICE_ACCOUNT_FILE = "./prescriptionchatbot-e33dbe9a80cb.json"
SEARCH_ENGINE_ID = "7642c5350181c4348"

# Define the scopes
SCOPES = ["https://www.googleapis.com/auth/cse"]

# Authenticate using the Service Account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

def fetch_web_info(query, num_results=3):
    results = []
    try:
        service = build("customsearch", "v1", credentials=credentials)
        print(f"Searching for: {query}")
        res = service.cse().list(
            q=query,
            cx=SEARCH_ENGINE_ID,
            num=num_results,
        ).execute()
        
        print(res)  # Debug: Print result

        if "items" in res:
            for item in res["items"]:
                url = item["link"]
                try:
                    response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, "html.parser")
                        text = soup.get_text(strip=True)[:5000]  # Truncate for brevity
                        results.append({"text": text, "url": url})
                except Exception as e:
                    print(f"Error fetching {url}: {e}")
        else:
            print("No search results found.")
    except Exception as e:
        print(f"Error during Google Custom Search: {e}")

    return results if results else [{"text": "No additional information found on the web.", "url": "N/A"}]