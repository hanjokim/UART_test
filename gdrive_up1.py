from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from httplib2 import Http
from oauth2client import file, client, tools

# api 연결 및 사전정보 입력
SCOPES = ['https://www.googleapis.com/auth/drive.metadata',
          'https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/drive']
store = file.Storage('storage.json')
creds = store.get()

# 권한 인증 창. 제일 처음만 창이 띄워짐
try:
    import argparse

    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None
if not creds or creds.invalid:
    print('make new cred')
    flow = client.flow_from_clientsecrets('C:/~/client_secret_drive.json', SCOPES)
    creds = tools.run_flow(flow, store, flags) if flags else tools.run_flow(flow, store)

service = build('drive', 'v3', credentials=creds)

# 업로드 할 파일
file_paths = "C:/Users/~.csv"

# 업로드할 파일 정보 정의
# parents: 업로드할 구글 드라이브 위치의 url 마지막 ID
file_metadata = {
    "name": "test_from_ibm.csv",
    "parents": ["19vPUpqFxYy~dzeVEkv"]}
# 파일 업로드
media = MediaFileUpload(file_paths, resumable=True)
file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()