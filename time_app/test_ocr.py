from PIL import Image
from ocr_utils import extract_bill_text

image = Image.open("sample_bill.jpeg")
text = extract_bill_text(image)

print("Extracted bill text:")
print(text)
