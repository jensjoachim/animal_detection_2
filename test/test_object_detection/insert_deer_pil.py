from PIL import Image

# Load the base image and the overlay image
base_image = Image.open("test.jpg").convert("RGBA")
overlay_image = Image.open('deer_trans_bg_0.png').convert("RGBA")

# Print sizes
print("base_image:    "+str(base_image.size))
print("overlay_image: "+str(overlay_image.size))

# Get the size of the base image
base_width, base_height = base_image.size

# Resize overlay image if needed (optional)
# overlay_image = overlay_image.resize((base_width, base_height))

# Position to place the overlay (top-left corner in this example)
position = (0, 0)  # Change this to the desired position

# Create a new image by combining the base image with the overlay
combined_image = Image.alpha_composite(base_image, Image.new("RGBA", base_image.size, (255, 255, 255, 0)))
combined_image.paste(overlay_image, position, overlay_image)

# Save the result
combined_image.save('combined_image.png')

print("Images combined successfully")
