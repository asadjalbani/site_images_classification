import streamlit as st
import os
import zipfile
import shutil
import requests
import base64
import cv2

# Function to list images in a folder
def list_images_in_folder(folder_path):
    files = os.listdir(folder_path)
    image_extensions = ('.png', '.jpg', '.jpeg')  # Added .jpeg for completeness
    images = [os.path.join(folder_path, file) for file in files if file.lower().endswith(image_extensions)]
    return images

# Find the highest resolution image in a folder
def find_highest_resolution_image(folder_path):
    max_resolution = 0
    max_resolution_image = None
    for image_file in os.listdir(folder_path):
        image_path = os.path.join(folder_path, image_file)
        img = cv2.imread(image_path)
        resolution = img.shape[0] * img.shape[1]
        if resolution > max_resolution:
            max_resolution = resolution
            max_resolution_image = image_path
    return max_resolution_image

# Function to encode image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Function to call the OpenAI API
def chat(image_path, prompt, api_key):
    base64_image = encode_image(image_path)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 300
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    return response.json()

# Streamlit app
st.title('Image Classification Tool')

uploaded_file = st.file_uploader("Upload a ZIP file containing images", type=['zip'])
api_key = 'sk-proj-D9m20mQRP06YvS2TseMxT3BlbkFJ2CmpxvgYmrsR3bmAFN2E'
prompt=f"""You will receive an image, and your job is to classify it into one of the following categories based solely on its content. After analyzing the image, return only the name of the category to which it belongs. Ensure your response is concise, providing only the class name.
Categories:
Site ID: Images that contains the site id number, often used for identification and documentation purposes.
Shelter: Images focusing on shelters located within the site.
Tower Structure: Images showing tower structures, capturing their design and current condition.
Panorama: Broad, panoramic views that cover all installed sectors at the site.
Instructions:
Examine the provided image.
Determine the category that best represents the image.
Respond with the category of image name.
Note: The classification should be accurate and based on clear visual identifiers specific to each category. Avoid extraneous details in your response. if the image does not belong to any category mentioned above return only None"""

if uploaded_file is not None and api_key:
    with st.spinner('Processing...'):
        # Save uploaded zip to temporary path
        with open("temp.zip", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Unzip the file
        if not os.path.exists('extracted_images'):
            os.makedirs('extracted_images')
        
        with zipfile.ZipFile("temp.zip", 'r') as zip_ref:
            zip_ref.extractall('extracted_images')

        # Process images
        images = list_images_in_folder('extracted_images')
        categorized_folders = {}
        for image_path in images:
            category_response = chat(image_path, prompt, api_key)
            category = category_response['choices'][0]['message']['content']
            if category.lower() != 'none':  # Exclude 'None' category
                category_folder = os.path.join('categorized_images', category)
                if not os.path.exists(category_folder):
                    os.makedirs(category_folder)
                shutil.copy(image_path, os.path.join(category_folder, os.path.basename(image_path)))
                categorized_folders[category_folder] = True
        
        # Zip the categorized folders
        shutil.make_archive('categorized_images', 'zip', 'categorized_images')

        # Select and zip high-resolution images separately
        high_res_folder = 'high_resolution_images'
        if not os.path.exists(high_res_folder):
            os.makedirs(high_res_folder)
        for folder in categorized_folders:
            high_res_image = find_highest_resolution_image(folder)
            if high_res_image:
                category_name = os.path.basename(folder)
                high_res_cat_folder = os.path.join(high_res_folder, category_name)
                os.makedirs(high_res_cat_folder, exist_ok=True)
                shutil.copy(high_res_image, high_res_cat_folder)
        shutil.make_archive(high_res_folder, 'zip', high_res_folder)
        
        # Display download links
        with open("categorized_images.zip", "rb") as f:
            st.download_button('Download Categorized Images', f, file_name="categorized_images.zip")
        with open("high_resolution_images.zip", "rb") as f:
            st.download_button('Download High Resolution Images', f, file_name="high_resolution_images.zip")
        
        # Clean up
        shutil.rmtree('extracted_images')
        shutil.rmtree('categorized_images')
        shutil.rmtree('high_resolution_images')
        os.remove("temp.zip")

st.write("Upload a ZIP file to classify images.")
