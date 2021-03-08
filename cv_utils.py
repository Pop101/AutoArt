import requests
import random
import cv2
import numpy as np

def cv_img_from_url(url):
    req = requests.get(url, stream=True).raw
    image = np.asarray(bytearray(req.read()), dtype="uint8")
    return cv2.imdecode(image, cv2.IMREAD_COLOR)

def cv_img_from_query(query, key):
    req = requests.get('https://pixabay.com/api/?'+
                        'key='+str(key)+
                        '&q='+str(query).replace(' ','+')+
                        #basic safety settings
                        '&image_type=photo&orientation=horizontal&min_height=700&safesearch=true&'+
                        #try and get the most liked results
                        '&page=1&per_page=10&order=popular')
    req.raise_for_status(); req = req.json()
    if len(req['hits']) == 0: return None
    url = random.choice(req['hits'])['largeImageURL']
    return cv_img_from_url(url)

def resize(img, scale:float = 0.5, px:int = -1):
    if px >= 0: scale = px / max(img.shape[0:2])
    if px > 1: return cv2.resize(img.copy(), (int(img.shape[1] * scale), int(img.shape[0] * scale)), interpolation = cv2.INTER_AREA)
    else: return cv2.resize(img.copy(), (int(img.shape[1] * scale), int(img.shape[0] * scale)), interpolation = cv2.INTER_AREA)

def setsize(img, width, height, x=0, y=0):
    shape = (height, width, img.shape[2]) if len(img.shape) >= 2 else (height, width)

    canvas = np.zeros(shape, dtype=np.uint8)
    frame = (min(img.shape[0], shape[0]-y), min(img.shape[1], shape[1]-x))
    canvas[y:frame[0]+y, x:frame[1]+x] = img[0:frame[0], 0:frame[1]]

    return canvas

# does not work on black and white images
def overlay_transparent(background, overlay, x, y):
    # If the overlay has no alpha, give it some
    if len(overlay.shape) >= 2 and overlay.shape[2] < 4:
        b, g, r = cv2.split(overlay)
        alpha = 255 * np.ones(b.shape, np.uint8)
        overlay = cv2.merge((b,g,r,alpha))
    
    # Move and fix overlay size to match background
    overlay = setsize(overlay.copy(), background.shape[1], background.shape[0], x=x, y=y)

    # Extract alpha channel, set to 0-1 (to multiply)
    alpha = overlay[:, :, 3] / 255.0

    # Median blur alpha channel based on size to make it look good
    alpha = cv2.medianBlur(alpha, int(int(max(background.shape[0:2])/800)/2)+1) # 2nd arg must be odd
    
    if len(background.shape) >= 3 and background.shape[2] == 3: # if background has no alpha
        result = np.zeros((background.shape[0], background.shape[1], 3), np.uint8)
        result[:, :, 0] = (1 - alpha) * background[:, :, 0] + alpha * overlay[:, :, 0]
        result[:, :, 1] = (1 - alpha) * background[:, :, 1] + alpha * overlay[:, :, 1]
        result[:, :, 2] = (1 - alpha) * background[:, :, 2] + alpha * overlay[:, :, 2]
        return result
    elif len(background.shape) >= 3 and background.shape[2] == 4: # if background has alpha
        result = np.zeros((background.shape[0], background.shape[1], 4), np.uint8)
        result[:, :, 0] = (1 - alpha) * background[:, :, 0] + alpha * overlay[:, :, 0]
        result[:, :, 1] = (1 - alpha) * background[:, :, 1] + alpha * overlay[:, :, 1]
        result[:, :, 2] = (1 - alpha) * background[:, :, 2] + alpha * overlay[:, :, 2]
        result[:, :, 3] = 255 * np.clip(background[:, :, 3] + overlay[:, :, 3], 0, 1)
        return result

def upload_file(path):
    with open(path, 'rb') as file:
        r = requests.post('https://transfer.sh/', files={'pxeconfig': file})
    return r.text.strip()