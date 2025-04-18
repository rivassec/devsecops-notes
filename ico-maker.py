from PIL import Image

img = Image.open("content/images/avatar.png")
img.save("content/images/favicon.ico", format="ICO", sizes=[(32, 32)])
