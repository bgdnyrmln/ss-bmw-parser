import requests
from bs4 import BeautifulSoup
from time import sleep

sublink = ''

while True:
    url = 'https://www.ss.lv/lv/transport/cars/bmw/'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    listings = soup.find_all("td", class_="msg2")
    prices = soup.find_all("td", class_="msga2-o pp6")
    prices = str(prices).split('€')
    step = 1
    if sublink == listings[0].find('a', {'class':'am'}).get('href'):
        pass
    else:
        listing = listings[0].find('a', {'class':'am'})
        if listing is not None:
            sublink = listing.get('href')
            txt = str(listing.text)
            txt = txt.split('. ')
            price = str(prices[0])[::-1]
            price = price.split('>""')
            price = str(price[0])[::-1]
            if price[0] == "<":
                price = price.split('>')
                price = str(price[1]).split('<')
                price = str(price[0])

            print(price + "€")
            print(str(txt[0]) + "..." + "\n" + str("https://www.ss.lv"+sublink))
            print("===")
    sleep(5)
