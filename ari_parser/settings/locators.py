from selenium.webdriver.common.by import By


class LoginPageLocators:
    EMAIL_INPUT = (By.NAME, 'txtUtilizador')
    PASSWORD_INPUT = (By.NAME, 'txtChaveAcesso')
    SUBMIT_BUTTON = (By.NAME, 'btnAuthenticar')


class HomePageLocators:
    STATUS_SPAN = (By.CSS_SELECTOR, 'span#Conteudo_lblSituacao')
