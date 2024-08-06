from PIL import Image

# Open the JPG image
img = Image.open("test.jpg").convert("RGBA")

# Convert to PNG and save
img.save("test.png", "PNG")
