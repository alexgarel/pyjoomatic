from urllib.parse import urljoin, urlparse, parse_qs

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec


ec_presence = ec.presence_of_element_located


class AdminError(Exception):
    """Exception raised when we didn't find expected behaviour while using joomla admin
    """
    pass


marker = object()


def no_such_element_default(fn):
    """Decorator tu use a default when NoSuchElementException is raised.
    The default being passed as a keyword argument to normal function call.
    """
    def decorated(self, *args, **kwargs):
        default = kwargs.pop('default', marker)
        try:
            return fn(self, *args, **kwargs)
        except NoSuchElementException:
            if default is not marker:
                return default
            else:
                raise
    return decorated


def chord(ctrl_keys, key):
    """pressing multiple controlers and a key at the same time

    :param list ctrl_keys: controlers keys
    :param key: key to press
    """
    a = ActionChains(driver)
    if not isinstance(ctrl_keys, list):
        ctrl_keys = [ctrl_keys]
    for k in ctrl_keys:
        a = a.key_down(k)
    a = a.send_keys(key)
    for k in reversed(ctrl_keys):
        a = a.key_up(Keys.CONTROL)
    return a.perform()


def update_url_params(url, **kwargs):
    """make a new url using url but updating some parameters

    :param str url: url to modify
    :param kwargs: new parameters with their values

    :return str: the modified url
    """
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    params.update(kwargs)
    elements = list(parsed_url)
    elements[4] = urlencode(params)
    return urlunparse(elements)


class EltWrapper:
    """A wrapper around selenium elements to add some shortcuts
    """

    def __init__(self, elt=None):
        self.elt = elt

    @no_such_element_default
    def by_tag(self, name):
        return EltWrapper(self.elt.find_element_by_tag_name(name))

    @no_such_element_default
    def all_tag(self, name):
        return [EltWrapper(e) for e in self.elt.find_elements_by_tag_name(name)]

    @no_such_element_default
    def by_name(self, name):
        return EltWrapper(self.elt.find_element_by_name(name))

    @no_such_element_default
    def all_name(self, name):
        return [EltWrapper(e) for e in self.elt.find_elements_by_name(name)]

    @no_such_element_default
    def by_css(self, selector):
        return EltWrapper(self.elt.find_element_by_css_selector(selector))

    @no_such_element_default
    def all_css(self, selector):
        return [EltWrapper(e) for e in self.elt.find_elements_by_css_selector(selector)]

    @no_such_element_default
    def by_xpath(self, selector):
        return EltWrapper(self.elt.find_element_by_xpath(selector))

    @no_such_element_default
    def all_xpath(self, selector):
        return [EltWrapper(e) for e in self.elt.find_elements_by_xpath(selector)]

    @no_such_element_default
    def by_id(self, id_):
        return EltWrapper(self.elt.find_element_by_id(id_))

    # transparently wrap
    def __getattr__(self, name):
        return getattr(self.elt, name)


class Browser(EltWrapper):
    """The main browser
    """

    def __init__(self, base_url, elt=None):
        if elt is None:
            elt = webdriver.Chrome()
        super().__init__(elt)
        self.base_url = base_url

    def abs_url(self, relative):
        return urljoin(self.base_url, relative)

    def wait(self, timeout=10):
        return WebDriverWait(self.elt, timeout)


class JoomlaAdminParts:
    """A class to have access to joomla admin part of pages
    """

    def __init__(self, b):
        self.b = b

    @property
    def logout(self):
        return self.b.by_xpath("//a[contains(@href, 'task=logout')]")

    @property
    def subheader(self):
        return self.b.by_css("div.subhead")

    @property
    def menu_contents(self):
        return self.b.by_xpath(
            "//a[contains(@class, 'menu-article')]/ancestor::ul/preceding-sibling::a")

    @property
    def menu_components(self):
        return self.b.by_xpath(
            "//a[contains(@class, 'menu-tags')]/ancestor::ul/preceding-sibling::a")

    @property
    def menu_user(self):
        return self.b.by_xpath(
            "//a[./span[contains(@class, 'icon-user')]]")

    @property
    def menu_article(self):
        return self.b.by_css("a.menu-article")

    @property
    def menu_attachments(self):
        return self.b.by_css("a.menu-attachments")

    def jform_action(self, name):
        return self.b.by_xpath("//button[contains(@onclick, '{name}')]".format(name=name))

    def jaction_link(self, name):
        return self.b.by_xpath("//a[contains(@href, 'task={name}')]".format(name=name))

    @property
    def jform_error(self):
        return self.b.by_css(".alert-error", default=[])

    @property
    def jform_invalid_fields(self):
        """List field names in error
        """
        return self.b.by_xpath("//label[contains(@class, 'invalid')]/@for")


