"""
pages/base_page.py – Base page object.

Provides shared WebDriver interaction helpers and explicit-wait utilities.
Every page object in this project inherits from BasePage so driver calls
stay in one place and are easy to swap out if the WebDriver API changes.
"""
from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class BasePage:
    """Thin, reusable wrapper around Selenium WebDriver."""

    DEFAULT_TIMEOUT: int = 15  # seconds

    def __init__(self, driver: WebDriver) -> None:
        self.driver = driver

    # ------------------------------------------------------------------
    # Waits
    # ------------------------------------------------------------------
    def wait_for(
        self, locator: tuple[str, str], timeout: int = DEFAULT_TIMEOUT
    ) -> WebElement:
        """Wait until the element is *visible* and return it."""
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(locator)
        )

    def wait_for_clickable(
        self, locator: tuple[str, str], timeout: int = DEFAULT_TIMEOUT
    ) -> WebElement:
        """Wait until the element is *clickable* and return it."""
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable(locator)
        )

    def wait_invisible(
        self, locator: tuple[str, str], timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        """Wait until the element is no longer visible/present."""
        return WebDriverWait(self.driver, timeout).until(
            EC.invisibility_of_element_located(locator)
        )

    def is_present(
        self, locator: tuple[str, str], timeout: int = 3
    ) -> bool:
        """Return True if the element appears within *timeout* seconds."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def click(self, locator: tuple[str, str]) -> None:
        """Wait for the element to be clickable, then click it."""
        self.wait_for_clickable(locator).click()

    def fill(self, locator: tuple[str, str], value: str) -> None:
        """Clear the input field and type *value* into it."""
        element = self.wait_for(locator)
        element.clear()
        element.send_keys(str(value))

    def text(self, locator: tuple[str, str]) -> str:
        """Return the visible text of the element, stripped of whitespace."""
        return self.wait_for(locator).text.strip()
