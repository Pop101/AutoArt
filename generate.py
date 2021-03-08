import requests, random
import urllib3.exceptions
import cv2
import glob
from cv_utils import *
import numpy as np

PIXABAY_KEY = open('./pixabay_key.txt','r').read()
assert '<KEY>' not in PIXABAY_KEY, "Please add your pixabay key. Get one here: https://pixabay.com/accounts/login/?next=/api/docs/"

def glob_images(dir='./'):
    files = list()
    for ext in ('*.png','*.jpg','*.jpeg'):
        files.extend(glob.glob(f'{dir}/{ext}'))
    return files

def apply_random_stickers(img, dir, num=1):
    pngs = glob_images('./Overlays/')
    for i in range(num):
        sticker = cv2.imread(random.choice(pngs), cv2.IMREAD_UNCHANGED)
        sticker = resize(sticker, px=max(img.shape[0:2])/6)
        sticker = setsize(sticker, height=img.shape[0], width=img.shape[1])

        x = random.randint(int(0.00*img.shape[1]), int(1*img.shape[1]))
        y = random.randint(int(0.00*img.shape[0]), int(1*img.shape[0]))
        
        img = overlay_transparent(img, sticker, x=x, y=y)
    return img

def apply_style(image, style, is_url, verbose=True, retries=10, use_proxies=True, set_proxy=''):
    """
    Transfers the style from one image onto another using deepai.org's service
    Parameters
    ----------
    image : np.array or str
        The opencv image or url that will be modified
    style : np.array or str
        The opencv image or url that will be applied
    is_url : bool
        If the image and style should be interpreted as a url or as an opencv image
    verbose : bool
        If the function should print information as it runs
    retries : int
        How many times it should retry with different proxies
    use_proxies : bool
        If the method should use proxies. Recommended, as deepai blocks multiple requests from a single ip
    set_proxy : str
        If set, will attempt this proxy first before other proxies
    Returns
    ----------
    str
        The URL of the image with the style applied
    str
        The proxy used
    """

    # Pick a proxy to use api for free (yeah it's cheap)
    proxy_req = requests.get('https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=elite&simplified=true')
    proxies = [str(x).strip() for x in (random.choices(proxy_req.text.split('\n'), k=retries) if retries < len(proxy_req.text.split('\n')) else proxy_req.text.split('\n'))]
    if len(set_proxy) > 0: proxies[0] = set_proxy

    # Construct api request
    api_req_kwargs = {'headers': {'api-key': 'quickstart-QUdJIGlzIGNvbWluZy4uLi4K'}}
    if is_url:
        api_req_kwargs['data'] = {
            'content': image,
            'style': style
        }
    else:
        api_req_kwargs['files'] = {
            'content': open(image, 'rb').read(),
            'style': open(style, 'rb').read(),
        }
    
    # Print the arguments (but not file binary)
    if verbose:
        if not is_url:
            override_dict = {'files': {'content': 'Binary for ./Output/processed.png', 'style': f'Binary for {style}'}}
            print('Request arguements:', {**api_req_kwargs, **override_dict})
        else: print('Request arguements:', api_req_kwargs)

    # Retry request with many proxies until retries or success
    i, url = 0, None
    while url == None and i < retries:
        proxy = proxies[i]
        try:
            # Apply proxy
            api_req_kwargs['proxies'] = {
                'http': proxy,
                'https': proxy
            }
            
            # Send request
            req = requests.post("https://api.deepai.org/api/fast-style-transfer", **api_req_kwargs)

            # Attempt parse
            if verbose: print('Response:', req.json())
            if 'output_url' in req.json(): url = req.json()['output_url']
        except (urllib3.exceptions.NewConnectionError, 
                urllib3.exceptions.MaxRetryError,
                requests.exceptions.ProxyError,
                requests.exceptions.SSLError):
            if verbose: print('Error with proxy', proxy)
        finally:
            i += 1
    
    if verbose: print('Success with proxy', proxy)
    del api_req_kwargs # Just in case (don't want to keep files in memory under any circumstance)
    if url == None: raise Exception('Error Applying Style with all proxies')
    return url, proxy

def generate_image(query, overlays=20, verbose=True, retries=10, intermediate_uploads=True):
    """
    Searches for an image by query, puts overlays on it, and applies a random style to generate art
    Parameters
    ----------
    query : str
        The query that will be searched for to get the initial image
    overlays : int
        How many images from ./Overlays/ should be applied
    verbose : bool
        If the function should print information as it runs
    retries : int
        How many times it should retry with different proxies
    intermediate_uploads : bool
        If intermediate images should be uploaded to transfer.sh (may speed up multiple proxy retries, but more detectable)
    Returns
    ----------
    str
        The URL of the image with the style applied
    """

    # Grab image from query
    img = cv_img_from_query(query, PIXABAY_KEY)

    # Save
    cv2.imwrite('./Output/raw.png', img)

    # Slap some stickers over it
    img = apply_random_stickers(img, './Overlays/', num=overlays)

    # Pick a background for pngs
    background = random.choice(glob_images('./Underlays/'))
    background = cv2.imread(background, cv2.IMREAD_UNCHANGED)
    background = resize(background, scale=max(img.shape[0:2])/min(background.shape[0:2])) # make big
    background = setsize(background, img.shape[1], img.shape[0]) # crop down
    img = overlay_transparent(background, img, 0, 0) # put it under the image

    # Enhance contrast
    cv2.addWeighted(img, 1.2, img, 0, -60)

    # Save
    cv2.imwrite('./Output/processed.png', img)
    if verbose: print('Created Image:', './Output/processed.png')

    # Pick a style
    styles = glob_images('./Styles/')
    style = random.choice(styles)
    if verbose: print('Style chosen:', style)

    # Upload images to secondary service
    if intermediate_uploads:
        img_url = upload_file('./Output/processed.png')
        if verbose: print('Image uploaded to', img_url)

        style_url = upload_file(style)
        if verbose: print('Style uploaded to', style_url)

    url, proxy = apply_style(
        img_url if intermediate_uploads else './Output/processed.png',
        style_url if intermediate_uploads else style,
        intermediate_uploads,
        verbose,
        retries
    )

    styled_img = cv_img_from_url(url)
    cv2.imwrite('./Output/final.png', styled_img)

if __name__ == '__main__':
    generate_image(input('Prompt: '), overlays=int(input('Number of Stickers: ')))

    cv2.imshow('Prompt', cv2.imread('./Output/raw.png'))
    cv2.imshow('Stickered', cv2.imread('./Output/processed.png'))
    cv2.imshow('Generated', cv2.imread('./Output/final.png'))
    cv2.waitKey(0)