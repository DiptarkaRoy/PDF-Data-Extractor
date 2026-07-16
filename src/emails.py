"""
Module: emails.py
Description: Automated, secure Gmail ingestion engine with built-in attachment 
             filtering and inbox status management. Connects to the Gmail API 
             via OAuth 2.0, handles 2FA token lifecycles, and polls for unread 
             emails to download specific, allowed file types.

Architecture & Workflow:
    1. Authenticator: Handles OAuth 2.0 authorization, prompting 2FA via browser 
       on first run and maintaining a persistent session using a local 'token.json'.
    2. Inbox Poller: Queries Gmail for unread messages containing attachments 
       using the search filter "has:attachment is:unread".
    3. Extension Filter: Scans incoming files and only downloads allowed extensions 
       (PDF, Excel, Word, and ZIP), skipping system noise like image signatures.
    4. Attachment Downloader: Decodes the base64-encoded file payload from Google 
       and streams the files directly into the local './downloads' directory.
    5. Inbox Janitor: Marks successfully processed emails as "Read" (removing the 
       UNREAD label) to prevent duplicate downloads on subsequent runs.
    6. Scheduler Loop: Runs a daemonized loop that automatically triggers the sync 
       cycle at a configurable interval (e.g., every 5 minutes).

Dependencies:
    - google-api-python-client (Gmail API wrapper)
    - google-auth-oauthlib (OAuth 2.0 client library)
    - credentials.json & token.json (Access secrets)

Author: Diptarka Roy
"""

import os
import base64
import time
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# We only need read-only access to messages and attachments
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    creds = None
    # token.json stores your access and refresh tokens created after logging in once
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    # If there are no valid credentials, let the user log in (triggers 2FA in browser)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def download_attachments():
    service = get_gmail_service()
    
    # Query: Unread emails with attachments
    query = "has:attachment is:unread"
    results = service.users().messages().list(userId='me', q=query).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No new unread emails with attachments found.")
        return

    os.makedirs("./downloads", exist_ok=True)

    # Define the allowed extensions (lowercase for safe matching)
    ALLOWED_EXTENSIONS = {
        '.pdf', 
        '.xlsx', '.xls', '.csv', '.xlsm', 
        '.docx', '.doc', 
        '.zip'
    }

    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        payload = msg.get('payload', {})
        parts = payload.get('parts', [])

        # We keep track if we downloaded any valid attachments from this email
        downloaded_any = False 

        for part in parts:
            if part.get('filename'):
                filename = part['filename']
                
                # If the filename doesn't contain a dot, it's an inline signature/system ID.
                # We can silently skip it without spamming the terminal.
                if '.' not in filename:
                    continue

                # Extract the file extension
                _, file_extension = os.path.splitext(filename.lower())
                
                # Check if the file matches our allowed list
                if file_extension not in ALLOWED_EXTENSIONS:
                    print(f"Skipped (Not allowed type): {filename}")
                    continue
                
                attachment_id = part['body'].get('attachmentId')
                
                # Fetch the actual attachment file data
                attachment = service.users().messages().attachments().get(
                    userId='me', messageId=message['id'], id=attachment_id
                ).execute()
                
                data = attachment.get('data')
                file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                
                filepath = os.path.join("./downloads", filename)
                with open(filepath, 'wb') as f:
                    f.write(file_data)
                
                print(f"Downloaded: {filename}")
                downloaded_any = True
                
        # Mark email as read ONLY if we processed it
        # (This leaves emails with unhandled file types unread, or you can change it to mark read regardless)
        if downloaded_any:
            service.users().messages().batchModify(
                userId='me',
                body={'ids': [message['id']], 'removeLabelIds': ['UNREAD']}
            ).execute()

def email_checker_loop():
    """Periodically checks Gmail for new attachments in a background loop."""
    EMAIL_CHECK_INTERVAL = 300  # Check every 5 minutes
    print("📬 Email Sync Thread started.")
    while True:
        try:
            print("\n🔄 Checking Gmail for new attachments...")
            download_attachments()
        except Exception as e:
            print(f"❌ Error in Email Sync Thread: {e}")
        
        # Wait before checking again
        time.sleep(EMAIL_CHECK_INTERVAL)            

if __name__ == "__main__":
    download_attachments()