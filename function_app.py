import azure.functions as func
import logging
import requests
from bs4 import BeautifulSoup
import json


app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="lincolnfsd")
def lincolnfsd(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    url = req.params.get('url')
    if not url:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            url = req_body.get('url')

    if url:
        # Fetch the content from the URL
        response = requests.get(url)
        response.raise_for_status()

        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all instances of the "result_hit" div
        result_hits = soup.find_all('div', class_='result_hit')

        data = []

        for hit in result_hits:
            service_name = hit.find('header').find('a').text
            link = hit.find('header').find('a')['href']
            
            # Navigate to the link and extract details
            LinkURL = 'https://lincolnshire.fsd.org.uk/kb5/lincs/fsd/'
            details = extract_details(LinkURL+link)
            
            description_tag = hit.find('div', class_='hit-content')
            description = description_tag.get_text(strip=True) if description_tag else None
            
            telephone_tag = hit.find('span', class_='comma_split_line')
            telephone = telephone_tag.get_text(strip=True) if telephone_tag else None
            
            email_tag = hit.find('a', class_='contact_link', href=True)
            email = email_tag['href'].replace("mailto:", "") if email_tag else None
            
            # Extracting website link
            website_link = None
            for tag in hit.find_all('p'):
                if "Website:" in tag.text and tag.find('a'):
                    website_link = tag.find('a')['href']
                    break
            
            # Append the extracted data to the main list
            data.append({
                'Service Name': service_name,
                'Main Description': description,
                'Telephone': telephone,
                'Email': email,
                'Website': website_link,
                'Details': details
            })

        # Save the data to a JSON file
        
        return func.HttpResponse(
            json.dumps(data, ensure_ascii=False),
            mimetype="application/json",
            status_code=200)
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a url in the query string or in the request body.",
             status_code=200
        )


# Base functions

def extract_details(link):
    response = requests.get(link)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    details = {}
    
    # Extract details from each section
    main_content = soup.find('div', id='main_content')
    
    if main_content:
        details['Title'] = main_content.find('h1').get_text(strip=True) if main_content.find('h1') else None
        
        # Description
        description_section = main_content.find('section', class_='field_section service_description')
        if description_section:
            description_text = description_section.find('div', class_='description_text')
            details['Description'] = description_text.get_text(strip=True) if description_text else None
            
        # Contact
        contact_section = main_content.find('section', class_='field_section service_contact')
        if contact_section:
            details['Contact'] = {dt.get_text(strip=True): dd.get_text(strip=True) for dt, dd in zip(contact_section.find_all('dt'), contact_section.find_all('dd'))}
        
        # Venue
        venue_section = main_content.find('section', class_='field_section service_venue')
        if venue_section:
            details['Venue'] = {dt.get_text(strip=True): dd.get_text(strip=True) for dt, dd in zip(venue_section.find_all('dt'), venue_section.find_all('dd'))}
        
        # Time/Date Details
        time_date_section = main_content.find('section', class_='field_section service_event')
        if time_date_section:
            opening_times_table = time_date_section.find('table', class_='table table-condensed')
            if opening_times_table:
                days = []
                opening_times = []
                closing_times = []
                for row in opening_times_table.find_all('tr')[1:]:  # Skip the header
                    columns = row.find_all('td')
                    day = columns[0].get_text(strip=True)
                    opening_time = columns[1].get_text(strip=True)
                    closing_time = columns[2].get_text(strip=True)
                    
                    days.append(day)
                    opening_times.append(opening_time)
                    closing_times.append(closing_time)
                
                details['Time/Date'] = {
                    'Days': days,
                    'Opening Times': opening_times,
                    'Closing Times': closing_times
                }
            else:
                 details['Time/Date'] = "; ".join([f"{dt.get_text(strip=True)}: {dd.get_text(strip=True)}" for dt, dd in zip(time_date_section.find_all('dt'), time_date_section.find_all('dd'))])
        
        
        # Other Details
        other_details_section = main_content.find('section', class_='field_section service_other')
        if other_details_section:
            details['Other Details'] = {dt.get_text(strip=True): dd.get_text(strip=True) for dt, dd in zip(other_details_section.find_all('dt'), other_details_section.find_all('dd'))}
    
    return details