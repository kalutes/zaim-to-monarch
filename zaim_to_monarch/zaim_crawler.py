import calendar
import datetime
import time

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class ZaimCrawler:
    def __init__(self, user_id, password):
        options = ChromeOptions()

        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--headless")

        self.driver = Chrome(options=options)

        self.driver.set_window_size(480, 270)

        print("Start Chrome Driver.")
        print("Login to Zaim.")

        self.driver.get("https://zaim.net/user_session/new")

        WebDriverWait(self.driver, 30).until(
            EC.element_to_be_clickable((By.ID, "submit"))
        )

        self.driver.find_element(By.ID, "email").send_keys(user_id)
        self.driver.find_element(By.ID, "password").send_keys(password)
        self.driver.find_element(By.ID, "submit").submit()

        WebDriverWait(self.driver, 30).until(
            EC.presence_of_all_elements_located((By.ID, "payment_form"))
        )

        print("Login Success.")
        self.data = []
        self.current = 0

    def get_account_balances(self):
        account_balances = {}

        # First navigate to the the accounts overview page which lists the full account names.
        self.driver.get("https://zaim.net/accounts/")

        accounts_table = self.driver.find_element(
            by=By.TAG_NAME,
            value="table",
        )

        account_names = accounts_table.find_elements(by=By.TAG_NAME, value="td")

        for account_name in account_names:
            # Account name entries do not have a class tag.
            if not account_name.get_attribute("class"):
                account_balances[account_name.text] = 0

        # Now that the full account names have been set, get the account balances.
        self.driver.get("https://zaim.net/home")
        time.sleep(1)

        accounts = self.driver.find_elements(
            by=By.CLASS_NAME,
            value="account-name",
        )

        for account in accounts:
            # This element only contains a shortened version of the full account
            # name that was retrieved above.
            # We must match it to the correct entry.
            short_account_name = account.find_element(
                by=By.CLASS_NAME, value="name"
            ).text.replace(".", "")

            try:
                account_balance_element = account.find_element(
                    by=By.CLASS_NAME, value="value"
                )
            except NoSuchElementException:
                continue

            if len(account_balance_element.text) < 2:
                continue

            account_balance = int(account_balance_element.text[1:].replace(",", ""))

            for full_account_name in account_balances.keys():
                if full_account_name.startswith(short_account_name):
                    account_balances[full_account_name] = account_balance

        return account_balances

    def get_data(self, year, month):
        self.data = []
        day_len = calendar.monthrange(int(year), int(month))[1]
        year = str(year)
        month = str(month).zfill(2)
        print(f"Get Data of {year}/{month}.")
        self.driver.get(f"https://zaim.net/money?month={year}{month}")
        time.sleep(1)

        print(f"Found {day_len} days in {year}/{month}.")
        self.current = day_len

        while self._crawler(year):
            pass

        return reversed(self.data)

    def close(self):
        self.driver.close()

    def _crawler(self, year):
        try:
            table = self.driver.find_element(
                by=By.XPATH,
                value="//*[starts-with(@class, 'SearchResult-module__list___')]",
            )
        except:
            return False
        lines = table.find_elements(
            by=By.XPATH,
            value="//*[starts-with(@class, 'SearchResult-module__body___')]",
        )

        for line in lines:
            items = line.find_elements(by=By.TAG_NAME, value="div")

            item = {}
            item["id"] = (
                items[0]
                .find_element(by=By.TAG_NAME, value="i")
                .get_attribute("data-url")
                .split("/")[2]
            )

            flg_duplicate = next(
                (data["id"] for data in self.data if data["id"] == item["id"]), None
            )
            if flg_duplicate:
                continue

            item["count"] = (
                items[1]
                .find_element(by=By.TAG_NAME, value="i")
                .get_attribute("title")
                .split("（")[0]
            )
            date = items[2].text.split("（")[0]
            item["date"] = datetime.datetime.strptime(f"{year}年{date}", "%Y年%m月%d日")
            item["category"] = (
                items[3]
                .find_element(by=By.TAG_NAME, value="span")
                .get_attribute("data-title")
            )
            item["genre"] = items[3].find_elements(by=By.TAG_NAME, value="span")[1].text
            item["amount"] = int(
                items[4]
                .find_element(by=By.TAG_NAME, value="span")
                .text.strip("¥")
                .replace(",", "")
            )
            m_from = items[5].find_elements(by=By.TAG_NAME, value="img")
            if len(m_from) != 0:
                item["from_account"] = m_from[0].get_attribute("data-title")
            m_to = items[6].find_elements(by=By.TAG_NAME, value="img")
            if len(m_to) != 0:
                item["to_account"] = m_to[0].get_attribute("data-title")
            item["type"] = (
                "transfer"
                if "from_account" in item and "to_account" in item
                else (
                    "payment"
                    if "from_account" in item
                    else "income" if "to_account" in item else None
                )
            )
            item["place"] = items[7].find_element(by=By.TAG_NAME, value="span").text
            item["name"] = items[8].find_element(by=By.TAG_NAME, value="span").text
            item["comment"] = items[9].find_element(by=By.TAG_NAME, value="span").text
            self.data.append(item)

        current_id = (
            lines[0]
            .find_elements(by=By.TAG_NAME, value="div")[0]
            .find_element(by=By.TAG_NAME, value="i")
            .get_attribute("data-url")
            .split("/")[2]
        )
        self.driver.execute_script(
            "arguments[0].scrollIntoView(true);", lines[len(lines) - 1]
        )
        time.sleep(0.1)
        next_id = (
            self.driver.find_element(
                by=By.XPATH,
                value="//*[starts-with(@class, 'SearchResult-module__list___')]",
            )
            .find_elements(
                by=By.XPATH,
                value="//*[starts-with(@class, 'SearchResult-module__body___')]",
            )[0]
            .find_elements(by=By.TAG_NAME, value="div")[0]
            .find_element(by=By.TAG_NAME, value="i")
            .get_attribute("data-url")
            .split("/")[2]
        )

        if current_id == next_id:
            return False
        else:
            return True
