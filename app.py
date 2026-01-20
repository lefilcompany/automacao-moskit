import time
import pandas as pd
from flask import Flask, render_template, request, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

MOSKIT_URL = "https://app.moskitcrm.com/deal/"
MOSKIT_EMAIL = "marketing@moradadapaz.com.br"
MOSKIT_PASSWORD = "GrupoGM_MKT_1948#"
SEARCH_BUTTON_ID = "search-button"
NO_RESULTS_MARKERS = [
    "Nenhum resultado encontrado",
    "nenhum resultado",
    "sem resultados",
    "não encontramos",
    "nao encontramos",
    "no results",
    "nada encontrado",
]

app = Flask(__name__)

def start_driver(headless=False):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--start-maximized")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)

def login(driver):
    driver.get(MOSKIT_URL)
    wait = WebDriverWait(driver, 25)

    try:
        email_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[autocomplete='username']")
            )
        )
        pass_input = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "input[type='password'], input[name='password'], input[autocomplete='current-password']")
            )
        )

        email_input.clear()
        email_input.send_keys(MOSKIT_EMAIL)
        pass_input.clear()
        pass_input.send_keys(MOSKIT_PASSWORD)
        pass_input.send_keys(Keys.ENTER)

        wait.until(EC.presence_of_element_located((By.ID, SEARCH_BUTTON_ID)))

    except Exception:
        print("Login automático não encontrado (SSO/fluxo diferente). Faça login manualmente.")
        input("Depois do login, aperte Enter aqui para continuar...")
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, SEARCH_BUTTON_ID)))

def open_search(driver):
    wait = WebDriverWait(driver, 20)
    btn = wait.until(EC.element_to_be_clickable((By.ID, SEARCH_BUTTON_ID)))
    btn.click()

def get_search_input(driver):
    wait = WebDriverWait(driver, 20)
    return wait.until(
        EC.visibility_of_element_located(
            (
                By.CSS_SELECTOR,
                "input[type='search'], input[placeholder*='Buscar'], input[aria-label*='Buscar'], "
                ".c-search input, .search input, .modal input"
            )
        )
    )

def set_query(input_el, value: str):
    input_el.click()
    input_el.send_keys(Keys.CONTROL, "a")
    input_el.send_keys(Keys.BACKSPACE)
    input_el.send_keys(value)

def has_no_results(driver) -> bool:
    html = driver.page_source.lower()
    return any(m in html for m in NO_RESULTS_MARKERS)

def process_emails(emails):
    driver = start_driver(headless=False)
    not_found = []

    try:
        login(driver)
        open_search(driver)
        search_input = get_search_input(driver)

        for i, email in enumerate(emails, start=1):
            print(f"[{i}/{len(emails)}] Consultando: {email}")

            try:
                set_query(search_input, email)
                time.sleep(2)

                if has_no_results(driver):
                    print(f"  -> SEM retorno: {email}")
                    not_found.append(email)
                else:
                    print(f"  -> OK (teve retorno): {email}")

            except Exception as e:
                print(f"  -> ERRO ao consultar {email}: {e}")
                not_found.append(email)

        pd.DataFrame({"email_sem_retorno": not_found}).to_csv(
            "emails_sem_retorno.csv", index=False, encoding="utf-8-sig"
        )

        print("\nFinalizado.")
        print(f"Sem retorno: {len(not_found)}")
        print("Gerado: emails_sem_retorno.csv")

    finally:
        driver.quit()
    return "emails_sem_retorno.csv", not_found  # Retorna o arquivo e os e-mails não encontrados

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        email_list_str = request.form["emails"]
        if not email_list_str:
            return render_template("index.html", message="Por favor, insira uma lista de e-mails.")
        
        emails = email_list_str.splitlines()
        result_file, not_found_emails = process_emails(emails)
        return render_template("index.html", 
                               message="Consulta concluída!", 
                               not_found_emails=not_found_emails, 
                               result_file=result_file)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
