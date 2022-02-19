# from selenium import webdriver
#
# geckodriver = '/usr/bin/geckodriver'
# browser = webdriver.Firefox(executable_path=geckodriver)
#
# url = 'https://www/duckduckgo.com'
# browser.get(url)

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.support.wait import WebDriverWait
import sys


sys.path.append('/usr/bin/Firefox')
options = Options()
# options.add_argument('-headless')
driver = Firefox(executable_path='geckodriver', options=options)
wait = WebDriverWait(driver, timeout=10)
driver.get('https://www.residentapps.com/home/residentapps/mobile/#/login')
wait.until(expected.visibility_of_element_located((By.CSS_SELECTOR, '#login-username'))).send_keys('DOxley' + Keys.ENTER)
wait.until(expected.visibility_of_element_located((By.CSS_SELECTOR, '#login-password'))).send_keys('0646' + Keys.ENTER)

wait.until(expected.visibility_of_element_located((By.CSS_SELECTOR, '#module-item-residents'))).click()

foo = driver.find_elements_by_class_name('module-list-entry-label')

for elem in foo:
    print(elem.text)
    elem.click()

wait.until(expected.visibility_of_element_located((By.CSS_SELECTOR, '#hdtb-tls'))).click()
print(driver.page_source)
driver.quit()
