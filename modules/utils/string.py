
def strip_html(html):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)