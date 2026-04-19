import os

import pytest


NETWORK_CLASS_PREFIXES = (
    "tests/test_arxiv_network.py::TestArxivSearcherNetwork::",
    "tests/test_biorxiv.py::TestBioRxivSearcher::",
    "tests/test_crossref.py::TestCrossRefSearcher::",
    "tests/test_dblp.py::TestDBLPSearcher::",
    "tests/test_hal.py::TestHALSearcher::",
    "tests/test_iacr.py::TestIACRSearcher::",
    "tests/test_medrxiv.py::TestMedRxivSearcher::",
    "tests/test_openalex.py::TestOpenAlexSearcher::",
    "tests/test_pmc.py::TestPMCSearcher::",
    "tests/test_ssrn.py::TestSSRNSearcher::",
)

NETWORK_TESTS = {
    "tests/test_google_scholar.py::TestGoogleScholarSearcher::test_search",
    "tests/test_semantic.py::TestSemanticSearcher::test_search_basic",
    "tests/test_semantic.py::TestSemanticSearcher::test_search_empty_query",
    "tests/test_semantic.py::TestSemanticSearcher::test_search_max_results",
    "tests/test_semantic.py::TestSemanticSearcher::test_download_pdf_functionality",
    "tests/test_semantic.py::TestSemanticSearcher::test_read_paper_functionality",
    "tests/test_semantic.py::TestSemanticSearcher::test_get_paper_details",
    "tests/test_semantic.py::TestSemanticSearcher::test_search_with_fetch_details",
    "tests/test_semantic.py::TestSemanticSearcher::test_search_performance_comparison",
}


def pytest_addoption(parser):
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="run tests that require live network access",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "network: test requires live network access")
    os.environ["PYTEST_RUN_NETWORK"] = "1" if config.getoption("--run-network") else "0"


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-network"):
        return

    skip_network = pytest.mark.skip(reason="needs --run-network")

    for item in items:
        nodeid = item.nodeid
        is_network = nodeid in NETWORK_TESTS or any(
            nodeid.startswith(prefix) for prefix in NETWORK_CLASS_PREFIXES
        )
        if not is_network:
            continue
        item.add_marker("network")
        item.add_marker(skip_network)
