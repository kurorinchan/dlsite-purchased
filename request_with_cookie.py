import requests

import http.cookiejar

import json

cr = http.cookiejar.MozillaCookieJar('cookies.txt')
print(str(cr))
cr.load()

for c in cr:
    print(c)

session = requests.session()

session.cookies.update(cr)

response = session.get('https://play.dlsite.com/api/purchases?page=1')

print(response)
json_text = response.text

response_json = json.loads(json_text)

for work in response_json['works']:
    print(work['workno'])
