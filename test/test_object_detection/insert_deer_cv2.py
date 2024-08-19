import cv2
import numpy as np

# Load the images with alpha channel
img_add = cv2.imread('deer_trans_bg_1.png', cv2.IMREAD_UNCHANGED)
#  Load image with no alpha channel
img_bg = cv2.imread('test.jpg', cv2.IMREAD_UNCHANGED)

# Debug
print("img_add: "+str(img_add.shape))
print("img_bg:  "+str(img_bg.shape))

# Split the channels of both images
b1, g1, r1, a1 = cv2.split(img_add)
b2, g2, r2 = cv2.split(img_bg[0:img_add.shape[0],0:img_add.shape[1]])
    
print(b1.shape)
print(b2.shape)
#exit

# Define a custom function
def custom_operation(x, y, a):
    return y if a==0 else x

# Apply the custom function element-wise using vectorize
vectorized_operation = np.vectorize(custom_operation)
b = vectorized_operation(b1, b2, a1)
g = vectorized_operation(g1, g2, a1)
r = vectorized_operation(r1, r2, a1)

# Merge the blended channels back into a single image
blended_image = cv2.merge([b, g, r])

# Add to background
img_bg_new = img_bg
img_bg_new[0:img_add.shape[0],0:img_add.shape[1]] = blended_image

# Save the resulting image
cv2.imwrite('blended_image.png', img_bg_new)
