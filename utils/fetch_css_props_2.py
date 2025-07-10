#!/usr/bin/python3


import requests
from bs4 import BeautifulSoup


def extract_css_property_links(url):
	# Send a GET request to the URL
	response = requests.get(url)

	# Check if the request was successful
	if response.status_code != 200:
		print(f"Failed to retrieve the page. Status code: {response.status_code}")
		return

	# Parse the HTML content using BeautifulSoup
	soup = BeautifulSoup(response.content, 'html.parser')

	# Find all h2 tags with class 'left'
	h2_tags = soup.find_all('h2', class_='left')

	for h2_tag in h2_tags:
		span_tag = h2_tag.find('span', class_='left_h2', string='CSS')
		if span_tag:
			# Check if the next sibling is exactly " Properties"
			next_sibling = span_tag.next_sibling
			if next_sibling and next_sibling.strip() == "Properties":
				break
	else:
		print("The specified h2 tag was not found.")
		return

	for link in h2_tag.next_siblings:
		if link.name == 'a':
			yield link.get_text(), link.get('href')
		elif link.name == 'br':
			return


def extract_css_property_details(url):
	# Send a GET request to the URL
	response = requests.get(url)

	# Check if the request was successful
	if response.status_code != 200:
		print(f"Failed to retrieve the page. Status code: {response.status_code}")
		return None

	# Parse the HTML content using BeautifulSoup
	soup = BeautifulSoup(response.content, 'html.parser')

	# Find the table with class 'ws-table-all'
	table = soup.find('table', class_='ws-table-all')

	if not table:
		print("The specified table was not found.")
		return None

	# Initialize variables to store the extracted details
	default_value = None
	inherited = None
	animatable = None
	css_version = None

	# Iterate over the rows in the table
	for row in table.find_all('tr'):
		header = row.find('th')
		if not header:
			continue

		# Extract the relevant information based on the header text
		if 'Default value:' in header.get_text():
			default_value = row.find('td').get_text(strip=True)
		elif 'Inherited:' in header.get_text():
			inherited = row.find('td').get_text(strip=True).lower() == 'yes'
		elif 'Animatable:' in header.get_text():
			animatable_text = row.find('td').get_text(strip=True).lower()
			animatable = animatable_text.startswith('yes')
		elif 'Version:' in header.get_text():
			css_version = row.find('td').get_text(strip=True)
			

	# Return the extracted details as a tuple
	return (default_value, inherited, animatable, css_version)




if __name__ == '__main__':
	baseurl = 'https://www.w3schools.com/cssref/'
	for css_property, link in extract_css_property_links(baseurl + 'index.php'):
		if css_property.startswith('@'):
			pass
		else:
			print(repr(css_property) + ':', repr(extract_css_property_details(baseurl + link)) + ',', flush=True)

