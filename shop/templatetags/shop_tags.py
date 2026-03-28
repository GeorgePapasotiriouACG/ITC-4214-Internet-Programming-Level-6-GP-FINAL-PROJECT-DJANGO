from django import template

# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/templatetags/shop_tags.py
# Description:  Custom Django template tags and filters for TrendMart.
#               - url_replace: preserves existing GET params when changing one
#               - subtract: arithmetic filter for template pagination math
#               - product_image: returns a curated Unsplash URL for a product,
#                 falling back to category pools or a generic lifestyle photo.
# =============================================================================

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, field, value):
    request = context.get('request')
    if request:
        params = request.GET.copy()
        params[field] = value
        return params.urlencode()
    return f'{field}={value}'


@register.filter
def subtract(value, arg):
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value


# ── Curated product image map (Unsplash photo IDs) ──────────────────────────
# Maps product slug → Unsplash photo ID for relevant, on-brand product images
_PRODUCT_IMAGE_MAP = {
    # Smartphones
    'iphone-15-pro':              'photo-1592750475338-74b7b21085ab',
    'samsung-galaxy-s24-ultra':   'photo-1610945415295-d9bbf067e59c',
    'google-pixel-8-pro':         'photo-1598327105666-5b89351aff97',
    'oneplus-12':                 'photo-1574920162043-b872873f19bc',
    'xiaomi-14-ultra':            'photo-1511707171634-5f897ff02aa9',

    # Laptops
    'macbook-pro-14':             'photo-1517336714731-489689fd1ca8',
    'dell-xps-15':                'photo-1593642632559-0c6d3fc62b89',
    'lenovo-thinkpad-x1-carbon':  'photo-1541807084-5c52b6b3adef',
    'asus-rog-strix-g16':         'photo-1593640495253-23196b27a87f',
    'hp-spectre-x360':            'photo-1593642634315-48f5414c3ad9',

    # Headphones
    'sony-wh-1000xm5':            'photo-1505740420928-5e560c06d30e',
    'bose-quietcomfort-45':       'photo-1484704849700-f032a568e944',
    'apple-airpods-pro-2nd-gen':  'photo-1600294037681-c80b4cb5b434',
    'jbl-tune-770nc':             'photo-1558756520-22cfe5d382ca',

    # Tablets
    'ipad-pro-129':               'photo-1544244015-0df4b3ffc6b0',
    'samsung-galaxy-tab-s9':      'photo-1587825140708-dfaf72ae4b04',
    'microsoft-surface-pro-9':    'photo-1611532736597-de2d4265fba3',

    # Smart Home
    'amazon-echo-dot-5th-gen':    'photo-1543512214-318c7553f230',
    'google-nest-hub-2nd-gen':    'photo-1567581935884-3349723552ca',
    'philips-hue-starter-kit':    'photo-1565814329452-e1efa11c5b89',
    'xiaomi-smart-air-purifier-4':'photo-1585771724684-38269d6639fd',
    'amazon-fire-tv-stick-4k-max':'photo-1593359677879-a4bb92f4834c',

    # Cameras
    'sony-a7-iv-mirrorless':      'photo-1516035069371-29a1b244cc32',
    'canon-eos-r50':              'photo-1502920917128-1aa500764b6f',
    'gopro-hero12-black':         'photo-1533310266094-8898a03807dd',

    # Men's Clothing
    'levis-501-original-jeans':   'photo-1542272604-787c3835535d',
    'ralph-lauren-polo-shirt':    'photo-1586790170083-2f9ceadc732d',
    'zara-slim-fit-chinos':       'photo-1473966968600-fa801b869a1a',
    'under-armour-hoodie':        'photo-1556821840-3a63f15732ce',
    'nike-tech-fleece-joggers':   'photo-1542291026-7eec264c27ff',

    # Women's Clothing
    'hm-summer-dress':            'photo-1595777457583-95e059d581b8',
    'zara-blazer':                'photo-1594938298603-c8148c4b4ac2',
    'adidas-originals-hoodie':    'photo-1591047139829-d91aecb6caea',
    'ralph-lauren-cashmere-sweater': 'photo-1576566588028-4147f3842f27',

    # Shoes
    'nike-air-max-270':           'photo-1549298916-b41d501d3772',
    'adidas-ultraboost-22':       'photo-1606107557049-31d8a3c2dc30',
    'new-balance-574':            'photo-1539185441755-769473a23570',
    'puma-suede-classic':         'photo-1620898887463-0ea14a6b6fbe',

    # Accessories / Watches
    'apple-watch-series-9':       'photo-1434494878577-86c23bcb06b9',
    'samsung-galaxy-watch-6':     'photo-1523275335684-37898b6baf30',

    # Furniture
    'ikea-billy-bookcase':        'photo-1555041469-a586c61ea9bc',
    'ikea-poang-armchair':        'photo-1586023492125-27b2c045efd7',

    # Kitchen
    'dyson-v15-detect':           'photo-1558618048-bbe30afc6f38',
    'kitchenaid-stand-mixer':     'photo-1556909114-f6e7ad7d3136',
    'instant-pot-duo-7-in-1':     'photo-1585515320310-259814833e62',
    'ninja-foodi-air-fryer':      'photo-1611532736576-22c2da48e877',
    'bosch-coffee-machine':       'photo-1570968915860-54d5c301fa9f',

    # Fitness
    'nike-training-mat':          'photo-1544367567-0f2fcb009e0b',
    'under-armour-training-gloves': 'photo-1571019613454-1cb2f99b2d8b',

    # Outdoor Gear
    'gopro-hero12-accessories-bundle': 'photo-1526406915894-7bcd65f60845',

    # Skincare
    'the-ordinary-hyaluronic-acid': 'photo-1576426863848-c21f53c60b19',
    'neutrogena-hydro-boost':     'photo-1556228724-74a3f7e3f904',
    'clinique-moisture-surge':    'photo-1615397349754-cfa2066a298e',

    # Makeup
    'loreal-lipstick-collection': 'photo-1586495777744-4e6232bf8a59',
    'maybelline-sky-high-mascara':'photo-1512496015851-a90fb38ba796',

    # Board Games
    'catan-board-game':           'photo-1610890716171-6b1bb98ffd09',
    'monopoly-classic':           'photo-1611996575749-79a3a250f948',

    # Action Figures / LEGO
    'lego-star-wars-millennium-falcon': 'photo-1585366119957-e9730b6d0f60',
    'lego-technic-mclaren-racing-set':  'photo-1518770660439-4636190af475',

    # Automotive
    'garmin-drivesmart-gps':      'photo-1544723795-3fb6469f5b39',

    # Electronics (root)
    'lg-oled-55-tv':              'photo-1593359677879-a4bb92f4834c',
    'sony-playstation-5':         'photo-1607853202273-797f1c22a38e',
    'razer-deathadder-v3-mouse':  'photo-1527864550417-7fd91fc51a46',
    'corsair-k70-mechanical-keyboard': 'photo-1587829741301-dc798b83add3',

    # Pet Supplies
    'premium-dog-food-5kg':       'photo-1589924691995-400dc9ecc119',
    'cat-interactive-toy-set':    'photo-1587300003388-59208cc962cb',
}

