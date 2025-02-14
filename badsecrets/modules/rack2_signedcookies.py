import re
import hmac
import base64
import binascii
from badsecrets.base import BadsecretsBase

class RackSignedCookies(BadsecretsBase):

    identify_regex = re.compile(r"^BAh[\.a-zA-z-0-9\%=]{32,}--[\.a-zA-z-0-9%=]{16,}$")
    description = {"product": "Rack 2.x Signed Cookie", "secret": "Rack 2.x secret key", "severity": "HIGH"}

    def carve_regex(self):
        return re.compile(r"session=(BAh[\.a-zA-z-0-9\%=]{32,}--[\.a-zA-z-0-9%=]{16,})")

    def rack2(self, rack_cookie, secret_key):
        try:
            # Split the cookie into data and signature
            data, signature = rack_cookie.rsplit("--", 1)

            # Create the HMAC using the secret key
            h = hmac.new(secret_key.encode(), data.encode(), digestmod="sha1")

            # Verify the signature
            if h.hexdigest() != signature:
                return None

            # Decode the data from base64
            decoded_data = base64.b64decode(data)

            # Check for Ruby Marshal header
            if decoded_data.startswith(b"\x04\x08"):
                return {"Confirmed Ruby Serialized Object": True, "hash_algorithm": "SHA1"}
            else:
                return {"Confirmed Ruby Serialized Object": False, "hash_algorithm": "SHA1"}

        except (binascii.Error, ValueError, IndexError):
            return None

    def check_secret(self, rack_cookie):
        if not self.identify(rack_cookie):
            return None
        for l in self.load_resources(
            ["rails_secret_key_base.txt", "top_100000_passwords.txt", "rack_secret_keys.txt"]
        ):
            secret_key_base = l.rstrip()
            r = self.rack2(rack_cookie, secret_key_base)
            if r:
                return {"secret": secret_key_base, "details": r}

        return None

    def get_hashcat_commands(self, rack_cookie, *args):
        return [
            {
                "command": f"hashcat -m 18500 -a 0 {rack_cookie} <dictionary_file>",
                "description": "Rack 2.x Signed Cookie",
                "severity": "HIGH",
            }
        ]
