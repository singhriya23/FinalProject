from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    '/Users/riyasingh/Downloads/client_secret_285447692709-oa5ck8ln636cv1lnumoeoo6hs4vt9jtf.apps.googleusercontent.com.json',
    scopes=['https://www.googleapis.com/auth/drive.readonly'])
creds = flow.run_local_server(port=0)
with open('token.json', 'w') as token:
    token.write(creds.to_json())