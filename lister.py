import os

from io import BytesIO
from urllib.parse import unquote_plus

import requests

from amazon.api import AmazonAPI
from bs4 import BeautifulSoup
from ebaysdk.trading import Connection
from jinja2 import Environment, FileSystemLoader
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from schema import Base, Link, UPC
from secrets import (
    ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG, DEVID, PRODUCTION_APPID,
    PRODUCTION_CERTID, PRODUCTION_TOKEN, SANDBOX_APPID, SANDBOX_CERTID,
    SANDBOX_TOKEN
)

engine = create_engine('sqlite:///sqlite3.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

amazon = AmazonAPI(ACCESS_KEY, SECRET_KEY, ASSOCIATE_TAG)
production = Connection(
    devid=DEVID,
    appid=PRODUCTION_APPID,
    certid=PRODUCTION_CERTID,
    token=PRODUCTION_TOKEN,
    config_file=None
)
sandbox = Connection(
    domain='api.sandbox.ebay.com',
    devid=DEVID,
    appid=SANDBOX_APPID,
    certid=SANDBOX_CERTID,
    token=SANDBOX_TOKEN,
    config_file=None
)

SEARCH_INDEX = [
    'All', 'UnboxVideo', 'Appliances', 'MobileApps', 'ArtsAndCrafts',
    'Automotive', 'Baby', 'Beauty', 'Books', 'Music', 'Wireless', 'Fashion'
    'FashionBaby', 'FashionBoys', 'FashionGirls', 'FashionMen', 'FashionWomen'
    'Collectibles', 'PCHardware', 'MP3Downloads', 'Electronics', 'GiftCards',
    'Grocery', 'HealthPersonalCare', 'Industrial', 'KindleStore', 'Luggage',
    'Magazines', 'Movies', 'MusicalInstruments', 'OfficeProducts',
    'LawnAndGarden', 'PetSupplies', 'Pantry', 'Software', 'SportingGoods',
    'Tools', 'Toys', 'VideoGames', 'Wine'
]

PERCENTAGE_MARKUP = 1.5

IMAGE_DIR = os.path.join(os.getcwd(), 'images')
IMAGE_URL = '45.55.207.40/images/{}'


def get_amazon_product_price(link):
    product = amazon.lookup(ItemId=link.amazon)
    return product.price_and_currency[0] or 0


def get_amazon_products():
    keyword = input('Please input Amazon search keyword: ')
    for i, search_index in enumerate(SEARCH_INDEX):
        print('{}. {}'.format(i, search_index))
    default = 0
    text = 'Please select Amazon search index: ({})'.format(default)
    index = input(text) or default
    index = SEARCH_INDEX[index]
    response = list(amazon.search(Keywords=keyword, SearchIndex=index))
    products = []
    for product in response:
        asin = product.asin
        if not asin or not session.query(Link).filter_by(amazon=asin).count():
            continue
        title = product.title
        if not title:
            continue
        try:
            category = product.browse_nodes[0].name
        except IndexError:
            continue
        try:
            image = unquote_plus(
                str(product.images[0].LargeImage.URL).split('/')[-1]
            )
        except IndexError:
            continue
        price = product.price_and_currency[0] or 0
        if price < 50:
            continue
        soup = BeautifulSoup(product.editorial_review or '', 'html.parser')
        description = soup.stripped_strings
        if not description:
            continue
        features = product.features
        if not features:
            continue
        soup = BeautifulSoup(product.to_string(), 'html.parser')
        if not soup.find('iseligibleforsupersavershipping').text == '1':
            continue
        brand = product.brand or product.manufacturer or '.'
        model = product.part_number or product.mpn or '.'
        products.append(
            {
                'asin': asin,
                'title': title,
                'category': category,
                'price': price,
                'image': image,
                'description': description,
                'features': features,
                'brand': brand,
                'model': model,
            }
        )
    return products


def get_ebay_title(product):
    print(
        'Amazon product: http://www.amazon.com/dp/{}/'.format(product['asin'])
    )
    while True:
        default = product['title']
        text = 'Char count {}. Please input eBay title: ({})'.format(
            len(default), default
        )
        title = input(text) or default
        if 75 <= len(title) <= 80:
            return title
        print('Title character count must be between 75 and 80 characters!')


def get_ebay_category(product):
    while True:
        text = 'Please input eBay category search ({}): '.format(
            product['category']
        )
        search = input(text) or product['category']
        response = production.execute(
            'GetSuggestedCategories', {'Query': search}
        )
        response = response.dict()
        for cat in response['SuggestedCategoryArray']['SuggestedCategory']:
            cat_id = cat['Category']['CategoryID']
            name = cat['Category']['CategoryName']
            print('{}. {}'.format(cat_id, name))
        default = response['SuggestedCategoryArray']['SuggestedCategory'][0]
        default = default['Category']['CategoryID']
        text = 'Please input eBay category id or . to retry: ({})'.format(
            default
        )
        category = input(text) or default
        if category == '.':
            continue
        return category


def get_ebay_image(product):
    path = os.path.join(IMAGE_DIR, product['image'])
    url = IMAGE_URL.format(product['image'])
    if os.path.exists(path):
        return url
    response = requests.get(
        'http://ecx.images-amazon.com/images/I/{}'.format(product['image'])
    )
    image = Image.open(BytesIO(response.content))
    width, height = image.size
    x = 0
    y = 0
    if width < 500:
        x = round((500 - width) / 2)
    if height < 500:
        y = round((500 - height) / 2)
    white = Image.new('RGBA', (500, 500), (255, 255, 255, 255))
    white.paste(image, (x, y))
    white.save(path)
    return url


def get_ebay_html(product):
    env = Environment(loader=FileSystemLoader('.'), trim_blocks=True)
    html = env.get_template('template.html').render(
        title=product['title'],
        description=product['description'],
        features=product['features']
    )
    return html.replace('\n', '')


def update_ebay_product_price(item_id, amazon_price):
    item = {
        'Item': {
            'ItemID': item_id,
            'StartPrice': amazon_price * PERCENTAGE_MARKUP
        }
    }
    sandbox.execute('ReviseItem', item)


def list_ebay_product(product):
    upc = UPC.random()
    item = {
        'Item': {
            'Title': get_ebay_title(product),
            'Description': u'<![CDATA[{}]]>'.format(get_ebay_html(product)),
            'PrimaryCategory': {'CategoryID': get_ebay_category(product)},
            'StartPrice': str(product['price'] * PERCENTAGE_MARKUP),
            'CategoryMappingAllowed': 'true',
            'ConditionID': '1000',
            'Country': 'US',
            'Currency': 'USD',
            'DispatchTimeMax': '3',
            'ListingDuration': 'Days_30',
            'ListingType': 'FixedPriceItem',
            'Location': 'Los Angeles, CA',
            'PaymentMethods': 'PayPal',
            'PayPalEmailAddress': 'joshwardini@gmail.com',
            'PictureDetails': {'PictureURL': get_ebay_image(product)},
            'ItemSpecifics': {
                'NameValueList': [
                    {'Name': 'Brand', 'Value': product['brand']},
                    {'Name': 'MPN', 'Value': product['model']}
                ]
            },
            'PostalCode': '90001',
            'Quantity': '1',
            'ListingDuration': 'GTC',
            'ShippingDetails': {
                'ShippingType': 'Flat',
                'GlobalShipping': '1',
                'ShippingServiceOptions': {
                    'ShippingServicePriority': '1',
                    'ShippingService': 'Other',
                    'ShippingServiceCost': '0.00'
                }
            },
            'ReturnPolicy': {
                'Description': '14 days money back, you pay return shipping',
                'ReturnsAcceptedOption': 'ReturnsAccepted',
                'RefundOption': 'MoneyBack',
                'ReturnsWithinOption': 'Days_14',
                'ShippingCostPaidByOption': 'Buyer'
            },
            'Site': 'US',
            'ProductListingDetails': {
                'UPC': upc,
                'ListIfNoProduct': 'true'
            }
        }
    }
    response = sandbox.execute('AddFixedPriceItem', item)
    item_id = response.dict()['ItemID']
    link = Link(amazon=product['asin'], ebay=item_id)
    session.add(link)
    upc.available = False
    session.commit()
    url = 'http://cgi.sandbox.ebay.com/ws/eBayISAPI.dll?ViewItem&item={}&ssPa'\
        'geName=STRK:MESELX:IT'.format(item_id)
    print('Ebay product: {}'.format(url))


def list():
    for product in get_amazon_products():
        list_ebay_product(product)


def update():
    for link in session.query(Link).all():
        amazon_price = get_amazon_product_price()
        update_ebay_product_price(link.ebay, amazon_price)