# ── Category fallback pools ───────────────────────────────────────────────────
_CATEGORY_FALLBACKS = {
    'smartphones':      ['photo-1510557880182-3d4d3cba35a5', 'photo-1511707171634-5f897ff02aa9'],
    'laptops':          ['photo-1517336714731-489689fd1ca8', 'photo-1593642634315-48f5414c3ad9'],
    'headphones':       ['photo-1505740420928-5e560c06d30e', 'photo-1484704849700-f032a568e944'],
    'tablets':          ['photo-1544244015-0df4b3ffc6b0', 'photo-1587825140708-dfaf72ae4b04'],
    'smart-home':       ['photo-1543512214-318c7553f230', 'photo-1567581935884-3349723552ca'],
    'cameras':          ['photo-1516035069371-29a1b244cc32', 'photo-1502920917128-1aa500764b6f'],
    'electronics':      ['photo-1593359677879-a4bb92f4834c', 'photo-1607853202273-797f1c22a38e'],
    "men's-clothing":   ['photo-1542272604-787c3835535d', 'photo-1586790170083-2f9ceadc732d'],
    "women's-clothing": ['photo-1595777457583-95e059d581b8', 'photo-1576566588028-4147f3842f27'],
    'shoes':            ['photo-1549298916-b41d501d3772', 'photo-1606107557049-31d8a3c2dc30'],
    'accessories':      ['photo-1434494878577-86c23bcb06b9', 'photo-1523275335684-37898b6baf30'],
    'fashion':          ['photo-1542272604-787c3835535d', 'photo-1595777457583-95e059d581b8'],
    'furniture':        ['photo-1555041469-a586c61ea9bc', 'photo-1586023492125-27b2c045efd7'],
    'kitchen':          ['photo-1556909114-f6e7ad7d3136', 'photo-1570968915860-54d5c301fa9f'],
    'fitness':          ['photo-1544367567-0f2fcb009e0b', 'photo-1571019613454-1cb2f99b2d8b'],
    'skincare':         ['photo-1576426863848-c21f53c60b19', 'photo-1556228724-74a3f7e3f904'],
    'makeup':           ['photo-1586495777744-4e6232bf8a59', 'photo-1512496015851-a90fb38ba796'],
    'board-games':      ['photo-1610890716171-6b1bb98ffd09', 'photo-1611996575749-79a3a250f948'],
    'action-figures':   ['photo-1585366119957-e9730b6d0f60', 'photo-1518770660439-4636190af475'],
    'pet-supplies':     ['photo-1589924691995-400dc9ecc119', 'photo-1587300003388-59208cc962cb'],
}

_BASE_URL = 'https://images.unsplash.com/{photo_id}?w={w}&h={h}&fit=crop&auto=format&q=80'


@register.simple_tag
def product_image(product, width=400, height=300):
    if product.image:
        return product.image.url

    slug = getattr(product, 'slug', '')
    photo_id = _PRODUCT_IMAGE_MAP.get(slug)

    if not photo_id:
        cat_slug = ''
        if product.category:
            cat_slug = getattr(product.category, 'slug', '').lower()
            if not cat_slug and product.category.name:
                from django.utils.text import slugify
                cat_slug = slugify(product.category.name)

        pool = _CATEGORY_FALLBACKS.get(cat_slug, [])
        if not pool and product.category and product.category.parent:
            parent_slug = getattr(product.category.parent, 'slug', '').lower()
            pool = _CATEGORY_FALLBACKS.get(parent_slug, [])

        if pool:
            idx = hash(slug) % len(pool)
            photo_id = pool[idx]

    if photo_id:
        return _BASE_URL.format(photo_id=photo_id, w=width, h=height)

    return f'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w={width}&h={height}&fit=crop&auto=format&q=80'
