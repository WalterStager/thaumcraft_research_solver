import os
import cv2 as cv
import numpy as np
from matplotlib import pyplot as plt

# Read main image in color so we can convert to HSV
img_bgr = cv.imread('example.png', cv.IMREAD_COLOR)
assert img_bgr is not None, "file could not be read, check example.png"

ratio = 0.0008012820512
img_size = img_bgr.shape[0] * img_bgr.shape[1]
template_size = 50*50
resize_ratio = template_size / ratio
resize_percentage = resize_ratio / img_size
print("resize percentage", resize_percentage)

# Resize the color image, then produce an HSV copy for matching
img_bgr = cv.resize(img_bgr, (int(img_bgr.shape[1] * resize_percentage), int(img_bgr.shape[0] * resize_percentage)), dst=None, interpolation=cv.INTER_CUBIC)
img_hsv = cv.cvtColor(img_bgr, cv.COLOR_BGR2HSV)

# Visualization image (draw rectangles on BGR)
show_ver = img_bgr.copy()

# Methods to combine
method_names = ['TM_CCOEFF_NORMED', 'TM_CCORR_NORMED', 'TM_SQDIFF_NORMED']
methods = [getattr(cv, name) for name in method_names]

for template_file in os.listdir("templates"):
    fullpath = os.path.join("templates", template_file)
    # process only files that are actual PNG files in the templates folder
    if not os.path.isfile(fullpath) or not template_file.lower().endswith(".png"):
        continue

    # Read template in color and convert to HSV to match the main-image HSV
    template_bgr = cv.imread(fullpath, cv.IMREAD_COLOR)
    assert template_bgr is not None, f"file could not be read, check templates/{template_file}"
    template_hsv = cv.cvtColor(template_bgr, cv.COLOR_BGR2HSV)
    w, h = template_hsv.shape[1], template_hsv.shape[0]

    # Compute per-method normalized scores, invert SQDIFF so higher == better, then average
    accum = None
    for method in methods:
        res = cv.matchTemplate(img_hsv, template_hsv, method)
        # normalize to [0,1]
        resf = res.astype(np.float32)
        mn, mx = float(resf.min()), float(resf.max())
        if mx - mn > 1e-6:
            normed = (resf - mn) / (mx - mn)
        else:
            normed = np.zeros_like(resf, dtype=np.float32)
        # invert SQDIFF so higher is better
        if method in [cv.TM_SQDIFF, cv.TM_SQDIFF_NORMED]:
            normed = 1.0 - normed
        if accum is None:
            accum = normed
        else:
            accum = accum + normed

    combined = accum / float(len(methods))

    # find best location on combined map (higher == better now)
    min_val, max_val, min_loc, max_loc = cv.minMaxLoc(combined)
    top_left = max_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)
    cv.rectangle(show_ver, top_left, bottom_right, (0, 0, 255), 1)

# Convert BGR->RGB for matplotlib display
show_rgb = cv.cvtColor(show_ver, cv.COLOR_BGR2RGB)
plt.imshow(show_rgb)
plt.title(f'Detected boxes'), plt.xticks([]), plt.yticks([])
plt.suptitle('+'.join(method_names))

plt.show()

# 61                wrong
# TM_CCOEFF         33
# TM_CCOEFF_NORMED  28
# TM_CCORR_NORMED   28   
# TM_SQDIFF_NORMED  32