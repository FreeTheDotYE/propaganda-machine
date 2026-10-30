import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("discover_govye", Path(__file__).resolve().parents[1] / "scripts/discover_govye.py")
discovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discovery)

class GovernmentInventoryTests(unittest.TestCase):
    def test_monitor_import_includes_apex_www_and_parent_of_service(self):
        rows = [
            {"hostname": "shohadaa.gov.ye", "registrable_domain": "shohadaa.gov.ye"},
            {"hostname": "www.shohadaa.gov.ye", "registrable_domain": "shohadaa.gov.ye"},
            {"hostname": "mail.new.gov.ye", "registrable_domain": "new.gov.ye"},
            {"hostname": "example.com.ye", "registrable_domain": "example.com.ye"},
        ]
        with patch.object(discovery, "request_bytes", return_value="\n".join(map(json.dumps, rows)).encode()):
            hosts, errors = discovery.collect_ye_domains()
        self.assertFalse(errors)
        self.assertEqual(set(hosts), {"shohadaa.gov.ye", "www.shohadaa.gov.ye", "new.gov.ye"})
        self.assertEqual(hosts["shohadaa.gov.ye"], {"ye-domains"})

    def test_source_failure_is_reported(self):
        with patch.object(discovery, "request_bytes", side_effect=TimeoutError("timeout")):
            hosts, errors = discovery.collect_ye_domains()
        self.assertFalse(hosts)
        self.assertIn("ye-domains", errors[0])

    def test_empty_source_is_not_silent_success(self):
        with patch.object(discovery, "request_bytes", return_value=b""):
            hosts, errors = discovery.collect_ye_domains()
        self.assertFalse(hosts)
        self.assertTrue(errors)
