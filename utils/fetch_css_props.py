#!/usr/bin/python3


import requests
from lxml import etree
from time import sleep
from sys import stderr


def extract_links_from_page(url):
	# Fetch the page
	response = requests.get(url)
	response.raise_for_status()  # Raise an error for bad status codes

	# Parse the XML content
	tree = etree.fromstring(response.content, etree.HTMLParser())

	# Find the <span> containing exactly the text "CSS Properties" within an <a>
	spans = tree.xpath('//a[span[text()="CSS Properties"]]/span[text()="CSS Properties"]')
	
	if not spans:
		raise ValueError("No <span/> with text 'CSS Properties' found within an <a/> tag.")
	
	# Move to the next element after the <a> which should be an <ul>
	for span in spans:
		#print(span)
		a_element = span.getparent()
		next_element = a_element.getnext()
		
		if next_element is not None and next_element.tag == "ul":
			# Extract href attributes from <a> tags within <li> elements
			for li in next_element.xpath('.//li'):
				a_tag = li.find('a')
				if a_tag is not None and 'href' in a_tag.attrib and a_tag.attrib['href'].startswith('/'):
					yield a_tag.text, a_tag.attrib['href']
		else:
			print(f"The next element after the <a> is not an <ul/> but {'<'+next_element.tag+'>' if next_element is not None else 'None'}/>.", file=stderr)


def extract_dd_content_from_subpage(url):
	# Fetch the subpage
	response = requests.get(url)
	response.raise_for_status()  # Raise an error for bad status codes
	
	# Parse the XML content
	tree = etree.fromstring(response.content, etree.HTMLParser())
	
	# Find the <div> with id attribute equal to "cssproperties"
	div = tree.xpath('//div[@id="cssproperties"]')
	
	if not div:
		print("No <div> with id 'cssproperties' found.", file=stderr)
		return "", "no"
	
	# Find the <dl> table inside the div
	dl = div[0].xpath('.//dl')
	
	if not dl:
		print("No <dl> table found inside the <div>.", file=stderr)
		return "", "no"
	
	# Extract the text content of the first and third <dd> elements
	dd_elements = dl[0].xpath('.//dd')
	if len(dd_elements) < 3:
		print("The <dl> table does not contain enough <dd> elements.", file=stderr)
		return "", "no"
	
	first_dd_content = dd_elements[0].text.strip()
	third_dd_content = dd_elements[2].text.strip()
	
	return first_dd_content, third_dd_content


# Example usage
url = 'https://www.cssportal.com'
n = 0
for propname, link in extract_links_from_page(url + '/css-properties'):
	initial, inheritable = extract_dd_content_from_subpage(url + link)
	print(f"			'{propname}': ('{initial}', {inheritable.lower() == 'yes'}),", flush=True)
	sleep(1)
	#if n > 5: break
	n += 1

