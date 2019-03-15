"""
This script loads a .txt file with the farming coordinates separated with a comma (i.e. 123|456, 678|901, ...)
User is asked to enter some inputs:
1) Game Username 
2) Game Password
3) Whether you want to farm players or not.
3) DeathByCaptcha Mode: On/Off (If on provide the script with Account Username & Password).
3) Time to wait before starting again from first coordinate (when finished)
4) Number of units to send. (default is 5)
5) Startpoint. The coordinates from which the script will start sending attacks (in case the script stop working, i.e. because of a captcha, etc.)

The way this script works is simple:

First it opens a window and prompts user to select the .txt file. Then it sorts all of the coordinates online, on twstats.com

It continuously loops through all of the coordinates, trying to send the attack. If coordinates match some hard-coded coordinates, then a report search is performed first,
to check if there is any red report from those coordinates. If it is, a message is displayed on the console and the script continues with the next pair of coordinates, without 
executing the 'red' pair. This is useful, when you might be farming inactive players, that may occasionally build some troops. Those players' coordinates are hard-coded in the script.

If there are not enough units, a search is performed trying to find the fastest arrival of returning troops. Then the script waits for that amount (until the troops return) and tries 
to execute the attack again. This loop continues, until the attack is executed. When the script ends, it restarts.

New: Implemented Deatchbycaptcha API with over 90% accuracy.
New: Place a second .txt file in the same directory named "playersCoords.txt". The script will first loop through those coordinates and farm the players villages.

"""

DEBUGGING = False


import time, sys, threading, os, win32api
from PIL import Image
import pytesseract
import datetime
import re
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from pathlib import Path
from bs4 import BeautifulSoup
from collections import OrderedDict
from pprint import pprint
import getpass
import deathbycaptcha
from twilio.rest import Client
import random, pyautogui
import webbrowser
import requests
import progressbar as pb

pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"

current_dir = os.getcwd()

if DEBUGGING == True:
    coordSize = 1
    captcha_alert_mode = 'no'
    scheduleBuild = 'no'
    richbarbs_mode = 'no'
    report_checking_mode = 'yes'
else:
    coordSize = input("Choose coordinates' size (S for small/B for big): ")
    os.system('cls')
    captcha_alert_mode = input('Do you want to be alerted about captcha-solving (yes/no)?')
    os.system('cls')
    scheduleBuild  = input('Do you want to schedule any build?')
    os.system('cls')
    richbarbs_mode = input('Do you want to mass farm rich barbs first (yes/no)?\n')
    os.system('cls')
    report_checking_mode = input('Do you want to check for reports (yes/no)?\n')
    os.system('cls')
    central_village_id = '5722' if (input('Enter central farming village (A or B)\n'))== 'A' else '5143'
    if scheduleBuild == 'yes':
        building = int(input('Enter the number of building you wish to upgrade selecting form the list below:\n\n1. Headquarters\n2. Barracks\n3. Stables\n4. Workshop\n5. Academy\n6. Smithy\n7. Rally Point\n8. Statue\n9. Market\n10. Timber Camp\n11. Clay Pit\n12. Iron Mine\n13. Farm\n14. Storage\n15. Hiding Place\n16. Wall\n\n'))
        build_level = int(input('Please enter a valid level you wish to upgrade to:\n\n'))
        hms = input('Time from now to execute build:\n\n').split(':')
        milliseconds = (int(hms[0]) * 60 * 60 + int(hms[1]) * 60 + int(hms[2]))*1000
      


#                               ******************************************************************   Script and Coords paths START   ******************************************************************
players_coords_path = str(Path(current_dir)) +'/playersCoords.txt'
checkIncomings_script_path = str(Path(current_dir)) +'/Incomings/incomingsDetails.js'
buildScheduler_script_path = str(Path(current_dir)) +'/utilities/buildScheduler - console.js'
villageChange_script_path = str(Path(current_dir)) +'/utilities/villageChanger/villageChangeShortcut.min.js'
richBarbs_path = str(Path(current_dir)) +'/richBarbs.txt'
blacklisted_path = str(Path(current_dir)) +'/blacklistedBarbs.txt'
#                               ******************************************************************   Script and Coords paths END   ******************************************************************

if DEBUGGING == True:
    default_coords_path = str(Path(current_dir)) + ('/test.txt')
    central_village = '530|444'
else:
    default_coords_path = str(Path(current_dir)) + ('/defaultCoords_88_r15.txt' if coordSize == 'S' else '/defaultCoords_300_r40.txt')
    central_village = '530|444' if central_village_id == '5722' else '527|437'
        


captcha_log_path = str(Path(current_dir)) +'/captcha_log.txt'


# Coordinates files
f = open(players_coords_path, 'r')
players_coords = f.read().split(', ')
f.close()
f = open(default_coords_path, 'r')
default_coords = f.read().split(', ')
f.close()
f = open(richBarbs_path, 'r')
richBarbs_coords = f.read().split(', ')
f.close()
f = open(blacklisted_path, 'r')
blacklisted_coords = f.read().split(', ')
f.close()

# Script files
f = open(checkIncomings_script_path, 'r')
checkIncomings_script = f.read()
f.close()
f = open(buildScheduler_script_path, 'r')
buildScheduler_script = f.read()
f.close()
f = open(villageChange_script_path, 'r')
villageChangeScript = f.read()
f.close()





