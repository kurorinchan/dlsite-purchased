DLsiteのAPIを利用して購入情報をJSONとして保存するツール。

# 使い方
cookieを使用するので、dlsiteにログインした状態でのcookieが必要。

## cookie取得
1. Dlsiteにログイン
2. https://play.dlsite.com/ にアクセス
3. [cookies.txt](https://chrome.google.com/webstore/detail/cookiestxt/njabckikapfpffapmjgojcnbfjonfjfg)
などの拡張を使い、cookieを`cookies.txt`として保存する。dlsite用のクッキーだけでいい。

## 使用例
上で入手した`cookies.txt`を同じディレクトリに置き、JSONを`all.json`に書き出す場合。

```
pipenv run python all_purchased.py -i cookies.txt -o all.json
```

# Setup
Use pipenv.

```
pipenv install
```
