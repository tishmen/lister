from urllib.parse import quote

import requests

from amazon.api import AmazonAPI

ACCESS_KEY = 'AKIAIZQJXTP3ERDEEQPQ'
SECRET_KEY = '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'
ASSOCIATE_TAG = 'tishmen-20'

amazon = AmazonAPI(ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG)

seen = set()


def scrape_suggested_keywords(keyword):
    print('Scraping suggested keywords for keyword {}'.format(keyword))
    url = 'http://completion.amazon.com/search/complete?mkt=1&search-alias=ap'\
        's&q={}'.format(quote(keyword))
    try:
        response = requests.get(url, )
        keywords = response.json()[1]
        print('Got {} keyword suggestions'.format(len(keywords)))
        return keywords
    except Exception as e:
        print(e)
        return []


def search_products(keyword):
    print('Searching for products by keyword {}'.format(keyword))
    try:
        result = amazon.search(Keywords=keyword, SearchIndex='All')
        for product in products:
            product.app
        asins = [p.asin for p in products]
        print('Got {} asins'.format(len(asins)))
        return asins
    except Exception as e:
        print(e)
        return []


def get_similarity_lookup_result_asins(self, asin):
    print('Searching for similar asins by asin {}'.format(asin))
    try:
        products = amazon.similarity_lookup(ItemId=asin)
        asins = [p.parent_asin or p.asin for p in products]
        print('Got {} asins'.format(len(asins)))
        return asins
    except Exception as e:
        print(e)
        return []


    # with self.empty_list_on_exc():
    #     call = Call(user=self.user, name='similarity_lookup')
    #     products = call.amazon('similarity_lookup', ItemId=asin)
    #     result = [p.parent_asin or p.asin for p in response]
    #     log.debug('Got {} products'.format(len(result)))
    #     return result


# keyword = input('Enter keyword: ')
# products =
# for product in amazon.search(Keywords=keyword, SearchIndex='All'):