def sortCoordinates(coordsArray):
    """
Create an array of sorted coordinates based on distance. 
An array of coordinates must be provided as the function's argument.
  """ 
    
    global central_village
    #initialize widgets
    widgets = ['Progress: ', pb.Percentage(), ' ',
              pb.Bar(marker=pb.RotatingMarker()), ' ', pb.ETA()]
    #initialize timer
    timer = pb.ProgressBar(widgets=widgets, maxval=len(coordsArray)).start()
    result = []
    for coord in coordsArray:
        target = str(coord)
        url = ('http://gr.twstats.com/gr56/ajax.php?mode=dcalc&o={}&t={}').format(central_village, target)
        r = requests.get(url)
        html_data = r.text
        soup = BeautifulSoup(html_data, 'html.parser')
        distance = float(soup.find('th', text='Πεδία').parent.find_next('tr').findChild().text.replace(',','.'))
        #Check if coordinates belong to a player
        html_data = requests.post('http://gr.twstats.com/gr56/index.php?page=rankings&mode=villages', data = {'page':'rankings', 'mode':'villages', 'x': str(target[:3]),'y': str(target[4:])}).text
        soup = BeautifulSoup(html_data, 'html.parser')
        owner = soup.select('.r1 > td:nth-child(3)')[0].get_text()
        if owner == 'Barbarian' and coord not in blacklisted_coords:
            result.append({'distance':distance, 'coordinates': coord})
            # print('Sorted coord ' + coord)
        #If they do, skip them.
        elif owner != 'Barbarian':
            print('Coords ' + coord +' were skipped because they belonged to a player.')
        else:
            print('\nCoords ' + coord + ' were skipped as they appear to be in black-listed barbarian villages, due to red reports.')
        timer.update(coordsArray.index(coord))


    f = sorted(result, key=lambda k: k['distance'])
    sorted_coords = ', '.join(c['coordinates'] for c in f) .split(', ')
    return sorted_coords
    timer.finish()

print('\n\nWelcome to FarmPy, an advanced Tribal Wars farming bot!\n')
print('Date: ' + str(datetime.datetime.now())[0:10] + '\nTime: ' + str(datetime.datetime.now())[11:19] )


print('\n\nSorting regular and players\'  coordinates...\n')
sorted_coords = sortCoordinates(default_coords)
print("\n\nSuccessfully sorted "+ str(len(default_coords))+" coordinates")

if richbarbs_mode == 'yes':
    print('\n\nSorting rich barbs\'  coordinates...\n')
    richBarbs_sorted_coords = sortCoordinates(richBarbs_coords)[35:]
    print("\n\nSuccessfully sorted "+ str(len(richBarbs_sorted_coords))+" coordinates")



driver = webdriver.Chrome()

driver.set_script_timeout(1200)

actions = ActionChains(driver)

print('\nOpening Chrome...')
driver.get("http://fyletikesmaxes.gr")


user = input('Enter your game username: \n')
pwd = getpass.getpass('Enter your game password: \n')
sms_mode = 1#int(input('Enter 1 to notify via SMS for CAPTCHA and halt program or 0 to just halt the program: \n'))
captcha_solve = 1#int(input('Select 1 to try and solve the CAPTCHA or 0 to just halt the program: \n'))
dbc_mode = 0#int(input('Select 1 to implement DBC solving method in case of image or 0 to just try checking the checkbox.))
captcha_username = 'alittlebyte'#input('Enter your DeathByCaptcha account username: \n')
captcha_password = '28041997Liakos' #getpass.getpass('Enter your DeathByCaptcha account password: \n')
interval = 2#int(input('Enter how much time to wait before starting again (in seconds, i.e. "60.0): \n'))
defaultLC = 5
if DEBUGGING == True:
    farmPlayers = 'no'
    startpoint = 0
else:
    farmPlayers = input('Do you want to farm players? (yes/no) \n')
    os.system('cls')
    startpoint = int(input("Enter the barbarian villages' coordinates' starting point (starting from 1): "))-1
    os.system('cls')
captcha_sms_counter = 0
incomings_sms_counter = 0
captchaStartpoint = 0
recorded_attacks = 0
lcVillages = 2 # int(input(How many farming (LC) villages do you have?))
defaultFarm_switch_counter = 0 # Switch only one time when not enough units
found_captcha = False # Currently unused. Initialized in case it is needed as a counter for captcha appearance.
recheck_reports = False # Gets activated (value of True) when a new report arrives during previous report execution or from emerging reports in non-premium accounts, where reports/page are of a certain number.
returnTimes = []


def sendSMS(smsBody):
    # Your Account Sid and Auth Token from twilio.com/console
    account_sid = 'ACd1dc76d78adcc4ec523a23bb007ea78f'
    auth_token = 'bc7b82fcc8287e26b0880c424a454dc8'
    client = Client(account_sid, auth_token)

    message = client.messages \
                    .create(
                        body=smsBody,
                        from_='+12267784225',
                        to='+306977173000'
                    )

    print('\nSuccessfully sent message with id: ' + message.sid)


def login():
    username = driver.find_element_by_id('user')
    driver.execute_script("arguments[0].setAttribute('value',"+"'"+user+"'"+")", username)

    password = driver.find_element_by_id('password')
    driver.execute_script("arguments[0].setAttribute('value',"+"'"+pwd+"'"+")", password)

    login_btn = driver.find_element_by_class_name('btn-login')
    login_btn.click()


