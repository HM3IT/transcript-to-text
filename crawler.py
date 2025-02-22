import os
import praw
import yt_dlp
 
from datetime import datetime, timezone
from py_dotenv import read_dotenv
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
 
read_dotenv(file_path=".env")
# Reddit API credentials
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
 
REDDIT_USER_AGENT =  os.environ["REDDIT_USER_AGENT"]
SUBREDDIT = os.environ["SUBREDDIT"]

# YouTube API credentials
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_PICKLE = "token.pickle"
CREDENTIALS_FILE = "client_secrets.json"

 
reddit = praw.Reddit(client_id=REDDIT_CLIENT_ID,
                     client_secret=REDDIT_CLIENT_SECRET,
                     user_agent=REDDIT_USER_AGENT)

def authenticate_youtube():
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, "rb") as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_PICKLE, "wb") as token:
            pickle.dump(creds, token)
    
    return build("youtube", "v3", credentials=creds)

def download_video(url, output_path="downloads"):
    os.makedirs(output_path, exist_ok=True)
    ydl_opts = {
        "outtmpl": f"{output_path}/%(title)s.%(ext)s",
        "format": "bestvideo+bestaudio/best",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def upload_to_youtube(youtube, file_path, title, description, privacy_status="private"):
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": ["Reddit", "Video"],
                "categoryId": "22"  # Category for 'People & Blogs'
            },
            "status": {
                "privacyStatus": privacy_status
            }
        },
        media_body=file_path
    )
    response = request.execute()
    print(f"Uploaded: {response['id']}")

def main(max_age_minutes=60):
    youtube = authenticate_youtube()
    subreddit = reddit.subreddit(SUBREDDIT)
    
    current_time = datetime.now(timezone.utc).timestamp()
    
    for submission in subreddit.new(limit=5):
        post_age_minutes = (current_time - submission.created_utc) / 60
        
        if post_age_minutes > max_age_minutes:
            continue
        
        if submission.url.endswith(('.mp4', '.mov', '.avi')) or "youtube.com" in submission.url or "youtu.be" in submission.url:
            print(f"Downloading {submission.title} from {submission.url}")
            download_video(submission.url)
            file_path = f"downloads/{submission.title}.mp4"
            upload_to_youtube(youtube, file_path, submission.title, submission.selftext)

if __name__ == "__main__":
    main(max_age_minutes=60*14)
