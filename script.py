from bs4 import BeautifulSoup
import json
import os
import hashlib
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc
import time

options = uc.ChromeOptions()
options.add_argument("--headless=new")
options.accept_insecure_certs = True
driver = uc.Chrome(option=options)


baseurl = "https://www.walmart.com/i/recipe-results?facet="
filename = "recipes_from_walmart.json"
tagtypes = {
    "meal": ["Breakfast", "Lunch", "Dinner", "Dessert"],
    "type": ["Main Dish", "Side Dish", "Snack"],
    "cuisine": ["American", "Asian", "European", "Latin American"],
    "ingredient": ["Beef", "Cheese", "Chicken", "Eggs", "Vegetables", "Fruit"],
}

if os.path.isfile(filename):
    savefile = open(filename)
    data = json.load(savefile)
else:
    data = {}


def edittag(name, edit_for="python"):
    if " " in name:
        if edit_for == "python":
            parts = name.split(" ")
            return parts[0] + parts[1]
        else:
            parts = name.split(" ")
            return parts[0] + "%20" + parts[1]
    else:
        return name


newrecipeurls = []


def get_recipe_urls_and_hash():
    for tagtype in tagtypes:
        for item in tagtypes[tagtype]:
            url = baseurl + tagtype + ":" + edittag(item, "url")
            while url:
                try:
                    print(f"getting urls from {url}")
                    driver.set_page_load_timeout(15)
                    driver.get(url)
                    page = driver.page_source
                    soup = BeautifulSoup(page, "html.parser")
                    results = soup.find_all(class_="flex w-50 w-25-l mb3 mb4-l ph2")
                    for result in results:
                        recipedetails = result.find(
                            class_="db-m dn no-underline flex flex-column h-100"
                        )
                        provider = recipedetails.find(
                            class_="mh3 f6 mh3-m f5-m mt3 dark-gray fw4 lh-solid lh-title-m"
                        ).text.strip()
                        title = recipedetails.find(
                            class_="w_kV33 w_LD4J w_mvVb f4 f3-m lh-title lh-copy-m"
                        ).text.strip()
                        url = recipedetails.get("href")

                        idhash = hashlib.md5(
                            f"{provider}+{title}".encode("utf-8")
                        ).hexdigest()
                        if idhash not in data:
                            data[idhash] = {"title": title, "url": url, "tags": [item]}
                        else:
                            if item not in data[idhash]["tags"]:
                                data[idhash]["tags"].append(item)
                    nextbutton = soup.find(
                        attrs={
                            "data-testid": "NextPage",
                            "class": "sans-serif ph1 pv2 w4 h4 border-box bg-white br-100 b--solid ba mh2-m db tc no-underline b--light-gray",
                        }
                    )
                    if nextbutton:
                        url = "https://www.walmart.com" + str(nextbutton.get("href"))
                    else:
                        url = ""
                except:
                    print(f"couldnt get urls fron {url}")
                    break
    for key in data:
        if data[key].get("complete") != True:
            newrecipeurls.append({"url": data[key]["url"], "hash": key})
    print(f"{len(newrecipeurls)} unique urls collected")


get_recipe_urls_and_hash()
baseurl = "https://www.walmart.com"

for item in newrecipeurls:
    
    try:
        print(f"scraping url: {baseurl+item['url']}")
        driver.set_page_load_timeout(15)
        driver.get(baseurl+item["url"])
        time.sleep(3)
        replacebuttons=driver.find_elements(by=By.XPATH,value= '//*[@id="maincontent"]/div/div[2]/div/div/div/div[2]/div/section/div/div/div/div[4]/button')
        for button in replacebuttons:
            button.click()
        time.sleep(3)
        page = driver.page_source
        soup = BeautifulSoup(page, "html.parser")

        imgdiv = soup.find(class_="w-100 w-two-thirds-m hero-pov")
        if imgdiv:
            data[item["hash"]]["img"] = imgdiv.find("img").get("src")
            
        # ratingdiv = soup.find(class_="ratings flex align-center")
        # if ratingdiv:
        #     data[item["hash"]]["rating"] = ratingdiv.find(
        #         class_="h3 rating-number"
        #     ).text.strip()
        # else:
        #     data[item["hash"]]["rating"] = "unrated"
        totaldiv = soup.find(class_="dn db-l fr pl0 pr3 pv2 w-third")
        data[item["hash"]]["totalcost"] = (
            "$"
            + soup.find(class_="flex justify-end justify-between-l w-100")
            .text.strip()
            .split("$")[1]
        )

        servinginfo = soup.find_all(class_="ma0 bold lh-title w-100 tl dark-gray")

        data[item["hash"]]["servingcost"] = servinginfo[0].text.strip()
        data[item["hash"]]["preptime"] = servinginfo[1].text.strip()
        data[item["hash"]]["cooktime"] = servinginfo[2].text.strip()
        data[item["hash"]]["description"] = soup.find(
            class_="ma0 f6 normal mt3 dark-gray"
        ).text.strip()

        data[item["hash"]]["ingredients"] = []
        results = soup.find(class_="fl w-100 pa3 w-two-thirds-l relative static-l z-1")
        ingredientlist = results.find_all("section")
        for ingsection in ingredientlist:
            ing=ingsection.find(class_="flex justify-between items-stretch items-center-m mt0-l")
            if ing:
                qty = ing.find(class_="flex items-center center f6 b")
                if qty:
                    qty=qty.text.strip()
                else:
                    qty="unavailable"
                desc = ing.find(class_="flex flex-row mt1 f6 gray normal").text.strip()
                ing_name = ing.find(class_="link dark-gray")
                if ing_name:
                    ing_name = ing_name.text.strip()
                    cost = ing.find(class_="w-100 f6 b dark-gray").text.strip()
                    specificcost = ing.find(class_="w-100 f7 gray").text.strip()
                    inglink=ing.find(class_="ml1 ml0-m w-100 f6 b")
                    itemid = inglink.find("a").get("href").split("/")[-1]
                else:
                    itemid = None
            else:
                continue
            replacementitems=ingsection.find(class_="pa0 bb b--near-white").find_all("li")
            replacementids=[]
            for listitem in replacementitems:
                replacementids.append(listitem.find("a").get("href").split("?")[0].split("/")[-1])

            data[item["hash"]]["ingredients"].append(
                {
                    "name": ing_name,
                    "quantity": qty,
                    "description": desc,
                    "cost": cost,
                    "specific_cost": specificcost,
                    "item_id":itemid,
                    "replacement_item_ids":replacementids
                }
            )
        data[item["hash"]]["numIngredients"] = str(len(data[item["hash"]]["ingredients"]))

        steplist = soup.find_all(class_="pb3-l pt2-l")

        data[item["hash"]]["tasks"] = []
        for i in steplist:
            title = i.find("h3").text.strip()
            instruction = i.find("p").text.strip()
            data[item["hash"]]["tasks"].append(
                {
                    "title": title,
                    "instruction": instruction
                }
            )
        data[item["hash"]]["complete"] = True

    except Exception as e:
        print(e)
        continue

with open(f"recipes_from_walmart.json", "w") as f:
    json.dump(data, f)
