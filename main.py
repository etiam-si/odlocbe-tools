import os
import re
from PyPDF2 import PdfReader
import argparse
import json
import glob

def validate_emso(emso):
    """
    Accepts an iterable of at least 12 digits and returns the number
    as a 13 digit string with a valid 13th control digit.
    Details about computation in
    http://www.uradni-list.si/1/objava.jsp?urlid=19998&stevilka=345
    """
    emso_factor_map = [7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    control_digit = sum([int(emso[i]) * emso_factor_map[i] for i in range(12)]) % 11
    control_digit = 0 if control_digit == 0 else 11 - control_digit
    return control_digit == int(emso[12])

def find_valid_emso(text):
    """
    Scans the input text for 13-digit numbers.
    It returns the first number found and the result of its validation.
    
    :param text: String to search within
    :return: A tuple (emso, is_valid, message) or (None, False, "No 13-digit number found")
    """
    # Find all 13-digit numbers (including those starting with 0)
    numbers = re.findall(r'\b\d{13}\b', text)
    
    if not numbers:
        return None, False, "No 13-digit number found"

    # Return the first number found, along with its validation status
    first_number = numbers[0]
    is_valid = validate_emso(first_number)
    
    return first_number, is_valid


def get_stevilka(text):
    """
    Extracts the Številka from text without using regex.
    Returns the first number found after 'Številka:' or None.
    """
    key = "Številka:"
    start = text.find(key)
    if start == -1:
        return None  # not found
    start += len(key)  # move past 'Številka:'
    
    # read until the end of the line
    end = text.find("\n", start)
    if end == -1:
        end = len(text)
    
    # extract and strip spaces
    stevilka = text[start:end].strip()
    return stevilka

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text from all pages of a PDF file using PyPDF2.

    Args:
        pdf_path: The absolute or relative path to the PDF file.

    Returns:
        A string containing the concatenated text from all pages.
        Returns an empty string if the file is not found or an error occurs.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at '{pdf_path}'")
        return ""

    # The PdfReader is the main object for interacting with a PDF
    # We use a 'with' statement to ensure the file is closed automatically
    try:
        with open(pdf_path, "rb") as file:
            # strict=False can prevent errors with some non-standard PDFs
            reader = PdfReader(file, strict=False)
            print(f"The PDF has {len(reader.pages)} page(s).")

            full_text = []
            # Iterate through each page in the PDF
            for i, page in enumerate(reader.pages):
                # The extract_text() method gets the text content from the page
                text = page.extract_text()
                if text:
                    full_text.append(text)
                else:
                    print(f"Warning: No text found on page {i + 1}.")
            
            return "\n".join(full_text)
    except Exception as e: # Catches potential PyPDF2 errors like malformed PDFs
        print(f"An error occurred while reading the PDF: {e}")
        return ""

def process_pdf(pdf_path):
    """Processes a single PDF file to extract information."""
    print(f"Processing '{pdf_path}'...")
    extracted_text = extract_text_from_pdf(pdf_path)
    if not extracted_text:
        return None
    
    emso, is_emso_valid = find_valid_emso(extracted_text)
    stevilka = get_stevilka(extracted_text)
    
    return {
        "fileName": os.path.basename(pdf_path),
        "stevilkaDokumenta": stevilka,
        "emso": emso,
        "emsoIsValid": is_emso_valid
    }

def main():
    """Main function to parse arguments and process files."""
    parser = argparse.ArgumentParser(
        description="Extracts EMŠO and Številka from PDF files and outputs to JSON."
    )
    parser.add_argument("path", help="Path to a PDF file or a directory containing PDF files.")
    parser.add_argument(
        "-o", "--output", 
        default="output.json", 
        help="Path for the output JSON file (default: output.json)."
    )
    args = parser.parse_args()

    input_path = args.path
    pdf_files_to_process = []

    if not os.path.exists(input_path):
        print(f"Error: Path '{input_path}' does not exist.")
        return

    if os.path.isdir(input_path):
        pdf_files_to_process = glob.glob(os.path.join(input_path, '*.pdf'))
        print(f"Found {len(pdf_files_to_process)} PDF files in '{input_path}'.")
    elif os.path.isfile(input_path) and input_path.lower().endswith('.pdf'):
        pdf_files_to_process.append(input_path)
    else:
        print(f"Error: Provided path '{input_path}' is not a PDF file or a directory.")
        return

    results = []
    for pdf_file in pdf_files_to_process:
        data = process_pdf(pdf_file)
        if data:
            results.append(data)

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"\nProcessing complete. Results saved to '{args.output}'.")

if __name__ == "__main__":
    main()