#Sovle CAPTCHA
def solveCaptcha():
    print('\n Trying to solve CAPTCHA...')
    # Disconnect from game
    driver.find_element_by_xpath("//*[@id='linkContainer']/a[6]").click()
    # Open regular browser
    if(webbrowser.open('www.fyletikesmaxes.gr')):
        
        time.sleep(4)
        # Login
        pyautogui.moveTo(1424,412)
        pyautogui.click()
        time.sleep(6.0)
        # Click checkbox
        pyautogui.moveTo(random.randint(1119, 1139),random.randint(310, 329))
        pyautogui.click()

        time.sleep(3.0)


        if dbc_mode == 1:
            while True:
                pyautogui.hotkey('ctrl', 'shift', 'k')
                time.sleep(2.0)
                pyautogui.typewrite(":screenshot --selector '#ds_body > div:nth-child(15) > div:nth-child(4) > iframe:nth-child(1)' --filename captcha")
                print('\nScreenshot taken for solving.')
                pyautogui.press('enter')
                pyautogui.hotkey('ctrl', 'shift', 'k')

                ################## DBC IMPLEMENTATION START ###################

                client = deathbycaptcha.SocketClient(captcha_username, captcha_password)
                captcha_file = 'D:/DOWNLOADS/captcha.png'
                im = Image.open(captcha_file)
                rgb_im = im.convert('RGB')
                rgb_im.save('captcha.jpg')
                captcha_file = 'captcha.jpg'

                try:
                    balance = client.get_balance()
                    print(balance)
                    # Put your CAPTCHA file name or file-like object, and optional
                    # solving timeout (in seconds) here:
                    print('\nSending captcha to API for solving...')
                    captcha = client.decode(captcha_file, type=2)
                    while True:
                        if captcha:
                            # The CAPTCHA was solved; captcha["captcha"] item holds its
                            # numeric ID, and captcha["text"] item its list of "coordinates".
                            print ("CAPTCHA %s solved: %s" % (captcha["captcha"], captcha["text"]))
                            canvas_top = driver.execute_script("$('#ds_body > div:nth-child(15) > div:nth-child(4) > iframe:nth-child(1)').offset().top;")
                            canvas_left = driver.execute_script("$('#ds_body > div:nth-child(15) > div:nth-child(4) > iframe:nth-child(1)').offset().left;")
                            print()
                            for i in captcha['text']:
                                print(str(i[0]+canvas_left) + str(i[1]+canvas_top+95))
                                pyautogui.click((i[0]+canvas_left),(i[1]+canvas_top+95))
                                time.sleep(2.0)
                            driver.execute_script("$('recaptcha-verify-button').click()")
                            time.sleep(3.0)
                            try:
                                driver.find_element_by_css_selector('#ds_body > div:nth-child(15) > div:nth-child(4) > iframe:nth-child(1)')
                                # take screenshot of image
                                pyautogui.hotkey('ctrl', 'shift', 'k')
                                time.sleep(2.0)
                                pyautogui.typewrite(":screenshot --selector '#ds_body > div:nth-child(15) > div:nth-child(4) > iframe:nth-child(1)' --filename captcha_after")
                                print('\nScreenshot taken for error checking.')
                                pyautogui.press('enter')
                                pyautogui.hotkey('ctrl', 'shift', 'k')

                                # OCR - check image for error message
                                def errorCheck(image):
                                    img = Image.open(image)
                                    img = img.crop((9,513,393,547))
                                    img = img.resize((768,68), Image.ANTIALIAS)
                                    img.save('test.png')
                                    return pytesseract.image_to_string('test.png')
                                    # check if the CAPTCHA was incorrectly solved
                                result = errorCheck('captcha_after.png')
                                if((result == "Please select all matching images") or  (result == "Please try again")):
                                    client.report(captcha["captcha"])
                                    print('\nWrong captcha reported to API.')
                            except:
                                pass
                            break
                        else:
                            print('Solving captcha...')
                            pass
                except deathbycaptcha.AccessDeniedException:
                    # Access to DBC API denied, check your credentials and/or balance
                    print ("error: Access to DBC API denied, check your credentials and/or balance")

                #close browser
                pyautogui.moveTo(2540, 12)
                pyautogui.click()
                print('\nCaptcha was successfully solved at: ' + str(datetime.datetime.now())[:19] +'\n')

        # manual browser termination
        # pyautogui.moveTo(2540, 12)
        # pyautogui.click()

        # terminate only current tab using hotkey
        pyautogui.hotkey('ctrl', 'w')


################## DBC IMPLEMENTATION END ###################

# Check for CAPTCHA
def checkCaptcha():
    captcha_log = open(captcha_log_path, 'a')
    global captcha_sms_counter
    global found_captcha
    while True:
        try:
            # Found captcha
            if(driver.find_element_by_xpath("//*[text()='Επίλυση captcha']") or driver.find_element_by_xpath("//*[@id='popup_box_bot_protection']='Επίλυση captcha']")):
                print('\nCaptcha detected. If an alert is displayed, press OK to continue solving it...')
                captcha_log.write('Captcha detected: ' + str(datetime.datetime.now())[:19] +'\n')
                found_captcha = True

                # Captcha alert mode = 1
                if captcha_alert_mode == 'yes':
                    # If OK is pressed on alert message 
                    if win32api.MessageBox(0, 'Press OK to continue solving the captcha. Stop using your mouse and keyboard until the process has finished.', 'Captcha Detected', 0x00000030) == 1:
                        if captcha_solve == 1:
                            print('\nProgram halted until it is solved.')
                            while True:
                                solveCaptcha()
                                break
                            driver.refresh()
                            time.sleep(3.0)
                            try:
                                driver.find_element_by_xpath("//*[@id='logout']/div[3]/div[3]/div[10]/div[2]/div[1]/div/a").click()
                                time.sleep(3.0)
                                driver.execute_script("$('span.world_button_active').eq(0).click();")
                                time.sleep(3.0)
                            except:
                                driver.execute_script("$('span.world_button_active').eq(0).click();")
                                time.sleep(3.0)
                            return
                        if sms_mode == 1 and captcha_sms_counter == 0:
                            #Send SMS once to notify about found captcha
                            sendSMS(str(datetime.datetime.now())[:-7] +'\nCaptcha detected. Please login to solve it')
                            captcha_sms_counter = 1
                        time.sleep(10.0)

                # Captcha alert mode = 0
                if captcha_alert_mode == 'no':
                    if captcha_solve == 1:
                        print('\nProgram halted until it is solved.')
                        while True:
                            solveCaptcha()
                            break
                        driver.refresh()
                        time.sleep(3.0)
                        try:
                            driver.find_element_by_xpath("//*[@id='logout']/div[3]/div[3]/div[10]/div[2]/div[1]/div/a").click()
                            time.sleep(3.0)
                            driver.execute_script("$('span.world_button_active').eq(0).click();")
                            time.sleep(3.0)
                        except:
                            driver.execute_script("$('span.world_button_active').eq(0).click();")
                            time.sleep(3.0)
                        return
                    if sms_mode == 1 and captcha_sms_counter == 0:
                        #Send SMS once to notify about found captcha
                        sendSMS(str(datetime.datetime.now())[:-7] +'\nCaptcha detected. Please login to solve it')
                        captcha_sms_counter = 1
                    time.sleep(10.0)

        #Didn't find any captcha 
        except:
            break

