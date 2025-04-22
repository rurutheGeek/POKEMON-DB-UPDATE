# ポケモンデータベース更新ツール

## 概要
このアプリケーションは、ポケモンのエイリアス（別名）を管理するためのシンプルなGUIツールです。SQLiteデータベースに保存されているポケモン名とその別名を追加、編集、削除することができます。ローカルファイルの編集だけでなく、Google Driveで共有されたデータベースファイルにアクセスして複数人で編集することもできます。

## 機能
- ポケモン名のオートコンプリート検索
- ポケモンのフォーム（すがた）選択
- 選択したポケモンとフォームに対する別名の表示
- 別名の追加、編集、削除
- Google Driveとの連携（remote_update.py使用時）

## 必要条件
- Python 3.x
- Tkinter (Pythonに通常含まれています)
- SQLite3 (Pythonに通常含まれています)

### リモート更新機能を使用する場合の追加要件
- Google API クライアントライブラリ:
```
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

## インストール方法
リポジトリをクローンするか、ダウンロードしてください:
```
git clone https://github.com/yourusername/pokemon-db-update.git
cd pokemon-db-update
```

## 使用方法

### ローカルファイル編集モード
1. ローカルアプリケーションを起動します:
```
python local_update.py
```

2. 検索ボックスにポケモン名を入力すると、オートコンプリートで候補が表示されます。
3. ポケモンを選択すると、そのポケモンの利用可能なフォーム（すがた）がドロップダウンメニューに表示されます。
4. フォームを選択すると、そのポケモンとフォームの組み合わせに登録されている別名がリストボックスに表示されます。
5. 「別名の追加」ボタンを押すと、新しい別名を追加できます。
6. リストボックス内の別名を右クリックすると、編集または削除のオプションが表示されます。

### Google Drive連携モード
1. Google Drive連携アプリケーションを起動します:
```
python remote_update.py
```

2. **重要**: remote_update.pyを使用するには、同じディレクトリに `credentials.json` ファイルが必要です。このファイルにはGoogle Drive APIへのアクセス権限が含まれています。

3. Google Driveからデータベースが自動的にダウンロードされます。
4. ローカルモードと同様に、ポケモン名を検索・選択し、別名を編集できます。
5. 「Google Driveに保存」ボタンをクリックすると、変更がクラウドにアップロードされます。
6. 「最新版を取得」ボタンをクリックすると、最新バージョンのデータベースを取得できます。

## credentials.jsonの設定
remote_update.pyを使用するには、以下のような形式のcredentials.jsonファイルが必要です：

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "abcdef1234567890abcdef1234567890abcdef12",
  "private_key": "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_CONTENT\n-----END PRIVATE KEY-----\n",
  "client_email": "service-account-name@your-project-id.iam.gserviceaccount.com",
  "client_id": "123456789012345678901",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/service-account-name%40your-project-id.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
```

このファイルは以下の手順で取得できます：
1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. Google Drive APIを有効化
3. サービスアカウントを作成し、JSONキーをダウンロード
4. 編集したいGoogle Driveファイルをこのサービスアカウントと共有

**注意**: credentials.jsonには秘密鍵が含まれているため、安全に管理してください。このファイルを共有することで、誰でもそのGoogle Driveファイルを編集できるようになります。

## セキュリティに関する注意事項
- credentials.jsonファイルはパスワードと同等の重要性があります。安全に保管してください。
- 同じcredentials.jsonファイルを共有している全員が、共有されたGoogle Driveファイルを編集できます。

## データベース構造
このアプリケーションは以下のSQLiteテーブルを使用します:

- `POKEMON_NAME`: ポケモンの基本情報（図鑑番号と名前）
- `POKEMON_NAME_FORM`: ポケモンのフォーム情報
- `POKEMON_NAME_ALIAS`: ポケモンとそのフォームに関連付けられた別名

### テーブルスキーマ

#### POKEMON_NAME テーブル
```sql
CREATE TABLE POKEMON_NAME (
    NDEX_NUMBER INTEGER PRIMARY KEY,  -- ポケモン図鑑番号（主キー）
    NAME TEXT NOT NULL                -- ポケモン名
);
```

#### POKEMON_NAME_FORM テーブル
```sql
CREATE TABLE POKEMON_NAME_FORM (
    NDEX_NUMBER INTEGER,              -- ポケモン図鑑番号（外部キー）
    FORM_ID INTEGER,                  -- フォームID（0が基本形）
    FORM_NAME TEXT,                   -- フォーム名（メガシンカ、アローラのすがた等）
    GENDER TEXT,                      -- 性別による形態違い
    PRIMARY KEY (NDEX_NUMBER, FORM_ID),
    FOREIGN KEY (NDEX_NUMBER) REFERENCES POKEMON_NAME(NDEX_NUMBER)
);
```

#### POKEMON_NAME_ALIAS テーブル
```sql
CREATE TABLE POKEMON_NAME_ALIAS (
    NAME_ALIAS TEXT,                  -- ポケモンの別名
    NDEX_NUMBER INTEGER,              -- ポケモン図鑑番号（外部キー）
    FORM_ID INTEGER,                  -- フォームID（外部キー）
    PRIMARY KEY (NAME_ALIAS, NDEX_NUMBER, FORM_ID),
    FOREIGN KEY (NDEX_NUMBER, FORM_ID) REFERENCES POKEMON_NAME_FORM(NDEX_NUMBER, FORM_ID)
);
```

### データベースの関係
- 各ポケモン（`POKEMON_NAME`）は複数のフォーム（`POKEMON_NAME_FORM`）を持つことができます
- 各フォーム（`POKEMON_NAME_FORM`）は複数の別名（`POKEMON_NAME_ALIAS`）を持つことができます
- `FORM_ID = 0`は基本形態を表します
- `FORM_NAME`または`GENDER`がNULLでない場合、特殊な形態を示します

このデータベース構造により、ピカチュウ（基本形態）、ピカチュウ（サトシのぼうし）、リザードン（メガXフォーム）などの異なる形態のポケモンと、それらの別名（ピカチュウの場合「ピカチュウ」「ピカチュー」など）を柔軟に管理できます。

## 他のデータベースファイルの編集
remote_update.pyは、credentials.jsonに適切な権限があれば、任意のGoogle Drive上のSQLiteデータベースファイルを編集できます。使用するファイルのURLを変更するには、remote_update.pyの以下の行を編集してください：

```python
drive_url = "https://drive.google.com/file/d/[YOUR_FILE_ID]/view?usp=sharing"
```

## ライセンス
このプロジェクトのライセンスは、**GNU General Public License (GPL v3)** に準拠しています。リポジトリ内の `LICENSE` ファイルを参照してください。