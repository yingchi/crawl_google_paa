import pytest
import pandas as pd
import numpy as np
import google_paa
import sys


@pytest.mark.skipif(sys.version_info <= (3, 6, 0), reason="skip this one, irrelevant")
def test_saveToCSV():
    test_job_title = "software engineer/python"
    test_faqs = np.array(["rank content", "question content", "answer content"])
    actual_val = google_paa.saveToCSV(test_job_title, test_faqs)
    expected_val = pd.DataFrame.from_dict(
        {"rank": [test_faqs[0]], "question": [test_faqs[1]], "answer": [test_faqs[2]]}, orient="index"
    )
    print(expected_val)
    pd.testing.assert_frame_equal(actual_val, expected_val, check_names=False)