class JoomlaFormDriver:
    """An helper to deal with joomla forms and their peculiarities
    """

    def fill_input(self, fname, field, value):
        """fill a simple imput
        """
        field.clear()
        field.send_keys(value)
        
    def fill_select(self, fname, field, value):
        """helper to select a value, even if the field is rendered with a search box
        """
        option = field.by_xpath(".//option[@value='%s']" % value)
        if field.is_displayed():
            # click right option
            option.click()
        else:
            # get option text, note : can't use text, for it is hidden
            text = option.get_attribute("text")
            # find the search box
            selector = self.b.by_id("jform_%s_chzn" % fname)
            # click on its link
            selector.by_tag("a").click()
            # fillin text of option
            selector.by_tag("input").send_keys(text)
            results = selector.by_css(".chzn-results").all_tag("li")
            # assert only one
            assert len(results) == 1, (
                "Found %d results for %s for %s = %s" % (len(results), option.text, fname, value))
            # click it
            results[0].click()

    def fill_textarea(self, fname, field, value):
        """helper to fill a text, dealing with the rich editor (disabling it)
        """
        if not field.is_displayed():
            # test if it's a tinymce
            assert "mce_editable" in field.get_attribute("class"), (
                "field not visible and not a tinymce one")
            # click the toggle
            self.b.by_id("wf_editor_jform_%s_toggle" % fname).click()
            # wait for text area visibility
            self.b.wait().until(lambda d: field.is_displayed())
        # clean and fill
        field.clear()
        field.send_keys(value)

    def fill_field(self, name, value, jform=True):
        """Generic method to fill a field in a form, choosing the right method for that
        """
        fname = "jform[%s]" % name if jform else name
        field = self.b.by_name(fname)
        filler = getattr(self, "fill_" + field.tag_name)
        filler(name, field, value)


class JoomlaAdminDriver(JoomlaFormDriver):
    """An helper too automate browsing the joomla administrator
    """

    def __init__(self, base_url, web=None):
        """
        :param str base_url: url of the joomla site
        :param web: an eventual selenium browser, if none is provided a new one is spawned
        """
        self.b = Browser(base_url, web)
        self.jap = JoomlaAdminParts(self.b)

    def login(self, username, passwd):
        self.b.get(self.b.abs_url("/administrator"))
        self.b.by_name("username").send_keys(username)
        self.b.by_name("passwd").send_keys(passwd)
        self.b.by_css("button.btn-primary").click()
        # assert we are in by searching logout url
        assert self.jap.logout, "No logout, after login, so it may have went wrong"
        # todo : raise with error from joomla instead

    def logout(self):
        self.jap.menu_user.click()
        self.jap.logout.click()

    def open_articles(self):
        self.jap.menu_contents.click()
        self.jap.menu_article.click()

    def add_article(self, fields):
        """Add an article

        fields is a dict of fields name with their values.

        Text should be provided as html as articletext
        """
        self.open_articles()
        # add article button
        self.jap.jform_action('article.add').click()
        # fill fields
        for k, v in fields.items():
            # set according to field type
            self.fill_field(k, v)
        # hit save
        self.jap.jform_action('article.apply').click()
        if self.jap.jform_error:
            raise AdminError(self.jap.jform_error[0].textContent)
        # we hit save so our id is in the url
        parsed_url = urlparse(self.b.current_url)
        params = parse_qs(parsed_url.query)
        article_id = params["id"][0]
        # exit
        self.jap.jform_action("article.cancel").click()
        return article_id


    def modify_article(self, id, fields):
        """Modify an article - NOT WELL TESTED
        """
        self.open_articles()
        # we can't really search for article
        # get link of action article.edit
        edit_url = self.b.jaction_link("article.edit").get_attribute("href")
        # change id
        edit_url = update_url_params(edit_url, id=id)
        # go
        self.b.get(self.b.abs_url(edit_url))
        # fill fields
        for k, v in fields.items():
            # set according to field type
            self.fill_field(k, v)
        # hit save and close
        self.jap.jform_action('article.save').click()
        # verify no error
        if self.jap.jform_error:
            raise AdminError(self.jap.jform_error[0].textContent)
        return id

    def attachment_select_article(self, article_id, article_title):
        """on attachment form, select an article to attach to
        """
        # open article popup
        self.b.by_xpath("//a[contains(@href, 'function=jSelectArticle')]").click()
        # wait for popup and select
        popup_xpath = "//iframe[contains(@src, 'function=jSelectArticle')]"
        self.b.wait().until(ec_presence((By.XPATH, popup_xpath)))
        frame = self.b.by_xpath(popup_xpath)
        self.b.switch_to.frame(frame.elt)
        # find article id
        link_xpath = """//a[contains(@onclick, "jSelectArticle('%s'")][1]""" % int(article_id)
        try:
            link = self.b.by_xpath(link_xpath)
        except NoSuchElementException:
            # search title
            search_field = self.b.by_name("filter[search]")
            search_field.clear()
            search_field.send_keys(article_title)
            search_field.by_xpath("./following-sibling::button").click()
            # wait for link
            link = self.b.wait().until(ec_presence((By.XPATH, link_xpath)))
        # select article
        link.click()
        # wait for window to disapear
        self.b.wait().until_not(ec_presence((By.XPATH, popup_xpath)))

    def add_attachment(self, article_id, article_title, fields):
        """
        Add attachment to article
        :param fields:
            form fields values

            article id is set through parent_id
        """
        self.jap.menu_components.click()
        self.jap.menu_attachments.click()
        # new button
        self.jap.jform_action('attachment.add').click()
        # select article
        self.attachment_select_article(article_id, article_title)
        # fill fields
        for k, v in fields.items():
            # set according to field type
            self.fill_field(k, v, jform=False)
        # save, without closing to get id
        self.jap.jform_action('attachment.applyNew').click()
        if self.jap.jform_error:
            raise AdminError(self.jap.jform_error[0].textContent)
        # we hit save so our id is in the url
        parsed_url = urlparse(self.b.current_url)
        params = parse_qs(parsed_url.query)
        attachment_id = params["cid[]"][0]
        # exit
        self.jap.jform_action("attachment.cancel").click()
        return attachment_id
