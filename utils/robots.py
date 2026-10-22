import urllib.robotparser
from urllib.parse import urlparse

class RobotsChecker:
    def __init__(self, user_agent="*"):
        self.user_agent = user_agent
        self.parsers = {}

    def allowed(self, url: str) -> bool:
        domain = urlparse(url).netloc

        if domain not in self.parsers:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"https://{domain}/robots.txt")
            try:
                rp.read()
            except Exception:
                return True
            self.parsers[domain] = rp

        return self.parsers[domain].can_fetch(self.user_agent, url)