import cv2
import numpy as np

# Load the images with alpha channel
image1 = cv2.imread('deer_trans_bg_1.png', cv2.IMREAD_UNCHANGED)
#  Load image with no alpha channel
image2 = cv2.imread('test.jpg', cv2.IMREAD_UNCHANGED)

# Ensure both images have the same size
# Resize image2 to image1 size if necessary
image2 = cv2.resize(image2, (image1.shape[1], image1.shape[0]))

# Split the channels of both images
b1, g1, r1, a1 = cv2.split(image1)
b2, g2, r2 = cv2.split(image2)

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

# Save the resulting image
cv2.imwrite('blended_image.png', blended_image)
