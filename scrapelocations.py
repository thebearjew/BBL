# Eliot Abrams
# Food truck location choice

# Packages
import urllib2
from bs4 import BeautifulSoup
import os as os
import pandas as pd
import datetime as dt

# Set Folder location
os.chdir('/Users/eliotabrams/Desktop/Data')

# Create list of addresses pulling data for the week based on each past Wednesday for about 4 years (the data is available back to August, 2011)
today = dt.datetime.today()
wednesday = today + dt.timedelta(days=-today.weekday() + 2, weeks=1)
addresses = []
file_names = []
for x in xrange(210):
    wednesday -= dt.timedelta(days=7)
    addresses.append(
        'http://www.chicagofoodtruckfinder.com/weekly-schedule?date='
        + dt.datetime.strftime(wednesday, '%Y%m%d'))
    file_names.append(dt.datetime.strftime(wednesday, '%Y%m%d') + '.txt')

# Scrap and save web pages
days = ['Sunday', 'Monday', 'Tuesday',
        'Wednesday', 'Thursday', 'Friday', 'Saturday'] # Day ordering matches page display
location_data = pd.DataFrame()
location = ''
day = ''
week = ''

for x in xrange(len(addresses)):

    # Get html
    raw_html = urllib2.urlopen(addresses[x]).read()

    # Save file
    f = open(file_names[x], 'w')
    f.write(raw_html)

    # Parse document
    soup = BeautifulSoup(raw_html)
    count = 0
    week = soup.h1.text

    for thing1 in soup.find_all('td'):
        if thing1.get('style') == 'width:13%':
            location = thing1.text
            count = 0

        else:
            day = days[count]
            count += 1

        new_soup = BeautifulSoup(str(thing1), 'html.parser')

        for thing2 in new_soup.find_all('img'):
            truck = thing2.get('title')
            location_data = location_data.append(
                pd.DataFrame([location, day, truck, week]).transpose())


# Clean scrapped data (WILL NEED TO PAY ATTENTION TO TIMESTAMP TO FIND
# LUNCH SERVICE)

# Set index
location_data = location_data.reset_index().drop('index', axis=1)

# Get truck name
location_data['Truck'] = location_data[2].apply(lambda x: x[20:])

# Construct data
location_data['Coarse_Date'] = location_data[3].apply(lambda x: x[11:])
location_data['Coarse_Date'] = location_data.Coarse_Date.apply(
    lambda x: dt.datetime.strptime(x, ' %b %d, %Y'))

location_data['Date'] = location_data.apply(lambda x: x.Coarse_Date + dt.timedelta(days=(0 - x.Coarse_Date.weekday() + days.index(x[1]) - 1)),
    axis=1)  # Note the indexing of datetime has Monday being 0

# Finalize columns
location_data = location_data.rename(columns={0: 'Location'})
location_data = location_data.drop(['Coarse_Date', 1, 2, 3], axis=1)

# Edit location names
location_data.Location = location_data.Location.apply(
    lambda x: x.replace('\n', ''))
location_data.Location = location_data.Location.apply(
    lambda x: x.replace(', Chicago, IL', ''))

# Print full data
print location_data.groupby('Truck').count().to_string()
print location_data.groupby('Location').count().to_string()

# Output data
location_data.to_csv('output.csv', encoding='utf-8')


