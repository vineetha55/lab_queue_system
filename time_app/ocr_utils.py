
import re
import pytesseract
from PIL import Image, ImageOps, ImageEnhance, ImageFilter


def extract_bill_text(image_file):
    image = Image.open(image_file)
    image = ImageOps.exif_transpose(image)

    # If your bill is sideways, rotate it manually:
    # image = image.rotate(90, expand=True)

    image = image.convert("L")
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = image.filter(ImageFilter.SHARPEN)

    # Enlarge the image to help read small printed text.
    image = image.resize(
        (image.width * 2, image.height * 2)
    )

    configs = [
        "--oem 3 --psm 4",
        "--oem 3 --psm 6",
        "--oem 3 --psm 11",
    ]

    results = []

    for config in configs:
        data = pytesseract.image_to_data(
            image,
            lang="eng",
            config=config,
            output_type=pytesseract.Output.DICT,
        )

        words = [
            word for word in data["text"]
            if word.strip()
        ]
        results.append(" ".join(words))

    # Return the longest extracted text for inspection.
    return max(results, key=len, default="")