def getRedReports():
    #checkCaptcha()
    report_coords = []
    print('\nChecking for red reports...')
    for i in range(0, 145, 12):
        driver.get("https://gr56.fyletikesmaxes.gr/game.php?village=5722&screen=report&mode=attack&from="+str(i))
        #checkCaptcha()
        length_red = int(driver.execute_script("return jQuery('img[src*=\"https://dsgr.innogamescdn.com/8.153/39901/graphic/dots/red.png\"]').length;"))
        length_redblue = int(driver.execute_script("return jQuery('img[src*=\"https://dsgr.innogamescdn.com/8.153/40020/graphic/dots/red_blue.png\"]').length;"))
        if length_red > 0:
            for i in range(1,length_red,1):
                coords = driver.execute_script("return jQuery('img[src*=\"https://dsgr.innogamescdn.com/8.153/39901/graphic/dots/red.png\"]')["+str(i)+"].closest('td').childNodes[7].innerText.match(/(?:.{3})[|](?:.{3})/g).toString()")
                report_coords.append(coords)
        if length_redblue > 0:
            for i in range(1,length_redblue,1):
                coords = driver.execute_script("return jQuery('img[src*=\"https://dsgr.innogamescdn.com/8.153/40020/graphic/dots/red_blue.png\"]')["+str(i)+"].closest('td').childNodes[5].innerText.match(/(?:.{3})[|](?:.{3})/g).toString()")
                report_coords.append(coords)
    return report_coords

