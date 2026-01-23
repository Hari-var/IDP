import os
from PIL import Image, ImageSequence
import re
from bs4 import BeautifulSoup
import cv2
import numpy as np
import docx2txt
import pandas as pd
# from sentence_transformers import SentenceTransformer
# from sklearn.cluster import AgglomerativeClustering
import numpy as np
import extract_msg
from app.helpers.config import BASE_DIR
from email import policy
from email.parser import BytesParser
from app import process
from PyPDF2 import PdfReader
import regex as re
# import google.generativeai as genai 
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from app.helpers.config import endpoint as AZURE_ENDPOINT, key as AZURE_KEY

doc_client = DocumentIntelligenceClient(
    endpoint=AZURE_ENDPOINT,
    credential=AzureKeyCredential(AZURE_KEY)
)


# def get_gemini_response(user_message):
    
#     try:
#         genai.configure(api_key='AIza')
#         model = genai.GenerativeModel('gemini-2.5-flash')  # Ensure the model name is correct
#         response = model.generate_content(f"You are a helpful assistant. User: {user_message}")
#         if response and hasattr(response, 'candidates') and len(response.candidates) > 0:
#             answer = response.candidates[0].content.parts[0].text
#             return answer
#         else:
#             return "Sorry, I couldn't get a response from Gemini. Please try again."
#     except Exception as e:
        
#         return f"Error: {str(e)}"


def pil_to_bytes(image):
    from io import BytesIO
    buf = BytesIO()
    Image.fromarray(image).save(buf, format="PNG")
    return buf.getvalue()

def read_eml(file_path, chars_per_page=1000):
    # Read and parse the EML file
    with open(file_path, 'rb') as f:
        msg = BytesParser(policy=policy.default).parse(f)

    # Try to extract plain text
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/plain':
                text = part.get_content()
                break
        else:
            text = msg.get_body(preferencelist=('plain')).get_content()
    else:
        text = msg.get_content()

    # Split into "pages" based on character count
    pages = [text[i:i+chars_per_page] for i in range(0, len(text), chars_per_page)]

    return pages

# Usage
# file_path = "C:\\Users\\ShashankTudum\\OneDrive - ValueMomentum, Inc\\Documents\\IDP-LLM\\claim_submission.eml"  # Path to your EML file
# pages = read_eml(file_path)

# # Display the pages
# for i, page in enumerate(pages, start=1):
#     print(page)



def pdf_to_text(pdf_path):
        """code to read the pdf data from the given file"""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text

# def cluster_paragraphs(paragraphs, model_name='all-MiniLM-L6-v2', relax_pages=1):
#     """Cluster paragraphs sequentially with boundary relaxation"""
#     model = SentenceTransformer(model_name)
#     embeddings = model.encode(paragraphs)
    
#     # Initial clustering
#     clustering = AgglomerativeClustering(
#         n_clusters=None,
#         metric='cosine', # cosine, euclidean, manhattan - cosine is used for sentence embeddings, euclidean for word embeddings, manhattan for BERT embeddings
#         linkage='average', # average, complete, single - average is used for sentence embeddings, complete for word embeddings, single for BERT embeddings
#         distance_threshold=0.65, # lower this value to get more clusters
#     )
#     labels = clustering.fit_predict(embeddings)
    
#     # Find sequential boundaries
#     boundaries = []
#     current_label = labels[0]
#     start_idx = 0
    
#     for i in range(1, len(labels)):
#         if labels[i] != current_label:
#             boundaries.append((start_idx, i-1))
#             start_idx = i
#             current_label = labels[i]
#     boundaries.append((start_idx, len(labels)-1))
    
#     # Relax boundaries
#     relaxed_boundaries = []
#     prev_end = -1
    
#     for i, (start, end) in enumerate(boundaries):
#         # Don't relax the start of first cluster
#         if i == 0:
#             new_start = start
#         else:
#             # Try to extend start backwards up to relax_pages
#             potential_start = max(prev_end - relax_pages + 1, prev_end + 1)
#             new_start = potential_start
            
#         # Don't relax the end of last cluster    
#         if i == len(boundaries) - 1:
#             new_end = end
#         else:
#             # Try to extend end forward up to relax_pages
#             next_start = boundaries[i+1][0]
#             potential_end = min(end + relax_pages, next_start)
#             new_end = potential_end
            
#         relaxed_boundaries.append((new_start, new_end))
#         prev_end = new_end
        
#     # Create final clusters based on relaxed boundaries
#     final_clusters = []
#     for start, end in relaxed_boundaries:
#         cluster_items = [(i, paragraphs[i]) for i in range(start, end + 1)]
#         final_clusters.append(cluster_items)
        
#     return final_clusters

