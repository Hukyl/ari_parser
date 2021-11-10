from selenium.webdriver.common.by import By


class BasePageLocators:
    LANGUAGE_SELECT = (By.CSS_SELECTOR, 'select#lstIdioma')


class LoginPageLocators(BasePageLocators):
    EMAIL_INPUT = (By.NAME, 'txtUtilizador')
    PASSWORD_INPUT = (By.NAME, 'txtChaveAcesso')
    SUBMIT_BUTTON = (By.NAME, 'btnAutenticar')
    ERROR_SPAN = (By.CSS_SELECTOR, 'span#Mensagem')


class HomePageLocators(BasePageLocators):
    STATUS_SPAN = (By.CSS_SELECTOR, 'span#Conteudo_lblSituacao')
    STATUS_OUTER_TABLE = (
        By.CSS_SELECTOR, 
        '#Conteudo_UpdatePanel1 > div > div.divConteudo > table'
    )
    CALENDAR_BUTTON = (
        By.CSS_SELECTOR, 'input#Conteudo_btnAgendamento'
    )
    APPLICANTS_BUTTON = (By.CSS_SELECTOR, '#Conteudo_btnAF')


class ApplicantsPageLocators(BasePageLocators):
    TABLE = (By.CSS_SELECTOR, 'table#Conteudo_dg > tbody')
    APPLICANT_CALENDAR_BUTTON = (
        By.CSS_SELECTOR, '#Conteudo_btnAgendamento'
    )
    APPLICANT_STATUS_SPAN = (By.CSS_SELECTOR, "span#Conteudo_txtSituacao")


class AppointmentPageLocators(BasePageLocators):
    REFRESH_BUTTON = (By.CSS_SELECTOR, "#Conteudo_btnNovo")
    MATTER_SELECT = (By.CSS_SELECTOR, '#Conteudo_lstAAG')
    BRANCH_SELECT = (By.CSS_SELECTOR, '#Conteudo_lstUNOR')
    DATE_SELECT = (By.CSS_SELECTOR, 'select#Conteudo_lstAgendamentoMes')
    DAY_SELECT = (By.CSS_SELECTOR, 'select#Conteudo_lstAgendamentoDia')
    TIME_SELECT = (By.CSS_SELECTOR, 'select#Conteudo_lstAgendamentoHora')
    SUBMIT_BUTTON = (By.CSS_SELECTOR, 'input#Conteudo_btnConfirmar')