def checkReports():
    global recheck_reports
    print('\nChecking for new reports...')
    # Check for incomings
    # try:
    #     incomings = driver.execute_script("return parseInt($('#incomings_amount').text());")
    #     if((incomings != recorded_attacks) and (incomings != 0)):
    #         checkIncomings()
    # except:
    #     pass
    try:
        driver.find_element_by_xpath("(//span[contains(@class, 'new_report_faded')])")
        print('No new reports yet...')

        # If url contains report, meaning if script is in report page raise exception,
        # forcing it to iterate through all of the reports again

        # if "report" in driver.current_url:
        #     raise NoSuchElementException
        # else:
        #     pass
    except NoSuchElementException:
        while True:
            row_position = 2 
            currentVillage_id = driver.execute_script("return currentVillage=window.location.search.match(/village=(.*\d)/)[1].slice(0,4);")
            driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+currentVillage_id+"&screen=report&mode=attack")
            rowsCount = len(driver.find_elements_by_xpath("//table[@id='report_list']/tbody/tr"))-2
            for i in range (rowsCount):
                report_row = driver.find_element_by_xpath("//table[@id='report_list']/tbody/tr["+str(row_position)+"]/td[2]")

                # If report is irrelevant, increment row_position by one
                if(("Χωριό βαρβάρων" not in report_row.text) and ("Χωριό με bonus" not in report_row.text)):
                    # Looping again through reports to check for new ones
                    if rowsCount > 1:
                        for i in range (rowsCount):
                            report_row = driver.find_element_by_xpath("//table[@id='report_list']/tbody/tr["+str(row_position)+"]/td[2]")
                            # If there are not any new reports, set recheck to False 
                            if "νέο" not in report_row.text:
                                recheck_reports = False
                            # If new report emerges set recheck to True, forcing a recheck and break loop
                            else:
                                recheck_reports = True
                                break
                        row_position += 1
                    else:
                        recheck_reports = False
                    continue
                    
                # If report is from barbarian or bonus village and not new (old)
                if "νέο" not in report_row.text and ("Χωριό βαρβάρων" in report_row.text or "Χωριό με bonus" in report_row.text):
                    report_id =  driver.find_element_by_css_selector("#report_list > tbody > tr:nth-child("+str(row_position)+") > td:nth-child(2) > span").get_attribute("data-id")
                    # Check report for deletion
                    driver.execute_script("$(\"input[name='id_"+report_id+"']\").click();")
                    # Delete reports
                    driver.execute_script("$(\"#content_value > table > tbody > tr > td:nth-child(2) > form > table:nth-child(2) > tbody > tr > td > input.btn.btn-cancel\").click();")
                    # Looping again through reports to check for new ones
                    for i in range (rowsCount):
                        report_row = driver.find_element_by_xpath("//table[@id='report_list']/tbody/tr["+str(row_position)+"]/td[2]")
                        # If there are not any new reports, set recheck to False 
                        if "νέο" not in report_row.text:
                            recheck_reports = False
                        # If new report emerges set recheck to True, forcing a recheck and break loop
                        else:
                            recheck_reports = True
                            break
                    continue
                
                
                # If new report and from barbarian or bonus village
                if "νέο" in report_row.text and ("Χωριό βαρβάρων" in report_row.text or "Χωριό με bonus" in report_row.text):
                    coords = driver.execute_script("return $(\"#report_list > tbody > tr:nth-child("+str(row_position)+") > td:nth-child(2) > span > span > a:nth-child(1) > span\").text().trim().match(/\(([^)]+)\)/g)[1].replace(/[{()}]/g, '')")
                    report_type = driver.find_element_by_css_selector("#report_list > tbody > tr:nth-child("+str(row_position)+") > td:nth-child(2) > img:nth-child(2)").get_attribute("src")
                    if("yellow" in report_type or "red" in report_type ):
                        #Add to black-listed
                        f = open(blacklisted_path, 'a+')
                        if coords not in blacklisted_coords:
                            f.write(', ' + coords)
                            f.close()
                            print('\nAdded village with coordinates ' + coords + ' to blacklistedBarbs.txt file due to losses in LC. Next time it will be ignored.')
                        report_id =  driver.find_element_by_css_selector("#report_list > tbody > tr:nth-child("+str(row_position)+") > td:nth-child(2) > span").get_attribute("data-id")
                        # select reports for deletion
                        driver.execute_script("$(\"input[name='id_"+report_id+"']\").click();")
                        # Delete reports
                        driver.execute_script("$(\"#content_value > table > tbody > tr > td:nth-child(2) > form > table:nth-child(2) > tbody > tr > td > input.btn.btn-cancel\").click();")
                        # Looping again through reports to check for new ones
                        for i in range (rowsCount):
                            report_row = driver.find_element_by_xpath("//table[@id='report_list']/tbody/tr["+str(row_position)+"]/td[2]")
                            # If there are not any new reports, set recheck to False 
                            if "νέο" not in report_row.text:
                                recheck_reports = False
                            # If new report emerges set recheck to True, forcing a recheck and break loop
                            else:
                                recheck_reports = True
                                break
                        continue

                    report_link = driver.find_element_by_xpath("//table[@id='report_list']/tbody/tr["+str(row_position)+"]/td[2]/span/span/a")
                    report_id =  driver.find_element_by_css_selector("#report_list > tbody > tr:nth-child("+str(row_position)+") > td:nth-child(2) > span").get_attribute("data-id")
                    

                    report_link.click()
                    time.sleep(2.0)

                    try:
                        wood = int(driver.find_element_by_xpath("//*[@id='attack_spy_resources']/tbody/tr[1]/td/span[1]").text.replace('.',''))
                        clay = int(driver.find_element_by_xpath("//*[@id='attack_spy_resources']/tbody/tr[1]/td/span[2]").text.replace('.',''))
                        iron = int(driver.find_element_by_xpath("//*[@id='attack_spy_resources']/tbody/tr[1]/td/span[3]").text.replace('.',''))
                        wood_mine = 0
                        clay_mine = 0
                        iron_mine = 0
                        total = wood + clay + iron
                        if(total >= 400):
                            switch_counter = 0
                            print('\nScouted ' + str(total) + ' resources in total.')
                            if(total > 6000): 
                                f = open(richBarbs_path, 'a+')
                                if coords not in f:
                                    f.write(', ' + coords )
                                    f.close()
                                    print('\nAdded village to richBarbs.txt file ! Next time it will get a higher priority.')
                            
                            while True:
                                currentVillage_id = driver.execute_script("return currentVillage=window.location.search.match(/village=(.*\d)/)[1].slice(0,4);")
                                if(cleanFarms(coords, total//80+1 if total<=20000 else 250, currentVillage_id)):
                                    print('Report with coords ' + str(coords) + ' successfully executed with ' + str(total//80+1) + ' LC.')
                                    driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+currentVillage_id+"&screen=report&mode=attack")

                                    driver.execute_script("$(\"input[name='id_"+report_id+"']\").click();")
                                    # Delete reports
                                    driver.execute_script("$(\"#content_value > table > tbody > tr > td:nth-child(2) > form > table:nth-child(2) > tbody > tr > td > input.btn.btn-cancel\").click();")
                                    switch_counter = 0
                                    # Looping again through reports to check for new ones
                                    for i in range (rowsCount):
                                        report_row = driver.find_element_by_xpath("//table[@id='report_list']/tbody/tr["+str(row_position)+"]/td[2]")
                                        # If there are not any new reports, set recheck to False 
                                        if "νέο" not in report_row.text:
                                            recheck_reports = False
                                        # If new report emerges set recheck to True, forcing a recheck and break loop
                                        else:
                                            recheck_reports = True
                                            break 
                                    break
                                else:
                                    print('Not enough units. Switching village...')

                                    # Append return times to array for comparison
                                    # for i in range(0,len(returnTimes)):
                                    #     if currentVillage_id not in returnTimes[i]: 
                                    #         returnTimes.append({currentVillage_id:checkReturnTime()})
                                    # print(returnTimes)
                                    if switch_counter <= lcVillages - 2:
                                        # Execute village changing script
                                        driver.execute_script(villageChangeScript)
                                        # Go to next farming village
                                        time.sleep(1.0)
                                        driver.execute_script("var evt = new KeyboardEvent('keydown', {'keyCode':68, 'which':68});document.dispatchEvent (evt);")
                                        switch_counter += 1
                                    else:
                                        
                                        # Returning to main village if no village has troops TODO: Check times and return to the one with fastest returning units
                                        driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+central_village_id+"&screen=place")
                                        
                                        returnTime = checkReturnTime() #TODO: if returnTime is undefined
                                        print("Not enough units. Retrying in " + str(returnTime) + " seconds...")
                                        for j in range(returnTime, 0, -1):
                                            print('Remaining seconds: ' + str(j))
                                            sys.stdout.flush()
                                            time.sleep(1)


                        else:
                            print('Scouted resources for ' + str(coords) + ' were below 400.')

                            driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+currentVillage_id+"&screen=report&mode=attack")               

                            driver.execute_script("$(\"input[name='id_"+report_id+"']\").click();")
                            # Delete reports
                            driver.execute_script("$(\"#content_value > table > tbody > tr > td:nth-child(2) > form > table:nth-child(2) > tbody > tr > td > input.btn.btn-cancel\").click();")

                            # Looping again through reports to check for new ones
                            for i in range (rowsCount):
                                report_row = driver.find_element_by_xpath("//table[@id='report_list']/tbody/tr["+str(2)+"]/td[2]")
                                # If there are not any new reports, set recheck to False 
                                if "νέο" not in report_row.text:
                                    recheck_reports = False
                                # If new report emerges set recheck to True, forcing a recheck and break loop
                                else:
                                    recheck_reports = True
                                    break                

                        
                            time.sleep(1.0)
                            driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+currentVillage_id+"&screen=report&mode=attack")
                    except NoSuchElementException:
                        print('No scouted resources for ' + str(coords) + '.')
                        driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+currentVillage_id+"&screen=report&mode=attack")               
                        # Check report for deletion
                        driver.execute_script("$(\"input[name='id_"+report_id+"']\").click();")
                        # Delete reports
                        driver.execute_script("$(\"#content_value > table > tbody > tr > td:nth-child(2) > form > table:nth-child(2) > tbody > tr > td > input.btn.btn-cancel\").click();")
                        driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+currentVillage_id+"&screen=report&mode=attack")
                        
                        # Looping again through reports to check for new ones
                        for i in range (rowsCount):
                            report_row = driver.find_element_by_xpath("//table[@id='report_list']/tbody/tr["+str(2)+"]/td[2]")
                            # If there are not any new reports, set recheck to False 
                            if "νέο" not in report_row.text:
                                recheck_reports = False
                            # If new report emerges set recheck to True, forcing a recheck and break loop
                            else:
                                recheck_reports = True
                                break
            # If recheck is True continue loop
            if recheck_reports == True:
                print('\nRechecking reports...')
            # Else break
            else:
                break
           
                
