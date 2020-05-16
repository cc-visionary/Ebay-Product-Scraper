# importing all the required libraries
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC

import os
import pandas as pd
import xlsxwriter
import time
from datetime import datetime, timedelta
import re
from random import randint

class EbayScraper():
    def __init__(self):
        self.item_ids = []   # store the item ids
        self.seller_ids = [] # store the seller ids
        self.amazon_ids = [] # stores the amazon ids
        self.sellers = {}    # 
        self.chromeOptions = Options() 
        self.base_url = 'https://www.ebay.co.uk/'
        self.tag = 'itm/' # % is the item id
        self.total_time = 0
        self.shown = False

    def start(self):
        start_time = datetime.now()
        itemfilename = self.getFilename('Item IDs') # asks for user input file
        sellerfilename = self.getFilename('Seller IDs') # asks for seller input file
        workbook = self.initializeWorkbook(itemfilename)
        self.settingDriverOptions()
        self.changeDirectory('./input') # go to input folder
        numItems = self.getItems(itemfilename)
        numSellers = self.getSellers(sellerfilename)
        self.changeDirectory('..') # go back 1 folder before
        print('INFO: There are {} sellers.'.format(numSellers))
        print('INFO: Amount of Items to Scrape: '  + str(numItems))
        
        driver = self.runDriver()
        for i, item in enumerate(self.item_ids):
            item = item[0]
            item_start = datetime.now()
            print('{}/{}: Scraping Item {}:'.format(i + 1, numItems, item))
            self.getPage(driver, self.base_url + self.tag + str(item))
            best_match_seller = None
            best_match_id = None
            sort_match_seller = None
            sort_match_id = None
            first_seller = None
            first_id = None
            best_match_price = None
            sort_seller = None
            sort_id = None
            sort_price = None
            amazon_id = self.extractAmazonId(i)
            item_price = self.scrapePrice(driver)   # Item ID's Lowest Price
            title = self.scrapeTitle(driver)        # Item ID's Product Title
            seller = self.scrapeISeller(driver)     # Item ID's Seller
            account = None                          # Item ID's Seller Account ID (ex. UK##)
            if(seller != None):
                seller_index = self.findAccount(seller)
                if(seller_index != -1):
                    account = self.seller_ids[seller_index][1]
            sold_out = self.scrapeSoldOut(driver)   # Determine's whether Item ID is sold out or not
            if(title != None or item_price != None):
                if(sold_out == None):
                    sold_out = 'No'
                search_result = self.searchTitle(driver, title)
                try:
                    search_result = int(re.sub(r'[^\w]', '', str(search_result)))
                    if(search_result > 0):
                        print('\tINFO: There are ' + str(search_result) + ' search results as Best Match.')
                        if(self.shown == False):
                            time.sleep(1)
                            self.setViewIDSeller(driver)
                    
                    first_seller = self.scrapeSeller(driver)
                    first_id = self.scrapeFirstID(driver)
                    if(first_id == None and first_id == None):
                        input('ERROR: Please run the program again...')
                        exit()

                    if(first_seller):
                        if(self.findAccount(first_seller) != -1):
                            best_match_seller = 'Yes'
                            print('\tINFO: First best match is one of our seller ID -> ' + first_seller)
                        else:
                            best_match_seller = 'No'
                    
                    if(first_id):
                        if(str(first_id) == str(item)):
                            best_match_id = 'Yes'
                        else:
                            best_match_id = 'No'
                    if(search_result > 1):
                        best_match_price = self.scrapeSecondPrice(driver)
                    else:
                        best_match_price = 'Only has 1 search result...'

                    self.getPage(driver, driver.current_url + '&_sop=15')
                    sort_seller = self.scrapeSeller(driver)
                    sort_id = self.scrapeFirstID(driver)
                
                    if(sort_seller):
                        if(self.findAccount(sort_seller) != -1):
                            sort_match_seller = 'Yes'
                            print('\tINFO: First Sorted Lowest Price + P&P is one of our seller IDs -> ' + sort_seller)
                        else:
                            sort_match_seller = 'No'
                    if(sort_id):
                        if(str(sort_id) == str(item)):
                            sort_match_id = 'Yes'
                        else:
                            sort_match_id = 'No'

                    sort_price = self.scrapeSortPrice(driver)
                except:
                    print('\tINFO: Item {} has 0 Best Match in the Search Results.'.format(item))
                    
            if(seller == None):
                seller = ' '
            if(seller not in self.sellers.keys()):
                self.sellers[seller] = []
                
            temp_list = [
                item,               # item id
                # amazon_id,          # id of amazon product
                item_price,         # item price
                title,              # title
                seller,             # seller
                account,            # account id (ex. UK51, ...)
                sold_out,           # sold out (yes/no)
                first_id,           # best match first id
                best_match_id,      # best match same id(yes/no)
                first_seller,       # best match seller is one of our sellers
                best_match_seller,  # best match same seller
                best_match_price,   # best match second price
                sort_id,            # sort first id
                sort_match_id,      # sort same id
                sort_seller,        # sort seller is one of our sellers
                sort_match_seller,  # sort same seller
                sort_price          # sort price
            ]
            for index, l in enumerate(temp_list):
                temp_list[index] = str(l) if l != None else ' '
            self.sellers[seller].append(temp_list)
            # time.sleep(randint(0,3))
            current_time = self.convertToSec(datetime.now() - item_start) # calculates the time it took
            self.total_time += current_time
            print('{}/{}: Succesfully scraped Item {}. Time Taken: {}s\n'.format(i + 1, numItems, item, current_time))
        self.saveData(workbook)
        self.closeDriver(driver)
        print('Congratulations! You\'ve successfully scraped {} items'.format(numItems))
        print('Stats:')
        print('\tAverage Time per Product: {}s'.format(round(self.total_time / 200, 2)))
        total_time = str(datetime.now() - start_time).split(':')
        print('\tTotal Time it took: {}hour(s) {}minute(s) {}second(s)'.format(total_time[0], total_time[1], total_time[2]))
        input('Please press enter to exit...')
        exit()

    # Extracts the amazon id from the url of the amazon product
    def extractAmazonId(self, index):
        amazon_id = None
        try:
            amazon_id = re.findall(r'B0\w+[?|/]', str(self.item_ids[index][1]))[0][:-1]
        except:
            print('\tINFO: No Amazon ID')
        return amazon_id

    # Checks whether or not the product is one of our seller's
    def findAccount(self, seller_id):
        for i, seller in enumerate(self.seller_ids):
            if(seller_id.lower() == seller[0].lower()):
                return i
        return -1

    # Converts Timedelta into Seconds (ex. 00:01:31.2134 -> 91)
    def convertToSec(self, time):
        return int(str(time).split(':')[0]) * 360 + int(str(time).split(':')[1]) * 60 + int(str(time).split(':')[2][:2])
            
    # Scrapes the Price of the Product
    def scrapePrice(self, driver):
        price = None
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
                except:
                    print('\tERROR: Failed to scrape item price, most probably a non-existent page')
        return price

    # Scrapes the Name of the Product
    def scrapeTitle(self, driver):
        try:
            title = driver.find_element_by_class_name('product-title').text
        except:
            try:
                title = driver.find_element_by_id('itemTitle').text
            except:
                try:
                    title = driver.find_element_by_class_name('vi-title__main').text
                except:
                    title = None
        return title

    # Scrapes the Seller of the Product
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
                except:
                    print('\tERROR: Failed to scrape seller')
        return seller

    # Scrapes the sold out alerts shown in the website
    def scrapeSoldOut(self, driver):
        sold_out = None
        try:
            message = driver.find_element_by_class_name('msgTextAlign').text
            if(message != ''):
                sold_out = 'Yes'
            else:
                soldout = driver.find_elements_by_class_name('outofstock')
                if(len(soldout) == 1):
                    sold_out = 'Yes'
        except:
            pass
        return sold_out

    # Searches the Best Match using the Name of the Product
    def searchTitle(self, driver, title):
        # clean the title
        try:
            new_title = re.sub(r'[^\w]', ' ', str(title))
            if(len(new_title) != len(title) or len(new_title) == 0):
                raise TypeError
        except:
            new_title = None
            # print('\tERROR: Failed to clean the title\n', e)

        driver.get(self.base_url + 'sch/' + new_title + '&_stpos=OL98JR')
        search_results = None
        reloadTimes = 0
        wait = WebDriverWait(driver, 10)
        while(search_results == None and reloadTimes < 5):
            try:
                wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'srp-controls__count-heading')))
                search_results = driver.find_element_by_class_name('srp-controls__count-heading').find_elements_by_tag_name('span')[0].text
            except:
                print('\tINFO: Waited too long 10s for the search result.  Refreshing.')  
                driver.refresh()
            reloadTimes += 1
        if(search_results == None):
            print('\tERROR: Search Result Failed to Load')
       
        return search_results
    
    # Changes the View Settings to show Item ID and Item Seller
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
                        except:
                            print('\tERROR: Failed to changed customization to view seller id and item id. Trying Again ({})'.format(iteration))
                        time.sleep(2)
                    except:
                        print('\tERROR: Can\'t open the customization')
                    break
            iteration += 1    
        self.shown = True

    # Scrapes the Seller of the first Best Match
    def scrapeSeller(self, driver):
        seller = None
        try:
            seller = driver.find_element_by_class_name('s-item__seller-info-text').text.split(': ')[1].split(' ')[0]
        except:
            print('\tERROR: Failed to get first_seller')
        return seller

    # Scrapes the ID of the first Best Match
    def scrapeFirstID(self, driver):
        try:
            first_id = driver.find_element_by_class_name('s-item__item-id').text.split(': ')[1]
        except:
            first_id = None
            # print('Failed to get first_seller\n')
        return first_id

    # Scrapes the Price of the second Best Match
    def scrapeSecondPrice(self, driver):
        # get the price of the second best
        try:
            best_match_price = driver.find_elements_by_class_name('s-item__price')[1].text
        except Exception as e:
            best_match_price = None
            print('\tERROR: Failed to find second item\'s price in best match\n', e)
            pass
        return best_match_price

    # Scrapes the Price of the Lowest Price + P&P
    def scrapeSortPrice(self, driver):
        try:
            price = driver.find_element_by_class_name('s-item__price').text
        except Exception as e:
            price = None
            print('\tERROR: Failed to get the seller id\n', e)
        return price

    # Asks the user for the Filenames
    def getFilename(self, name):
        filename = None
        while(filename == None or '.xlsx' not in filename): # only takes .xlsx as format
            filename = input('Enter your {} .xlsx file name: '.format(name))
            if('.xlsx' not in filename):
                print('Please make sure you include .xlsx')
                os.system('cls')
        return filename

    # Change Directory with Error Handling
    def changeDirectory(self, dirName):
        try:
            os.chdir(dirName)
        except Exception as e:
            print('\tERROR: Something is wrong with directory "{}"...\n'.format(dirName), e)
            input('Press enter to exit...')
            exit()

    # Extracts the items within the filename.xlsx
    def getItems(self, filename):
        try:
            df = pd.read_excel(filename)
            columns = df.columns # takes all the column name
            for row in df.iloc:
                self.item_ids.append([row[columns[0]], row[columns[1]]])
        except Exception as e:
            print('ERROR: Something is wrong with filename -> ' + filename + '\n', e)
            input('Press enter to exit...')
            exit()
        return len(self.item_ids)
    
    # Extracts the sellers within the filename.xlsx
    def getSellers(self, filename):
        try:
            df = pd.read_excel(filename)
            columns = df.columns # takes all the column name
            for i in df.iloc:
                self.seller_ids.append([i[columns[0]].lower(), i[columns[1]].lower()])
        except Exception as e:
            print('ERROR: Something is wrong with filename -> ' + filename + '\n', e)
            input('Press enter to exit...')
            exit()
        return len(self.seller_ids)

    # Creates the Workbook and the headers.
    def initializeWorkbook(self, filename):
        workbook = xlsxwriter.Workbook(filename.split('.')[0] + '-output.xlsx')
        bold = workbook.add_format({'bold': True})
        self.worksheet = workbook.add_worksheet()
        self.worksheet.set_column('A:O', 15)
        self.worksheet.set_column('C:C', 30)

        self.writeRow(0, [
            'Item ID', 
            'Price(1)', 
            'Title(2)', 
            'Seller',
            'Account ID',
            'Sold Out',
            'Best ID', 
            'Best Match(3)', 
            'Best Seller',
            'Best Match One of our Seller?',
            'Second Best Price(4)', 
            'Sort Lowest + P&P ID', 
            'Sort Lowest + P&P Match(5)', 
            'Sort Seller ID(6)',
            'Sort Lowest + P&P One of our Seller?',
            'Sort Lowest + P&P Price(7)', 
        ], bold)
        
        return workbook

    def writeRow(self, row, contents, formatter = None):
        if(formatter == None):
            for i, content in enumerate(contents):    # write all the contents to a row
                self.worksheet.write(row, i, content) # in self.worksheet
        else:
            for i, content in enumerate(contents):    # write all the contents to a row
                self.worksheet.write(row, i, content, formatter) # in self.worksheet in format

    # Sets up chromeOptions for the Web Driver Settings
    def settingDriverOptions(self):
        # webdriver options
        self.chromeOptions.add_argument('--kiosk') # sets the headless browser into full screen mode
        # self.chromeOptions.add_argument('--headless') # opens the browser silently
        # self.chromeOptions.add_argument('--log-level=3') # stops the headless browser's logging features
        self.chromeOptions.add_argument('blink-settings=imagesEnabled=false') # set loading images to be false (for faster loading)
        # self.chromeOptions.add_argument('--disable-extensions')
        # self.chromeOptions.add_argument('--profile-directory=Default')
        self.chromeOptions.add_argument("--incognito")
        # self.chromeOptions.add_argument("--disable-plugins-discovery")
        self.chromeOptions.page_load_strategy = 'normal'

    # Runs the driver
    def runDriver(self):
        try:
            driver = webdriver.Chrome('./chromedriver/chromedriver', options=self.chromeOptions) # opens the headless browser
        except Exception as e:
            print('ERROR: Failed to open Chrome Web Driver...\n', e)
            input('Press enter to exit...')
            exit()
        return driver

    # Goes to the URL
    def getPage(self, driver, url):
        try:
            driver.get(url)
        except Exception as e:
            print('\tERROR: Failed to load page ' + url + '\n', e)

    # Saves the data saved into the dictionary self.sellers
    def saveData(self, workbook):
        row = 1
        for seller in sorted(self.sellers.keys(), reverse=True):
            for items in sorted(self.sellers[seller], key=lambda item: (item[4], item[12], item[14]), reverse=True):
                self.writeRow(row, items)
                row += 1
        self.changeDirectory('./output')
        workbook.close()
        self.changeDirectory('..')

    # Close the Driver
    def closeDriver(self, driver):
        try:
            driver.close()
        except Exception as e:
            print('ERROR: Something occured while closing the driver...\n', e)

if __name__ == "__main__":
    ebayScraper = EbayScraper()
    ebayScraper.start()