def extract_key_value_pairs(lines, x_tolerance=50):
    key_value_pairs = []
    for line in lines:
        median_x = pd.Series([word['x1'] for word in line]).median()
        key_words = [word for word in line if word['x1'] <= median_x - x_tolerance]
        value_words = [word for word in line if word['x1'] > median_x + x_tolerance]
        
        # If we have key and value in the line
        if key_words and value_words:
            key_text = ' '.join([w['text'] for w in key_words])
            value_text = ' '.join([w['text'] for w in value_words])
            key_value_pairs.append((key_text.strip(), value_text.strip()))
        else:
            # Handle cases where key or value spans the entire line
            line_text = ' '.join([w['text'] for w in line])
            key_value_pairs.append((None, line_text.strip()))
    
    return key_value_pairs


def preprocessImage(image):
    # Ensure image is in RGB mode
    if image.mode != "RGB":
        image = image.convert("RGB")

    new_size = (image.width * 2, image.height * 2)
    image_rescaled = image.resize(new_size, Image.Resampling.LANCZOS)
    np_image_rescaled = np.array(image_rescaled)

    gray_image = cv2.cvtColor(np_image_rescaled, cv2.COLOR_RGB2GRAY)  # Use RGB, not BGR

    blurred_image = cv2.GaussianBlur(gray_image, (3, 3), 0)
    binary_image = cv2.adaptiveThreshold(
        blurred_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 37, 1
    )
    return binary_image


def group_words_into_lines(words, y_tolerance=10):
    # Sort words by their vertical position
    words = sorted(words, key=lambda w: w['center_y'])
    
    lines = []
    current_line = []
    current_y = None
    
    for word in words:
        if current_y is None:
            current_y = word['center_y']
        
        if abs(word['center_y'] - current_y) <= y_tolerance:
            current_line.append(word)
        else:
            # Sort current line words by x position
            current_line = sorted(current_line, key=lambda w: w['x1'])
            lines.append(current_line)
            current_line = [word]
            current_y = word['center_y']
    
    if current_line:
        current_line = sorted(current_line, key=lambda w: w['x1'])
        lines.append(current_line)
    
    return lines



def parse_hocr(hocr_content):
    soup = BeautifulSoup(hocr_content, 'html.parser')
    
    # Extract words with their bounding boxes
    words = []
    for span in soup.find_all('span', class_='ocrx_word'):
        text = span.get_text()
        # Extract bounding box coordinates
        title = span['title']
        bbox = re.search(r'bbox (\d+) (\d+) (\d+) (\d+);', title)
        if bbox:
            x1, y1, x2, y2 = map(int, bbox.groups())
            words.append({
                'text': text,
                'x1': x1,
                'y1': y1,
                'x2': x2,
                'y2': y2,
                'center_y': (y1 + y2) / 2,
                'center_x': (x1 + x2) / 2
            })
    
    print(words)
    return words


def extract_information(hocr_content):
    words = parse_hocr(hocr_content)
    lines = group_words_into_lines(words)
    key_value_pairs = extract_key_value_pairs(lines)
    
    # Remove pairs where both key and value are None or empty
    key_value_pairs = [pair for pair in key_value_pairs if pair[0] or pair[1]]
    
    print(key_value_pairs)
    return key_value_pairs


def extract_text(image, config, timeout=30):
    """
    Azure OCR replacement for pytesseract.image_to_string
    image_bytes: bytes (open(file, 'rb').read())
    """
    try:
        poller = doc_client.begin_analyze_document(
            model_id="prebuilt-read",
            body=image
        )

        result = poller.result(timeout=timeout)

        lines = []
        for page in result.pages:
            for line in page.lines:
                lines.append(line.content)

        return "\n".join(lines)

    except Exception as e:
        print(f"Basic text extraction failed: {str(e)}")
        return ""
def extract_and_process_hocr(image, config, timeout=30):
    hocr = ["<html><body>"]
    try:
        for page in image.pages:
            hocr.append(f'<div class="ocr_page" id="page_{page.page_number}">')

            for i, line in enumerate(page.lines):
                bbox = line.polygon
                if bbox:
                    xs = [p.x for p in bbox]
                    ys = [p.y for p in bbox]
                    bbox_str = f"{int(min(xs))} {int(min(ys))} {int(max(xs))} {int(max(ys))}"
                else:
                    bbox_str = "0 0 0 0"

                hocr.append(
                    f'<span class="ocr_line" id="line_{i}" title="bbox {bbox_str};">'
                    f'{line.content}</span>'
                )

            hocr.append("</div>")

        hocr.append("</body></html>")
        return "\n".join(hocr)
    except Exception as e:
        print(f"OCR extraction failed: {str(e)}")
        return extract_text(image, config, timeout)


def tif_process(file_path):
    with Image.open(file_path) as img:
        return [page.copy() for page in ImageSequence.Iterator(img)]
    
    