def checkReturnTime():
    """
  Returns time (int) of the soonest arriving farm attack.
  """
    returnTime = driver.execute_script("return jQuery('img[src*=\"return\"]').closest('tr').children().eq(2)[0].innerText;")
    hours = returnTime[0]
    minutes = returnTime[2:4] if returnTime[2] != 0 else returnTime[3]
    seconds = returnTime[5:7] if returnTime[5] != 0 else returnTime[6]
    return int(hours)*3600 + int(minutes)*60 + int(seconds)

# Loop over array of coords farm function
def defaultFarm():

    # Check for incomings
    # try:
    #     incomings = driver.execute_script("return parseInt($('#incomings_amount').text());")
    #     if((incomings != recorded_attacks) and (incomings != 0)):
    #         checkIncomings()
    # except:
    #     pass

    global captchaStartpoint
    global startpoint #Coordinate startpoint
    global lcVillages
    global defaultFarm_switch_counter
    c = startpoint #Independent counter changing each time, used for printing attack number
            

    # Looping through coordinates
    for coord in range(startpoint, len(sorted_coords),1):
        currentVillage_id = driver.execute_script("return currentVillage=window.location.search.match(/village=(.*\d)/)[1].slice(0,4);")
        if report_checking_mode == 'yes':
            checkReports()
        driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+currentVillage_id+"&screen=place")
        time.sleep(random.uniform(1,2))

        unit_input = driver.find_element_by_id('unit_input_light')
        spy_input = driver.find_element_by_id('unit_input_spy')
        spy_count = int(driver.find_element_by_xpath("//*[@id='units_entry_all_spy']").text.replace('(','').replace(')',''))
        coords_input = driver.find_element_by_xpath("//*[@id='place_target']/input")
        attack_btn = driver.find_element_by_xpath("//*[@id='target_attack']")
        unit_input.clear()
        spy_input.clear()
        coords_input.clear()

        time.sleep(random.uniform(1,2))
        spy_input.send_keys('1' if spy_count != 0 else '0')

        unit = defaultLC

        time.sleep(random.uniform(1,2))
        unit_input.send_keys(unit)

        time.sleep(random.uniform(1,2))

        #Sending each keystroke separately
        for char in sorted_coords[coord]:
            coords_input.send_keys(char)
            time.sleep(random.uniform(0.03,0.08)) #random fp number 0.03-0.08 | delay between each keystroke

        # For debugging purposes
        # if DEBUGGING == True:
        #     driver.execute_script("$('#content_value').html('<h2>Επίλυση captcha</h2>')")
        #     raise NoSuchElementException

        attack_btn.click()
        time.sleep(random.uniform(0,1))

        # Try to execute attack
        try:
            #If last coordinate -> Send attack and wait x seconds before starting again
            if( coord == len(sorted_coords)-1):
                attackConfirm = driver.find_element_by_xpath("//*[@id='troop_confirm_go']")
                attackConfirm.click()
                time.sleep(random.uniform(2,3))
                print('Sent attack number '+ str(c+1) +' to ' + sorted_coords[coord] + ' at: ' + str(datetime.datetime.now())[11:19])
                c += 1
                startpoint = 0
                captchaStartpoint = 0
                defaultFarm_switch_counter = 0 # Reset switch counter
                print('Loop ended. Waiting '+str(interval)+ ' seconds before starting again...\n')
                for i in range(interval, 0, -1):
                    print('\r')
                    print('Remaining seconds: ' + str(i),  flush=True)
                    time.sleep(1)

            #Else send attack and increment
            else:
                #checkCaptcha()
                attackConfirm = driver.find_element_by_xpath("//*[@id='troop_confirm_go']")
                attackConfirm.click()
                time.sleep(random.uniform(2,3))
                print('Sent attack number '+ str(c+1) +' to ' + sorted_coords[coord] + ' at: ' + str(datetime.datetime.now())[11:19])
                c += 1
                captchaStartpoint += 1
                defaultFarm_switch_counter = 0 # Reset switch counter
        # If error ( probably due to not having enough units) switch village
        except NoSuchElementException:
            if defaultFarm_switch_counter <= lcVillages - 2:
                # Execute village changing script
                driver.execute_script(villageChangeScript)
                # Go to next farming village
                time.sleep(1.0)
                driver.execute_script("var evt = new KeyboardEvent('keydown', {'keyCode':68, 'which':68});document.dispatchEvent (evt);")
                defaultFarm_switch_counter += 1
            else:
                # Try to find return times
                try:
                    # Returning to main village if no village has troops TODO: Check times and return to the one with fastest returning units
                    driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+central_village_id+"&screen=place")
                    returnTime = checkReturnTime() #TODO: if returnTime is undefined
                    print("Not enough units. Retrying in " + str(returnTime) + " seconds...")
                    for j in range(returnTime, 0, -1):
                        print('Remaining seconds: ' + str(j))
                        sys.stdout.flush()
                        time.sleep(1)
                except:
                    # Execute village changing script
                    driver.execute_script(villageChangeScript)
                    # Go to next farming village
                    time.sleep(1.0)
                    driver.execute_script("var evt = new KeyboardEvent('keydown', {'keyCode':68, 'which':68});document.dispatchEvent (evt);")
                    defaultFarm_switch_counter += 1

            startpoint = coord
            break


