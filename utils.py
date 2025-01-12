import requests
import re

def get_title_from_url(url, max_bytes=4096):
    """
    Retrieves title from given url
    first tries to get title from head request
    then from content - minimizing data transfer by checking during chunk download

    :param url: the URL of the webpage to get the title from
    :param max_bytes: the maximum number of bytes to download from the webpage - default is 4096
    :return: the title of the webpage or None if not found or an error occurs
    """
    try:
        head_response = requests.head(url, timeout=5)
        head_response.raise_for_status()

        if 'title' in head_response.headers:
            return head_response.headers['title']

        with requests.get(url, stream=True, timeout=10) as response:
            response.raise_for_status()

            content = b''
            for chunk in response.iter_content(chunk_size=512):
                if not chunk:  # Handle empty chunks (end of stream)
                    break

                content += chunk
                html_content = content.decode('utf-8', errors='ignore')

                title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
                if title_match:
                    return title_match.group(1).strip()

                if len(content) > max_bytes:
                    break

            return None # Return None if title not found after reaching max_bytes

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