def batch_process_ocr_text_extraction(batch_data):
    result = []
    idx, images = batch_data
    for image in images:
        try:
            final_image = preprocessImage(image)
            image_bytes = pil_to_bytes(final_image)
            config = '--oem 3 --psm 12'
            # Try with initial short timeout
            extracted_text = extract_text(image_bytes, config, timeout=30)
            if not extracted_text.strip():
                # If failed, retry with longer timeout
                extracted_text = extract_text(image_bytes, config, timeout=60)
            result.append(extracted_text)
        except Exception as e:
            print(f"OCR processing error: {str(e)}")
            result.append("")
    return idx, result





import os

def count_files_in_folder(folder_path):
    
    if not os.path.isdir(folder_path):
        return None

    file_count = 0
    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        if os.path.isfile(item_path):
            file_count += 1
    return file_count


# Start timer
def operation(file_path,source):
    
    
    extension = os.path.splitext(file_path)[1]
    # doc_types=["Litigation","Police Report","Medical","Demand Letter","Claims Database","Arbitration","Other"]
    if extension  in [".tiff",".jpeg",".jpg",".png"]:
        images = tif_process(file_path)
        page_count=len(images)
        # OCR processing directly
        extracted_text = []
        for image in images:
            text = batch_process_ocr_text_extraction(batch_data=[0, [image]])  # Wrap image in a list
            extracted_text.append(text)
        # print(extracted_text)
        if page_count < 2:
            grouped_texts = extracted_text
            # grouped_page_numbers = [[1]]
        else:
            # grouped_pages = cluster_paragraphs(extracted_text)
            # grouped_pages = [page for page in grouped_pages if page]
            # grouped_page_numbers = [[page[0] for page in cluster] for cluster in grouped_pages]
            # # grouped_texts = ["\n".join([para[1] for para in cluster]) for cluster in grouped_pages]
            grouped_texts = extracted_text
        # [
        #     "\n".join([str(para[1]) if not isinstance(para[1], str) else para[1] for para in cluster])
        #     for cluster in grouped_pages
        # ]
        text=grouped_texts
        # print(text)
    elif extension in [".xls",".XLS"]:
        text=pd.read_excel(file_path,engine="xlrd")
    elif extension in [".docx"]:
        text = docx2txt.process(file_path)
        
    elif extension in [".pdf"]:
        
        text = pdf_to_text(file_path)
        

 
        
    elif extension in [".eml"]:
        text=""
        pages = read_eml(file_path)
        for i, page in enumerate(pages, start=1):
            text=text+page
    elif extension in [".msg"]:
        # output_folder = 'C:\\Users\\ShashankTudum\\OneDrive - ValueMomentum, Inc\\Documents\\IDP-LLM\\msg_attachments'
        output_folder = os.path.join(BASE_DIR, 'msg_attachments')
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        msg = extract_msg.Message(file_path)
        msg_sender = msg.sender
        msg_date = msg.date
        msg_subj = msg.subject
        text = msg.body

        # Get folder name from the msg filename (without extension)
        msg_name = os.path.splitext(os.path.basename(file_path))[0]
        msg_folder = os.path.join(output_folder, msg_name)
        print("msg_folder:", msg_folder)

        # Make sure the folder exists
        if not os.path.exists(msg_folder):
            os.makedirs(msg_folder)

        # Save each attachment inside this folder
        for attachment in msg.attachments:
            if attachment.longFilename:
                attachment_filename, extension = os.path.splitext(attachment.longFilename)

                # Create a consistent filename (no timestamp to avoid duplicates)
                new_filename = f"{msg_name}{attachment_filename}{extension}"
                save_path = os.path.join(msg_folder, new_filename)

                if not os.path.exists(save_path):
                    attachment.save(customPath=msg_folder, customFilename=new_filename)
                    print(f"Saved attachment: {new_filename}")
                else:
                    print(f"Skipped duplicate attachment: {new_filename}")
            else:
                print("Skipping attachment with None filename.")

        msg.close()

        print('Processed file:', file_path)
        print('Sender:', msg_sender)
        print('Sent On:', msg_date)
        print('Subject:', msg_subj)
        print('Body:', text)
        file_count=count_files_in_folder(msg_folder)
        if file_count>0:
            for file in os.listdir(msg_folder):
                full_path = os.path.join(msg_folder, file)
                process.process_file(full_path,source=source) 

    return text

def main():
    file_path = r"C:\practice\Files\uploaded_files\Subrogation029.tiff"  # path to your TIFF file

    # Load TIFF pages
    images = tif_process(file_path)

    # Prepare batch input (single batch example)
    batch_idx = 0
    batch_data = (batch_idx, images)

    # Run OCR batch processing
    idx, ocr_results = batch_process_ocr_text_extraction(batch_data)

    # Handle results
    for page_num, text in enumerate(ocr_results):
        print(f"\n--- Page {page_num + 1} ---")
        print(text)


if __name__ == "__main__":
    main()

    

