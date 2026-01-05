import io
import zipfile

def unzip_in_memory(zip_content):
    """
    Unzips a ZIP archive from memory and returns a dictionary 
    containing the file names and their content.

    Args:
        zip_content (bytes): The content of the ZIP archive as bytes.

    Returns:
        dict: A dictionary where keys are file names and values are 
              the file contents as bytes.
    """
    in_memory_zip = io.BytesIO(zip_content)
    with zipfile.ZipFile(in_memory_zip, mode='r') as zf:
        return {name: zf.read(name) for name in zf.namelist()}

def unzip_in_memory_file(zip_filepath):
    """
    Unzips a ZIP archive from file and returns a dictionary 
    containing the file names and their content.

    Args:
        zip_filepath (str): The path to the ZIP archive file.

    Returns:
        dict: A dictionary where keys are file names and values are 
              the file contents as bytes.
    """
    with zipfile.ZipFile(zip_filepath) as zf:
        return {name: zf.read(name) for name in zf.namelist()}


def extract_cdata(xml_bytes):
    """
    Extract all CDATA sections from the given XML byte-string.

    Parameters:
        xml_bytes (bytes): A byte-string containing XML data.

    Returns:
        list: A list of strings, each corresponding to the content within a CDATA section.
    """
    # Decode the byte-string to a Unicode string using UTF-8 encoding.
    # This is necessary because the regular expression operates on strings.
    xml_string = xml_bytes #xml_bytes.decode('utf-8')
    
    # Define a regular expression pattern that matches a CDATA section.
    # The pattern looks for literal "<![CDATA[" followed by any characters (non-greedy),
    # until the closing "]]>" is encountered.
    # The re.DOTALL flag ensures that newline characters are also matched by the dot (.).
    pattern = re.compile(r'<!\[CDATA\[(.*?)\]\]>', re.DOTALL)
    
    # Use re.findall to search the entire XML string for non-overlapping matches of the pattern.
    cdata_contents = pattern.findall(xml_string)
    return cdata_contents

def extract_livescript_file( filename ):
    extracted_files = unzip_in_memory_file( filename )
    for name, content in extracted_files.items():
        if name == "matlab/document.xml":
            # print(f"File: {name}, Content: {content[:100]}...")
            # print(f"File: {name}, Content: {content}...")
            xmlstring = f"{content}"
            return (bytes("".join(extract_cdata(xmlstring)), "utf-8").decode("unicode_escape"))

def extract_livescript_code( filecontents ):
    extracted_files = unzip_in_memory( filecontents )
    for name, content in extracted_files.items():
        if name == "matlab/document.xml":
            # print(f"File: {name}, Content: {content[:100]}...")
            # print(f"File: {name}, Content: {content}...")
            xmlstring = f"{content}"
            return (bytes("".join(extract_cdata(xmlstring)), "utf-8").decode("unicode_escape"))
