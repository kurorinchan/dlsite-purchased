DLsiteのAPIを利用して購入情報をJSONとして保存するツール。

# 使い方

## ユーザー名とパスワードを使う

ユーザー名とパスワードを指定してスクリプト内でログインして情報を取得する方法。ユーザー名は
登録したメールアドレスでもログイン用のIDのどちらでも使用可能。

## cookieを利用する方法

cookieを使用するので、dlsiteにログインした状態でのcookieが必要。

### cookie取得
1. Dlsiteにログイン
2. https://play.dlsite.com/ にアクセス
3. [cookies.txt](https://chrome.google.com/webstore/detail/cookiestxt/njabckikapfpffapmjgojcnbfjonfjfg)
などの拡張を使い、cookieを`cookies.txt`として保存する。dlsite用のクッキーだけでいい。

## 使用例

### ユーザー名とパスワードを使用する
```
pipenv run python all_purchased.py --username '<login email or user ID>' --password '<password>'
```

### cookieを使用する
上で入手した`cookies.txt`を同じディレクトリに置き、JSONを`all.json`に書き出す場合。

```
pipenv run python all_purchased.py -i cookies.txt -o all.json
```

# Setup
Use pipenv.

```
pipenv install
```

# 解説

## クッキー取得

プログラマティカルにクッキーを取得する方法

### ログイン

ログイン用URLは[`https://login.dlsite.com/login`](https://login.dlsite.com/login)

1. `https://login.dlsite.com/login` にGETリクエストを送る
2. クッキーのXSRF-TOKENの値(token)を取得
3. POSTリクエスト用のpayloadを `_token=$token`, `login_id=$username`, `password=$password` にする。
4. GET時に取得したクッキーをそのまま使い、POSTリクエストを上記のpayloadで `https://login.dlsite.com/login` に送る。
5. ステータスコードのチェックと共に、レスポンスのクッキーに`PHPSESSID`が入っていればログイン成功。

3の`$token`は2の`XSRF-TOKEN`の値を使う。`$username`はユーザー名`$password`は平文パスワード。

Pythonの`requests`を利用していれば4のクッキーの使いまわしは`session`を使い回せば、気にする必要はない。

### APIを利用するために必要なクッキーを取得する

上記の1-5のあと

6. 今まで取得したクッキーを維持したまま、`https://ssl.dlsite.com/home/mypage` にGETリクエストを送る。
7. 今まで取得したクッキーを維持したまま、`https://play.dlsite.com/#/library` にGETリクエストを送る。

これらを行うことにより必要なクッキーがそろう。

1-5により`login.dlsite.com`のクッキーを
6により`.dlsite.com`のクッキーを
7により`play.dlsite.com`のクッキーを
取得するので、これらすべてにアクセスする必要がある。

## 購入リストの取得

上で取得したクッキーを利用して`https://play.dlsite.com/api/purchases?page=###`にGETリクエストをする。
上記URLの`###`は数字で置き換える。

pageは必ず`1`から始まるので、最初のリクエストは`https://play.dlsite.com/api/purchases?page=1`になる。
帰ってくるJSONは

```JSON
{
  "last": "1970-01-01T00:00:00.000000Z",
  "limit": 100,
  "offset": 0,
  "total": 2,
  "works": [
    ...
  ]
}
```

のようなものになっている。

`last`と`limit`は固定の模様。`limit`は恐らくこのJSONに含まれる`works`の最大数だが、`works`
の要素数を数えればいいので特に気にする必要はない。

`offset`は`page=1`ページを含まない、残りページ数。この値も`works`の数を数えればいいので
とくに必要はない。

`total`は購入したアイテムの数。`page`の値が大きすぎると`HTTP STATUS 404`などが帰ってくる
可能性があるのでここは注意したい。