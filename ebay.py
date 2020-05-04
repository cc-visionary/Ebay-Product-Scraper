# importing all the required libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
# from selenium.webdriver.support import expected_conditions as EC

import os
import pandas as pd
import xlsxwriter
import time
from datetime import datetime, timedelta
import re
from random import randint

class EbayScraper():
    def __init__(self):
        self.item_ids = []
        self.seller_ids = []
        self.sellers = {}
        self.chromeOptions = Options() 
        self.base_url = 'https://www.ebay.co.uk/'
        self.tag = 'itm/' # % is the item id

    def start(self):
        start_time = datetime.now()
        print(start_time)
        itemfilename = 'data.xlsx'
        sellerfilename = 'same.xlsx'
        # itemfilename = self.getFilename('Item IDs') # asks for user input file
        # sellerfilename = self.getFilename('Seller IDs') # asks for seller input file
        workbook = self.initializeWorkbook(itemfilename)
        self.settingDriverOptions()
        self.changeDirectory('./input') # go to input folder
        numItems = self.getItems(itemfilename)
        numSellers = self.getSellers(sellerfilename) 
        self.changeDirectory('..') # go back 1 folder before
        print('INFO: Amount of Items to Scrape: '  + str(numItems))
        
        driver = self.runDriver()
        for i, item in enumerate(self.item_ids):
            print('{}/{}: Scraping Item {}:'.format(i + 1, numItems, item))
            self.getPage(driver, self.base_url + self.tag + str(item))
            best_match_seller = None
            best_match_id = None
            sort_match_seller = None
            sort_match_id = None
            item_price = self.scrapePrice(driver) # Item ID's Lowest Price
            title = self.scrapeTitle(driver) # Item ID's Product Title
            seller = self.scrapeISeller(driver)
            sold_out = self.scrapeSoldOut(driver)
            if(title != None or item_price != None):
                if(sold_out == None):
                    sold_out = 'No'
                search_result = self.searchTitle(driver, title)
                if(int(search_result) > 0):
                    print('\tINFO: There are ' + search_result + ' search results as Best Match.')
                    if(i == 0):
                        time.sleep(1)
                        self.setViewIDSeller(driver)
                    first_seller = self.scrapeSeller(driver)
                    first_id = self.scrapeFirstID(driver)

                    if(first_seller):
                        if(first_seller in self.seller_ids):
                            best_match_seller = 'Yes'
                            print('INFO: First best match is one of the seller ID -> ' + first_seller)
                        else:
                            best_match_seller = 'No'
                    
                    if(first_id):
                        if(first_id == item):
                            best_match_id = 'Yes'
                        else:
                            best_match_id = 'No'
                    if(int(search_result) > 1):
                        best_match_price = self.scrapeSecondPrice(driver)
                    else:
                        best_match_price = 'Only has 1 search result...'

                    self.getPage(driver, driver.current_url + '&_sop=15')
                    sort_seller = self.scrapeSeller(driver)
                    sort_id = self.scrapeFirstID(driver)
                
                    if(sort_seller):
                        if(sort_seller in self.seller_ids):
                            sort_match_seller = 'Yes'
                            print('INFO: First Sorted Lowest Price + P&P is one of the seller IDs -> ' + sort_seller)
                        else:
                            sort_match_seller = 'No'
                    if(sort_id):
                        if(sort_id == item):
                            sort_match_id = 'Yes'
                        else:
                            sort_match_id = 'No'

                    sort_price = self.scrapeSortPrice(driver)
                else:
                    first_seller = None
                    first_id = None
                    best_match_price = None
                    sort_seller = None
                    sort_id = None
                    sort_price = None
                    print('\tINFO: Item {} has 0 Best Match in the Search Results.'.format(item))
            if(seller not in self.sellers.keys()):
                self.sellers[seller] = []
                
            self.sellers[seller].append([
                item,               # item id
                item_price,         # item price
                title,              # title
                seller,             # seller
                sold_out,           # sold out (yes/no)
                first_id,           # best match first id
                best_match_id,      # best match same id(yes/no)
                first_seller,       # best match seller id (seller )
                best_match_seller,  # best match same seller
                best_match_price,   # best match second price
                sort_id,            # sort first id
                sort_match_id,      # sort same id
                sort_seller,        # sort seller id 
                sort_match_seller,  # sort same seller
                sort_price          # sort price
            ])
            # time.sleep(randint(0,3))
        self.saveData(workbook)
        self.closeDriver(driver)
        print(datetime.now() - start_time)
            
    def scrapePrice(self, driver):
        try:
            price = driver.find_element_by_class_name('display-price').text
        except:
            try:
                price = driver.find_element_by_id('prcIsum').text
                if(randint(0, 1) == 1):
                    driver.find_element_by_id('prcIsum').click()
                    print('\tINFO: randomly clicked on the price (let\'s not be obvious) ;)')
            except:
                try:
                    price = driver.find_element_by_class_name('vi-bin-primary-price__main-price').text
                except Exception as e:
                    price = None
                    print('\tERROR: Failed to scrape item price, most probably a non-existent page')
        return price

    def scrapeTitle(self, driver):
        try:
            title = driver.find_element_by_class_name('product-title').text
        except:
            try:
                title = driver.find_element_by_id('itemTitle').text
            except:
                try:
                    title = driver.find_element_by_class_name('vi-title__main').text
                except Exception as e:
                    title = None
                    # print('\tERROR: Failed to scrape item title\n', e)
        return title

    def scrapeISeller(self, driver):
        seller = None
        try:
            seller = driver.find_element_by_class_name('mbg-nw').text
        except:
            try:
                seller = driver.find_element_by_class_name('app-sellerpresence__sellername').text.split(' ')[0]
            except:
                try:
                    seller = driver.find_element_by_class_name('seller-persona').find_elements_by_tag_name('span')[1].text.split(' ')[0]
                except Exception as e:
                    seller = None
                    print('\tERROR: Failed to scrape seller')
        return seller

    def scrapeSoldOut(self, driver): # scrapes the sold out alert shown in the website
        sold_out = None
        messages = driver.find_elements_by_class_name('msgTextAlign')
        if(len(messages) > 0):
            sold_out = 'Yes'
        else:
            soldout = driver.find_elements_by_class_name('outofstock')
            if(len(soldout) == 1):
                sold_out = 'Yes'
        return sold_out

    def searchTitle(self, driver, title):
        # clean the title
        try:
            new_title = re.sub(r'[^\w]', ' ', title)
            if(len(new_title) != len(title) or len(new_title) == 0):
                raise TypeError
        except Exception as e:
            new_title = None
            # print('\tERROR: Failed to clean the title\n', e)

        driver.get(self.base_url + 'sch/' + new_title + '&_stpos=OL98JR')

        search_results = None
        wait = 0
        while(search_results == None and wait <= 10): # waits for the search result to load
            if(wait >= 10):
                print('\tERROR: Waited too long (10 seconds) for the search result')
                search_results = '0'
            try: 
                search_results = driver.find_element_by_class_name('srp-controls__count-heading').find_elements_by_tag_name('span')[0].text
            except:
                time.sleep(1) # wait for the page to load for 1 sec
                wait += 1
        return search_results
    
    def setViewIDSeller(self, driver): # opens customization view then sets the setting to show the seller id and item id of the item
        iteration = 1
        success = False
        while(not success and iteration <= 5):
            for button in driver.find_elements_by_class_name('fake-menu-button__button'): # setting it to show the seller
                if(button.get_attribute('aria-controls') == 's0-13-11-5-1[0]-60-1-content'):
                    button.click()
                    try:
                        driver.find_element_by_class_name('srp-view-options__customize').click()
                        time.sleep(2)
                        try:
                            seller = driver.find_element_by_id('e1-13')
                            seller.click()
                            driver.find_element_by_id('e1-11').click()
                            driver.find_element_by_id('e1-3').click()
                            success = True
                        except Exception as e:
                            print('\tERROR: Failed to changed customization to view seller id and item id. Trying Again ({})'.format(iteration))
                        time.sleep(2)
                    except Exception as e:
                        print('\tERROR: Can\'t open the customization')
                    break
            iteration += 1

    def scrapeSeller(self, driver):
        try:
            seller = driver.find_element_by_class_name('s-item__seller-info-text').text.split(': ')[1].split(' ')[0]
        except Exception as e:
            seller = None
            print('\tERROR: Failed to get first_seller\n')
        return seller

    def scrapeFirstID(self, driver):
        try:
            first_id = driver.find_element_by_class_name('s-item__item-id').text.split(': ')[1]
        except Exception as e:
            first_id = None
            # print('Failed to get first_seller\n')
        return first_id

    def scrapeSecondPrice(self, driver):
        # get the price of the second best
        try:
            best_match_price = driver.find_elements_by_class_name('s-item__price')[1].text
        except Exception as e:
            best_match_price = None
            print('\tERROR: Failed to find second item\'s price in best match\n', e)
            pass
        return best_match_price

    def scrapeSortPrice(self, driver):
        try:
            price = driver.find_element_by_class_name('s-item__price').text
        except Exception as e:
            price = None
            print('\tERROR: Failed to get the seller id\n', e)
        return price

    def getFilename(self, name):
        fileName = input('Enter your {} .xlsx file name: '.format(name))
        return fileName

    def changeDirectory(self, dirName):
        try:
            os.chdir(dirName)
        except Exception as e:
            print('\tERROR: Something is wrong with directory "{}"...\n'.format(dirName), e)
            last = input('Press enter to exit...')
            exit()

    def getItems(self, filename):
        try:
            df = pd.read_excel(filename)
            columns = df.columns # takes all the column name
            for i in df.iloc:
                self.item_ids.append(i[columns[0]])
        except Exception as e:
            print('ERROR: Something is wrong with filename -> ' + filename + '\n', e)
            last = input('Press enter to exit...')
            exit()
        return len(self.item_ids)
    
    def getSellers(self, filename):
        try:
            df = pd.read_excel(filename)
            columns = df.columns # takes all the column name
            for i in df.iloc:
                self.seller_ids.append(i[columns[0]])
        except Exception as e:
            print('ERROR: Something is wrong with filename -> ' + filename + '\n', e)
            last = input('Press enter to exit...')
            exit()
        return len(self.item_ids)

    def initializeWorkbook(self, filename):
        workbook = xlsxwriter.Workbook(filename.split('.')[0] + '-output.xlsx')
        self.worksheet = workbook.add_worksheet()
        self.worksheet.set_column('A:J', 15)
        self.worksheet.set_column('C:C', 30)

        self.writeRow(0, [
            'Item ID', 
            'Price(1)', 
            'Title(2)', 
            'Seller',
            'Sold Out',
            'Best ID', 
            'Best Match(3)', 
            'Best Seller',
            'Best Same Seller',
            'Second Best Price(4)', 
            'Sort Lowest + P&P ID', 
            'Sort Lowest + P&P Match(5)', 
            'Sort Seller ID(6)',
            'Sort Same Seller',
            'Sort Lowest + P&P Price(7)', 
        ])

        return workbook

    def writeRow(self, row, contents):
        for i, content in enumerate(contents):    # write all the contents to a row
            self.worksheet.write(row, i, str(content) if content != None else '') # in self.worksheet

    def settingDriverOptions(self):
        # webdriver options
        self.chromeOptions.add_argument('--kiosk') # sets the headless browser into full screen mode
        # self.chromeOptions.add_argument('--headless') # opens the browser silently
        # self.chromeOptions.add_argument('--log-level=3') # stops the headless browser's logging features
        self.chromeOptions.add_argument('blink-settings=imagesEnabled=false') # set loading images to be false (for faster loading)
        # self.chromeOptions.add_argument('--disable-extensions')
        # self.chromeOptions.add_argument('--profile-directory=Default')
        # self.chromeOptions.add_argument("--incognito")
        # self.chromeOptions.add_argument("--disable-plugins-discovery")
        self.chromeOptions.page_load_strategy = 'normal'

    def runDriver(self):
        try:
            driver = webdriver.Chrome('./chromedriver/chromedriver', options=self.chromeOptions) # opens the headless browser
        except Exception as e:
            print('ERROR: Failed to open Chrome Web Driver...\n', e)
            last = input('Press enter to exit...')
            exit()
        return driver

    def getPage(self, driver, url):
        try:
            driver.get(url)
        except Exception as e:
            print('\tERROR: Failed to load page ' + url + '\n', e)

    def saveData(self, workbook):
        row = 1
        for seller in sorted(self.sellers.keys()):
            for items in sorted(self.sellers[seller], key=lambda item: (item[6], item[14]), reverse=True):
                self.writeRow(row, items)
                row += 1
        self.changeDirectory('./output')
        workbook.close()
        self.changeDirectory('..')

    def closeDriver(self, driver):
        try:
            driver.close()
        except Exception as e:
            print('ERROR: Something occured while closing the driver...\n', e)

if __name__ == "__main__":
    ebayScraper = EbayScraper()
    ebayScraper.start()