# Specific coords farm function
def cleanFarms(coords, units, village_id):
    """
  Takes 2 arguments: Coordinates to farm and LC number to send. If successful returns True, 
  else returns False.
  """

    driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+village_id+"&screen=place")

    unit_input = driver.find_element_by_id('unit_input_light')
    spy_input = driver.find_element_by_id('unit_input_spy')
    spy_count = int(driver.find_element_by_xpath("//*[@id='units_entry_all_spy']").text.replace('(','').replace(')',''))
    coords_input = driver.find_element_by_xpath("//*[@id='place_target']/input")
    attack_btn = driver.find_element_by_xpath("//*[@id='target_attack']")

    unit_input.clear()
    spy_input.clear()
    coords_input.clear()

    time.sleep(random.uniform(1,2))
    spy_input.send_keys('1' if spy_count != 0 else '0')

    time.sleep(random.uniform(1,2))
    unit_input.send_keys(units)

    for char in coords:
        coords_input.send_keys(char)
        time.sleep(random.uniform(0.03,0.08)) #random fp number 0.03-0.08 | delay between each keystroke

    time.sleep(random.uniform(1,2))

    #checkCaptcha()
    attack_btn.click()


    time.sleep(random.uniform(0,1))

    try:
        #checkCaptcha()
        attackConfirm = driver.find_element_by_xpath("//*[@id='troop_confirm_go']")
        attackConfirm.click()
        print('Sent attack to ' + coords)
        time.sleep(random.uniform(2,3))
        return True

    except NoSuchElementException:
             
        attack_btn = driver.find_element_by_xpath("//*[@id='target_attack']")
        unit_input = driver.find_element_by_id('unit_input_light')

        # Try to compromise first, by sending less units depending on the percentage of the original needed quantity, as well as the scale (different percentage for over 50 units, over 100 and over 250)
        available_units = driver.execute_script("return parseInt($('#units_entry_all_light').text().slice(1,3))")
        percentage = round((available_units/units)*100)
        if(units <= 50 and units > 20):
            if(percentage>=70):
                driver.find_element_by_id("units_entry_all_light").click()
                time.sleep(random.uniform(1,2))
                attack_btn.click()
                time.sleep(random.uniform(1,2))
        elif(units <= 150 and units > 50):
            if(percentage>=60):
                driver.find_element_by_id("units_entry_all_light").click()
                time.sleep(random.uniform(1,2))
                attack_btn.click()
                time.sleep(random.uniform(1,2))
        elif(units <= 250 and units > 150):
            if(percentage>=50):
                driver.find_element_by_id("units_entry_all_light").click()
                time.sleep(random.uniform(1,2))
                attack_btn.click()
                time.sleep(random.uniform(1,2))
        else:
            if(units > 250):
                driver.execute_script("$(\"#unit_input_light\").val('')")
                time.sleep(0.5)
                unit_input.send_keys(250)
                time.sleep(random.uniform(1,2))
                attack_btn.click()
                time.sleep(random.uniform(1,2))
        
        try:
            attackConfirm = driver.find_element_by_xpath("//*[@id='troop_confirm_go']")
            attackConfirm.click()
            print('Sent attack to ' + coords)
            time.sleep(random.uniform(2,3))
            return True
        except:
            #returnTime = checkReturnTime() #TODO: if returnTime is undefined
            print("Switching villages...")
            return False


def playersFarm():
    reds = getRedReports()
    global captcha_sms_counter
    if farmPlayers == 'yes':
        units = defaultLC
        for i in range(0,len(players_coords)):
            if(reds != None):
                if(players_coords[i] in reds):
                    print('You have one red report on ' + players_coords[i] + ' !!\n\nAttack was skipped.\n Current time: ' + str(datetime.datetime.now())[11:19])
            if(players_coords[i]=='532|433'):
                units = 75
            elif(players_coords[i]=='535|438'):
                units = 35
            elif(players_coords[i]=='525|434'):
                units = 25
            elif(players_coords[i]=='520|435'):
                units = 20
            elif(players_coords[i]=='532|441'):
                units = 35
            captcha_sms_counter = 0
            coords = players_coords[i]
            cleanFarms(coords, units, village1_id)



