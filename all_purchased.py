import argparse
import requests
import http.cookiejar
import json
import logging

__URL_TEMPLATE = 'https://play.dlsite.com/api/purchases?page={}'


def GetAllPurchases(cookie):
    current_page_num = 1
    all_works = []

    session = requests.session()
    session.cookies.update(cookie)
    response = session.get(__URL_TEMPLATE.format(current_page_num))
    current_page_num += 1

    response_json = json.loads(response.text)
    total = int(response_json['total'])
    left = total
    
    works = response_json['works']
    left -= len(works)
    for work in works:
        all_works.append(work)
    logging.info('Processed {} out of {}'.format(total - left, total))


    while left > 0:
        response = session.get(__URL_TEMPLATE.format(current_page_num))
        current_page_num += 1
        response_json = json.loads(response.text)
        works = response_json['works']
        left -= len(works)
        for work in works:
            all_works.append(work)

        logging.info('Processed {} out of {}'.format(total - left, total))

    return all_works


def WriteAllPurchases(cookie_file, output_file):
    cookie_jar = http.cookiejar.MozillaCookieJar(cookie_file)
    cookie_jar.load()

    all_works = GetAllPurchases(cookie_jar)
    with open(output_file, 'w') as f:
        json.dump(all_works, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--cookie', required=True, help='Cookie file.')
    parser.add_argument('-o',
                        '--output',
                        required=True,
                        help='Output file containing all purchased items.')

    logging.basicConfig(level=logging.INFO)

    args = parser.parse_args()
    WriteAllPurchases(args.cookie, args.output)
