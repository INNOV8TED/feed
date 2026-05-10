from PIL import Image
import os

def remove_white_bg(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()

    new_data = []
    for item in datas:
        # If the pixel is pure white or very close to it, make it transparent
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)

    img.putdata(new_data)
    img.save(output_path, "PNG")
    print(f"Processed image saved to {output_path}")

if __name__ == "__main__":
    remove_white_bg(r"C:\Users\Stephen Portman\.gemini\antigravity\brain\aa667af6-d0bd-4e78-aca0-68ab04753bbf\media__1778369451540.jpg", "stephen_sleeping.png")