def checkIncomings():
    for village in villages:
        driver.get("https://gr56.fyletikesmaxes.gr/game.php?village="+village+"&screen=overview")

        global incomings_sms_counter
        global recorded_attacks

        #attacks = driver.execute_script("return parseInt($('#incomings_amount').text());")

        try:
            incomings_length = driver.execute_script("return $('tr.command-row.no_ignored_command').length")
            incomings_details = []
            print('Checking for incoming attacks...')
            for i in range(0,incomings_length):
                tag = driver.find_element_by_css_selector("#commands_incomings > form > table > tbody > tr.command-row.no_ignored_command > td:nth-child("+str(i+1)+") > span > span > a > span.quickedit-label")
                tag.click()
                attacker = driver.find_element_by_xpath("//*[@id='content_value']/table/tbody/tr[2]/td[3]/a").text
                origin_village = driver.find_element_by_xpath("//*[@id='content_value']/table/tbody/tr[3]/td[2]/span/a[1]").text
                target_village = driver.find_element_by_xpath("//*[@id='content_value']/table/tbody/tr[5]/td[2]/span/a[1]").text
                arrival_time = driver.find_element_by_xpath("//*[@id='content_value']/table/tbody/tr[7]/td[2]").text
                incomings_details.append({'time detected':str(datetime.datetime.now())[:19], 'attacker' : attacker, 'origin' : origin_village, 'target' : target_village, 'arrives in' : arrival_time})
                driver.back()

            # Premium# incomings_details = driver.execute_script(checkIncomings_script)

            f = open("incomings_"+str(datetime.datetime.now())[:10]+".txt","a")
            for i in range(0,len(incomings_details)):
                if incomings_length >= 1 and incomings_length != recorded_attacks:
                    incomings_sms_counter = 1
                    recorded_attacks += 1
                    f.write('\n**************NEW RECORDING**************\nIncoming attacks: ' + str(incomings_length) + '\n\n' + 'Time detected: ' + incomings_details[i]['time detected'] + '\n'
                    + 'Attacker: ' + incomings_details[i]['attacker'] + '\n' + 'Origin: ' + incomings_details[i]['origin'] + '\n' + 'Target: ' + incomings_details[i]['target'] + '\n'
                    + 'Arrives in: ' + incomings_details[i]['arrives in'] +'\n\n')
                    print('Successfully recorded attacks. Please check incoming attacks log for more details.')
                    if incomings_sms_counter == 0:
                        sendSMS('You have ' + str(incomings_length+1) + ' incoming attacks! For details please see txt file.')
                        print('Successfully recorded attacks. Please check incoming attacks log for more details.')
            f.close()
        except:
            pass

def identifyAttack(source, target):
    source = str(source)
    target = str(target)
    url = ('http://gr.twstats.com/gr56/ajax.php?mode=dcalc&o={}&t={}').format(source, target)
    import requests
    from bs4 import BeautifulSoup
    from collections import OrderedDict
    from pprint import pprint
    #r = requests.get('http://gr.twstats.com/gr56/ajax.php?mode=dcalc&o=530|444&t=500|500')
    r = requests.get(url)
    html_data = r.text
    soup = BeautifulSoup(html_data, 'lxml')

    troops = OrderedDict()
    for th, td in zip(soup.select('th')[1:], soup.select('td')[1:]):
        td[th.text.strip()] = td.text.strip().splitlines()


    print(min(troops, key=lambda x:abs(x-18)))

    pprint(d.keys())

# identifyAttack(530|444, 500|500)

def build(interval):
    timer = threading.Timer(5.0, build)
    timer.start() #time.stop() to end timer
    # Open new tab
    driver.execute_script("window.open('https://gr56.fyletikesmaxes.gr/game.php?village="+village1_id+"&screen=overview');")
    # Switch to new tab
    actions.send_keys('v')
    actions.perform()
    checkIncomings()
    driver.close()
    driver.switch_to.window(driver.window_handles[0])

###################################################################################################

login()

print('Selecting world...')

time.sleep (random.uniform(2,3))

driver.find_element_by_css_selector("span.world_button_active").click()

print("Successfully logged in!")

actions.send_keys('v')
actions.perform()


################## Captcha insertion / for debugging purposes #####################
## driver.execute_script("$('#content_value').html('<h2>Επίλυση captcha</h2>')") ##
###################################################################################
 

time.sleep(random.uniform(1,2))



# driver.get('https://gr56.fyletikesmaxes.gr/game.php?screen=overview_villages')
# rows = driver.find_elements_by_xpath("//*[@id='production_table']/tbody/tr")
# for village in range(len(rows)-1):
#   village = driver.find_elements_by_xpath("//*[@id='production_table']/tbody/tr["+str(village+2)+"]/td[1]/span/span/a[1]")
# village1_id = re.search('village=(.*)&screen', driver.current_url).group(1)
# village2_id = re.search('village=(.*)&screen', driver.current_url).group(1)

# Farming villages
village1_id = '5722'
village2_id = '5143'

# All villages
villages = ['5722', '5703', '4686', '5143', '5470']






def main():
    if(build in globals() or build in locals()):
        driver.execute_script(buildScheduler_script, str(building), str(build_level), str(milliseconds))
    global startpoint
    global captchaStartpoint
    global found_captcha
    while True:
        print('Script started at: '  + str(datetime.datetime.now())[:-7])
        print('Startpoint: ' + str(startpoint+1))

        if found_captcha == True:
            actions.send_keys('v')
            actions.perform()
            found_captcha = False

        # Try to execute checkIncomings(), playersFarm() -if set- and defaultFarm() functions. If for any reason something fails, then it is assumed that a CAPTCHA 
        # has been detected and a checkCaptcha() function is executed. 

        # WARNING: COMMENT OUT THE FOLLOWING SECTION, AS ANY ERRORS DURING PRODUCTION WILL BE CATCHED BY THE CAPTCHA CHECK 
        # AND YOU WILL EITHER ENTER AN ENDLESS LOOP, WITH NO ERROR DETECTION OR SKIP PIECES OF CODE DUE TO ERROR HANDLING.
        #  DISABLE TO SEE ERRORS!!!
        
        if DEBUGGING == True:
            if report_checking_mode == 'yes':
                checkReports()  
            if farmPlayers == 'yes':
                playersFarm()
            if richbarbs_mode == 'yes':
                for coord in richBarbs_sorted_coords:
                    cleanFarms(coord, 50, '5722')
            defaultFarm()
        else:
            try:       
                if report_checking_mode == 'yes':
                    checkReports()        
                if farmPlayers == 'yes':
                    playersFarm()
                if richbarbs_mode == 'yes':
                    for coord in richBarbs_sorted_coords:
                        cleanFarms(coord, 50, '5722')
                defaultFarm()
            except:
                checkCaptcha()
                startpoint = captchaStartpoint


main()
