import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import csv

class SpreadSheetUploader:
    # GoogleAPI
    SCOPE = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    # 認証用キー
    JSON_KEYFILE_PATH = 'json_keyfile.jsonのパス'
    # スプレッドシートIDを取得
    SHEET_ID = '<スプレッドシートIDを入力>'

    def __init__(self):
        # サービスアカウントキーを読み込む
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self.JSON_KEYFILE_PATH, self.SCOPE)
        # pydrive用の認証
        gauth = GoogleAuth()
        gauth.credentials = credentials
        drive = GoogleDrive(gauth)
        # gspread用の認証
        self.gc = gspread.authorize(credentials)

    def upload(self, file_name):
        # スプレッドシートを開く
        workbook = self.gc.open_by_key(self.SHEET_ID)
        workbook.add_worksheet(title=file_name, rows=1000, cols=26)
        # スプレッドシートにCSVをインポート
        workbook.values_update(
            file_name,
            params={'valueInputOption': 'USER_ENTERED'},
            body={'values': list(csv.reader(open(file_name, encoding='utf_8_sig')))}
        )
        return 'success'
